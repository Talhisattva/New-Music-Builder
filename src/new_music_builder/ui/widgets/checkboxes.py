from __future__ import annotations

import customtkinter as ctk

from new_music_builder.ui import theme


def apply_builder_checkbox_style(checkbox: ctk.CTkCheckBox) -> ctk.CTkCheckBox:
    checkbox.configure(
        fg_color=theme.ACCENT,
        hover_color=theme.ACCENT_DARK,
        border_color=theme.ACCENT_LIGHT,
        checkmark_color=theme.BUTTON_TEXT,
        text_color=theme.TEXT,
        font=ctk.CTkFont(family='Orbitron', size=12, weight='bold'),
        checkbox_width=22,
        checkbox_height=22,
        corner_radius=6,
        border_width=1,
    )
    return checkbox