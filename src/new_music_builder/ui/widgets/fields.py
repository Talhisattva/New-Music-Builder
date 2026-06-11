from __future__ import annotations

import customtkinter as ctk

from new_music_builder.ui import theme


def apply_builder_entry_style(entry: ctk.CTkEntry, *, font_size: int = 13) -> ctk.CTkEntry:
    entry.configure(
        fg_color=theme.PANEL,
        border_color=theme.BORDER,
        text_color=theme.TEXT,
        placeholder_text_color=theme.MUTED,
        corner_radius=10,
        height=34,
        font=ctk.CTkFont(family='Orbitron', size=font_size),
    )
    return entry


def apply_builder_textbox_style(textbox: ctk.CTkTextbox, *, font_size: int = 12) -> ctk.CTkTextbox:
    textbox.configure(
        fg_color=theme.PANEL,
        border_color=theme.BORDER,
        border_width=1,
        text_color=theme.TEXT,
        corner_radius=10,
        font=ctk.CTkFont(family='Orbitron', size=font_size),
        scrollbar_button_color=theme.ACCENT,
        scrollbar_button_hover_color=theme.ACCENT_DARK,
    )
    return textbox


def apply_builder_progress_style(progress: ctk.CTkProgressBar) -> ctk.CTkProgressBar:
    progress.configure(
        fg_color=theme.PANEL,
        border_color=theme.BORDER,
        border_width=1,
        progress_color=theme.ACCENT,
        corner_radius=8,
        height=14,
    )
    return progress


class LabeledEntry(ctk.CTkFrame):
    def __init__(self, master, label: str, variable, *, width: int = 240):
        super().__init__(master, fg_color='transparent')
        ctk.CTkLabel(
            self,
            text=label,
            text_color=theme.TEXT,
            anchor='w',
            font=ctk.CTkFont(family='Orbitron', size=12, weight='bold'),
        ).pack(fill='x')
        self.entry = ctk.CTkEntry(self, textvariable=variable, width=width)
        apply_builder_entry_style(self.entry)
        self.entry.pack(fill='x', pady=(4, 0))
