from __future__ import annotations

from pathlib import Path
import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage


class ImageCheckbox(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        icon_path: str | Path | None,
        bg_color: str = spec.POSTER_NAME_CHECKBOX_BG,
        outline_color: str = spec.POSTER_NAME_CHECKBOX_OUTLINE,
        size: tuple[int, int] = spec.POSTER_NAME_CHECKBOX_SIZE,
        outline_width: int = spec.POSTER_NAME_CHECKBOX_OUTLINE_WIDTH,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            width=size[0],
            height=size[1],
            bd=0,
            highlightthickness=0,
        )
        self._size = size
        self._outline_width = outline_width
        self._bg_color = bg_color
        self._outline_color = outline_color
        self._image = load_tk_photoimage(icon_path, size)

        self._draw()

    def _draw(self) -> None:
        inset = self._outline_width
        self.create_rectangle(
            0,
            0,
            self._size[0],
            self._size[1],
            outline='',
            fill=self._outline_color,
        )
        self.create_rectangle(
            inset,
            inset,
            self._size[0] - inset,
            self._size[1] - inset,
            outline='',
            fill=self._bg_color,
        )
        if self._image is not None:
            self.create_image(self._size[0] // 2, self._size[1] // 2, image=self._image)


class LabeledCheckbox(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        icon_path: str | Path | None,
        text: str = spec.POSTER_NAME_LABEL_TEXT,
        checkbox_gap: int = spec.POSTER_NAME_CHECKBOX_GAP,
        text_color: str = spec.POSTER_NAME_LABEL_COLOR,
        font_size: int = spec.POSTER_NAME_LABEL_FONT_SIZE,
        bg_color: str | None = None,
    ) -> None:
        resolved_bg = bg_color if bg_color is not None else parent.cget('bg')
        super().__init__(parent, bg=resolved_bg, bd=0, highlightthickness=0)

        self.checkbox = ImageCheckbox(self, icon_path=icon_path)
        self.checkbox.pack(side='left')

        self.text_label = tk.Label(
            self,
            text=text,
            bg=resolved_bg,
            fg=text_color,
            bd=0,
            highlightthickness=0,
            font=('Orbitron Medium', font_size),
            anchor='w',
            justify='left',
        )
        self.text_label.pack(side='left', padx=(checkbox_gap, 0), fill='y')
