from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import queue
import time

from new_music_builder.domain.models import AudioRunEvent


QueuedBuildItem = tuple[str, object]


@dataclass(slots=True)
class BuildEventPumpStats:
    queue_size_before: int = 0
    queue_size_after: int = 0
    raw_items_processed: int = 0
    emitted_items_processed: int = 0
    event_kind_counts: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class BuildEventPumpBatch:
    items: list[QueuedBuildItem]
    queue_empty: bool
    stats: BuildEventPumpStats


class BuildEventPump:
    def __init__(
        self,
        *,
        max_raw_items_per_tick: int = 200,
        time_budget_ms: float = 6.0,
    ) -> None:
        self._max_raw_items_per_tick = max_raw_items_per_tick
        self._time_budget_ms = time_budget_ms

    def drain(self, event_queue: queue.Queue[object]) -> BuildEventPumpBatch:
        stats = BuildEventPumpStats(queue_size_before=_safe_qsize(event_queue))
        started = time.perf_counter()
        emitted: list[QueuedBuildItem] = []
        pending_progress: OrderedDict[tuple[int, str, int], AudioRunEvent] = OrderedDict()

        while stats.raw_items_processed < self._max_raw_items_per_tick:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            if elapsed_ms >= self._time_budget_ms:
                break
            try:
                queued_item = event_queue.get_nowait()
            except queue.Empty:
                break
            stats.raw_items_processed += 1
            kind, payload = queued_item
            stats.event_kind_counts[kind] = stats.event_kind_counts.get(kind, 0) + 1

            if kind == "event" and isinstance(payload, AudioRunEvent) and payload.kind == "song_progress":
                song_index = payload.song_index if payload.song_index is not None else -1
                progress_key = (payload.row_id, payload.side, song_index)
                pending_progress[progress_key] = payload
                continue

            self._flush_pending_progress(pending_progress, emitted)
            emitted.append((kind, payload))
            if kind in {"result", "fatal"}:
                break

        self._flush_pending_progress(pending_progress, emitted)
        stats.emitted_items_processed = len(emitted)
        stats.queue_size_after = _safe_qsize(event_queue)
        return BuildEventPumpBatch(
            items=emitted,
            queue_empty=stats.queue_size_after == 0,
            stats=stats,
        )

    @staticmethod
    def _flush_pending_progress(
        pending_progress: OrderedDict[tuple[int, str, int], AudioRunEvent],
        emitted: list[QueuedBuildItem],
    ) -> None:
        if not pending_progress:
            return
        for event in pending_progress.values():
            emitted.append(("event", event))
        pending_progress.clear()


def _safe_qsize(event_queue: queue.Queue[object]) -> int:
    try:
        return max(0, int(event_queue.qsize()))
    except NotImplementedError:
        return 0
