from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.main_button import MainButton


class MediaCreationHeader(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        add_command: Callable[[], None] | None = None,
        remove_command: Callable[[], None] | None = None,
        size: tuple[int, int] = spec.MODULE_TWO_TOP_HEADER_SIZE,
        bg_color: str = spec.MODULE_TWO_TOP_HEADER_BG,
        outline_color: str = spec.MODULE_TWO_TOP_HEADER_OUTLINE,
        outline_width: int = spec.MODULE_TWO_TOP_HEADER_OUTLINE_WIDTH,
    ) -> None:
        super().__init__(
            parent,
            bg=outline_color,
            bd=0,
            highlightthickness=0,
            width=size[0],
            height=size[1],
        )
        self.pack_propagate(False)

        inner_width = size[0] - (outline_width * 2)
        inner_height = size[1] - (outline_width * 2)
        self.surface = tk.Frame(
            self,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=inner_width,
            height=inner_height,
        )
        self.surface.place(x=outline_width, y=outline_width)
        self.surface.pack_propagate(False)

        add_x, add_y = spec.MODULE_TWO_TOP_HEADER_BUTTON_OFFSET
        self.add_button = MainButton(
            self.surface,
            text='+ Add Media Row',
            command=add_command,
            variant='positive',
            size=spec.MODULE_TWO_TOP_HEADER_BUTTON_SIZE,
        )
        self.add_button.place(x=add_x, y=add_y)

        remove_x = add_x + spec.MODULE_TWO_TOP_HEADER_BUTTON_SIZE[0] + spec.MODULE_TWO_TOP_HEADER_BUTTON_GAP_X
        self.remove_button = MainButton(
            self.surface,
            text='- Remove Row',
            command=remove_command,
            variant='negative',
            size=spec.MODULE_TWO_TOP_HEADER_BUTTON_SIZE,
        )
        self.remove_button.place(x=remove_x, y=add_y)

    def resize(self, width: int) -> None:
        self.configure(width=width)
        inner_width = width - (spec.MODULE_TWO_TOP_HEADER_OUTLINE_WIDTH * 2)
        self.surface.configure(width=inner_width)
        self.surface.place_configure(
            x=spec.MODULE_TWO_TOP_HEADER_OUTLINE_WIDTH,
            y=spec.MODULE_TWO_TOP_HEADER_OUTLINE_WIDTH,
            width=inner_width,
        )
