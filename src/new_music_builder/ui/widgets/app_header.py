from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_ctk_image


class AppHeader(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        *,
        logo_path: str | Path | None,
        title: str = spec.HEADER_TITLE,
        version: str = spec.HEADER_VERSION,
        bg_color: str = spec.HEADER_BG,
        text_color: str = spec.HEADER_TEXT,
    ) -> None:
        super().__init__(parent, fg_color=bg_color, corner_radius=0, height=spec.HEADER_HEIGHT)
        self.pack_propagate(False)
        self._logo_image = load_ctk_image(logo_path, spec.HEADER_LOGO_SIZE)

        title_pad = (spec.HEADER_LOGO_X, spec.HEADER_LOGO_GAP)
        if self._logo_image is not None:
            self.logo_label = ctk.CTkLabel(self, text='', image=self._logo_image)
            self.logo_label.pack(
                side='left',
                padx=(spec.HEADER_LOGO_X, spec.HEADER_LOGO_GAP),
                pady=9,
            )
            title_pad = (0, 8)
        else:
            self.logo_label = None

        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            text_color=text_color,
            font=ctk.CTkFont(family='Orbitron', size=spec.HEADER_TITLE_SIZE, weight='bold'),
        )
        self.title_label.pack(side='left', padx=title_pad, pady=10)

        self.version_label = ctk.CTkLabel(
            self,
            text=version,
            text_color=text_color,
            font=ctk.CTkFont(family='Orbitron', size=spec.HEADER_VERSION_SIZE, weight='normal'),
        )
        self.version_label.pack(side='left', pady=14)

        self.byline_label = ctk.CTkLabel(
            self,
            text=spec.HEADER_BYLINE,
            text_color=spec.HEADER_BYLINE_TEXT_COLOR,
            font=ctk.CTkFont(
                family=spec.HEADER_BYLINE_FONT_FAMILY,
                size=spec.HEADER_BYLINE_FONT_SIZE,
                weight='normal',
            ),
        )
        self.byline_label.pack(side='right', padx=(0, spec.HEADER_BYLINE_RIGHT_INSET), pady=spec.HEADER_BYLINE_PAD_Y)
