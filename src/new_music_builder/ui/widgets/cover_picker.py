from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.icon_button import FolderIconButton
from new_music_builder.ui.widgets.images import load_tk_photoimage_contained


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
        self._cover_size = cover_size
        self._cover_image = None

        self.cover_border = tk.Frame(
            self,
            bg=cover_outline,
            bd=0,
            highlightthickness=0,
            width=cover_size[0],
            height=cover_size[1],
        )
        self.cover_border.place(x=0, y=10)

        self.cover_surface = tk.Label(
            self.cover_border,
            bg=cover_bg,
            bd=0,
            highlightthickness=0,
        )
        self.cover_surface.place(x=1, y=1, width=cover_size[0] - 2, height=cover_size[1] - 2)

        button_x = cover_size[0] - button_center_inset[0] - (button_size[0] // 2)
        self.folder_button = FolderIconButton(
            self,
            icon_path=folder_icon_path,
            command=command,
            size=button_size,
        )
        self.folder_button.place(x=button_x, y=0)

    def set_cover_path(self, cover_path: str | Path | None) -> None:
        self._cover_image = load_tk_photoimage_contained(
            cover_path,
            (self._cover_size[0] - 2, self._cover_size[1] - 2),
        )
        self.cover_surface.configure(image=self._cover_image)

    def set_enabled(self, enabled: bool) -> None:
        self.folder_button.set_enabled(enabled)
