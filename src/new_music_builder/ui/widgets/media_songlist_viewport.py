from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from new_music_builder.domain.models import MediaRow, SongSortColumn, TrackEntry
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.media_songlist_table import MediaSonglistTable, TrackSelectionModifiers
from new_music_builder.ui.widgets.scroll_area import ScrollViewport


class MediaSonglistViewport(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        row: MediaRow,
        bg_color: str,
        ear_icon_path: str | None = None,
        grab_icon_path: str | None = None,
        table_check_icon_path: str | None = None,
        preview_audio_icon_path: str | None = None,
        selected_track_indices: set[int] | None = None,
        on_track_selected: Callable[[int, TrackSelectionModifiers], None] | None = None,
        on_track_remove_requested: Callable[[int], None] | None = None,
        on_header_sort_requested: Callable[[SongSortColumn], None] | None = None,
        on_track_drag_started: Callable[[int, int, int], None] | None = None,
        on_track_drag_moved: Callable[[int, int], None] | None = None,
        on_track_drag_finished: Callable[[int, int], None] | None = None,
        dnd_type: str | None = None,
        can_accept_drop: Callable[[list[str]], bool] | None = None,
        on_drop_files: Callable[[list[str]], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_SONGLIST_VIEWPORT_SIZE[0],
            height=spec.MEDIA_ROW_SONGLIST_VIEWPORT_SIZE[1],
        )
        self.pack_propagate(False)
        self._row = row
        self._bg_color = bg_color
        self._default_border_color = spec.MODULE_TWO_SCROLL_VIEWPORT_EDGE_COLOR
        self._dnd_type = dnd_type
        self._can_accept_drop = can_accept_drop
        self._on_drop_files = on_drop_files
        self._selected_track_indices = set(selected_track_indices or set())
        self._on_track_selected = on_track_selected
        self._on_track_remove_requested = on_track_remove_requested
        self._on_header_sort_requested = on_header_sort_requested
        self._on_track_drag_started = on_track_drag_started
        self._on_track_drag_moved = on_track_drag_moved
        self._on_track_drag_finished = on_track_drag_finished
        self._drag_active = False
        self._drag_indices: list[int] = []
        self._last_width = spec.MEDIA_ROW_SONGLIST_VIEWPORT_SIZE[0]

        self.scroll_viewport = ScrollViewport(
            self,
            size=spec.MEDIA_ROW_SONGLIST_VIEWPORT_SIZE,
            viewport_size=spec.MEDIA_ROW_SONGLIST_VIEWPORT_MASK_SIZE,
            scrollbar_size=spec.MEDIA_ROW_SONGLIST_SCROLLBAR_SIZE,
            show_top_edge=True,
            content_bottom_padding=0,
            bg_color=bg_color,
        )
        self.scroll_viewport.place(x=0, y=0)

        self.viewport_canvas = self.scroll_viewport.viewport_canvas
        self.content_frame = self.scroll_viewport.content_frame
        self.scrollbar = self.scroll_viewport.scrollbar

        self.table = MediaSonglistTable(
            self.content_frame,
            bg_color=bg_color,
            ear_icon_path=ear_icon_path,
            grab_icon_path=grab_icon_path,
            table_check_icon_path=table_check_icon_path,
            preview_audio_icon_path=preview_audio_icon_path,
            on_track_selected=self._emit_track_selection,
            on_track_remove_requested=self._emit_track_remove,
            on_header_sort_requested=self._emit_header_sort_requested,
            on_track_drag_started=self._emit_track_drag_started,
            on_track_drag_moved=self._emit_track_drag_moved,
            on_track_drag_finished=self._emit_track_drag_finished,
        )
        self.table.pack(anchor='nw')
        self.bind('<Destroy>', self._on_destroy, add='+')
        self._bind_drop_target()
        self.refresh_content()
        self.refresh_scroll_region()

    def resize(self, width: int) -> None:
        if width == self._last_width:
            return
        self._last_width = width
        viewport_width = max(1, width - spec.MEDIA_ROW_SONGLIST_SCROLLBAR_SIZE[0])
        self.configure(width=width, height=spec.MEDIA_ROW_SONGLIST_VIEWPORT_SIZE[1])
        self.scroll_viewport.resize(
            size=(width, spec.MEDIA_ROW_SONGLIST_VIEWPORT_SIZE[1]),
            viewport_size=(viewport_width, spec.MEDIA_ROW_SONGLIST_VIEWPORT_MASK_SIZE[1]),
            scrollbar_size=spec.MEDIA_ROW_SONGLIST_SCROLLBAR_SIZE,
        )
        self.table.resize(viewport_width)

    def refresh_scroll_region(self) -> None:
        self.scroll_viewport.refresh_scroll_region()

    def refresh_content(self) -> None:
        self.table.set_tracks(self._active_tracks())
        sort_state = self._row.song_sort_for_side(self._row.selected_side)
        self.table.set_sort_state(sort_state.column, sort_state.direction)
        self.table.set_selection_state(self._selected_track_indices)
        self.refresh_scroll_region()

    def tooltip_widgets(self) -> tuple[tk.Misc, ...]:
        return (
            self,
            self.scroll_viewport,
            self.viewport_canvas,
            self.content_frame,
            self.table,
        )

    def header_tooltip_widgets(self) -> tuple[tk.Misc, ...]:
        return (self.table,)

    def is_pointer_in_header(self, event: tk.Event | None) -> bool:
        if event is not None and hasattr(event, 'y'):
            return 0 <= int(event.y) < spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_HEIGHT
        try:
            pointer_x = self.table.winfo_pointerx()
            pointer_y = self.table.winfo_pointery()
            local_x = pointer_x - self.table.winfo_rootx()
            local_y = pointer_y - self.table.winfo_rooty()
            return 0 <= local_x < self.table.winfo_width() and 0 <= local_y < spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_HEIGHT
        except tk.TclError:
            return False

    def set_selection_state(self, selected_track_indices: set[int]) -> None:
        self._selected_track_indices = set(selected_track_indices)
        self.table.set_selection_state(self._selected_track_indices)

    def set_drop_highlight(self, active: bool) -> None:
        color = spec.MEDIA_ROW_SONGLIST_DROP_HIGHLIGHT_BORDER if active else self._default_border_color
        self.scroll_viewport.set_viewport_border_color(color)

    def begin_drag(self, dragged_indices: set[int], x_root: int, y_root: int) -> None:
        sorted_indices = sorted(index for index in dragged_indices if 0 <= index < self.table.track_count())
        if not sorted_indices:
            return
        if self._drag_active:
            self.cancel_drag()
        else:
            self.table.clear_drag_overlay()
        self._drag_active = True
        self._drag_indices = sorted_indices
        self.table.begin_drag_overlay(set(sorted_indices), x_root, y_root)
        self.update_drag(x_root, y_root)

    def update_drag(self, x_root: int, y_root: int) -> None:
        if not self._drag_active:
            return
        self._auto_scroll_if_needed(y_root)
        self.table.update_drag_overlay(x_root, y_root)

    def finish_drag(self, x_root: int, y_root: int) -> int | None:
        if not self._drag_active:
            return None
        self.update_drag(x_root, y_root)
        insertion_index = self.table.current_insertion_index()
        self.cancel_drag()
        return insertion_index

    def cancel_drag(self) -> None:
        self._drag_active = False
        self._drag_indices = []
        if self.table.winfo_exists():
            self.table.clear_drag_state()
        if self.winfo_exists():
            self.refresh_scroll_region()

    def _active_tracks(self) -> list[TrackEntry]:
        return self._row.tracks_a if self._row.selected_side == 'A' else self._row.tracks_b

    def _bind_drop_target(self) -> None:
        if self._dnd_type is None or not hasattr(self.table, 'drop_target_register'):
            return
        try:
            self.table.drop_target_register(self._dnd_type)
            self.table.dnd_bind('<<DropEnter>>', self._on_drop_enter, add='+')
            self.table.dnd_bind('<<DropPosition>>', self._on_drop_position, add='+')
            self.table.dnd_bind('<<DropLeave>>', self._on_drop_leave, add='+')
            self.table.dnd_bind('<<Drop>>', self._on_drop, add='+')
        except tk.TclError:
            self._dnd_type = None

    def _split_drop_paths(self, raw_data: str) -> list[str]:
        try:
            return [item for item in self.tk.splitlist(raw_data) if item]
        except tk.TclError:
            return [raw_data] if raw_data else []

    def _drop_is_valid(self, raw_data: str) -> bool:
        if self._can_accept_drop is None:
            return False
        return self._can_accept_drop(self._split_drop_paths(raw_data))

    def _on_drop_enter(self, event: tk.Event) -> str:
        self.set_drop_highlight(self._drop_is_valid(getattr(event, 'data', '')))
        return getattr(event, 'action', 'copy')

    def _on_drop_position(self, event: tk.Event) -> str:
        self.set_drop_highlight(self._drop_is_valid(getattr(event, 'data', '')))
        return getattr(event, 'action', 'copy')

    def _on_drop_leave(self, event: tk.Event) -> str:
        self.set_drop_highlight(False)
        return getattr(event, 'action', 'copy')

    def _on_drop(self, event: tk.Event) -> str:
        paths = self._split_drop_paths(getattr(event, 'data', ''))
        valid = self._can_accept_drop(paths) if self._can_accept_drop is not None else False
        if valid and self._on_drop_files is not None:
            self._on_drop_files(paths)
        self.set_drop_highlight(False)
        return getattr(event, 'action', 'copy')

    def _emit_track_selection(self, track_index: int, modifiers: TrackSelectionModifiers) -> None:
        if self._on_track_selected is not None:
            self._on_track_selected(track_index, modifiers)

    def _emit_track_remove(self, track_index: int) -> None:
        if self._on_track_remove_requested is not None:
            self._on_track_remove_requested(track_index)

    def _emit_header_sort_requested(self, column: SongSortColumn) -> None:
        if self._on_header_sort_requested is not None:
            self._on_header_sort_requested(column)

    def _emit_track_drag_started(self, track_index: int, x_root: int, y_root: int) -> None:
        if self._on_track_drag_started is not None:
            self._on_track_drag_started(track_index, x_root, y_root)

    def _emit_track_drag_moved(self, x_root: int, y_root: int) -> None:
        if self._on_track_drag_moved is not None:
            self._on_track_drag_moved(x_root, y_root)

    def _emit_track_drag_finished(self, x_root: int, y_root: int) -> None:
        if self._on_track_drag_finished is not None:
            self._on_track_drag_finished(x_root, y_root)

    def _auto_scroll_if_needed(self, y_root: int) -> None:
        if not self.scroll_viewport.is_scroll_active():
            return
        top = self.viewport_canvas.winfo_rooty()
        bottom = top + spec.MEDIA_ROW_SONGLIST_VIEWPORT_MASK_SIZE[1]
        if y_root < top + spec.MEDIA_ROW_SONGLIST_DRAG_AUTOSCROLL_EDGE_PX:
            self.scroll_viewport.scroll_by_pixels(-spec.MEDIA_ROW_SONGLIST_DRAG_AUTOSCROLL_STEP_PX)
            self.update_idletasks()
        elif y_root > bottom - spec.MEDIA_ROW_SONGLIST_DRAG_AUTOSCROLL_EDGE_PX:
            self.scroll_viewport.scroll_by_pixels(spec.MEDIA_ROW_SONGLIST_DRAG_AUTOSCROLL_STEP_PX)
            self.update_idletasks()

    def _on_destroy(self, _event: tk.Event) -> None:
        self.cancel_drag()
