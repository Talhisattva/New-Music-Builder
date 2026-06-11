from __future__ import annotations

import customtkinter as ctk

from new_music_builder.ui import theme


def make_builder_font(*, size: int = 12, weight: str = 'normal') -> ctk.CTkFont:
    return ctk.CTkFont(family='Orbitron', size=size, weight=weight)


def apply_builder_label_style(
    label: ctk.CTkLabel,
    *,
    size: int = 12,
    weight: str = 'normal',
    text_color: str | None = None,
) -> ctk.CTkLabel:
    label.configure(
        text_color=text_color or theme.TEXT,
        font=make_builder_font(size=size, weight=weight),
    )
    return label


def make_builder_label(
    master,
    text: str = '',
    *,
    size: int = 12,
    weight: str = 'normal',
    text_color: str | None = None,
    **kwargs,
) -> ctk.CTkLabel:
    label = ctk.CTkLabel(master, text=text, **kwargs)
    return apply_builder_label_style(label, size=size, weight=weight, text_color=text_color)


def apply_builder_entry_style(entry: ctk.CTkEntry, *, font_size: int = 13) -> ctk.CTkEntry:
    entry.configure(
        fg_color=theme.PANEL,
        border_color=theme.BORDER,
        text_color=theme.TEXT,
        placeholder_text_color=theme.MUTED,
        corner_radius=10,
        height=34,
        font=make_builder_font(size=font_size),
    )
    return entry


def apply_builder_textbox_style(textbox: ctk.CTkTextbox, *, font_size: int = 12) -> ctk.CTkTextbox:
    textbox.configure(
        fg_color=theme.PANEL,
        border_color=theme.BORDER,
        border_width=1,
        text_color=theme.TEXT,
        corner_radius=10,
        font=make_builder_font(size=font_size),
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
        make_builder_label(self, label, text_color=theme.TEXT, anchor='w', size=12, weight='bold').pack(fill='x')
        self.entry = ctk.CTkEntry(self, textvariable=variable, width=width)
        apply_builder_entry_style(self.entry)
        self.entry.pack(fill='x', pady=(4, 0))
