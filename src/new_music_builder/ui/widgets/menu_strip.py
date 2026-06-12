from __future__ import annotations

import customtkinter as ctk

from new_music_builder.ui import spec


class MenuStrip(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        *,
        items: tuple[str, ...] = spec.MENU_ITEMS,
        bg_color: str = spec.MENU_BG,
        hover_color: str = spec.MENU_HOVER,
        text_color: str = spec.HEADER_TEXT,
    ) -> None:
        super().__init__(parent, fg_color=bg_color, corner_radius=0, height=spec.MENU_HEIGHT)
        self.pack_propagate(False)
        self._item_widgets: list[tuple[ctk.CTkFrame, ctk.CTkLabel]] = []

        items_frame = ctk.CTkFrame(self, fg_color='transparent')
        items_frame.pack(side='left')

        for item in items:
            item_frame = ctk.CTkFrame(items_frame, fg_color=bg_color, corner_radius=0)
            item_frame.pack(side='left', padx=0, pady=0)
            label = ctk.CTkLabel(
                item_frame,
                text=item,
                text_color=text_color,
                font=ctk.CTkFont(family='Orbitron', size=spec.MENU_FONT_SIZE, weight='normal'),
            )
            label.pack(padx=spec.MENU_ITEM_PAD_X, pady=spec.MENU_ITEM_PAD_Y)
            item_frame.bind('<Enter>', lambda _e, frame=item_frame: frame.configure(fg_color=hover_color))
            item_frame.bind('<Leave>', lambda _e, frame=item_frame: frame.configure(fg_color=bg_color))
            label.bind('<Enter>', lambda _e, frame=item_frame: frame.configure(fg_color=hover_color))
            label.bind('<Leave>', lambda _e, frame=item_frame: frame.configure(fg_color=bg_color))
            self._item_widgets.append((item_frame, label))
