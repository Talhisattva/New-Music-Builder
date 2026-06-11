from __future__ import annotations

import customtkinter as ctk

from new_music_builder.ui import theme


def apply_builder_button_style(
    button: ctk.CTkButton,
    *,
    variant: str = 'primary',
    size: str = 'default',
) -> ctk.CTkButton:
    palette = {
        'primary': (theme.ACCENT, theme.ACCENT_DARK, theme.ACCENT_DARK, theme.BUTTON_TEXT),
        'secondary': (theme.PANEL_ALT, theme.PANEL, theme.BORDER, theme.BUTTON_TEXT),
        'subtle': (theme.PANEL, theme.PANEL_ALT, theme.BORDER, theme.TEXT),
        'selected': (theme.ACCENT, theme.ACCENT_DARK, theme.ACCENT_LIGHT, theme.BUTTON_TEXT),
    }
    fg_color, hover_color, border_color, text_color = palette.get(variant, palette['primary'])
    font_size = 12 if size == 'compact' else 13
    height = 30 if size == 'compact' else 34
    corner_radius = 8 if size == 'compact' else 10

    button.configure(
        fg_color=fg_color,
        hover_color=hover_color,
        border_width=1,
        border_color=border_color,
        text_color=text_color,
        font=ctk.CTkFont(family='Orbitron', size=font_size, weight='bold'),
        corner_radius=corner_radius,
        height=height,
    )
    return button


def make_builder_button(
    master,
    text: str,
    command,
    *,
    width: int | None = None,
    variant: str = 'primary',
    size: str = 'default',
    **kwargs,
) -> ctk.CTkButton:
    button_kwargs = {'text': text, 'command': command}
    if width is not None:
        button_kwargs['width'] = width
    button_kwargs.update(kwargs)
    button = ctk.CTkButton(master, **button_kwargs)
    return apply_builder_button_style(button, variant=variant, size=size)
