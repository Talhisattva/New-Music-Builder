from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk

from PIL import Image, ImageTk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.cursor_tooltip import CursorTooltip
from new_music_builder.ui.widgets.icon_button import FolderIconButton
from new_music_builder.ui.widgets.images import load_tk_photoimage_contained


class CoverPicker(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        folder_icon_path: str | Path | None,
        command: Callable[[], None] | None = None,
        dnd_type: str | None = None,
        can_accept_drop: Callable[[list[str]], bool] | None = None,
        on_drop_files: Callable[[list[str]], None] | None = None,
        cover_bg: str = spec.COVER_BG,
        cover_outline: str = spec.COVER_OUTLINE,
        cover_size: tuple[int, int] = spec.COVER_SIZE,
        button_size: tuple[int, int] = spec.FOLDER_BUTTON_SIZE,
        button_center_inset: tuple[int, int] = spec.FOLDER_BUTTON_CENTER_INSET,
    ) -> None:
        width = max(cover_size[0], cover_size[0] - button_center_inset[0] + (button_size[0] // 2))
        height = max(cover_size[1] + 10, button_size[1])
        super().__init__(parent, bg=parent.cget('bg'), bd=0, highlightthickness=0, width=width, height=height)
        self._cover_size = cover_size
        self._cover_image = None
        self._cover_preview_image: Image.Image | None = None
        self._tooltip_preview_image: Image.Image | None = None
        self._default_outline = cover_outline
        self._dnd_type = dnd_type
        self._can_accept_drop = can_accept_drop
        self._on_drop_files = on_drop_files
        self._cursor_tooltip = CursorTooltip(self)
        self._tooltip_hide_after_id: str | None = None

        self.cover_border = tk.Frame(
            self,
            bg=cover_outline,
            bd=0,
            highlightthickness=0,
            width=cover_size[0],
            height=cover_size[1],
        )
        self.cover_border.place(x=0, y=10)

        self.cover_surface = tk.Label(
            self.cover_border,
            bg=cover_bg,
            bd=0,
            highlightthickness=0,
        )
        self.cover_surface.place(x=1, y=1, width=cover_size[0] - 2, height=cover_size[1] - 2)

        button_x = cover_size[0] - button_center_inset[0] - (button_size[0] // 2)
        self.folder_button = FolderIconButton(
            self,
            icon_path=folder_icon_path,
            command=command,
            size=button_size,
        )
        self.folder_button.place(x=button_x, y=0)
        self._bind_drop_target()
        self._bind_preview_tooltip()

    def set_cover_path(self, cover_path: str | Path | None) -> None:
        self._cover_preview_image = None
        self._tooltip_preview_image = None
        self._cover_image = load_tk_photoimage_contained(
            cover_path,
            (self._cover_size[0] - 2, self._cover_size[1] - 2),
        )
        self.cover_surface.configure(image=self._cover_image if self._cover_image is not None else '')
        self.cover_surface.image = self._cover_image

    def set_cover_image(self, image: Image.Image | None) -> None:
        self._cover_preview_image = image.copy() if image is not None else None
        if image is None:
            self._cover_image = None
        else:
            contained = image.copy()
            contained.thumbnail((self._cover_size[0] - 2, self._cover_size[1] - 2), Image.Resampling.LANCZOS)
            fitted = Image.new('RGBA', (self._cover_size[0] - 2, self._cover_size[1] - 2), (0, 0, 0, 0))
            paste_x = (fitted.width - contained.width) // 2
            paste_y = (fitted.height - contained.height) // 2
            fitted.paste(contained, (paste_x, paste_y), contained)
            self._cover_image = ImageTk.PhotoImage(fitted)
        self.cover_surface.configure(image=self._cover_image if self._cover_image is not None else '')
        self.cover_surface.image = self._cover_image

    def set_tooltip_image(self, image: Image.Image | None) -> None:
        self._tooltip_preview_image = image.copy() if image is not None else None

    def tooltip_widgets(self) -> tuple[tk.Misc, ...]:
        return (
            self,
            self.cover_border,
            self.cover_surface,
            self.folder_button,
        )

    def has_preview_image(self) -> bool:
        return (
            self._tooltip_preview_image is not None
            or self._cover_preview_image is not None
            or self._cover_image is not None
        )

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

    def _bind_preview_tooltip(self) -> None:
        for widget in self.tooltip_widgets():
            widget.bind('<Enter>', self._on_preview_enter, add='+')
            widget.bind('<Motion>', self._on_preview_motion, add='+')
            widget.bind('<Leave>', self._on_preview_leave, add='+')

    def _on_preview_enter(self, event: tk.Event) -> None:
        if not self.has_preview_image():
            self._cursor_tooltip.hide()
            return
        self._cancel_tooltip_hide()
        self._cursor_tooltip.set_pil_image(self._tooltip_preview_image or self._cover_preview_image)
        self._cursor_tooltip.show_at_cursor(int(event.x_root), int(event.y_root), direction='right')

    def _on_preview_motion(self, event: tk.Event) -> None:
        if not self.has_preview_image():
            self._cursor_tooltip.hide()
            return
        self._cancel_tooltip_hide()
        self._cursor_tooltip.set_pil_image(self._tooltip_preview_image or self._cover_preview_image)
        self._cursor_tooltip.move_to_cursor(int(event.x_root), int(event.y_root))

    def _on_preview_leave(self, _event: tk.Event) -> None:
        self._schedule_tooltip_hide()

    def _schedule_tooltip_hide(self) -> None:
        self._cancel_tooltip_hide()
        self._tooltip_hide_after_id = self.after(spec.MODULE_THREE_GRID_HOVER_HIDE_DELAY_MS, self._hide_tooltip_now)

    def _cancel_tooltip_hide(self) -> None:
        if self._tooltip_hide_after_id is not None:
            try:
                self.after_cancel(self._tooltip_hide_after_id)
            except tk.TclError:
                pass
            self._tooltip_hide_after_id = None

    def _hide_tooltip_now(self) -> None:
        self._tooltip_hide_after_id = None
        self._cursor_tooltip.hide()
