from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont

from PIL import Image, ImageTk

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
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[0],
            height=spec.MEDIA_ROW_SONGLIST_TABLE_SIZE[1],
        )
        self._bg_color = bg_color
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
        self._on_track_selected = on_track_selected
        self._on_track_remove_requested = on_track_remove_requested
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

    def _visible_row_count(self) -> int:
        return max(self._min_row_count, len(self._tracks))

    def _table_height(self) -> int:
        return self._header_height + (self._visible_row_count() * self._row_height)

    def set_tracks(self, tracks: list[TrackEntry]) -> None:
        self._tracks = list(tracks)
        self._selected_indices = {index for index in self._selected_indices if index < len(self._tracks)}
        if self._hover_index is not None and self._hover_index >= self._visible_row_count():
            self._hover_index = None
        self.redraw()

    def set_selection_state(self, selected_indices: set[int]) -> None:
        filtered = {index for index in selected_indices if index < len(self._tracks)}
        if filtered == self._selected_indices:
            return
        self._selected_indices = filtered
        self.redraw()

    def redraw(self) -> None:
        self.delete('all')
        height = self._table_height()
        self.configure(height=height, width=self._width)
        self._draw_background(height)
        self._draw_header_content()
        self._draw_track_rows()

    def _draw_background(self, height: int) -> None:
        self.create_rectangle(
            0,
            0,
            self._width,
            self._header_height,
            outline='',
            fill=spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_BG,
        )

        body_y = self._header_height
        for row_index in range(self._visible_row_count()):
            row_top = body_y + (row_index * self._row_height)
            row_bottom = row_top + self._row_height
            fill = self._row_fill(row_index)
            self.create_rectangle(
                0,
                row_top,
                self._width,
                row_bottom,
                outline='',
                fill=fill,
            )

        column_x = 0
        for width in self._column_widths[:-1]:
            column_x += width
            self.create_rectangle(
                column_x,
                0,
                column_x + self._divider_width,
                height,
                outline='',
                fill=self._divider_color,
            )

        self.create_rectangle(
            0,
            self._header_height,
            self._width,
            self._header_height + self._divider_width,
            outline='',
            fill=self._divider_color,
        )

        for row_index in range(1, self._visible_row_count()):
            row_divider_y = self._header_height + (row_index * self._row_height)
            self.create_rectangle(
                0,
                row_divider_y,
                self._width,
                row_divider_y + self._divider_width,
                outline='',
                fill=self._divider_color,
            )

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
                    font=(
                        spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_FONT_FAMILY,
                        spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_FONT_SIZE,
                    ),
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
        if self._hover_index == row_index:
            return spec.MEDIA_ROW_SONGLIST_TABLE_ROW_HOVER_BG
        return (
            spec.MEDIA_ROW_SONGLIST_TABLE_ROW_BG_ODD
            if row_index % 2 == 0
            else spec.MEDIA_ROW_SONGLIST_TABLE_ROW_BG_EVEN
        )

    def _column_left_x(self, column_index: int) -> int:
        return sum(self._column_widths[:column_index])

    def _draw_grab_icon(self, row_center_y: float) -> None:
        if self._grab_icon_image is None:
            return
        self.create_image(self._column_center_x(0), row_center_y, image=self._grab_icon_image, anchor='c')

    def _draw_ogg_status(self, track: TrackEntry, row_center_y: float) -> None:
        if self._table_check_icon_image is None:
            return
        if Path(track.source_path).suffix.lower() != '.ogg':
            return
        self.create_image(self._column_center_x(1), row_center_y, image=self._table_check_icon_image, anchor='c')

    def _draw_song_name(self, track: TrackEntry, row_center_y: float) -> None:
        column_left = self._column_left_x(2)
        available_width = self._column_widths[2] - 12
        text = self._truncate_text(track.display_label or Path(track.source_path).stem, available_width)
        self.create_text(
            column_left + 6,
            row_center_y,
            text=text,
            fill=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_TEXT_COLOR,
            font=self._row_font,
            anchor='w',
        )

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
        self.create_text(
            self._column_center_x(4),
            row_center_y,
            text=track.duration,
            fill=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_TEXT_COLOR,
            font=self._row_font,
            anchor='c',
        )

    def _draw_preview_icon(self, row_center_y: float) -> None:
        if self._preview_audio_icon_image is None:
            return
        self.create_image(self._column_center_x(3), row_center_y, image=self._preview_audio_icon_image, anchor='c')

    def _draw_remove_marker(self, row_center_y: float) -> None:
        self.create_text(
            self._column_center_x(5),
            row_center_y,
            text='X',
            fill=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_TEXT_COLOR,
            font=self._remove_font,
            anchor='c',
        )

    def _bind_interactions(self) -> None:
        self.bind('<Motion>', self._on_motion)
        self.bind('<Leave>', self._on_leave)
        self.bind('<ButtonRelease-1>', self._on_click)

    def _on_motion(self, event: tk.Event) -> None:
        hover_index = self._row_index_at(int(getattr(event, 'y', -1)))
        if hover_index == self._hover_index:
            return
        self._hover_index = hover_index
        self.redraw()

    def _on_leave(self, _event: tk.Event) -> None:
        if self._hover_index is None:
            return
        self._hover_index = None
        self.redraw()

    def _on_click(self, event: tk.Event) -> str:
        row_index = self._row_index_at(int(getattr(event, 'y', -1)))
        if row_index is None or row_index >= len(self._tracks):
            return 'break'
        column_index = self._column_index_at(int(getattr(event, 'x', -1)))
        if column_index == 5 and self._on_track_remove_requested is not None:
            self._on_track_remove_requested(row_index)
            return 'break'
        if self._on_track_selected is not None:
            self._on_track_selected(row_index, self._decode_selection_modifiers(event))
        return 'break'

    def _row_index_at(self, y: int) -> int | None:
        if y < self._header_height:
            return None
        row_index = (y - self._header_height) // self._row_height
        if row_index < 0 or row_index >= self._visible_row_count():
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
        return TrackSelectionModifiers(
            shift=bool(state & 0x0001),
            additive=bool(state & 0x0004),
        )
