from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from new_music_builder.domain.models import MediaRow
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.main_button import MainButton


class MediaSideToggle(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        row: MediaRow,
        bg_color: str,
        on_side_selected: Callable[[str], None] | None = None,
    ) -> None:
        width = (spec.MEDIA_ROW_SIDE_TOGGLE_BUTTON_SIZE[0] * 2) + spec.MEDIA_ROW_SIDE_TOGGLE_GAP_X
        height = spec.MEDIA_ROW_SIDE_TOGGLE_BUTTON_SIZE[1]
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=width,
            height=height,
        )
        self.pack_propagate(False)
        self._bg_color = bg_color
        self._row = row
        self._selected_side = row.selected_side
        self._on_side_selected = on_side_selected

        self.a_button = MainButton(
            self,
            text='A-Side',
            command=lambda: self._select_side('A'),
            size=spec.MEDIA_ROW_SIDE_TOGGLE_BUTTON_SIZE,
        )
        self.a_button.place(x=0, y=0)

        self.b_button = MainButton(
            self,
            text='B-side',
            command=lambda: self._select_side('B'),
            size=spec.MEDIA_ROW_SIDE_TOGGLE_BUTTON_SIZE,
        )
        self.b_button.place(
            x=spec.MEDIA_ROW_SIDE_TOGGLE_BUTTON_SIZE[0] + spec.MEDIA_ROW_SIDE_TOGGLE_GAP_X,
            y=0,
        )

        self._apply_state()

    def _select_side(self, side: str) -> None:
        if side == self._selected_side:
            return
        self._selected_side = side
        self._apply_state()
        if self._on_side_selected is not None:
            self._on_side_selected(side)

    def _apply_state(self) -> None:
        self.a_button.set_active(self._selected_side == 'A')
        self.b_button.set_active(self._selected_side == 'B')

    def set_bg_color(self, color: str) -> None:
        self._bg_color = color
        self.configure(bg=color)

    def set_enabled(self, enabled: bool) -> None:
        self.a_button.set_enabled(enabled)
        self.b_button.set_enabled(enabled)

    def tooltip_widgets_for_side(self, side: str) -> tuple[tk.Misc, ...]:
        if side == 'A':
            return (self.a_button,)
        return (self.b_button,)

    def set_row(self, row: MediaRow) -> None:
        self._row = row
        self._selected_side = row.selected_side
        self._apply_state()
