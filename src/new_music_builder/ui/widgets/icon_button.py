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
        hover_bg_color: str = spec.FOLDER_BUTTON_HOVER_BG,
        pressed_bg_color: str = spec.FOLDER_BUTTON_PRESSED_BG,
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
        self._hover_bg_color = hover_bg_color
        self._pressed_bg_color = pressed_bg_color
        self._outline_color = outline_color
        self._is_pressed = False

        self._draw()
        self._bind_interactions()

    def _draw(self) -> None:
        inset = self._outline_width
        self._outline_id = self.create_rectangle(
            0,
            0,
            self._size[0],
            self._size[1],
            outline='',
            fill=self._outline_color,
        )
        self._fill_id = self.create_rectangle(
            inset,
            inset,
            self._size[0] - inset,
            self._size[1] - inset,
            outline='',
            fill=self._bg_color,
        )
        if self._image is not None:
            self.create_image(self._size[0] // 2, self._size[1] // 2, image=self._image)

    def _bind_interactions(self) -> None:
        self.bind('<Enter>', self._on_enter, add='+')
        self.bind('<Leave>', self._on_leave, add='+')
        self.bind('<ButtonPress-1>', self._on_press, add='+')
        self.bind('<ButtonRelease-1>', self._on_release, add='+')

    def _set_fill(self, color: str) -> None:
        self.itemconfigure(self._fill_id, fill=color)
        self.configure(bg=color)

    def _on_enter(self, _event: tk.Event | None = None) -> None:
        if not self._is_pressed:
            self._set_fill(self._hover_bg_color)

    def _on_leave(self, _event: tk.Event | None = None) -> None:
        self._is_pressed = False
        self._set_fill(self._bg_color)

    def _on_press(self, _event: tk.Event | None = None) -> str:
        self._is_pressed = True
        self._set_fill(self._pressed_bg_color)
        return 'break'

    def _on_release(self, event: tk.Event | None = None) -> str:
        if self._is_pressed:
            self._is_pressed = False
            inside = False
            if event is not None:
                inside = 0 <= event.x <= self._size[0] and 0 <= event.y <= self._size[1]
            if inside:
                self._set_fill(self._hover_bg_color)
                if self._command is not None:
                    self._command()
            else:
                self._set_fill(self._bg_color)
        return 'break'
