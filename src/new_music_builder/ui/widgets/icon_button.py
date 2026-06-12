from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage


class FolderIconButton(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        icon_path: str | Path | None,
        command: Callable[[], None] | None = None,
        bg_color: str = spec.FOLDER_BUTTON_BG,
        outline_color: str = spec.FOLDER_BUTTON_OUTLINE,
        size: tuple[int, int] = spec.FOLDER_BUTTON_SIZE,
        outline_width: int = spec.FOLDER_BUTTON_OUTLINE_WIDTH,
        icon_size: tuple[int, int] | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            width=size[0],
            height=size[1],
            bd=0,
            highlightthickness=0,
        )
        self._command = command
        self._image = load_tk_photoimage(icon_path, icon_size)
        self._size = size
        self._outline_width = outline_width
        self._bg_color = bg_color
        self._outline_color = outline_color

        self._draw()
        self.bind('<Button-1>', self._run_command)

    def _draw(self) -> None:
        inset = self._outline_width
        self.create_rectangle(
            0,
            0,
            self._size[0],
            self._size[1],
            outline='',
            fill=self._outline_color,
        )
        self.create_rectangle(
            inset,
            inset,
            self._size[0] - inset,
            self._size[1] - inset,
            outline='',
            fill=self._bg_color,
        )
        if self._image is not None:
            self.create_image(self._size[0] // 2, self._size[1] // 2, image=self._image)

    def _run_command(self, _event: tk.Event | None = None) -> None:
        if self._command is not None:
            self._command()
