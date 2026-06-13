from __future__ import annotations

import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.scroll_area import ScrollViewport


class MediaSonglistViewport(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        bg_color: str,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_SONGLIST_VIEWPORT_SIZE[0],
            height=spec.MEDIA_ROW_SONGLIST_VIEWPORT_SIZE[1],
        )
        self.pack_propagate(False)

        self.scroll_viewport = ScrollViewport(
            self,
            size=spec.MEDIA_ROW_SONGLIST_VIEWPORT_SIZE,
            viewport_size=spec.MEDIA_ROW_SONGLIST_VIEWPORT_MASK_SIZE,
            scrollbar_size=spec.MEDIA_ROW_SONGLIST_SCROLLBAR_SIZE,
            show_top_edge=True,
            bg_color=bg_color,
        )
        self.scroll_viewport.place(x=0, y=0)

        self.viewport_canvas = self.scroll_viewport.viewport_canvas
        self.content_frame = self.scroll_viewport.content_frame
        self.scrollbar = self.scroll_viewport.scrollbar

    def refresh_scroll_region(self) -> None:
        self.scroll_viewport.refresh_scroll_region()
