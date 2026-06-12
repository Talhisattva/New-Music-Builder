from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.icon_button import FolderIconButton


class CoverPicker(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        folder_icon_path: str | Path | None,
        command: Callable[[], None] | None = None,
        cover_bg: str = spec.COVER_BG,
        cover_outline: str = spec.COVER_OUTLINE,
        cover_size: tuple[int, int] = spec.COVER_SIZE,
        button_size: tuple[int, int] = spec.FOLDER_BUTTON_SIZE,
        button_center_inset: tuple[int, int] = spec.FOLDER_BUTTON_CENTER_INSET,
    ) -> None:
        width = max(cover_size[0], cover_size[0] - button_center_inset[0] + (button_size[0] // 2))
        height = max(cover_size[1] + 10, button_size[1])
        super().__init__(parent, bg=parent.cget('bg'), bd=0, highlightthickness=0, width=width, height=height)

        self.cover_border = tk.Frame(
            self,
            bg=cover_outline,
            bd=0,
            highlightthickness=0,
            width=cover_size[0],
            height=cover_size[1],
        )
        self.cover_border.place(x=0, y=10)

        self.cover_surface = tk.Frame(
            self.cover_border,
            bg=cover_bg,
            bd=0,
            highlightthickness=0,
            width=cover_size[0] - 2,
            height=cover_size[1] - 2,
        )
        self.cover_surface.place(x=1, y=1)

        button_x = cover_size[0] - button_center_inset[0] - (button_size[0] // 2)
        self.folder_button = FolderIconButton(
            self,
            icon_path=folder_icon_path,
            command=command,
            size=button_size,
        )
        self.folder_button.place(x=button_x, y=0)
