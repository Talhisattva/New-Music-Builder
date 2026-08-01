from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
import os
from pathlib import Path

from new_music_builder.domain.models import AudioRunEvent, AudioRunResult, AudioWorkPlan, PlannedAudioWorkItem
from new_music_builder.services.audio_cache_lookup import cache_path_for_work_item
from new_music_builder.services.audio_conversion import ensure_cached_ogg
from new_music_builder.services.cancelable_file_copy import copy_file_with_cancel
from new_music_builder.services.export_cancellation import ExportAbortedError


@dataclass(frozen=True, slots=True)
class _ItemContext:
    item: PlannedAudioWorkItem
    song_index: int
    cache_path: Path


@dataclass(frozen=True, slots=True)
class _TerminalItemResult:
    row_id: int
    side: str
    song_index: int
    track_number: int
    source_row_id: int
    source_track_index: int
    display_label: str
    terminal_kind: str
    cached_ogg_path: str = ""
    size_text: str = ""
    error_message: str = ""
    converted: bool = False


class _SideProgress:
    __slots__ = ("emit_side", "total_items", "completed_items", "built_any")

    def __init__(self, emit_side: Callable[..., None], total_items: int) -> None:
        self.emit_side = emit_side
        self.total_items = total_items
        self.completed_items = 0
        self.built_any = False


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
    side_progress = _prepare_side_progress(grouped_items, emit)
    convert_contexts: list[_ItemContext] = []

    for (row_id, side), items in grouped_items:
        _raise_if_cancelled(cancel_requested, result)
        for song_index, item in enumerate(items):
            _raise_if_cancelled(cancel_requested, result)
            context = _ItemContext(
                item=item,
                song_index=song_index,
                cache_path=cache_path_for_work_item(cache_parent_dir, item),
            )
            if item.action == "convert_to_ogg":
                convert_contexts.append(context)
                continue
            terminal = _export_single_item(
                context,
                cancel_requested=cancel_requested,
                emit_progress=None,
            )
            _record_terminal_result(result, side_progress, terminal)

    _run_parallel_conversions(
        convert_contexts,
        result=result,
        side_progress=side_progress,
        cancel_requested=cancel_requested,
    )

    if result.aborted:
        result.mod_size_text = ""
        return result

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


def _prepare_side_progress(
    grouped_items: list[tuple[tuple[int, str], list[PlannedAudioWorkItem]]],
    emit: Callable[[AudioRunEvent], None] | None,
) -> dict[tuple[int, str], _SideProgress]:
    side_progress: dict[tuple[int, str], _SideProgress] = {}
    for (row_id, side), items in grouped_items:
        emit_side = _emit_wrapper(emit, row_id, side)
        emit_side("side_started", message=f"Starting {side}-Side")
        side_progress[(row_id, side)] = _SideProgress(emit_side, len(items))
    return side_progress


def _run_parallel_conversions(
    contexts: list[_ItemContext],
    *,
    result: AudioRunResult,
    side_progress: dict[tuple[int, str], _SideProgress],
    cancel_requested: Callable[[], bool] | None,
) -> None:
    if not contexts:
        return
    worker_count = min(len(contexts), _auto_worker_count())
    pending_contexts = iter(contexts)
    in_flight: dict[Future[_TerminalItemResult], _ItemContext] = {}
    aborting = False
    executor = ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="nmb-audio")
    try:
        while True:
            if not aborting:
                if cancel_requested is not None and cancel_requested():
                    result.aborted = True
                    result.abort_message = "Build aborted by user."
                    result.fatal_error = result.abort_message
                    aborting = True
                else:
                    while len(in_flight) < worker_count:
                        try:
                            context = next(pending_contexts)
                        except StopIteration:
                            break
                        _emit_song_started(side_progress, context)
                        future = executor.submit(
                            _export_single_item,
                            context,
                            cancel_requested=cancel_requested,
                            emit_progress=_progress_emitter(side_progress, context),
                        )
                        in_flight[future] = context

            if not in_flight:
                break

            done, _pending = wait(tuple(in_flight.keys()), timeout=0.05, return_when=FIRST_COMPLETED)
            if not done:
                continue
            for future in done:
                context = in_flight.pop(future)
                try:
                    terminal = future.result()
                except ExportAbortedError as exc:
                    terminal = _aborted_result(context, str(exc))
                _record_terminal_result(result, side_progress, terminal)
                if terminal.terminal_kind == "aborted":
                    aborting = True
        if aborting and not result.abort_message:
            result.abort_message = "Build aborted by user."
            result.fatal_error = result.abort_message
    finally:
        executor.shutdown(wait=True, cancel_futures=True)


def _export_single_item(
    context: _ItemContext,
    *,
    cancel_requested: Callable[[], bool] | None,
    emit_progress: Callable[[int, str], None] | None,
) -> _TerminalItemResult:
    item = context.item
    if item.action == "error":
        return _failed_result(context, item.reason)

    target_path = Path(item.target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        export_source_path = context.cache_path
        succeeded_cached_path = str(context.cache_path)
        converted = False
        if item.action == "copy_ogg":
            export_source_path = Path(item.source_path)
            succeeded_cached_path = ""
        else:
            converted = ensure_cached_ogg(
                item,
                context.cache_path,
                emit_progress=emit_progress or (lambda _percent, _message: None),
                cancel_requested=cancel_requested,
            )

        _raise_if_cancelled(cancel_requested)
        progress_callback = emit_progress if item.action != "copy_ogg" else None
        copy_file_with_cancel(
            export_source_path,
            target_path,
            cancel_requested=cancel_requested,
            emit_progress=progress_callback,
            progress_message="Copying exported song...",
            emit_every_percent=100 if item.action == "copy_ogg" else 10,
        )
        return _TerminalItemResult(
            row_id=item.row_id,
            side=item.side,
            song_index=context.song_index,
            track_number=item.track_number,
            source_row_id=item.source_row_id,
            source_track_index=item.source_track_index,
            display_label=item.display_label,
            terminal_kind="song_succeeded",
            cached_ogg_path=succeeded_cached_path,
            size_text=_format_size_text(target_path.stat().st_size),
            converted=converted,
        )
    except ExportAbortedError as exc:
        return _aborted_result(context, str(exc))
    except Exception as exc:
        return _failed_result(context, str(exc))


def _record_terminal_result(
    result: AudioRunResult,
    side_progress: dict[tuple[int, str], _SideProgress],
    terminal: _TerminalItemResult,
) -> None:
    side_key = (terminal.row_id, terminal.side)
    side_state = side_progress[side_key]
    if terminal.terminal_kind == "song_succeeded":
        result.built_song_count += 1
        if terminal.converted:
            result.converted_count += 1
        side_state.built_any = True
        side_state.emit_side(
            "song_succeeded",
            song_index=terminal.song_index,
            track_number=terminal.track_number,
            source_row_id=terminal.source_row_id,
            source_track_index=terminal.source_track_index,
            display_label=terminal.display_label,
            cached_ogg_path=terminal.cached_ogg_path,
            percent=100,
            message="Exported song.",
            size_text=terminal.size_text,
        )
    elif terminal.terminal_kind == "song_failed":
        result.failed_song_count += 1
        result.errors.append(f"{terminal.display_label}: {terminal.error_message}")
        side_state.emit_side(
            "song_failed",
            song_index=terminal.song_index,
            track_number=terminal.track_number,
            source_row_id=terminal.source_row_id,
            source_track_index=terminal.source_track_index,
            display_label=terminal.display_label,
            percent=0,
            message=terminal.error_message,
        )
    elif terminal.terminal_kind == "aborted":
        result.aborted = True
        result.abort_message = terminal.error_message or "Build aborted by user."
        result.fatal_error = result.abort_message
        return

    side_state.completed_items += 1
    if side_state.completed_items != side_state.total_items:
        return
    if side_state.built_any:
        result.successful_sides.append(side_key)
    side_state.emit_side("side_completed", message="Side complete.")


def _emit_song_started(
    side_progress: dict[tuple[int, str], _SideProgress],
    context: _ItemContext,
) -> None:
    item = context.item
    side_progress[(item.row_id, item.side)].emit_side(
        "song_started",
        song_index=context.song_index,
        track_number=item.track_number,
        source_row_id=item.source_row_id,
        source_track_index=item.source_track_index,
        display_label=item.display_label,
        percent=0,
        message=item.reason,
    )


def _progress_emitter(
    side_progress: dict[tuple[int, str], _SideProgress],
    context: _ItemContext,
) -> Callable[[int, str], None]:
    item = context.item
    emit_side = side_progress[(item.row_id, item.side)].emit_side

    def _emit(percent: int, message: str) -> None:
        emit_side(
            "song_progress",
            song_index=context.song_index,
            track_number=item.track_number,
            source_row_id=item.source_row_id,
            source_track_index=item.source_track_index,
            display_label=item.display_label,
            percent=percent,
            message=message,
            size_text="",
        )

    return _emit


def _failed_result(context: _ItemContext, error_message: str) -> _TerminalItemResult:
    item = context.item
    return _TerminalItemResult(
        row_id=item.row_id,
        side=item.side,
        song_index=context.song_index,
        track_number=item.track_number,
        source_row_id=item.source_row_id,
        source_track_index=item.source_track_index,
        display_label=item.display_label,
        terminal_kind="song_failed",
        error_message=error_message,
    )


def _aborted_result(context: _ItemContext, error_message: str) -> _TerminalItemResult:
    item = context.item
    return _TerminalItemResult(
        row_id=item.row_id,
        side=item.side,
        song_index=context.song_index,
        track_number=item.track_number,
        source_row_id=item.source_row_id,
        source_track_index=item.source_track_index,
        display_label=item.display_label,
        terminal_kind="aborted",
        error_message=error_message,
    )


def _auto_worker_count() -> int:
    return min(4, max(2, (os.cpu_count() or 4) - 1))


def _raise_if_cancelled(cancel_requested: Callable[[], bool] | None, result: AudioRunResult | None = None) -> None:
    if cancel_requested is not None and cancel_requested():
        if result is not None:
            result.aborted = True
            result.abort_message = "Build aborted by user."
            result.fatal_error = result.abort_message
        raise ExportAbortedError("Build aborted by user.")


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
        source_row_id: int | None = None,
        source_track_index: int | None = None,
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
                source_row_id=source_row_id,
                source_track_index=source_track_index,
                display_label=display_label,
                cached_ogg_path=cached_ogg_path,
                percent=percent,
                message=message,
                size_text=size_text,
            )
        )

    return _wrapped


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
