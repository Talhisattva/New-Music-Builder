from __future__ import annotations

import hashlib
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from new_music_builder.domain.models import AudioRunEvent, AudioRunResult, AudioWorkPlan, PlannedAudioWorkItem


def run_audio_export(
    work_plan: AudioWorkPlan,
    *,
    ffmpeg_path: str,
    cache_root: str | Path,
    output_root: str | Path,
    emit: Callable[[AudioRunEvent], None] | None = None,
) -> AudioRunResult:
    cache_dir = Path(cache_root).resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_dir = Path(output_root).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    result = AudioRunResult(output_path=str(output_dir))
    grouped_items = _group_items(work_plan)

    for (row_id, side), items in grouped_items:
        emit_side = _emit_wrapper(emit, row_id, side)
        emit_side("side_started", message=f"Starting {side}-Side")

        side_built_any = False
        for song_index, item in enumerate(items):
            emit_side(
                "song_started",
                song_index=song_index,
                track_number=item.track_number,
                display_label=item.display_label,
                percent=0,
                message=item.reason,
            )

            if item.action == "error":
                result.failed_song_count += 1
                error_message = f"{item.display_label}: {item.reason}"
                result.errors.append(error_message)
                emit_side(
                    "song_failed",
                    song_index=song_index,
                    track_number=item.track_number,
                    display_label=item.display_label,
                    message=item.reason,
                )
                continue

            target_path = Path(item.target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path = _cache_path_for_item(cache_dir, item)

            try:
                if item.action == "copy_ogg":
                    _copy_source_to_cache(Path(item.source_path), cache_path)
                    emit_side(
                        "song_progress",
                        song_index=song_index,
                        track_number=item.track_number,
                        display_label=item.display_label,
                        percent=100,
                        message="Copied source .ogg.",
                        size_text=_format_size_text(cache_path.stat().st_size),
                    )
                else:
                    _ensure_converted_ogg(
                        item,
                        cache_path,
                        ffmpeg_path=ffmpeg_path,
                        emit_progress=lambda percent, message: emit_side(
                            "song_progress",
                            song_index=song_index,
                            track_number=item.track_number,
                            display_label=item.display_label,
                            percent=percent,
                            message=message,
                            size_text=_format_size_text(cache_path.stat().st_size) if cache_path.exists() else "",
                        ),
                    )
                    result.converted_count += 1

                shutil.copy2(cache_path, target_path)
                size_text = _format_size_text(target_path.stat().st_size)
                result.built_song_count += 1
                side_built_any = True
                emit_side(
                    "song_succeeded",
                    song_index=song_index,
                    track_number=item.track_number,
                    display_label=item.display_label,
                    percent=100,
                    message="Exported song.",
                    size_text=size_text,
                )
            except Exception as exc:
                result.failed_song_count += 1
                error_message = f"{item.display_label}: {exc}"
                result.errors.append(error_message)
                emit_side(
                    "song_failed",
                    song_index=song_index,
                    track_number=item.track_number,
                    display_label=item.display_label,
                    percent=0,
                    message=str(exc),
                )

        if side_built_any:
            result.successful_sides.append((row_id, side))
        emit_side("side_completed", message="Side complete.")

    emit_final = emit or (lambda _event: None)
    emit_final(
        AudioRunEvent(
            kind="run_completed",
            row_id=0,
            side="A",
            message="Audio export run complete.",
        )
    )
    result.mod_size_text = _format_size_text(_directory_size_bytes(output_dir))
    return result


def _group_items(work_plan: AudioWorkPlan) -> list[tuple[tuple[int, str], list[PlannedAudioWorkItem]]]:
    grouped: list[tuple[tuple[int, str], list[PlannedAudioWorkItem]]] = []
    current_key: tuple[int, str] | None = None
    current_items: list[PlannedAudioWorkItem] = []
    for item in work_plan.items:
        key = (item.row_id, item.side)
        if current_key is None:
            current_key = key
        if key != current_key:
            grouped.append((current_key, current_items))
            current_key = key
            current_items = []
        current_items.append(item)
    if current_key is not None:
        grouped.append((current_key, current_items))
    return grouped


def _emit_wrapper(
    emit: Callable[[AudioRunEvent], None] | None,
    row_id: int,
    side: str,
) -> Callable[..., None]:
    if emit is None:
        return lambda *args, **kwargs: None

    def _wrapped(
        kind: str,
        *,
        song_index: int | None = None,
        track_number: int | None = None,
        display_label: str = "",
        percent: int = 0,
        message: str = "",
        size_text: str = "",
    ) -> None:
        emit(
            AudioRunEvent(
                kind=kind,  # type: ignore[arg-type]
                row_id=row_id,
                side=side,  # type: ignore[arg-type]
                song_index=song_index,
                track_number=track_number,
                display_label=display_label,
                percent=percent,
                message=message,
                size_text=size_text,
            )
        )

    return _wrapped


def _cache_path_for_item(cache_root: Path, item: PlannedAudioWorkItem) -> Path:
    source = Path(item.source_path)
    stat = source.stat()
    key = "|".join(
        (
            str(source.resolve()),
            str(stat.st_mtime_ns),
            str(stat.st_size),
            str(item.sample_rate),
        )
    )
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    safe_stem = _safe_file_stem(item.display_label or source.stem)
    return cache_root / f"{safe_stem}-{digest}.ogg"


def _safe_file_stem(value: str) -> str:
    cleaned = "".join(ch if ch not in '<>:"/\\|?*' else "_" for ch in value).strip()
    return cleaned or "track"


def _copy_source_to_cache(source_path: Path, cache_path: Path) -> None:
    if cache_path.exists():
        return
    shutil.copy2(source_path, cache_path)


def _ensure_converted_ogg(
    item: PlannedAudioWorkItem,
    cache_path: Path,
    *,
    ffmpeg_path: str,
    emit_progress: Callable[[int, str], None],
) -> None:
    if cache_path.exists():
        emit_progress(100, "Using cached conversion.")
        return

    duration_seconds = max(1, item.duration_seconds)
    cmd = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        item.source_path,
        "-vn",
        "-ar",
        str(item.sample_rate),
        "-c:a",
        "libvorbis",
        "-q:a",
        "5",
        "-progress",
        "pipe:1",
        "-nostats",
        str(cache_path),
    ]
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        universal_newlines=True,
        startupinfo=startup,
    )

    last_percent = 0
    try:
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key == "out_time_ms":
                percent = _percent_from_ffmpeg_time(value, duration_seconds)
                if percent > last_percent:
                    last_percent = percent
                    emit_progress(percent, "Converting song...")
            elif key == "progress" and value == "end":
                last_percent = 100
                emit_progress(100, "Conversion complete.")
        stderr_text = process.stderr.read() if process.stderr is not None else ""
        return_code = process.wait()
    finally:
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()

    if return_code != 0:
        detail = (stderr_text or "ffmpeg conversion failed").strip()
        raise RuntimeError(detail)
    emit_progress(100, "Conversion complete.")


def _percent_from_ffmpeg_time(out_time_ms_text: str, duration_seconds: int) -> int:
    try:
        out_time_ms = int(out_time_ms_text)
    except ValueError:
        return 0
    elapsed_seconds = out_time_ms / 1_000_000.0
    if duration_seconds <= 0:
        return 0
    bounded = max(0.0, min(1.0, elapsed_seconds / float(duration_seconds)))
    return min(100, max(0, int(round(bounded * 100))))


def _format_size_text(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def _directory_size_bytes(root: Path) -> int:
    total = 0
    if not root.exists():
        return total
    for path in root.rglob("*"):
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:
                continue
    return total
