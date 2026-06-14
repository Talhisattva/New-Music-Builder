from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from new_music_builder.domain.models import MediaRow
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
        self._default_border_color = spec.MODULE_TWO_SCROLL_VIEWPORT_EDGE_COLOR
        self._dnd_type = dnd_type
        self._can_accept_drop = can_accept_drop
        self._on_drop_files = on_drop_files
        self._selected_track_indices = set(selected_track_indices or set())
        self._on_track_selected = on_track_selected

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
        )
        self.table.pack(anchor='nw')
        self._bind_drop_target()
        self.refresh_content()
        self.refresh_scroll_region()

    def refresh_scroll_region(self) -> None:
        self.scroll_viewport.refresh_scroll_region()

    def refresh_content(self) -> None:
        tracks = self._row.tracks_a if self._row.selected_side == 'A' else self._row.tracks_b
        self.table.set_tracks(tracks)
        self.table.set_selection_state(self._selected_track_indices)
        self.refresh_scroll_region()

    def set_selection_state(self, selected_track_indices: set[int]) -> None:
        self._selected_track_indices = set(selected_track_indices)
        self.table.set_selection_state(self._selected_track_indices)

    def set_drop_highlight(self, active: bool) -> None:
        color = spec.MEDIA_ROW_SONGLIST_DROP_HIGHLIGHT_BORDER if active else self._default_border_color
        self.scroll_viewport.set_viewport_border_color(color)

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
