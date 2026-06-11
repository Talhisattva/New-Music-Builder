from __future__ import annotations

import customtkinter as ctk

from new_music_builder.ui import theme
from new_music_builder.ui.widgets.buttons import apply_builder_button_style


class ModulePanel(ctk.CTkFrame):
    def __init__(self, master, title: str, *, accent: str | None = None, header_button: bool = False, command=None):
        super().__init__(master, fg_color=theme.PANEL, border_color=theme.BORDER, border_width=1, corner_radius=12)
        header_fg = accent or theme.ACCENT
        if header_button:
            self.header = ctk.CTkButton(
                self,
                text=title,
                command=command,
                anchor='w',
            )
            apply_builder_button_style(self.header, variant='secondary')
            self.header.configure(font=ctk.CTkFont(family='Orbitron', size=15, weight='bold'))
            self.header.pack(fill='x', padx=8, pady=(8, 4))
        else:
            header = ctk.CTkFrame(self, fg_color='transparent')
            header.pack(fill='x', padx=10, pady=(10, 6))
            chip = ctk.CTkFrame(header, width=28, height=28, fg_color=header_fg, corner_radius=8)
            chip.pack(side='left')
            ctk.CTkLabel(
                header,
                text=title,
                text_color=header_fg,
                font=ctk.CTkFont(family='Orbitron', size=15, weight='bold'),
            ).pack(side='left', padx=(8, 0))
        self.body = ctk.CTkFrame(self, fg_color=theme.PANEL_ALT, corner_radius=10)
        self.body.pack(fill='both', expand=True, padx=10, pady=(0, 10))
