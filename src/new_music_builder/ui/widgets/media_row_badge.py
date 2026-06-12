from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from new_music_builder.ui import spec


class MediaRowBadge(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        row_number: int,
        size: tuple[int, int] = spec.MEDIA_ROW_BADGE_SIZE,
        bg_color: str = spec.MEDIA_ROW_BADGE_BG,
        outline_color: str = spec.MEDIA_ROW_BADGE_OUTLINE,
        outline_width: int = spec.MEDIA_ROW_BADGE_OUTLINE_WIDTH,
        text_color: str = spec.MEDIA_ROW_BADGE_TEXT_COLOR,
        command: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            width=size[0],
            height=size[1],
            bd=0,
            highlightthickness=0,
        )
        self._size = size
        self._bg_color = bg_color
        self._hover_bg_color = spec.MEDIA_ROW_BADGE_HOVER_BG
        self._pressed_bg_color = spec.MEDIA_ROW_BADGE_PRESSED_BG
        self._outline_color = outline_color
        self._outline_width = outline_width
        self._text_color = text_color
        self._row_number = row_number
        self._command = command
        self._hovered = False
        self._pressed = False
        self._inner_id: int | None = None

        self._draw()
        self._bind_interactions()

    def _font_size_for_number(self, row_number: int) -> int:
        digits = len(str(abs(row_number)))
        if digits >= 4:
            return spec.MEDIA_ROW_BADGE_FONT_SIZE_4_DIGITS
        if digits == 3:
            return spec.MEDIA_ROW_BADGE_FONT_SIZE_3_DIGITS
        return spec.MEDIA_ROW_BADGE_FONT_SIZE

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
        self._inner_id = self.create_rectangle(
            inset,
            inset,
            self._size[0] - inset,
            self._size[1] - inset,
            outline='',
            fill=self._bg_color,
        )
        self.create_text(
            (self._size[0] // 2) + spec.MEDIA_ROW_BADGE_TEXT_OFFSET[0],
            (self._size[1] // 2) + spec.MEDIA_ROW_BADGE_TEXT_OFFSET[1],
            text=str(self._row_number),
            fill=self._text_color,
            font=(spec.MEDIA_ROW_BADGE_FONT_FAMILY, self._font_size_for_number(self._row_number)),
            anchor='c',
        )

    def _bind_interactions(self) -> None:
        for sequence, handler in (
            ('<Enter>', self._on_enter),
            ('<Leave>', self._on_leave),
            ('<ButtonPress-1>', self._on_press),
            ('<ButtonRelease-1>', self._on_release),
        ):
            self.bind(sequence, handler)

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._apply_visual_state()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._pressed = False
        self._apply_visual_state()

    def _on_press(self, _event: tk.Event) -> None:
        self._pressed = True
        self._apply_visual_state()

    def _on_release(self, _event: tk.Event) -> None:
        should_invoke = self._pressed and self._event_within_bounds(_event)
        self._pressed = False
        self._hovered = (0 <= self.winfo_pointerx() - self.winfo_rootx() < self._size[0]) and (
            0 <= self.winfo_pointery() - self.winfo_rooty() < self._size[1]
        )
        self._apply_visual_state()
        if should_invoke and self._command is not None:
            self._command()

    def _apply_visual_state(self) -> None:
        if self._inner_id is None:
            return
        fill_color = self._bg_color
        if self._pressed:
            fill_color = self._pressed_bg_color
        elif self._hovered:
            fill_color = self._hover_bg_color
        self.itemconfigure(self._inner_id, fill=fill_color)

    def _event_within_bounds(self, event: tk.Event) -> bool:
        return 0 <= event.x < self._size[0] and 0 <= event.y < self._size[1]
