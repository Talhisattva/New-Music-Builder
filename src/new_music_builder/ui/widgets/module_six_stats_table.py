from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

from new_music_builder.domain.models import BuildSummaryStats
from new_music_builder.ui import spec


class ModuleSixStatsTable(tk.Canvas):
    _ROW_LABELS = (
        ('Media Rows', 'media_rows'),
        ('Total Sides', 'total_sides'),
        ('Total Songs', 'total_songs'),
        ('Converted', 'converted'),
        ('Mod Size', 'mod_size_text'),
        ('Errors', 'errors'),
    )

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(
            parent,
            bg=spec.MODULE_MIDGROUND_BG,
            bd=0,
            highlightthickness=0,
            width=spec.MODULE_SIX_STATS_PANE_SIZE[0],
            height=spec.MODULE_SIX_STATS_PANE_SIZE[1],
        )
        self._stats = BuildSummaryStats(mod_size_text='0 KB')
        self._row_font = tkfont.Font(
            family=spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_FONT_FAMILY,
            size=spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_FONT_SIZE,
        )
        self.redraw()

    def set_stats(self, stats: BuildSummaryStats) -> None:
        self._stats = stats
        self.redraw()

    def reset_stats(self) -> None:
        self._stats = BuildSummaryStats(mod_size_text='0 KB')
        self.redraw()

    def redraw(self) -> None:
        self.delete('all')
        width, height = spec.MODULE_SIX_STATS_PANE_SIZE
        row_height = spec.MODULE_SIX_STATS_ROW_HEIGHT
        divider = spec.PHASE_THREE_MODULE_FOUR_QUEUE_DIVIDER_COLOR

        self.configure(width=width, height=height)
        self.create_rectangle(0, 0, width, height, outline='', fill=spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_BG_EVEN)

        for index, (label, attr_name) in enumerate(self._ROW_LABELS):
            row_top = index * row_height
            row_bottom = row_top + row_height
            fill = (
                spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_BG_ODD
                if index % 2 == 0
                else spec.PHASE_THREE_MODULE_FOUR_QUEUE_ROW_BG_EVEN
            )
            self.create_rectangle(0, row_top, width, row_bottom, outline='', fill=fill)
            if index > 0:
                self.create_rectangle(0, row_top, width, row_top + 1, outline='', fill=divider)

            row_center_y = row_top + (row_height / 2)
            label_color = (
                spec.MODULE_SIX_STATS_ERROR_TEXT_COLOR
                if attr_name == 'errors'
                else spec.MODULE_SIX_STATS_TEXT_COLOR
            )
            value_color = (
                spec.MODULE_SIX_STATS_ERROR_TEXT_COLOR
                if attr_name == 'errors'
                else spec.MODULE_SIX_STATS_VALUE_COLOR
            )
            self.create_text(
                spec.MODULE_SIX_STATS_LABEL_X,
                row_center_y,
                text=label,
                fill=label_color,
                font=self._row_font,
                anchor='w',
            )
            value = getattr(self._stats, attr_name)
            self.create_text(
                width - spec.MODULE_SIX_STATS_VALUE_INSET_X,
                row_center_y,
                text=str(value),
                fill=value_color,
                font=self._row_font,
                anchor='e',
            )

        self.create_rectangle(0, height - 1, width, height, outline='', fill=divider)
