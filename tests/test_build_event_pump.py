from __future__ import annotations

import queue

from new_music_builder.domain.models import AudioRunEvent
from new_music_builder.services.build_event_pump import BuildEventPump


def _event(kind: str, *, row_id: int = 1, side: str = "A", song_index: int | None = None) -> AudioRunEvent:
    return AudioRunEvent(
        kind=kind,  # type: ignore[arg-type]
        row_id=row_id,
        side=side,  # type: ignore[arg-type]
        song_index=song_index,
        display_label=kind,
    )


def test_build_event_pump_drops_stale_nonterminal_events_after_abort() -> None:
    event_queue: queue.Queue[object] = queue.Queue()
    event_queue.put(("event", _event("song_started", song_index=0)))
    event_queue.put(("event", _event("song_progress", song_index=0)))
    event_queue.put(("event", _event("song_succeeded", song_index=0)))
    event_queue.put(("event", _event("run_aborted")))
    event_queue.put(("result", object()))

    batch = BuildEventPump().drain(event_queue, abort_requested=True)

    assert [kind for kind, _payload in batch.items] == ["event", "result"]
    assert [payload.kind for kind, payload in batch.items if kind == "event"] == ["run_aborted"]
    assert batch.queue_empty is True


def test_build_event_pump_keeps_latest_progress_without_abort() -> None:
    event_queue: queue.Queue[object] = queue.Queue()
    event_queue.put(("event", _event("song_progress", song_index=0)))
    event_queue.put(("event", AudioRunEvent(kind="song_progress", row_id=1, side="A", song_index=0, percent=75)))

    batch = BuildEventPump().drain(event_queue)

    assert len(batch.items) == 1
    kind, payload = batch.items[0]
    assert kind == "event"
    assert payload.kind == "song_progress"
    assert payload.percent == 75
