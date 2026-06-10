from __future__ import annotations

import customtkinter as ctk


class Tooltip:
    def __init__(self, widget: ctk.CTkBaseClass, text: str) -> None:
        self.widget = widget
        self.text = text
        self.window: ctk.CTkToplevel | None = None
        widget.bind('<Enter>', self._show)
        widget.bind('<Leave>', self._hide)

    def _show(self, _event=None) -> None:
        if self.window is not None:
            return
        self.window = ctk.CTkToplevel(self.widget)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        label = ctk.CTkLabel(self.window, text=self.text, justify='left', wraplength=280)
        label.pack(padx=8, pady=6)
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.window.geometry(f'+{x}+{y}')

    def _hide(self, _event=None) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None