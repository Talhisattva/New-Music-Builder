from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.icon_button import FolderIconButton
from new_music_builder.ui.widgets.images import load_tk_photoimage


class ExpandedMediaCover(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        folder_icon_path: str | Path | None,
        cover_path: str | Path | None = None,
        command: Callable[[], None] | None = None,
        cover_size: tuple[int, int] = spec.MEDIA_ROW_EXPANDED_COVER_SIZE,
        cover_bg: str = spec.COVER_BG,
        cover_outline: str = spec.COVER_OUTLINE,
        button_size: tuple[int, int] = spec.FOLDER_BUTTON_SIZE,
    ) -> None:
        super().__init__(
            parent,
            bg=parent.cget('bg'),
            bd=0,
            highlightthickness=0,
            width=cover_size[0],
            height=cover_size[1],
        )
        self.pack_propagate(False)
        self._cover_image = load_tk_photoimage(cover_path, (cover_size[0] - 2, cover_size[1] - 2))

        self.cover_border = tk.Frame(
            self,
            bg=cover_outline,
            bd=0,
            highlightthickness=0,
            width=cover_size[0],
            height=cover_size[1],
        )
        self.cover_border.place(x=0, y=0)

        self.cover_surface = tk.Label(
            self.cover_border,
            bg=cover_bg,
            bd=0,
            highlightthickness=0,
            image=self._cover_image,
        )
        self.cover_surface.place(x=1, y=1, width=cover_size[0] - 2, height=cover_size[1] - 2)

        self.folder_button = FolderIconButton(
            self,
            icon_path=folder_icon_path,
            command=command,
            size=button_size,
        )
        self.folder_button.place(x=cover_size[0] - button_size[0], y=0)


class CollapsedMediaCover(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        cover_path: str | Path | None = None,
        cover_size: tuple[int, int] = spec.MEDIA_ROW_COLLAPSED_COVER_SIZE,
        cover_bg: str = spec.COVER_BG,
        cover_outline: str = spec.COVER_OUTLINE,
    ) -> None:
        super().__init__(
            parent,
            bg=parent.cget('bg'),
            bd=0,
            highlightthickness=0,
            width=cover_size[0],
            height=cover_size[1],
        )
        self.pack_propagate(False)
        self._cover_image = load_tk_photoimage(cover_path, (cover_size[0] - 2, cover_size[1] - 2))

        self.cover_border = tk.Frame(
            self,
            bg=cover_outline,
            bd=0,
            highlightthickness=0,
            width=cover_size[0],
            height=cover_size[1],
        )
        self.cover_border.place(x=0, y=0)

        self.cover_surface = tk.Label(
            self.cover_border,
            bg=cover_bg,
            bd=0,
            highlightthickness=0,
            image=self._cover_image,
        )
        self.cover_surface.place(x=1, y=1, width=cover_size[0] - 2, height=cover_size[1] - 2)
