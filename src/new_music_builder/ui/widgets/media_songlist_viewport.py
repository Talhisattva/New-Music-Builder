from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk

from new_music_builder.domain.models import MediaRow, TrackEntry
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
        self._on_track_drag_started = on_track_drag_started
        self._on_track_drag_moved = on_track_drag_moved
        self._on_track_drag_finished = on_track_drag_finished
        self._drag_active = False
        self._drag_indices: list[int] = []
        self._drag_ghost: tk.Toplevel | None = None
        self._drag_ghost_canvas: tk.Canvas | None = None

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
            on_track_drag_started=self._emit_track_drag_started,
            on_track_drag_moved=self._emit_track_drag_moved,
            on_track_drag_finished=self._emit_track_drag_finished,
        )
        self.table.pack(anchor='nw')
        self.bind('<Destroy>', self._on_destroy, add='+')
        self._bind_drop_target()
        self.refresh_content()
        self.refresh_scroll_region()

    def refresh_scroll_region(self) -> None:
        self.scroll_viewport.refresh_scroll_region()

    def refresh_content(self) -> None:
        self.table.set_tracks(self._active_tracks())
        self.table.set_selection_state(self._selected_track_indices)
        self.refresh_scroll_region()

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
        self.cancel_drag()
        self._drag_active = True
        self._drag_indices = sorted_indices
        self._create_drag_ghost()
        self._render_drag_ghost()
        self.update_drag(x_root, y_root)

    def update_drag(self, x_root: int, y_root: int) -> None:
        if not self._drag_active:
            return
        self._position_drag_ghost(x_root, y_root)
        self._auto_scroll_if_needed(y_root)
        insertion_index = self._insertion_index_for_pointer(x_root, y_root)
        self.table.set_insertion_index(insertion_index)

    def finish_drag(self, x_root: int, y_root: int) -> int | None:
        if not self._drag_active:
            return None
        self.update_drag(x_root, y_root)
        insertion_index = self._insertion_index_for_pointer(x_root, y_root)
        self.cancel_drag()
        return insertion_index

    def cancel_drag(self) -> None:
        self._drag_active = False
        self._drag_indices = []
        self.table.clear_drag_state()
        self._destroy_drag_ghost()

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

    def _emit_track_drag_started(self, track_index: int, x_root: int, y_root: int) -> None:
        if self._on_track_drag_started is not None:
            self._on_track_drag_started(track_index, x_root, y_root)

    def _emit_track_drag_moved(self, x_root: int, y_root: int) -> None:
        if self._on_track_drag_moved is not None:
            self._on_track_drag_moved(x_root, y_root)

    def _emit_track_drag_finished(self, x_root: int, y_root: int) -> None:
        if self._on_track_drag_finished is not None:
            self._on_track_drag_finished(x_root, y_root)

    def _create_drag_ghost(self) -> None:
        ghost = tk.Toplevel(self.winfo_toplevel())
        ghost.overrideredirect(True)
        ghost.configure(bg=spec.MEDIA_ROW_OUTLINE)
        try:
            ghost.wm_attributes('-alpha', spec.MEDIA_ROW_SONGLIST_DRAG_GHOST_ALPHA)
        except tk.TclError:
            pass
        try:
            ghost.wm_attributes('-topmost', True)
        except tk.TclError:
            pass
        self._drag_ghost = ghost
        self._drag_ghost_canvas = tk.Canvas(
            ghost,
            width=spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[0],
            height=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_HEIGHT,
            bg=spec.MEDIA_ROW_OUTLINE,
            bd=0,
            highlightthickness=0,
        )
        self._drag_ghost_canvas.pack()

    def _render_drag_ghost(self) -> None:
        if self._drag_ghost_canvas is None:
            return
        tracks = self._active_tracks()
        visible_indices = self._drag_indices[:spec.MEDIA_ROW_SONGLIST_DRAG_GHOST_MAX_ROWS]
        hidden_count = max(0, len(self._drag_indices) - len(visible_indices))
        row_height = spec.MEDIA_ROW_SONGLIST_TABLE_ROW_HEIGHT
        footer_height = row_height if hidden_count else 0
        total_height = (len(visible_indices) * row_height) + footer_height
        self._drag_ghost_canvas.configure(height=total_height)
        self._drag_ghost_canvas.delete('all')
        for preview_row, track_index in enumerate(visible_indices):
            row_top = preview_row * row_height
            row_bottom = row_top + row_height
            track = tracks[track_index]
            fill = spec.MEDIA_ROW_SONGLIST_TABLE_ROW_SELECTED_BG
            self._drag_ghost_canvas.create_rectangle(
                0,
                row_top,
                spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[0],
                row_bottom,
                outline='',
                fill=fill,
            )
            self._draw_drag_ghost_grid(row_top, row_bottom)
            self._drag_ghost_canvas.create_text(
                sum(spec.MEDIA_ROW_SONGLIST_TABLE_COLUMN_WIDTHS[:2]) + 6,
                row_top + (row_height / 2),
                text=track.display_label or Path(track.source_path).stem,
                fill=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_TEXT_COLOR,
                font=(
                    spec.MEDIA_ROW_SONGLIST_TABLE_ROW_FONT_FAMILY,
                    spec.MEDIA_ROW_SONGLIST_TABLE_ROW_FONT_SIZE,
                ),
                anchor='w',
            )
            if track.duration:
                self._drag_ghost_canvas.create_text(
                    sum(spec.MEDIA_ROW_SONGLIST_TABLE_COLUMN_WIDTHS[:4]) + (spec.MEDIA_ROW_SONGLIST_TABLE_COLUMN_WIDTHS[4] / 2),
                    row_top + (row_height / 2),
                    text=track.duration,
                    fill=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_TEXT_COLOR,
                    font=(
                        spec.MEDIA_ROW_SONGLIST_TABLE_ROW_FONT_FAMILY,
                        spec.MEDIA_ROW_SONGLIST_TABLE_ROW_FONT_SIZE,
                    ),
                    anchor='c',
                )
        if hidden_count:
            footer_top = len(visible_indices) * row_height
            footer_bottom = footer_top + row_height
            self._drag_ghost_canvas.create_rectangle(
                0,
                footer_top,
                spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[0],
                footer_bottom,
                outline='',
                fill=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_BG_EVEN,
            )
            self._drag_ghost_canvas.create_text(
                spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[0] / 2,
                footer_top + (row_height / 2),
                text=f'+{hidden_count} more',
                fill=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_TEXT_COLOR,
                font=(
                    spec.MEDIA_ROW_SONGLIST_TABLE_ROW_FONT_FAMILY,
                    spec.MEDIA_ROW_SONGLIST_TABLE_ROW_FONT_SIZE,
                ),
                anchor='c',
            )
        self._drag_ghost_canvas.configure(scrollregion=(0, 0, spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[0], total_height))

    def _draw_drag_ghost_grid(self, row_top: int, row_bottom: int) -> None:
        if self._drag_ghost_canvas is None:
            return
        column_x = 0
        for width in spec.MEDIA_ROW_SONGLIST_TABLE_COLUMN_WIDTHS[:-1]:
            column_x += width
            self._drag_ghost_canvas.create_rectangle(
                column_x,
                row_top,
                column_x + spec.MEDIA_ROW_SONGLIST_TABLE_DIVIDER_WIDTH,
                row_bottom,
                outline='',
                fill=spec.MEDIA_ROW_SONGLIST_TABLE_DIVIDER_COLOR,
            )

    def _position_drag_ghost(self, x_root: int, y_root: int) -> None:
        if self._drag_ghost is None:
            return
        self._drag_ghost.geometry(f'+{x_root + 16}+{y_root + 16}')

    def _pointer_inside_viewport(self, x_root: int, y_root: int) -> bool:
        left = self.viewport_canvas.winfo_rootx()
        top = self.viewport_canvas.winfo_rooty()
        right = left + spec.MEDIA_ROW_SONGLIST_VIEWPORT_MASK_SIZE[0]
        bottom = top + spec.MEDIA_ROW_SONGLIST_VIEWPORT_MASK_SIZE[1]
        return left <= x_root <= right and top <= y_root <= bottom

    def _insertion_index_for_pointer(self, x_root: int, y_root: int) -> int | None:
        if not self._pointer_inside_viewport(x_root, y_root):
            return None
        local_y = int(y_root - self.table.winfo_rooty())
        return self.table.insertion_index_at_canvas_y(local_y)

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

    def _destroy_drag_ghost(self) -> None:
        if self._drag_ghost is not None:
            self._drag_ghost.destroy()
        self._drag_ghost = None
        self._drag_ghost_canvas = None

    def _on_destroy(self, _event: tk.Event) -> None:
        self.cancel_drag()
