from __future__ import annotations

from types import SimpleNamespace

from new_music_builder.domain.models import TrackEntry
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.media_songlist_table import MediaSonglistTable, TrackSelectionModifiers


def _build_table() -> MediaSonglistTable:
    table = MediaSonglistTable.__new__(MediaSonglistTable)
    table._header_height = spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_HEIGHT
    table._row_height = spec.MEDIA_ROW_SONGLIST_TABLE_ROW_HEIGHT
    table._min_row_count = spec.MEDIA_ROW_SONGLIST_TABLE_MIN_ROWS
    table._column_widths = spec.MEDIA_ROW_SONGLIST_TABLE_COLUMN_WIDTHS
    table._width = sum(spec.MEDIA_ROW_SONGLIST_TABLE_COLUMN_WIDTHS)
    table._tracks = [
        TrackEntry(source_path="a.ogg", display_label="Alpha", duration="00:10"),
        TrackEntry(source_path="b.ogg", display_label="Beta", duration="00:20"),
    ]
    table._selected_indices = set()
    table._hover_index = None
    table._hover_header_column = None
    table._insertion_index = None
    table._pending_grab_row_index = None
    table._grab_press_x_root = 0
    table._grab_press_y_root = 0
    table._drag_active = False
    table._drag_overlay_indices = []
    table._drag_overlay_cursor_y = None
    table._drag_overlay_anchor_offset_y = 0
    table._on_track_selected = None
    table._on_track_remove_requested = None
    table._on_header_sort_requested = None
    table._on_track_drag_started = None
    table._on_track_drag_moved = None
    table._on_track_drag_finished = None
    table.redraw = lambda: None
    table.update_drag_overlay = lambda _x, _y: None
    table._bind_drag_capture = lambda: None
    table._unbind_drag_capture = lambda: None
    table.clear_drag_overlay = lambda: None
    table.clear_drag_state = lambda: setattr(table, "_pending_grab_row_index", None)
    return table


def test_song_table_selects_from_song_name_column() -> None:
    table = _build_table()
    selections: list[tuple[int, TrackSelectionModifiers]] = []
    table._on_track_selected = lambda index, modifiers: selections.append((index, modifiers))

    row_y = table._header_height + (table._row_height // 2)
    song_name_x = sum(table._column_widths[:2]) + 12

    table._on_button_press(SimpleNamespace(x=song_name_x, y=row_y, x_root=song_name_x, y_root=row_y))
    table._on_button_release(SimpleNamespace(x=song_name_x, y=row_y, x_root=song_name_x, y_root=row_y, state=0))

    assert selections == [(0, TrackSelectionModifiers())]


def test_song_table_starts_drag_from_song_name_column_after_threshold() -> None:
    table = _build_table()
    drag_started: list[tuple[int, int, int]] = []
    table._on_track_drag_started = lambda index, x_root, y_root: drag_started.append((index, x_root, y_root))

    row_y = table._header_height + (table._row_height // 2)
    song_name_x = sum(table._column_widths[:2]) + 12

    table._on_button_press(SimpleNamespace(x=song_name_x, y=row_y, x_root=100, y_root=100))
    table._on_button_motion(
        SimpleNamespace(
            x=song_name_x + spec.MEDIA_ROW_SONGLIST_DRAG_THRESHOLD_PX,
            y=row_y,
            x_root=100 + spec.MEDIA_ROW_SONGLIST_DRAG_THRESHOLD_PX,
            y_root=100,
        )
    )

    assert drag_started == [(0, 100 + spec.MEDIA_ROW_SONGLIST_DRAG_THRESHOLD_PX, 100)]


def test_song_table_remove_column_does_not_select_row() -> None:
    table = _build_table()
    selections: list[int] = []
    removed: list[int] = []
    table._on_track_selected = lambda index, _modifiers: selections.append(index)
    table._on_track_remove_requested = lambda index: removed.append(index)

    row_y = table._header_height + (table._row_height // 2)
    remove_x = sum(table._column_widths[:4]) + (table._column_widths[4] // 2)

    table._on_button_press(SimpleNamespace(x=remove_x, y=row_y, x_root=remove_x, y_root=row_y))
    table._on_button_release(SimpleNamespace(x=remove_x, y=row_y, x_root=remove_x, y_root=row_y, state=0))

    assert selections == []
    assert removed == [0]
