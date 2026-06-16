from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont

from PIL import ImageTk

from new_music_builder.domain.models import TrackEntry
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage


@dataclass(frozen=True, slots=True)
class TrackSelectionModifiers:
    shift: bool = False
    additive: bool = False


class MediaSonglistTable(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        bg_color: str,
        ear_icon_path: str | None = None,
        grab_icon_path: str | None = None,
        table_check_icon_path: str | None = None,
        preview_audio_icon_path: str | None = None,
        on_track_selected: Callable[[int, TrackSelectionModifiers], None] | None = None,
        on_track_remove_requested: Callable[[int], None] | None = None,
        on_track_drag_started: Callable[[int, int, int], None] | None = None,
        on_track_drag_moved: Callable[[int, int], None] | None = None,
        on_track_drag_finished: Callable[[int, int], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[0],
            height=spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[1],
        )
        self._width = spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[0]
        self._header_height = spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_HEIGHT
        self._row_height = spec.MEDIA_ROW_SONGLIST_TABLE_ROW_HEIGHT
        self._min_row_count = spec.MEDIA_ROW_SONGLIST_TABLE_MIN_ROWS
        self._column_widths = spec.MEDIA_ROW_SONGLIST_TABLE_COLUMN_WIDTHS
        self._divider_color = spec.MEDIA_ROW_SONGLIST_TABLE_DIVIDER_COLOR
        self._divider_width = spec.MEDIA_ROW_SONGLIST_TABLE_DIVIDER_WIDTH
        self._tracks: list[TrackEntry] = []
        self._selected_indices: set[int] = set()
        self._hover_index: int | None = None
        self._insertion_index: int | None = None
        self._pending_grab_row_index: int | None = None
        self._grab_press_x_root = 0
        self._grab_press_y_root = 0
        self._drag_active = False
        self._drag_motion_bind_id: str | None = None
        self._drag_release_bind_id: str | None = None
        self._drag_overlay_indices: list[int] = []
        self._drag_overlay_cursor_y: int | None = None
        self._drag_overlay_anchor_offset_y = 0
        self._on_track_selected = on_track_selected
        self._on_track_remove_requested = on_track_remove_requested
        self._on_track_drag_started = on_track_drag_started
        self._on_track_drag_moved = on_track_drag_moved
        self._on_track_drag_finished = on_track_drag_finished
        self._row_font = tkfont.Font(
            family=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_FONT_FAMILY,
            size=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_FONT_SIZE,
        )
        self._remove_font = (
            spec.MEDIA_ROW_SONGLIST_TABLE_REMOVE_FONT_FAMILY,
            spec.MEDIA_ROW_SONGLIST_TABLE_REMOVE_FONT_SIZE,
        )
        self._ear_icon_image = self._load_icon(ear_icon_path)
        self._grab_icon_image = self._load_icon(grab_icon_path)
        self._table_check_icon_image = self._load_icon(table_check_icon_path)
        self._preview_audio_icon_image = self._load_icon(preview_audio_icon_path)
        self._bind_interactions()
        self.redraw()

    def _load_icon(self, path: str | None) -> ImageTk.PhotoImage | None:
        return load_tk_photoimage(path)

    def track_count(self) -> int:
        return len(self._tracks)

    def visible_row_count(self) -> int:
        return max(self._min_row_count, len(self._tracks))

    def table_height(self) -> int:
        return self._header_height + (self.visible_row_count() * self._row_height)

    def set_tracks(self, tracks: list[TrackEntry]) -> None:
        self._tracks = list(tracks)
        self._selected_indices = {index for index in self._selected_indices if index < len(self._tracks)}
        self._drag_overlay_indices = [index for index in self._drag_overlay_indices if index < len(self._tracks)]
        if self._hover_index is not None and self._hover_index >= len(self._tracks):
            self._hover_index = None
        if self._insertion_index is not None:
            self._insertion_index = max(0, min(len(self._tracks), self._insertion_index))
        self.redraw()

    def set_selection_state(self, selected_indices: set[int]) -> None:
        filtered = {index for index in selected_indices if index < len(self._tracks)}
        if filtered == self._selected_indices:
            return
        self._selected_indices = filtered
        self.redraw()

    def set_insertion_index(self, insertion_index: int | None) -> None:
        bounded = insertion_index
        if bounded is not None:
            bounded = max(0, min(len(self._tracks), bounded))
        if bounded == self._insertion_index:
            return
        self._insertion_index = bounded
        self.redraw()

    def current_insertion_index(self) -> int | None:
        return self._insertion_index

    def begin_drag_overlay(self, dragged_indices: set[int], x_root: int, y_root: int) -> None:
        self._drag_overlay_indices = sorted(index for index in dragged_indices if 0 <= index < len(self._tracks))
        if not self._drag_overlay_indices:
            return
        local_y = self._canvas_y_from_root(y_root)
        anchor_row_index = self._drag_overlay_indices[0]
        anchor_row_top = self._header_height + (anchor_row_index * self._row_height)
        self._drag_overlay_anchor_offset_y = max(0, local_y - anchor_row_top)
        self._drag_overlay_cursor_y = local_y
        self._set_drag_insertion_from_local_y(local_y)
        self.redraw()

    def update_drag_overlay(self, x_root: int, y_root: int) -> None:
        if not self._drag_overlay_indices:
            return
        local_y = self._canvas_y_from_root(y_root)
        self._drag_overlay_cursor_y = local_y
        self._set_drag_insertion_from_local_y(local_y)
        self.redraw()

    def clear_drag_state(self) -> None:
        self._pending_grab_row_index = None
        self._drag_active = False
        self._unbind_drag_capture()
        self.clear_drag_overlay()

    def clear_drag_overlay(self) -> None:
        self._drag_overlay_indices = []
        self._drag_overlay_cursor_y = None
        self._drag_overlay_anchor_offset_y = 0
        self.set_insertion_index(None)

    def insertion_index_at_canvas_y(self, y: int) -> int | None:
        if not self._tracks:
            return None
        if y <= self._header_height:
            return 0
        relative_y = y - self._header_height
        for boundary_index in range(len(self._tracks) + 1):
            boundary_y = boundary_index * self._row_height
            if relative_y < boundary_y + (self._row_height / 2):
                return boundary_index
        return len(self._tracks)

    def redraw(self) -> None:
        self.delete('all')
        height = self.table_height()
        self.configure(height=height, width=self._width)
        self._draw_background(height)
        self._draw_insertion_line()
        self._draw_header_content()
        self._draw_track_rows()
        self._draw_drag_overlay()

    def _draw_background(self, height: int) -> None:
        self.create_rectangle(0, 0, self._width, self._header_height, outline='', fill=spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_BG)
        body_y = self._header_height
        for row_index in range(self.visible_row_count()):
            row_top = body_y + (row_index * self._row_height)
            row_bottom = row_top + self._row_height
            self.create_rectangle(0, row_top, self._width, row_bottom, outline='', fill=self._row_fill(row_index))

        column_x = 0
        for width in self._column_widths[:-1]:
            column_x += width
            self.create_rectangle(column_x, 0, column_x + self._divider_width, height, outline='', fill=self._divider_color)

        self.create_rectangle(0, self._header_height, self._width, self._header_height + self._divider_width, outline='', fill=self._divider_color)
        for row_index in range(1, self.visible_row_count()):
            row_divider_y = self._header_height + (row_index * self._row_height)
            self.create_rectangle(0, row_divider_y, self._width, row_divider_y + self._divider_width, outline='', fill=self._divider_color)

    def _draw_insertion_line(self) -> None:
        if self._insertion_index is None or not self._tracks:
            return
        y = self._header_height + (self._insertion_index * self._row_height)
        self.create_rectangle(0, y, self._width, y + spec.MEDIA_ROW_SONGLIST_DRAG_INSERT_WIDTH, outline='', fill=spec.MEDIA_ROW_SONGLIST_DRAG_INSERT_COLOR)

    def _draw_drag_overlay(self) -> None:
        if not self._drag_overlay_indices or self._drag_overlay_cursor_y is None:
            return
        preview_tracks = [self._tracks[index] for index in self._drag_overlay_indices if 0 <= index < len(self._tracks)]
        if not preview_tracks:
            return
        overlay_top = self._drag_overlay_cursor_y - self._drag_overlay_anchor_offset_y
        overlay_bottom = overlay_top + (len(preview_tracks) * self._row_height)
        self.create_rectangle(
            0,
            overlay_top,
            self._width,
            overlay_bottom,
            outline=spec.MEDIA_ROW_SONGLIST_DRAG_INSERT_COLOR,
            width=1,
            fill=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_SELECTED_BG,
        )
        for preview_row, track in enumerate(preview_tracks):
            row_top = overlay_top + (preview_row * self._row_height)
            row_center_y = row_top + (self._row_height / 2)
            if preview_row > 0:
                self.create_rectangle(0, row_top, self._width, row_top + self._divider_width, outline='', fill=self._divider_color)
            self._draw_grab_icon(row_center_y)
            self._draw_ogg_status(track, row_center_y)
            self._draw_song_name(track, row_center_y)
            self._draw_preview_icon(row_center_y)
            self._draw_duration(track, row_center_y)
            self._draw_remove_marker(row_center_y)

    def _draw_header_content(self) -> None:
        current_x = 0
        labels = spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_LABELS
        for index, column_width in enumerate(self._column_widths):
            center_x = current_x + (column_width / 2)
            center_y = self._header_height / 2
            if index == 3:
                self._draw_ear_icon(center_x, center_y)
            elif labels[index]:
                self.create_text(
                    center_x,
                    center_y,
                    text=labels[index],
                    fill=spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_TEXT_COLOR,
                    font=(spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_FONT_FAMILY, spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_FONT_SIZE),
                    anchor='c',
                )
            current_x += column_width

    def _draw_ear_icon(self, center_x: float, center_y: float) -> None:
        if self._ear_icon_image is None:
            return
        self.create_image(center_x, center_y, image=self._ear_icon_image, anchor='c')

    def _draw_track_rows(self) -> None:
        for row_index, track in enumerate(self._tracks):
            row_top = self._header_height + (row_index * self._row_height)
            row_center_y = row_top + (self._row_height / 2)
            self._draw_grab_icon(row_center_y)
            self._draw_ogg_status(track, row_center_y)
            self._draw_song_name(track, row_center_y)
            self._draw_preview_icon(row_center_y)
            self._draw_duration(track, row_center_y)
            self._draw_remove_marker(row_center_y)

    def _column_center_x(self, column_index: int) -> float:
        return sum(self._column_widths[:column_index]) + (self._column_widths[column_index] / 2)

    def _row_fill(self, row_index: int) -> str:
        if row_index in self._selected_indices:
            return spec.MEDIA_ROW_SONGLIST_TABLE_ROW_SELECTED_BG
        if self._hover_index == row_index and row_index < len(self._tracks):
            return spec.MEDIA_ROW_SONGLIST_TABLE_ROW_HOVER_BG
        return spec.MEDIA_ROW_SONGLIST_TABLE_ROW_BG_ODD if row_index % 2 == 0 else spec.MEDIA_ROW_SONGLIST_TABLE_ROW_BG_EVEN

    def _column_left_x(self, column_index: int) -> int:
        return sum(self._column_widths[:column_index])

    def _draw_grab_icon(self, row_center_y: float) -> None:
        if self._grab_icon_image is None:
            return
        self.create_image(self._column_center_x(0), row_center_y, image=self._grab_icon_image, anchor='c')

    def _draw_ogg_status(self, track: TrackEntry, row_center_y: float) -> None:
        if self._table_check_icon_image is None or Path(track.source_path).suffix.lower() != '.ogg':
            return
        self.create_image(self._column_center_x(1), row_center_y, image=self._table_check_icon_image, anchor='c')

    def _draw_song_name(self, track: TrackEntry, row_center_y: float) -> None:
        column_left = self._column_left_x(2)
        available_width = self._column_widths[2] - 12
        text = self._truncate_text(track.display_label or Path(track.source_path).stem, available_width)
        self.create_text(column_left + 6, row_center_y, text=text, fill=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_TEXT_COLOR, font=self._row_font, anchor='w')

    def _truncate_text(self, text: str, max_width: int) -> str:
        if self._row_font.measure(text) <= max_width:
            return text
        ellipsis = '...'
        truncated = text
        while truncated and self._row_font.measure(f'{truncated}{ellipsis}') > max_width:
            truncated = truncated[:-1]
        return f'{truncated}{ellipsis}' if truncated else ellipsis

    def _draw_duration(self, track: TrackEntry, row_center_y: float) -> None:
        if not track.duration:
            return
        self.create_text(self._column_center_x(4), row_center_y, text=track.duration, fill=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_TEXT_COLOR, font=self._row_font, anchor='c')

    def _draw_preview_icon(self, row_center_y: float) -> None:
        if self._preview_audio_icon_image is None:
            return
        self.create_image(self._column_center_x(3), row_center_y, image=self._preview_audio_icon_image, anchor='c')

    def _draw_remove_marker(self, row_center_y: float) -> None:
        self.create_text(self._column_center_x(5), row_center_y, text='X', fill=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_TEXT_COLOR, font=self._remove_font, anchor='c')

    def _bind_interactions(self) -> None:
        self.bind('<Motion>', self._on_motion, add='+')
        self.bind('<Leave>', self._on_leave, add='+')
        self.bind('<ButtonPress-1>', self._on_button_press, add='+')
        self.bind('<B1-Motion>', self._on_button_motion, add='+')
        self.bind('<ButtonRelease-1>', self._on_button_release, add='+')

    def _on_motion(self, event: tk.Event) -> None:
        if self._drag_active:
            return
        row_index = self._row_index_at(int(getattr(event, 'y', -1)))
        hover_index = row_index if row_index is not None and row_index < len(self._tracks) else None
        if hover_index == self._hover_index:
            return
        self._hover_index = hover_index
        self.redraw()

    def _on_leave(self, _event: tk.Event) -> None:
        if self._hover_index is None:
            return
        self._hover_index = None
        self.redraw()

    def _on_button_press(self, event: tk.Event) -> str:
        row_index = self._row_index_at(int(getattr(event, 'y', -1)))
        if row_index is None or row_index >= len(self._tracks):
            self.clear_drag_state()
            return 'break'
        column_index = self._column_index_at(int(getattr(event, 'x', -1)))
        if column_index == 0:
            self._pending_grab_row_index = row_index
            self._grab_press_x_root = int(getattr(event, 'x_root', 0))
            self._grab_press_y_root = int(getattr(event, 'y_root', 0))
            self._drag_active = False
            return 'break'
        self._pending_grab_row_index = None
        self._drag_active = False
        return 'break'

    def _on_button_motion(self, event: tk.Event) -> str:
        if self._pending_grab_row_index is None:
            return 'break'
        x_root = int(getattr(event, 'x_root', 0))
        y_root = int(getattr(event, 'y_root', 0))
        if not self._drag_active:
            if not self._drag_threshold_exceeded(x_root, y_root):
                return 'break'
            self._drag_active = True
            self._bind_drag_capture()
            if self._on_track_drag_started is not None:
                self._on_track_drag_started(self._pending_grab_row_index, x_root, y_root)
        self.update_drag_overlay(x_root, y_root)
        if self._on_track_drag_moved is not None:
            self._on_track_drag_moved(x_root, y_root)
        return 'break'

    def _on_button_release(self, event: tk.Event) -> str:
        x = int(getattr(event, 'x', -1))
        y = int(getattr(event, 'y', -1))
        x_root = int(getattr(event, 'x_root', 0))
        y_root = int(getattr(event, 'y_root', 0))
        row_index = self._row_index_at(y)
        column_index = self._column_index_at(x)

        if self._drag_active:
            if self._on_track_drag_finished is not None:
                self._on_track_drag_finished(x_root, y_root)
            self.clear_drag_state()
            return 'break'

        if self._pending_grab_row_index is not None:
            self.clear_drag_state()
            return 'break'

        if row_index is None or row_index >= len(self._tracks):
            return 'break'
        if column_index == 5 and self._on_track_remove_requested is not None:
            self._on_track_remove_requested(row_index)
            return 'break'
        if self._on_track_selected is not None:
            self._on_track_selected(row_index, self._decode_selection_modifiers(event))
        return 'break'

    def _drag_threshold_exceeded(self, x_root: int, y_root: int) -> bool:
        dx = abs(x_root - self._grab_press_x_root)
        dy = abs(y_root - self._grab_press_y_root)
        return max(dx, dy) >= spec.MEDIA_ROW_SONGLIST_DRAG_THRESHOLD_PX

    def _bind_drag_capture(self) -> None:
        owner = self.winfo_toplevel()
        self._unbind_drag_capture()
        self._drag_motion_bind_id = owner.bind('<B1-Motion>', self._on_captured_drag_motion, add='+')
        self._drag_release_bind_id = owner.bind('<ButtonRelease-1>', self._on_captured_drag_release, add='+')

    def _unbind_drag_capture(self) -> None:
        owner = self.winfo_toplevel()
        if self._drag_motion_bind_id is not None:
            owner.unbind('<B1-Motion>', self._drag_motion_bind_id)
            self._drag_motion_bind_id = None
        if self._drag_release_bind_id is not None:
            owner.unbind('<ButtonRelease-1>', self._drag_release_bind_id)
            self._drag_release_bind_id = None

    def _on_captured_drag_motion(self, event: tk.Event) -> str | None:
        if not self._drag_active or self._pending_grab_row_index is None:
            return None
        x_root = int(getattr(event, 'x_root', 0))
        y_root = int(getattr(event, 'y_root', 0))
        self.update_drag_overlay(x_root, y_root)
        if self._on_track_drag_moved is not None:
            self._on_track_drag_moved(x_root, y_root)
        return 'break'

    def _on_captured_drag_release(self, event: tk.Event) -> str | None:
        if not self._drag_active:
            return None
        x_root = int(getattr(event, 'x_root', 0))
        y_root = int(getattr(event, 'y_root', 0))
        if self._on_track_drag_finished is not None:
            self._on_track_drag_finished(x_root, y_root)
        self.clear_drag_state()
        return 'break'

    def _canvas_y_from_root(self, y_root: int) -> int:
        return int(y_root - self.winfo_rooty())

    def _set_drag_insertion_from_local_y(self, local_y: int) -> None:
        if not self._tracks:
            self.set_insertion_index(None)
            return
        if local_y < self._header_height:
            return
        if local_y > self.table_height():
            return
        max_real_body_y = self._header_height + (len(self._tracks) * self._row_height)
        if local_y > max_real_body_y:
            self.set_insertion_index(len(self._tracks))
            return
        self.set_insertion_index(self.insertion_index_at_canvas_y(local_y))

    def _row_index_at(self, y: int) -> int | None:
        if y < self._header_height:
            return None
        row_index = (y - self._header_height) // self._row_height
        if row_index < 0 or row_index >= self.visible_row_count():
            return None
        return int(row_index)

    def _column_index_at(self, x: int) -> int | None:
        if x < 0 or x >= self._width:
            return None
        current_x = 0
        for index, width in enumerate(self._column_widths):
            if current_x <= x < current_x + width:
                return index
            current_x += width
        return None

    def _decode_selection_modifiers(self, event: tk.Event) -> TrackSelectionModifiers:
        state = int(getattr(event, 'state', 0))
        return TrackSelectionModifiers(shift=bool(state & 0x0001), additive=bool(state & 0x0004))
