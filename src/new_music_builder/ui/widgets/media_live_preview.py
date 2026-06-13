from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from new_music_builder.domain.models import MediaRow
from new_music_builder.ui import spec


class _PreviewModeButton(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        text: str,
        command: Callable[[], None] | None = None,
        size: tuple[int, int],
    ) -> None:
        super().__init__(
            parent,
            width=size[0],
            height=size[1],
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_INACTIVE_BG,
            bd=0,
            highlightthickness=0,
        )
        self._command = command
        self._size = size
        self._is_active = False
        self._draw(text)
        self.bind('<ButtonPress-1>', self._on_press, add='+')
        self.bind('<ButtonRelease-1>', self._on_release, add='+')

    def _draw(self, text: str) -> None:
        self.create_rectangle(
            0,
            0,
            self._size[0],
            self._size[1],
            outline='',
            fill=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE,
        )
        self._fill_id = self.create_rectangle(
            spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE_WIDTH,
            spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE_WIDTH,
            self._size[0] - spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE_WIDTH,
            self._size[1] - spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE_WIDTH,
            outline='',
            fill=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_INACTIVE_BG,
        )
        self.create_text(
            self._size[0] / 2,
            self._size[1] / 2,
            text=text,
            fill=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_TEXT_COLOR,
            font=(
                spec.MEDIA_ROW_LIVE_PREVIEW_MODE_FONT_FAMILY,
                spec.MEDIA_ROW_LIVE_PREVIEW_MODE_FONT_SIZE,
            ),
            anchor='c',
        )

    def _on_press(self, _event: tk.Event | None = None) -> str:
        return 'break'

    def _on_release(self, event: tk.Event | None = None) -> str:
        inside = False
        if event is not None:
            inside = 0 <= event.x <= self._size[0] and 0 <= event.y <= self._size[1]
        if inside and self._command is not None:
            self._command()
        return 'break'

    def set_active(self, active: bool) -> None:
        self._is_active = active
        self.itemconfigure(
            self._fill_id,
            fill=(
                spec.MEDIA_ROW_LIVE_PREVIEW_MODE_ACTIVE_BG
                if active
                else spec.MEDIA_ROW_LIVE_PREVIEW_MODE_INACTIVE_BG
            ),
        )
        self.configure(
            bg=(
                spec.MEDIA_ROW_LIVE_PREVIEW_MODE_ACTIVE_BG
                if active
                else spec.MEDIA_ROW_LIVE_PREVIEW_MODE_INACTIVE_BG
            )
        )


class MediaLivePreview(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        row: MediaRow,
        bg_color: str,
        on_mode_selected: Callable[[int, str], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[0],
            height=spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[1],
        )
        self.pack_propagate(False)
        self._row_id = row.row_id
        self._selected_mode = row.preview_mode
        self._on_mode_selected = on_mode_selected

        self.header = tk.Frame(
            self,
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_OUTLINE,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[0],
            height=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_HEIGHT,
        )
        self.header.place(x=0, y=0)
        self.header.pack_propagate(False)

        self.header_fill = tk.Frame(
            self.header,
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_BG,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[0] - (spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_OUTLINE_WIDTH * 2),
            height=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_HEIGHT - (spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_OUTLINE_WIDTH * 2),
        )
        self.header_fill.place(
            x=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_OUTLINE_WIDTH,
            y=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_OUTLINE_WIDTH,
        )
        self.header_fill.pack_propagate(False)

        self.header_label = tk.Label(
            self.header_fill,
            text=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_TEXT,
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_BG,
            fg=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_TEXT_COLOR,
            font=(
                spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_FONT_FAMILY,
                spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_FONT_SIZE,
            ),
        )
        self.header_label.place(relx=0.5, rely=0.5, anchor='c')

        strip_y = spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_HEIGHT
        self.mode_strip = tk.Frame(
            self,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[0],
            height=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_STRIP_HEIGHT,
        )
        self.mode_strip.place(x=0, y=strip_y)
        self.mode_strip.pack_propagate(False)

        self.inventory_button = _PreviewModeButton(
            self.mode_strip,
            text='Inventory',
            command=lambda: self._select_mode('inventory'),
            size=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_BUTTON_SIZE,
        )
        self.inventory_button.place(x=0, y=0)

        self.world_button = _PreviewModeButton(
            self.mode_strip,
            text='World',
            command=lambda: self._select_mode('world'),
            size=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_BUTTON_SIZE,
        )
        self.world_button.place(x=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_BUTTON_SIZE[0], y=0)

        content_y = strip_y + spec.MEDIA_ROW_LIVE_PREVIEW_MODE_STRIP_HEIGHT
        self.content_border = tk.Frame(
            self,
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_OUTLINE,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_SIZE[0],
            height=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_SIZE[1],
        )
        self.content_border.place(x=0, y=content_y)
        self.content_border.pack_propagate(False)

        self.content_area = tk.Frame(
            self.content_border,
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_BG,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_SIZE[0] - (spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_OUTLINE_WIDTH * 2),
            height=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_SIZE[1] - (spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_OUTLINE_WIDTH * 2),
        )
        self.content_area.place(
            x=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_OUTLINE_WIDTH,
            y=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_OUTLINE_WIDTH,
        )
        self.content_area.pack_propagate(False)

        self._apply_state()

    def _select_mode(self, mode: str) -> None:
        if mode == self._selected_mode:
            return
        self._selected_mode = mode
        self._apply_state()
        if self._on_mode_selected is not None:
            self._on_mode_selected(self._row_id, mode)

    def _apply_state(self) -> None:
        self.inventory_button.set_active(self._selected_mode == 'inventory')
        self.world_button.set_active(self._selected_mode == 'world')

    def set_bg_color(self, color: str) -> None:
        self.configure(bg=color)
        self.mode_strip.configure(bg=color)
