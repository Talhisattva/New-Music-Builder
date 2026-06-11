from __future__ import annotations

import customtkinter as ctk

from new_music_builder.ui import theme


def apply_builder_button_style(button: ctk.CTkButton, *, variant: str = 'primary') -> ctk.CTkButton:
    if variant == 'secondary':
        button.configure(
            fg_color=theme.PANEL_ALT,
            hover_color=theme.PANEL,
            border_width=1,
            border_color=theme.BORDER,
            text_color=theme.BUTTON_TEXT,
            font=ctk.CTkFont(family='Orbitron', size=13, weight='bold'),
            corner_radius=10,
            height=34,
        )
    else:
        button.configure(
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_DARK,
            border_width=1,
            border_color=theme.ACCENT_DARK,
            text_color=theme.BUTTON_TEXT,
            font=ctk.CTkFont(family='Orbitron', size=13, weight='bold'),
            corner_radius=10,
            height=34,
        )
    return button


def make_builder_button(master, text: str, command, *, width: int | None = None, variant: str = 'primary') -> ctk.CTkButton:
    kwargs = {'text': text, 'command': command}
    if width is not None:
        kwargs['width'] = width
    button = ctk.CTkButton(master, **kwargs)
    return apply_builder_button_style(button, variant=variant)
