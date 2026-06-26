from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

from new_music_builder.domain.models import AudioRunEvent, AudioRunResult, AudioWorkPlan, PlannedAudioWorkItem
from new_music_builder.services.audio_conversion import ensure_cached_ogg
from new_music_builder.services.audio_profile import compression_bucket_name, compression_profile_id
from new_music_builder.services.cancelable_file_copy import copy_file_with_cancel
from new_music_builder.services.export_cancellation import ExportAbortedError


def run_audio_export(
    work_plan: AudioWorkPlan,
    *,
    cache_root: str | Path,
    output_root: str | Path,
    emit: Callable[[AudioRunEvent], None] | None = None,
    cancel_requested: Callable[[], bool] | None = None,
) -> AudioRunResult:
    cache_parent_dir = Path(cache_root).resolve()
    cache_parent_dir.mkdir(parents=True, exist_ok=True)
    output_dir = Path(output_root).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    result = AudioRunResult(output_path=str(output_dir))
    grouped_items = _group_items(work_plan)

    for (row_id, side), items in grouped_items:
        _raise_if_cancelled(cancel_requested, result)
        emit_side = _emit_wrapper(emit, row_id, side)
        emit_side("side_started", message=f"Starting {side}-Side")

        side_built_any = False
        for song_index, item in enumerate(items):
            _raise_if_cancelled(cancel_requested, result)
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
            cache_path = _cache_path_for_item(cache_parent_dir, item)

            try:
                export_source_path = cache_path
                succeeded_cached_path = str(cache_path)
                if item.action == "copy_ogg":
                    export_source_path = Path(item.source_path)
                    succeeded_cached_path = ""
                else:
                    converted = ensure_cached_ogg(
                        item,
                        cache_path,
                        emit_progress=lambda percent, message: emit_side(
                            "song_progress",
                            song_index=song_index,
                            track_number=item.track_number,
                            display_label=item.display_label,
                            percent=percent,
                            message=message,
                            size_text=_format_size_text(cache_path.stat().st_size) if cache_path.exists() else "",
                        ),
                        cancel_requested=cancel_requested,
                    )
                    if converted:
                        result.converted_count += 1

                _raise_if_cancelled(cancel_requested, result)
                copy_file_with_cancel(
                    export_source_path,
                    target_path,
                    cancel_requested=cancel_requested,
                    emit_progress=lambda percent, message: emit_side(
                        "song_progress",
                        song_index=song_index,
                        track_number=item.track_number,
                        display_label=item.display_label,
                        percent=percent,
                        message=message,
                        size_text=_format_size_text(export_source_path.stat().st_size) if export_source_path.exists() else "",
                    ),
                    progress_message="Copying exported song...",
                )
                size_text = _format_size_text(target_path.stat().st_size)
                result.built_song_count += 1
                side_built_any = True
                emit_side(
                    "song_succeeded",
                    song_index=song_index,
                    track_number=item.track_number,
                    display_label=item.display_label,
                    cached_ogg_path=succeeded_cached_path,
                    percent=100,
                    message="Exported song.",
                    size_text=size_text,
                )
            except ExportAbortedError as exc:
                result.aborted = True
                result.abort_message = str(exc)
                result.fatal_error = str(exc)
                result.mod_size_text = _format_size_text(_directory_size_bytes(output_dir))
                return result
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


def _raise_if_cancelled(cancel_requested: Callable[[], bool] | None, result: AudioRunResult) -> None:
    if cancel_requested is not None and cancel_requested():
        result.aborted = True
        result.abort_message = "Build aborted by user."
        result.fatal_error = result.abort_message
        raise ExportAbortedError(result.abort_message)


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
        cached_ogg_path: str = "",
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
                cached_ogg_path=cached_ogg_path,
                percent=percent,
                message=message,
                size_text=size_text,
            )
        )

    return _wrapped


def _cache_path_for_item(cache_root: Path, item: PlannedAudioWorkItem) -> Path:
    source = Path(item.source_path)
    stat = source.stat()
    bucket_dir = cache_root / compression_bucket_name(item.sample_rate, item.compression_quality)
    key = "|".join(
        (
            str(source.resolve()),
            str(stat.st_mtime_ns),
            str(stat.st_size),
            str(item.sample_rate),
            compression_profile_id(item.compression_quality),
        )
    )
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    safe_stem = _safe_file_stem(item.display_label or source.stem)
    return bucket_dir / f"{safe_stem}-{digest}.ogg"


def _safe_file_stem(value: str) -> str:
    cleaned = "".join(ch if ch not in '<>:"/\\|?*' else "_" for ch in value).strip()
    return cleaned or "track"


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
