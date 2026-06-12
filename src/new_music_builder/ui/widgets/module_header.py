from __future__ import annotations

import tkinter as tk
from pathlib import Path

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
        x: int = 10,
        y: int = 5,
        icon_size: tuple[int, int] = (20, 20),
        icon_gap: int = 10,
    ) -> None:
        super().__init__(parent, bg=bg_color, bd=0, highlightthickness=0)
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
            font=('Orbitron Medium', 12),
            anchor='w',
        )
        self.text_label.place(x=label_x, y=center_y, anchor='w')
