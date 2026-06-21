from __future__ import annotations

import tkinter as tk
from pathlib import Path

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage


class ModuleHeader(tk.Frame):
    """Reusable icon + title strip for module headers."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        text: str,
        icon_path: str | Path | None,
        bg_color: str,
        text_color: str,
        x: int = spec.MODULE_HEADER_X,
        y: int = spec.MODULE_HEADER_Y,
        icon_size: tuple[int, int] = spec.MODULE_HEADER_ICON_SIZE,
        icon_gap: int = spec.MODULE_HEADER_ICON_GAP,
    ) -> None:
        super().__init__(parent, bg=bg_color, bd=0, highlightthickness=0)
        self._icon_size = icon_size
        self._bg_color = bg_color
        self._text_color = text_color
        self._image = load_tk_photoimage(icon_path, icon_size)

        label_x = x + icon_size[0] + icon_gap
        center_y = y + (icon_size[1] // 2)

        if self._image is not None:
            self.icon_label = tk.Label(
                parent,
                image=self._image,
                bg=bg_color,
                bd=0,
                highlightthickness=0,
            )
            self.icon_label.place(x=x, y=y, width=icon_size[0], height=icon_size[1])
        else:
            self.icon_label = None

        self.text_label = tk.Label(
            parent,
            text=text,
            bg=bg_color,
            fg=text_color,
            bd=0,
            highlightthickness=0,
            font=('Orbitron Medium', spec.MODULE_HEADER_FONT_SIZE),
            anchor='w',
        )
        self.text_label.place(x=label_x, y=center_y, anchor='w')

    def set_icon_path(self, icon_path: str | Path | None) -> None:
        self._image = load_tk_photoimage(icon_path, self._icon_size)
        if self.icon_label is not None:
            self.icon_label.configure(image=self._image if self._image is not None else '')
            self.icon_label.image = self._image

    def set_text_color(self, text_color: str) -> None:
        self._text_color = text_color
        self.text_label.configure(fg=text_color)
