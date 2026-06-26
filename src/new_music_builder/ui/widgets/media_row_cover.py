from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.icon_button import FolderIconButton
from new_music_builder.ui.widgets.images import load_tk_photoimage_contained


class ExpandedMediaCover(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        folder_icon_path: str | Path | None,
        cover_path: str | Path | None = None,
        command: Callable[[], None] | None = None,
        dnd_type: str | None = None,
        can_accept_drop: Callable[[list[str]], bool] | None = None,
        on_drop_files: Callable[[list[str]], None] | None = None,
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
        self._cover_size = cover_size
        self._cover_image = None
        self._default_outline = cover_outline
        self._dnd_type = dnd_type
        self._can_accept_drop = can_accept_drop
        self._on_drop_files = on_drop_files

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
        self.set_cover_path(cover_path)
        self._bind_drop_target()

    def tooltip_widgets(self) -> tuple[tk.Misc, ...]:
        return (self, self.cover_border, self.cover_surface, self.folder_button)

    def set_cover_path(self, cover_path: str | Path | None) -> None:
        self._cover_image = load_tk_photoimage_contained(
            cover_path,
            (self._cover_size[0] - 2, self._cover_size[1] - 2),
        )
        self.cover_surface.configure(image=self._cover_image)

    def set_enabled(self, enabled: bool) -> None:
        self.folder_button.set_enabled(enabled)
        if not enabled:
            self.set_drop_highlight(False)

    def set_drop_highlight(self, active: bool) -> None:
        self.cover_border.configure(bg=spec.MEDIA_ROW_SONGLIST_DROP_HIGHLIGHT_BORDER if active else self._default_outline)

    def _bind_drop_target(self) -> None:
        if self._dnd_type is None or self._can_accept_drop is None or self._on_drop_files is None:
            return
        for widget in (self.cover_border, self.cover_surface, self.folder_button):
            if not hasattr(widget, 'drop_target_register'):
                continue
            try:
                widget.drop_target_register(self._dnd_type)
                widget.dnd_bind('<<DropEnter>>', self._on_drop_enter, add='+')
                widget.dnd_bind('<<DropPosition>>', self._on_drop_position, add='+')
                widget.dnd_bind('<<DropLeave>>', self._on_drop_leave, add='+')
                widget.dnd_bind('<<Drop>>', self._on_drop, add='+')
            except tk.TclError:
                self._dnd_type = None
                self.set_drop_highlight(False)
                return

    def _split_drop_paths(self, raw_data: str) -> list[str]:
        try:
            return [item for item in self.tk.splitlist(raw_data) if item]
        except tk.TclError:
            return [raw_data] if raw_data else []

    def _drop_is_valid(self, raw_data: str) -> bool:
        if self._can_accept_drop is None:
            return False
        return self._can_accept_drop(self._split_drop_paths(raw_data))

    def _on_drop_enter(self, event: tk.Event) -> str:
        self.set_drop_highlight(self._drop_is_valid(getattr(event, 'data', '')))
        return getattr(event, 'action', 'copy')

    def _on_drop_position(self, event: tk.Event) -> str:
        self.set_drop_highlight(self._drop_is_valid(getattr(event, 'data', '')))
        return getattr(event, 'action', 'copy')

    def _on_drop_leave(self, event: tk.Event) -> str:
        self.set_drop_highlight(False)
        return getattr(event, 'action', 'copy')

    def _on_drop(self, event: tk.Event) -> str:
        paths = self._split_drop_paths(getattr(event, 'data', ''))
        valid = self._can_accept_drop(paths) if self._can_accept_drop is not None else False
        if valid and self._on_drop_files is not None:
            self._on_drop_files(paths)
        self.set_drop_highlight(False)
        return getattr(event, 'action', 'copy')


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
        self._cover_size = cover_size
        self._cover_image = None

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
        )
        self.cover_surface.place(x=1, y=1, width=cover_size[0] - 2, height=cover_size[1] - 2)
        self.set_cover_path(cover_path)

    def tooltip_widgets(self) -> tuple[tk.Misc, ...]:
        return (self, self.cover_border, self.cover_surface)

    def set_cover_path(self, cover_path: str | Path | None) -> None:
        self._cover_image = load_tk_photoimage_contained(
            cover_path,
            (self._cover_size[0] - 2, self._cover_size[1] - 2),
        )
        self.cover_surface.configure(image=self._cover_image)
