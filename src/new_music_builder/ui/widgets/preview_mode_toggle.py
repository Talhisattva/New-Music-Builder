from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from new_music_builder.ui import spec


class _ModeButton(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        text: str,
        size: tuple[int, int],
        command: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            width=size[0],
            height=size[1],
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_INACTIVE_BG,
            bd=0,
            highlightthickness=0,
        )
        self._command = command
        self._size = size
        self._draw(text)
        self.bind('<ButtonPress-1>', self._on_press, add='+')
        self.bind('<ButtonRelease-1>', self._on_release, add='+')

    def _draw(self, text: str) -> None:
        self._fill_id = self.create_rectangle(
            0,
            0,
            self._size[0],
            self._size[1],
            outline='',
            fill=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_INACTIVE_BG,
        )
        self.create_text(
            self._size[0] / 2,
            self._size[1] / 2,
            text=text,
            fill=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_TEXT_COLOR,
            font=(
                spec.MEDIA_ROW_LIVE_PREVIEW_MODE_FONT_FAMILY,
                spec.MEDIA_ROW_LIVE_PREVIEW_MODE_FONT_SIZE,
            ),
            anchor='c',
        )

    def set_active(self, active: bool) -> None:
        fill = (
            spec.MEDIA_ROW_LIVE_PREVIEW_MODE_ACTIVE_BG
            if active
            else spec.MEDIA_ROW_LIVE_PREVIEW_MODE_INACTIVE_BG
        )
        self.itemconfigure(self._fill_id, fill=fill)
        self.configure(bg=fill)

    def _on_press(self, _event: tk.Event | None = None) -> str:
        return 'break'

    def _on_release(self, event: tk.Event | None = None) -> str:
        inside = False
        if event is not None:
            inside = 0 <= event.x <= self._size[0] and 0 <= event.y <= self._size[1]
        if inside and self._command is not None:
            self._command()
        return 'break'


class PreviewModeToggle(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        left_text: str,
        right_text: str,
        left_mode: str,
        right_mode: str,
        left_width: int,
        right_width: int,
        height: int,
        initial_mode: str,
        command: Callable[[str], None] | None = None,
        bg_color: str,
        outline_color: str,
        outline_width: int = 1,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=left_width + right_width,
            height=height,
        )
        self.pack_propagate(False)
        self._left_mode = left_mode
        self._right_mode = right_mode
        self._mode = initial_mode if initial_mode in {left_mode, right_mode} else left_mode
        self._command = command

        self.left_border = tk.Frame(self, bg=outline_color, bd=0, highlightthickness=0, width=outline_width, height=height)
        self.left_border.place(x=0, y=0)
        self.right_border = tk.Frame(self, bg=outline_color, bd=0, highlightthickness=0, width=outline_width, height=height)
        self.right_border.place(x=(left_width + right_width) - outline_width, y=0)
        self.top_border = tk.Frame(self, bg=outline_color, bd=0, highlightthickness=0, width=left_width + right_width, height=outline_width)
        self.top_border.place(x=0, y=0)
        self.bottom_border = tk.Frame(self, bg=outline_color, bd=0, highlightthickness=0, width=left_width + right_width, height=outline_width)
        self.bottom_border.place(x=0, y=height - outline_width)
        self.middle_border = tk.Frame(self, bg=outline_color, bd=0, highlightthickness=0, width=outline_width, height=height)
        self.middle_border.place(x=left_width, y=0)

        self.left_button = _ModeButton(
            self,
            text=left_text,
            size=(left_width, height),
            command=lambda: self._select(left_mode),
        )
        self.left_button.place(x=0, y=0)
        self.right_button = _ModeButton(
            self,
            text=right_text,
            size=(right_width, height),
            command=lambda: self._select(right_mode),
        )
        self.right_button.place(x=left_width, y=0)
        self.set_mode(self._mode)

    def get_mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        if mode not in {self._left_mode, self._right_mode}:
            return
        self._mode = mode
        self.left_button.set_active(mode == self._left_mode)
        self.right_button.set_active(mode == self._right_mode)

    def _select(self, mode: str) -> None:
        if mode == self._mode:
            return
        self.set_mode(mode)
        if self._command is not None:
            self._command(mode)
