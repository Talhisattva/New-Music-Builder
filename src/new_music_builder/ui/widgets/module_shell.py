from __future__ import annotations

import tkinter as tk

from new_music_builder.ui import spec


class ModuleShell(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        size: tuple[int, int] = spec.MODULE_ONE_SIZE,
        outline_color: str = spec.MODULE_OUTLINE,
        outline_width: int = spec.MODULE_OUTLINE_WIDTH,
        background_color: str = spec.MODULE_BACKGROUND_BG,
        midground_size: tuple[int, int] = spec.MODULE_MIDGROUND_SIZE,
        midground_offset: tuple[int, int] = spec.MODULE_MIDGROUND_OFFSET,
        midground_outline_color: str = spec.MODULE_MIDGROUND_OUTLINE,
        midground_color: str = spec.MODULE_MIDGROUND_BG,
    ) -> None:
        super().__init__(
            parent,
            bg=outline_color,
            width=size[0],
            height=size[1],
            bd=0,
            highlightthickness=0,
        )
        self._size = size
        self._outline_width = outline_width
        self._midground_size = midground_size
        self._midground_offset = midground_offset

        self.create_rectangle(0, 0, size[0], size[1], outline='', fill=outline_color)

        self.background_surface = tk.Frame(
            self,
            bg=background_color,
            bd=0,
            highlightthickness=0,
            width=size[0] - (outline_width * 2),
            height=size[1] - (outline_width * 2),
        )
        self.create_window(
            outline_width,
            outline_width,
            anchor='nw',
            window=self.background_surface,
            width=size[0] - (outline_width * 2),
            height=size[1] - (outline_width * 2),
        )

        self.midground_border = tk.Frame(
            self,
            bg=midground_outline_color,
            bd=0,
            highlightthickness=0,
            width=midground_size[0],
            height=midground_size[1],
        )
        self.create_window(
            midground_offset[0],
            midground_offset[1],
            anchor='nw',
            window=self.midground_border,
            width=midground_size[0],
            height=midground_size[1],
        )

        self.midground_surface = tk.Frame(
            self.midground_border,
            bg=midground_color,
            bd=0,
            highlightthickness=0,
            width=midground_size[0] - 2,
            height=midground_size[1] - 2,
        )
        self.midground_surface.place(x=1, y=1)
