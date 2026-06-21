from __future__ import annotations

from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont

from PIL import ImageTk

from new_music_builder.domain.models import ConversionSideGroup
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage


class ModuleFourQueueTable(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        check_icon_path: str | None = None,
        converting_icon_path: str | None = None,
        queued_icon_path: str | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=spec.PHASE_THREE_MODULE_FOUR_QUEUE_BG,
            bd=0,
            highlightthickness=0,
            width=spec.PHASE_THREE_MODULE_FOUR_QUEUE_VIEWPORT_SIZE[0],
            height=spec.PHASE_THREE_MODULE_FOUR_QUEUE_VIEWPORT_SIZE[1],
        )
        self._width = spec.PHASE_THREE_MODULE_FOUR_QUEUE_VIEWPORT_SIZE[0]
        self._min_height = spec.PHASE_THREE_MODULE_FOUR_QUEUE_VIEWPORT_SIZE[1]
        self._header_height = spec.PHASE_THREE_MODULE_FOUR_QUEUE_HEADER_HEIGHT
        self._row_height = spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_HEIGHT
        self._base_column_widths = spec.PHASE_THREE_MODULE_FOUR_QUEUE_COLUMNS
        self._column_widths = self._base_column_widths
        self._divider_color = spec.PHASE_THREE_MODULE_FOUR_QUEUE_DIVIDER_COLOR
        self._groups: list[ConversionSideGroup] = []
        self._header_font = (
            spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_FONT_FAMILY,
            spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_FONT_SIZE,
        )
        self._media_font = tkfont.Font(
            family=spec.PHASE_THREE_MODULE_FOUR_MEDIA_FONT_FAMILY,
            size=spec.PHASE_THREE_MODULE_FOUR_MEDIA_FONT_SIZE,
        )
        self._media_side_font = tkfont.Font(
            family=spec.PHASE_THREE_MODULE_FOUR_MEDIA_FONT_FAMILY,
            size=spec.PHASE_THREE_MODULE_FOUR_MEDIA_SIDE_FONT_SIZE,
        )
        self._row_font = tkfont.Font(
            family=spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_FONT_FAMILY,
            size=spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_FONT_SIZE,
        )
        self._percent_font = tkfont.Font(
            family=spec.PHASE_THREE_MODULE_FOUR_PERCENT_FONT_FAMILY,
            size=spec.PHASE_THREE_MODULE_FOUR_PERCENT_FONT_SIZE,
        )
        self._status_font = tkfont.Font(
            family=spec.PHASE_THREE_MODULE_FOUR_STATUS_FONT_FAMILY,
            size=spec.PHASE_THREE_MODULE_FOUR_STATUS_FONT_SIZE,
        )
        self._done_icon = self._load_icon(check_icon_path)
        self._converting_icon = self._load_icon(converting_icon_path)
        self._queued_icon = self._load_icon(queued_icon_path)
        self._last_song_column_width = self._column_widths[1]
        self.redraw()

    def resize(self, width: int) -> None:
        extra_width = max(0, width - spec.PHASE_THREE_MODULE_FOUR_QUEUE_VIEWPORT_SIZE[0])
        columns = list(self._base_column_widths)
        columns[1] = self._base_column_widths[1] + extra_width
        if columns[1] == self._last_song_column_width:
            return
        self._column_widths = tuple(columns)
        self._width = sum(self._column_widths)
        self._last_song_column_width = columns[1]
        self.redraw()

    def _load_icon(self, path: str | None) -> ImageTk.PhotoImage | None:
        return load_tk_photoimage(path)

    def set_groups(self, groups: list[ConversionSideGroup]) -> None:
        self._groups = list(groups)
        self.redraw()

    def append_group(self, group: ConversionSideGroup) -> None:
        self._groups.append(group)
        self.redraw()

    def update_song_progress(self, row_id: int, side: str, song_index: int, percent: int, status: str, size_label: str) -> None:
        for group in self._groups:
            if group.row_id != row_id or group.side != side:
                continue
            if 0 <= song_index < len(group.songs):
                song = group.songs[song_index]
                song.percent = percent
                song.status = status  # type: ignore[assignment]
                song.size_label = size_label
                self.redraw()
            return

    def clear_groups(self) -> None:
        self._groups = []
        self.redraw()

    def table_height(self) -> int:
        total_song_rows = sum(len(group.songs) for group in self._groups)
        body_height = total_song_rows * self._row_height
        return max(self._min_height, self._header_height + body_height)

    def redraw(self) -> None:
        self.delete('all')
        height = self.table_height()
        self.configure(width=self._width, height=height)
        self._draw_background(height)
        self._draw_groups(height)
        self._draw_column_dividers(height)
        self._draw_header_divider()
        self._draw_header()

    def _draw_background(self, height: int) -> None:
        self.create_rectangle(
            0,
            0,
            self._width,
            self._header_height,
            outline='',
            fill=spec.PHASE_THREE_MODULE_FOUR_QUEUE_HEADER_BG,
        )
        self.create_rectangle(
            0,
            self._header_height,
            self._width,
            height,
            outline='',
            fill=spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_BG_EVEN,
        )

    def _draw_header(self) -> None:
        current_x = 0
        center_y = self._header_height / 2
        for label, width in zip(spec.PHASE_THREE_MODULE_FOUR_QUEUE_HEADER_LABELS, self._column_widths):
            self.create_text(
                current_x + (width / 2),
                center_y,
                text=label,
                fill=spec.PHASE_THREE_MODULE_FOUR_QUEUE_HEADER_TEXT_COLOR,
                font=self._header_font,
                anchor='c',
            )
            current_x += width

    def _draw_groups(self, canvas_height: int) -> None:
        body_y = self._header_height
        for group_index, group in enumerate(self._groups):
            song_count = len(group.songs)
            if song_count <= 0:
                continue

            row_count = song_count
            group_height = row_count * self._row_height
            group_bottom = body_y + group_height
            group_fill = self._group_fill(group_index)
            self.create_rectangle(0, body_y, self._width, group_bottom, outline='', fill=group_fill)
            self.create_rectangle(0, body_y, self._column_widths[0], group_bottom, outline='', fill=group_fill)
            self.create_rectangle(
                0,
                body_y,
                self._column_widths[0],
                body_y + 1,
                outline='',
                fill=self._divider_color,
            )

            media_center_x = self._column_widths[0] / 2
            media_name, _, side_label = group.display_label.partition('\n')
            media_label = self._truncate_text(
                f'{media_name} ({side_label})',
                self._column_widths[0] - 10,
                font=self._media_font,
            )
            media_center_y = body_y + (self._row_height / 2)

            self.create_text(
                media_center_x,
                media_center_y,
                text=media_label,
                fill=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_TEXT_COLOR,
                font=self._media_font,
                anchor='c',
            )

            for row_index in range(row_count):
                row_top = body_y + (row_index * self._row_height)
                row_center_y = row_top + (self._row_height / 2)
                if row_index > 0:
                    self.create_rectangle(
                        self._column_widths[0],
                        row_top,
                        self._width,
                        row_top + 1,
                        outline='',
                        fill=self._divider_color,
                    )
                if row_index < song_count:
                    song = group.songs[row_index]
                    self._draw_song_cell(song.queue_index, song.song_label, row_center_y)
                    self._draw_progress_cell(song.percent, song.status, row_center_y)
                    self._draw_status_cell(song.status, row_center_y)

            self.create_rectangle(
                0,
                group_bottom - 1,
                self._width,
                group_bottom,
                outline='',
                fill=self._divider_color,
            )
            body_y = group_bottom

        if body_y < canvas_height:
            self.create_rectangle(
                0,
                body_y,
                self._width,
                canvas_height,
                outline='',
                fill=spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_BG_EVEN,
            )

    def _draw_column_dividers(self, height: int) -> None:
        column_x = 0
        for width in self._column_widths[:-1]:
            column_x += width
            self.create_rectangle(
                column_x,
                0,
                column_x + 1,
                height,
                outline='',
                fill=self._divider_color,
            )

    def _draw_header_divider(self) -> None:
        self.create_rectangle(
            0,
            self._header_height,
            self._width,
            self._header_height + 1,
            outline='',
            fill=self._divider_color,
        )

    def _draw_song_cell(self, queue_index: int, song_label: str, row_center_y: float) -> None:
        column_left = self._column_left_x(1)
        available_width = self._column_widths[1] - 12
        text = self._truncate_text(f'{queue_index}.  {song_label}', available_width, font=self._row_font)
        self.create_text(
            column_left + 6,
            row_center_y,
            text=text,
            fill=spec.MEDIA_ROW_SONGLIST_TABLE_ROW_TEXT_COLOR,
            font=self._row_font,
            anchor='w',
        )

    def _draw_progress_cell(self, percent: int, status: str, row_center_y: float) -> None:
        column_left = self._column_left_x(2)
        bar_x = column_left + 5
        bar_y = int(round(row_center_y - (spec.PHASE_THREE_MODULE_FOUR_PROGRESS_BAR_SIZE[1] / 2)))
        self._draw_progress_bar(bar_x, bar_y, percent, status)
        percent_text = f'{self._rounded_percent(percent)}%'
        percent_right = bar_x + spec.PHASE_THREE_MODULE_FOUR_PROGRESS_BAR_SIZE[0] + spec.PHASE_THREE_MODULE_FOUR_PERCENT_WIDTH
        self.create_text(
            percent_right,
            row_center_y,
            text=percent_text,
            fill=spec.PHASE_THREE_MODULE_FOUR_PERCENT_TEXT_COLOR,
            font=self._percent_font,
            anchor='e',
        )

    def _draw_progress_bar(self, x: int, y: int, percent: int, status: str) -> None:
        bar_width, bar_height = spec.PHASE_THREE_MODULE_FOUR_PROGRESS_BAR_SIZE
        self.create_rectangle(x, y, x + bar_width, y + bar_height, outline='', fill=spec.PHASE_THREE_MODULE_FOUR_PROGRESS_BG)
        completed_segments = max(0, min(10, self._rounded_percent(percent) // 10))
        fill_color = spec.PHASE_THREE_MODULE_FOUR_PROGRESS_ACTIVE_FILL
        border_color = spec.PHASE_THREE_MODULE_FOUR_PROGRESS_ACTIVE_BORDER
        if status == 'done':
            completed_segments = 10
            fill_color = spec.PHASE_THREE_MODULE_FOUR_PROGRESS_DONE_FILL
            border_color = spec.PHASE_THREE_MODULE_FOUR_PROGRESS_DONE_BORDER

        segment_size = spec.PHASE_THREE_MODULE_FOUR_PROGRESS_SEGMENT_SIZE
        for segment_index in range(completed_segments):
            segment_left = x + (segment_index * segment_size)
            self.create_rectangle(
                segment_left,
                y,
                segment_left + segment_size,
                y + bar_height,
                outline='',
                fill=fill_color,
            )

        for divider_index in range(1, 10):
            divider_x = x + (divider_index * segment_size)
            divider_color = spec.PHASE_THREE_MODULE_FOUR_PROGRESS_DORMANT_BORDER
            if divider_index <= completed_segments:
                divider_color = border_color
            self.create_line(divider_x, y, divider_x, y + bar_height, fill=divider_color)

    def _draw_status_cell(self, status: str, row_center_y: float) -> None:
        column_left = self._column_left_x(3)
        icon = self._queued_icon
        text = 'QUEUED'
        text_color = spec.PHASE_THREE_MODULE_FOUR_STATUS_QUEUED_COLOR
        if status == 'done':
            icon = self._done_icon
            text = 'DONE'
            text_color = spec.PHASE_THREE_MODULE_FOUR_STATUS_DONE_COLOR
        elif status == 'converting':
            icon = self._converting_icon
            text = 'CONVERTING'

        if icon is not None:
            self.create_image(
                column_left + spec.PHASE_THREE_MODULE_FOUR_STATUS_ICON_CENTER_X,
                row_center_y,
                image=icon,
                anchor='c',
            )
        self.create_text(
            column_left + spec.PHASE_THREE_MODULE_FOUR_STATUS_TEXT_X,
            row_center_y,
            text=text,
            fill=text_color,
            font=self._status_font,
            anchor='w',
        )

    def _column_left_x(self, column_index: int) -> int:
        return sum(self._column_widths[:column_index])

    def _group_fill(self, group_index: int) -> str:
        return (
            spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_BG_ODD
            if group_index % 2 == 0
            else spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_BG_EVEN
        )

    def _rounded_percent(self, percent: int) -> int:
        bounded = max(0, min(100, percent))
        return int(round(bounded / 10.0) * 10)

    def _truncate_text(self, text: str, max_width: int, *, font: tkfont.Font | None = None) -> str:
        active_font = font or self._row_font
        if active_font.measure(text) <= max_width:
            return text
        ellipsis = '...'
        truncated = text
        while truncated and active_font.measure(f'{truncated}{ellipsis}') > max_width:
            truncated = truncated[:-1]
        return f'{truncated}{ellipsis}' if truncated else ellipsis
