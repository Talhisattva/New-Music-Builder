from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from new_music_builder.ui import spec


class MainButton(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        text: str,
        command: Callable[[], None] | None = None,
        variant: str = 'positive',
        size: tuple[int, int] = spec.MAIN_BUTTON_SIZE,
        outline_width: int = spec.MAIN_BUTTON_OUTLINE_WIDTH,
    ) -> None:
        palette = self._palette_for(variant)
        super().__init__(
            parent,
            bg=palette['bg'],
            width=size[0],
            height=size[1],
            bd=0,
            highlightthickness=0,
        )
        self._command = command
        self._size = size
        self._outline_width = outline_width
        self._colors = palette
        self._is_pressed = False

        self._draw(text)
        self._bind_interactions()

    def _palette_for(self, variant: str) -> dict[str, str]:
        if variant == 'negative':
            return {
                'bg': spec.MAIN_BUTTON_NEGATIVE_BG,
                'outline': spec.MAIN_BUTTON_NEGATIVE_OUTLINE,
                'text': spec.MAIN_BUTTON_NEGATIVE_TEXT_COLOR,
                'hover': spec.MAIN_BUTTON_NEGATIVE_HOVER_BG,
                'pressed': spec.MAIN_BUTTON_NEGATIVE_PRESSED_BG,
            }
        return {
            'bg': spec.MAIN_BUTTON_POSITIVE_BG,
            'outline': spec.MAIN_BUTTON_POSITIVE_OUTLINE,
            'text': spec.MAIN_BUTTON_TEXT_COLOR,
            'hover': spec.MAIN_BUTTON_POSITIVE_HOVER_BG,
            'pressed': spec.MAIN_BUTTON_POSITIVE_PRESSED_BG,
        }

    def _draw(self, text: str) -> None:
        inset = self._outline_width
        self._outline_id = self.create_rectangle(
            0,
            0,
            self._size[0],
            self._size[1],
            outline='',
            fill=self._colors['outline'],
        )
        self._fill_id = self.create_rectangle(
            inset,
            inset,
            self._size[0] - inset,
            self._size[1] - inset,
            outline='',
            fill=self._colors['bg'],
        )
        self._text_id = self.create_text(
            self._size[0] // 2,
            self._size[1] // 2,
            text=text,
            fill=self._colors['text'],
            font=('Orbitron Bold', spec.MAIN_BUTTON_FONT_SIZE),
            anchor='c',
        )

    def _bind_interactions(self) -> None:
        for target in (self,):
            target.bind('<Enter>', self._on_enter, add='+')
            target.bind('<Leave>', self._on_leave, add='+')
            target.bind('<ButtonPress-1>', self._on_press, add='+')
            target.bind('<ButtonRelease-1>', self._on_release, add='+')

    def _set_fill(self, color: str) -> None:
        self.itemconfigure(self._fill_id, fill=color)
        self.configure(bg=color)

    def _on_enter(self, _event: tk.Event | None = None) -> None:
        if not self._is_pressed:
            self._set_fill(self._colors['hover'])

    def _on_leave(self, _event: tk.Event | None = None) -> None:
        self._is_pressed = False
        self._set_fill(self._colors['bg'])

    def _on_press(self, _event: tk.Event | None = None) -> str:
        self._is_pressed = True
        self._set_fill(self._colors['pressed'])
        return 'break'

    def _on_release(self, event: tk.Event | None = None) -> str:
        if self._is_pressed:
            self._is_pressed = False
            inside = False
            if event is not None:
                inside = 0 <= event.x <= self._size[0] and 0 <= event.y <= self._size[1]
            if inside:
                self._set_fill(self._colors['hover'])
                if self._command is not None:
                    self._command()
            else:
                self._set_fill(self._colors['bg'])
        return 'break'
