from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.main_button import MainButton


class MediaSongActions(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        bg_color: str,
        on_add_song: Callable[[], None] | None = None,
        on_remove_song: Callable[[], None] | None = None,
    ) -> None:
        width = (spec.MEDIA_ROW_SONG_ACTION_BUTTON_SIZE[0] * 2) + spec.MEDIA_ROW_SONG_ACTION_GAP_X
        height = spec.MEDIA_ROW_SONG_ACTION_BUTTON_SIZE[1]
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=width,
            height=height,
        )
        self.pack_propagate(False)

        self.add_button = MainButton(
            self,
            text='+ Add Songs',
            command=on_add_song,
            size=spec.MEDIA_ROW_SONG_ACTION_BUTTON_SIZE,
        )
        self.add_button.place(x=0, y=0)

        self.remove_button = MainButton(
            self,
            text='- Remove Songs',
            command=on_remove_song,
            size=spec.MEDIA_ROW_SONG_ACTION_BUTTON_SIZE,
            variant='negative',
        )
        self.remove_button.place(
            x=spec.MEDIA_ROW_SONG_ACTION_BUTTON_SIZE[0] + spec.MEDIA_ROW_SONG_ACTION_GAP_X,
            y=0,
        )

    def set_bg_color(self, color: str) -> None:
        self.configure(bg=color)

    def set_enabled(self, enabled: bool) -> None:
        self.add_button.set_enabled(enabled)
        self.remove_button.set_enabled(enabled)
