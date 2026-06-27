from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Callable

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage


class ModuleActionHeader(tk.Frame):
    """Reusable full-width action strip for module-shell overlays."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        width: int,
        text: str,
        icon_path: str | Path | None,
        right_text: str | None = None,
        command: Callable[[], None] | None = None,
        bg_color: str = spec.MODULE_ACTION_HEADER_BG,
        hover_bg_color: str = spec.MODULE_ACTION_HEADER_HOVER_BG,
        pressed_bg_color: str = spec.MODULE_ACTION_HEADER_PRESSED_BG,
        text_color: str = spec.MODULE_ACTION_HEADER_TEXT_COLOR,
        right_text_color: str = spec.MODULE_ACTION_HEADER_RIGHT_TEXT_COLOR,
        right_text_font_size: int = spec.MODULE_ACTION_HEADER_RIGHT_FONT_SIZE,
        height: int = spec.MODULE_ACTION_HEADER_HEIGHT,
        icon_size: tuple[int, int] = spec.MODULE_HEADER_ICON_SIZE,
        icon_x: int = spec.MODULE_ACTION_HEADER_ICON_X,
        icon_y: int = spec.MODULE_ACTION_HEADER_ICON_Y,
        icon_gap: int = spec.MODULE_HEADER_ICON_GAP,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=width,
            height=height,
            cursor='hand2' if command is not None else '',
        )
        self.pack_propagate(False)
        self._command = command
        self._bg_color = bg_color
        self._hover_bg_color = hover_bg_color
        self._pressed_bg_color = pressed_bg_color
        self._pressed = False
        self._hovered = False
        self._enabled = command is not None
        self._image = load_tk_photoimage(icon_path, icon_size)

        if command is not None:
            self._bind_interaction(self)

        self.icon_label = None
        if self._image is not None:
            self.icon_label = tk.Label(
                self,
                image=self._image,
                bg=bg_color,
                bd=0,
                highlightthickness=0,
                cursor='hand2' if command is not None else '',
            )
            self.icon_label.place(x=icon_x, y=icon_y, width=icon_size[0], height=icon_size[1])
            if command is not None:
                self._bind_interaction(self.icon_label)

        label_x = icon_x + icon_size[0] + icon_gap
        center_y = icon_y + (icon_size[1] // 2)
        self.text_label = tk.Label(
            self,
            text=text,
            bg=bg_color,
            fg=text_color,
            bd=0,
            highlightthickness=0,
            font=(spec.MODULE_ACTION_HEADER_FONT_FAMILY, spec.MODULE_HEADER_FONT_SIZE),
            anchor='w',
            cursor='hand2' if command is not None else '',
        )
        self.text_label.place(x=label_x, y=center_y, anchor='w')
        if command is not None:
            self._bind_interaction(self.text_label)

        self.right_text_label = None
        if right_text:
            self.right_text_label = tk.Label(
                self,
                text=right_text,
                bg=bg_color,
                fg=right_text_color,
                bd=0,
                highlightthickness=0,
                font=(spec.MODULE_ACTION_HEADER_FONT_FAMILY, right_text_font_size),
                anchor='e',
                cursor='hand2' if command is not None else '',
            )
            self.right_text_label.place(
                x=width - spec.MODULE_ACTION_HEADER_RIGHT_INSET_X,
                y=center_y,
                anchor='e',
            )
            if command is not None:
                self._bind_interaction(self.right_text_label)

    def tooltip_widgets(self) -> tuple[tk.Misc, ...]:
        widgets: list[tk.Misc] = [self, self.text_label]
        if self.icon_label is not None:
            widgets.append(self.icon_label)
        if self.right_text_label is not None:
            widgets.append(self.right_text_label)
        return tuple(widgets)

    def resize(self, width: int) -> None:
        self.configure(width=width)
        if self.right_text_label is not None:
            self.right_text_label.place_configure(
                x=width - spec.MODULE_ACTION_HEADER_RIGHT_INSET_X,
            )

    def set_right_text(self, text: str) -> None:
        if self.right_text_label is None:
            return
        self.right_text_label.configure(text=text)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self._pressed = False
            self._hovered = False
            self._set_bg_color(self._bg_color)

    def _bind_interaction(self, widget: tk.Widget) -> None:
        widget.bind('<Enter>', self._on_enter, add='+')
        widget.bind('<Leave>', self._on_leave, add='+')
        widget.bind('<ButtonPress-1>', self._on_press, add='+')
        widget.bind('<ButtonRelease-1>', self._on_release, add='+')

    def _set_bg_color(self, color: str) -> None:
        self.configure(bg=color)
        if self.icon_label is not None:
            self.icon_label.configure(bg=color)
        self.text_label.configure(bg=color)
        if self.right_text_label is not None:
            self.right_text_label.configure(bg=color)

    def _on_enter(self, _event: tk.Event[tk.Misc]) -> None:
        if not self._enabled:
            return
        self._hovered = True
        if not self._pressed:
            self._set_bg_color(self._hover_bg_color)

    def _on_leave(self, _event: tk.Event[tk.Misc]) -> None:
        if not self._enabled:
            return
        self._hovered = False
        if self._pressed:
            return
        self._set_bg_color(self._bg_color)

    def _on_press(self, _event: tk.Event[tk.Misc]) -> None:
        if not self._enabled:
            return
        self._pressed = True
        self._set_bg_color(self._pressed_bg_color)

    def _on_release(self, event: tk.Event[tk.Misc]) -> None:
        if not self._enabled:
            return
        was_pressed = self._pressed
        self._pressed = False
        next_color = self._hover_bg_color if self._hovered else self._bg_color
        self._set_bg_color(next_color)
        if was_pressed:
            self._on_click(event)

    def _on_click(self, _event: tk.Event[tk.Misc]) -> None:
        if self._command is not None:
            self._command()
