from __future__ import annotations

import tkinter as tk

from new_music_builder.domain.models import MediaRow
from new_music_builder.ui import spec


class _SegmentedLine(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        segments: list[tuple[str, str]],
        bg_color: str,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[0],
            height=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[1],
        )
        self.pack_propagate(False)
        self._bg_color = bg_color
        self._labels: list[tk.Label] = []

        for text, color in segments:
            label = tk.Label(
                self,
                text=text,
                bg=bg_color,
                fg=color,
                bd=0,
                highlightthickness=0,
                anchor='w',
                justify='left',
                font=(
                    spec.MEDIA_ROW_COLLAPSED_STATS_FONT_FAMILY,
                    spec.MEDIA_ROW_COLLAPSED_STATS_FONT_SIZE,
                ),
            )
            label.pack(side='left', anchor='w')
            self._labels.append(label)

    def set_bg_color(self, color: str) -> None:
        self._bg_color = color
        self.configure(bg=color)
        for label in self._labels:
            label.configure(bg=color)


class CollapsedRowDetails(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        row: MediaRow,
        bg_color: str,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_COLLAPSED_DETAILS_SIZE[0],
            height=spec.MEDIA_ROW_COLLAPSED_DETAILS_SIZE[1],
        )
        self.pack_propagate(False)
        self._bg_color = bg_color

        self.title_label = tk.Label(
            self,
            text=row.media_name,
            bg=bg_color,
            fg=spec.MEDIA_ROW_COLLAPSED_TITLE_TEXT_COLOR,
            bd=0,
            highlightthickness=0,
            anchor='w',
            justify='left',
            font=(
                spec.MEDIA_ROW_COLLAPSED_TITLE_FONT_FAMILY,
                spec.MEDIA_ROW_COLLAPSED_TITLE_FONT_SIZE,
            ),
        )
        self.title_label.place(
            x=0,
            y=0,
            width=spec.MEDIA_ROW_COLLAPSED_TITLE_SIZE[0],
            height=spec.MEDIA_ROW_COLLAPSED_TITLE_SIZE[1],
        )

        self.stats_table = tk.Frame(
            self,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_COLLAPSED_STATS_SIZE[0],
            height=spec.MEDIA_ROW_COLLAPSED_STATS_SIZE[1],
        )
        self.stats_table.place(
            x=spec.MEDIA_ROW_COLLAPSED_STATS_POS[0],
            y=spec.MEDIA_ROW_COLLAPSED_STATS_POS[1],
        )
        self.stats_table.pack_propagate(False)

        self.a_side_label = _SegmentedLine(
            self.stats_table,
            segments=[
                ('A-Side (', spec.MEDIA_ROW_COLLAPSED_STATS_MUTED_COLOR),
                ('0 Songs', spec.MEDIA_ROW_COLLAPSED_STATS_VALUE_COLOR),
                (')', spec.MEDIA_ROW_COLLAPSED_STATS_MUTED_COLOR),
            ],
            bg_color=bg_color,
        )
        self.a_side_label.place(
            x=0,
            y=0,
            width=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[0],
            height=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[1],
        )

        self.a_duration_label = _SegmentedLine(
            self.stats_table,
            segments=[
                ('Duration: ', spec.MEDIA_ROW_COLLAPSED_STATS_MUTED_COLOR),
                ('00:00:00', spec.MEDIA_ROW_COLLAPSED_STATS_VALUE_COLOR),
            ],
            bg_color=bg_color,
        )
        self.a_duration_label.place(
            x=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[0],
            y=0,
            width=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[0],
            height=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[1],
        )

        self.b_side_label = _SegmentedLine(
            self.stats_table,
            segments=[
                ('B-Side (', spec.MEDIA_ROW_COLLAPSED_STATS_MUTED_COLOR),
                ('0 Songs', spec.MEDIA_ROW_COLLAPSED_STATS_VALUE_COLOR),
                (')', spec.MEDIA_ROW_COLLAPSED_STATS_MUTED_COLOR),
            ],
            bg_color=bg_color,
        )
        self.b_side_label.place(
            x=0,
            y=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[1],
            width=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[0],
            height=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[1],
        )

        self.b_duration_label = _SegmentedLine(
            self.stats_table,
            segments=[
                ('Duration: ', spec.MEDIA_ROW_COLLAPSED_STATS_MUTED_COLOR),
                ('00:00:00', spec.MEDIA_ROW_COLLAPSED_STATS_VALUE_COLOR),
            ],
            bg_color=bg_color,
        )
        self.b_duration_label.place(
            x=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[0],
            y=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[1],
            width=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[0],
            height=spec.MEDIA_ROW_COLLAPSED_STATS_CELL_SIZE[1],
        )

    def set_bg_color(self, color: str) -> None:
        self._bg_color = color
        self.configure(bg=color)
        self.title_label.configure(bg=color)
        self.stats_table.configure(bg=color)
        self.a_side_label.set_bg_color(color)
        self.a_duration_label.set_bg_color(color)
        self.b_side_label.set_bg_color(color)
        self.b_duration_label.set_bg_color(color)
