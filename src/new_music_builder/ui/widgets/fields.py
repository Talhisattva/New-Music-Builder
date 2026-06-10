from __future__ import annotations

import customtkinter as ctk

from new_music_builder.ui import theme


class LabeledEntry(ctk.CTkFrame):
    def __init__(self, master, label: str, variable, *, width: int = 240):
        super().__init__(master, fg_color='transparent')
        ctk.CTkLabel(self, text=label, text_color=theme.TEXT, anchor='w').pack(fill='x')
        self.entry = ctk.CTkEntry(self, textvariable=variable, width=width)
        self.entry.pack(fill='x', pady=(4, 0))