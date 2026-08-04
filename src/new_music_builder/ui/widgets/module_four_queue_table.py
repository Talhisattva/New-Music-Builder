from __future__ import annotations

from dataclasses import dataclass
import math
import tkinter as tk
import tkinter.font as tkfont

from PIL import ImageTk

from new_music_builder.domain.models import ConversionSideGroup, ConversionSongProgress
from new_music_builder.platform.i18n import t
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage


@dataclass(slots=True)
class _QueueRenderRow:
    item_label: str
    item_color: str
    song: ConversionSongProgress
    row_index: int


class ModuleFourQueueTable(tk.Canvas):
    _ROW_OVERSCAN = 2

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
        self._viewport_height = spec.PHASE_THREE_MODULE_FOUR_QUEUE_VIEWPORT_SIZE[1]
        self._min_height = spec.PHASE_THREE_MODULE_FOUR_QUEUE_VIEWPORT_SIZE[1]
        self._header_height = spec.PHASE_THREE_MODULE_FOUR_QUEUE_HEADER_HEIGHT
        self._row_height = spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_HEIGHT
        self._base_column_widths = spec.PHASE_THREE_MODULE_FOUR_QUEUE_COLUMNS
        self._column_widths = self._base_column_widths
        self._divider_color = spec.PHASE_THREE_MODULE_FOUR_QUEUE_DIVIDER_COLOR
        self._groups: list[ConversionSideGroup] = []
        self._visible_rows: list[_QueueRenderRow] = []
        self._scroll_offset = 0
        self._header_font = (
            spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_FONT_FAMILY,
            spec.MEDIA_ROW_SONGLIST_TABLE_HEADER_FONT_SIZE,
        )
        self._media_font = tkfont.Font(
            family=spec.PHASE_THREE_MODULE_FOUR_MEDIA_FONT_FAMILY,
            size=spec.PHASE_THREE_MODULE_FOUR_MEDIA_FONT_SIZE,
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

    def resize(self, width: int, viewport_height: int | None = None) -> None:
        extra_width = max(0, width - spec.PHASE_THREE_MODULE_FOUR_QUEUE_VIEWPORT_SIZE[0])
        columns = list(self._base_column_widths)
        columns[1] = self._base_column_widths[1] + extra_width
        self._column_widths = tuple(columns)
        self._width = sum(self._column_widths)
        self._last_song_column_width = columns[1]
        if viewport_height is not None:
            self._viewport_height = max(1, int(viewport_height))
        self.redraw()

    def set_groups(self, groups: list[ConversionSideGroup]) -> None:
        self._groups = list(groups)
        self._visible_rows = self._flatten_rows()
        self.redraw()

    def set_scroll_offset(self, offset: int) -> None:
        self._scroll_offset = max(0, int(offset))
        self.redraw()

    def total_content_height(self) -> int:
        return max(self._min_height, self._header_height + (len(self._visible_rows) * self._row_height))

    def redraw(self) -> None:
        self.delete('all')
        self.configure(width=self._width, height=self._viewport_height)
        self._draw_background()
        self._draw_column_dividers()
        self._draw_visible_content()

    def _load_icon(self, path: str | None) -> ImageTk.PhotoImage | None:
        return load_tk_photoimage(path)

    def _flatten_rows(self) -> list[_QueueRenderRow]:
        rows: list[_QueueRenderRow] = []
        for group in self._groups:
            item_label = group.queue_label or group.display_label
            if group.show_side_suffix and group.side_display_text:
                item_label = f"{item_label} ({group.side_display_text})"
            item_color = (
                spec.PHASE_THREE_MODULE_FOUR_TYPE_SINGLES_COLOR
                if group.queue_mode == "singles"
                else spec.PHASE_THREE_MODULE_FOUR_TYPE_MIXTAPE_COLOR
            )
            for song in group.songs:
                rows.append(
                    _QueueRenderRow(
                        item_label=item_label,
                        item_color=item_color,
                        song=song,
                        row_index=len(rows),
                    )
                )
        return rows

    def _draw_background(self) -> None:
        self.create_rectangle(
            0,
            0,
            self._width,
            self._viewport_height,
            outline='',
            fill=spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_BG_EVEN,
        )

    def _draw_column_dividers(self) -> None:
        column_x = 0
        for width in self._column_widths[:-1]:
            column_x += width
            self.create_rectangle(
                column_x,
                0,
                column_x + 1,
                self._viewport_height,
                outline='',
                fill=self._divider_color,
            )

    def _draw_visible_content(self) -> None:
        visible_top = self._scroll_offset
        visible_bottom = visible_top + self._viewport_height
        self._draw_header(visible_top)
        if visible_bottom <= self._header_height:
            return

        body_top = max(self._header_height, visible_top)
        first_row = max(0, (body_top - self._header_height) // self._row_height)
        visible_row_count = max(
            1,
            math.ceil(max(0, visible_bottom - max(self._header_height, visible_top)) / self._row_height),
        )
        start_index = max(0, first_row - self._ROW_OVERSCAN)
        end_index = min(len(self._visible_rows), first_row + visible_row_count + self._ROW_OVERSCAN)

        for render_row in self._visible_rows[start_index:end_index]:
            row_top = self._header_height + (render_row.row_index * self._row_height) - self._scroll_offset
            row_bottom = row_top + self._row_height
            if row_bottom < 0 or row_top > self._viewport_height:
                continue
            self._draw_row(render_row, row_top)

    def _draw_header(self, visible_top: int) -> None:
        header_y = -visible_top
        header_bottom = header_y + self._header_height
        if header_bottom <= 0 or header_y >= self._viewport_height:
            return
        self.create_rectangle(
            0,
            header_y,
            self._width,
            header_bottom,
            outline='',
            fill=spec.PHASE_THREE_MODULE_FOUR_QUEUE_HEADER_BG,
        )
        self.create_rectangle(
            0,
            header_bottom - 1,
            self._width,
            header_bottom,
            outline='',
            fill=self._divider_color,
        )
        current_x = 0
        center_y = header_y + (self._header_height / 2)
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

    def _draw_row(self, render_row: _QueueRenderRow, row_top: int) -> None:
        row_bottom = row_top + self._row_height
        row_fill = self._group_fill(render_row.row_index)
        self.create_rectangle(0, row_top, self._width, row_bottom, outline='', fill=row_fill)
        self.create_rectangle(
            0,
            row_bottom - 1,
            self._width,
            row_bottom,
            outline='',
            fill=self._divider_color,
        )
        row_center_y = row_top + (self._row_height / 2)
        self._draw_item_cell(render_row.item_label, render_row.item_color, row_center_y)
        self._draw_song_cell(render_row.song.queue_index, render_row.song.song_label, row_center_y)
        self._draw_progress_cell(render_row.song.percent, render_row.song.status, row_center_y)
        self._draw_status_cell(render_row.song.status, row_center_y)

    def _draw_item_cell(self, item_label: str, item_color: str, row_center_y: float) -> None:
        column_left = self._column_left_x(0)
        available_width = self._column_widths[0] - 12
        text = self._truncate_text(item_label, available_width, font=self._media_font)
        self.create_text(
            column_left + 6,
            row_center_y,
            text=text,
            fill=item_color,
            font=self._media_font,
            anchor='w',
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
        elif status == 'failed':
            fill_color = spec.MAIN_BUTTON_NEGATIVE_TEXT_COLOR
            border_color = spec.MAIN_BUTTON_NEGATIVE_OUTLINE

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
        text = t('QUEUED')
        text_color = spec.PHASE_THREE_MODULE_FOUR_STATUS_QUEUED_COLOR
        if status == 'done':
            icon = self._done_icon
            text = t('DONE')
            text_color = spec.PHASE_THREE_MODULE_FOUR_STATUS_DONE_COLOR
        elif status == 'converting':
            icon = self._converting_icon
            text = t('CONVERTING')
        elif status == 'failed':
            icon = None
            text = t('ERROR')
            text_color = spec.MAIN_BUTTON_NEGATIVE_TEXT_COLOR

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

    def row_index_for_group_song(self, group_index: int, song_index: int) -> int | None:
        if group_index < 0 or group_index >= len(self._groups):
            return None
        if song_index < 0 or song_index >= len(self._groups[group_index].songs):
            return None
        return sum(len(group.songs) for group in self._groups[:group_index]) + song_index

    def row_bounds_for_index(self, row_index: int) -> tuple[int, int] | None:
        if row_index < 0 or row_index >= len(self._visible_rows):
            return None
        top = self._header_height + (row_index * self._row_height)
        return (top, top + self._row_height)

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
