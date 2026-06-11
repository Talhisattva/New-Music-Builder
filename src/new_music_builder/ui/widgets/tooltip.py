from __future__ import annotations

import customtkinter as ctk


class Tooltip:
    def __init__(self, widget: ctk.CTkBaseClass, text: str, *, delay_ms: int = 250) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.window: ctk.CTkToplevel | None = None
        self.label: ctk.CTkLabel | None = None
        self._show_after_id: str | None = None
        self._watch_after_id: str | None = None
        self._last_pointer: tuple[int, int] = (0, 0)

        widget.bind('<Enter>', self._on_enter, add='+')
        widget.bind('<Leave>', self._on_leave, add='+')
        widget.bind('<Motion>', self._on_motion, add='+')
        widget.bind('<ButtonPress>', self._hide, add='+')
        widget.bind('<Destroy>', self._hide, add='+')

    def _on_enter(self, event=None) -> None:
        self._capture_pointer(event)
        self._schedule_show()

    def _on_motion(self, event=None) -> None:
        self._capture_pointer(event)
        if self.window is not None:
            self._position_window()

    def _on_leave(self, _event=None) -> None:
        self._cancel_show()
        if self.window is not None:
            self.widget.after(40, self._hide_if_pointer_left)

    def _capture_pointer(self, event=None) -> None:
        if event is not None and hasattr(event, 'x_root') and hasattr(event, 'y_root'):
            self._last_pointer = (int(event.x_root), int(event.y_root))
        else:
            self._last_pointer = (self.widget.winfo_pointerx(), self.widget.winfo_pointery())

    def _schedule_show(self) -> None:
        self._cancel_show()
        self._show_after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel_show(self) -> None:
        if self._show_after_id is not None:
            try:
                self.widget.after_cancel(self._show_after_id)
            except Exception:
                pass
            self._show_after_id = None

    def _cancel_watch(self) -> None:
        if self._watch_after_id is not None:
            try:
                self.widget.after_cancel(self._watch_after_id)
            except Exception:
                pass
            self._watch_after_id = None

    def _show(self) -> None:
        self._show_after_id = None
        if self.window is not None or not self._is_pointer_over_widget():
            return
        self.window = ctk.CTkToplevel(self.widget)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.label = ctk.CTkLabel(self.window, text=self.text, justify='left', wraplength=280)
        self.label.pack(padx=8, pady=6)
        self._position_window()
        self._watch_visibility()

    def _position_window(self) -> None:
        if self.window is None:
            return
        x_root, y_root = self._last_pointer
        x = x_root + 14
        y = y_root + 18
        self.window.geometry(f'+{x}+{y}')

    def _watch_visibility(self) -> None:
        self._cancel_watch()
        if self.window is None:
            return
        if not self._is_pointer_over_widget():
            self._hide()
            return
        self._watch_after_id = self.widget.after(80, self._watch_visibility)

    def _hide_if_pointer_left(self) -> None:
        if not self._is_pointer_over_widget():
            self._hide()

    def _is_pointer_over_widget(self) -> bool:
        try:
            x = self.widget.winfo_pointerx()
            y = self.widget.winfo_pointery()
            left = self.widget.winfo_rootx()
            top = self.widget.winfo_rooty()
            right = left + self.widget.winfo_width()
            bottom = top + self.widget.winfo_height()
            return left <= x <= right and top <= y <= bottom
        except Exception:
            return False

    def _hide(self, _event=None) -> None:
        self._cancel_show()
        self._cancel_watch()
        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
            self.label = None