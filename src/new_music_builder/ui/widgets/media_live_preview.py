from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk

from PIL import Image, ImageTk

from new_music_builder.domain.models import MediaRow
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage


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
        self._fill_id = self.create_rectangle(
            0,
            0,
            self._size[0],
            self._size[1],
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
        asset_paths: dict[str, dict[str, str]] | None = None,
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
        self._asset_paths = asset_paths or {}
        self._on_mode_selected = on_mode_selected
        self._content_bg = spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_BG
        self._slot_keys = (
            ('cassette', 'cassette_case'),
            ('vinyl', 'vinyl_jacket'),
            ('cd', 'cd_cover'),
        )
        self._slot_frames: list[tk.Frame] = []
        self._slot_labels: list[tk.Label] = []
        self._images: dict[str, dict[str, tk.PhotoImage | None]] = {
            mode: {
                key: self._load_preview_image(mode, key, path)
                for key, path in mode_paths.items()
            }
            for mode, mode_paths in self._asset_paths.items()
        }

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

        self.mode_left_border = tk.Frame(
            self.mode_strip,
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE_WIDTH,
            height=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_STRIP_HEIGHT,
        )
        self.mode_left_border.place(x=0, y=0)

        self.world_button = _PreviewModeButton(
            self.mode_strip,
            text='World',
            command=lambda: self._select_mode('world'),
            size=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_BUTTON_SIZE,
        )
        self.world_button.place(x=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_BUTTON_SIZE[0], y=0)

        self.mode_right_border = tk.Frame(
            self.mode_strip,
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE_WIDTH,
            height=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_STRIP_HEIGHT,
        )
        self.mode_right_border.place(
            x=spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[0] - spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE_WIDTH,
            y=0,
        )

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

        self._build_content_slots()

        self._apply_state()

    def _load_preview_image(
        self,
        mode: str,
        key: str,
        path: str | None,
    ) -> tk.PhotoImage | None:
        if mode != 'world':
            return load_tk_photoimage(path)
        if key == 'cassette':
            return self._load_aspect_fit_image(path, spec.MEDIA_ROW_LIVE_PREVIEW_SLOT_SIZE)
        return load_tk_photoimage(path, size=spec.MEDIA_ROW_LIVE_PREVIEW_SLOT_SIZE)

    def _load_aspect_fit_image(
        self,
        path: str | None,
        box_size: tuple[int, int],
    ) -> tk.PhotoImage | None:
        if not path:
            return None
        img_path = Path(path)
        if not img_path.exists():
            return None
        image = Image.open(img_path)
        fitted = Image.new('RGBA', box_size, (0, 0, 0, 0))
        contained = image.copy()
        contained.thumbnail(box_size, Image.Resampling.LANCZOS)
        paste_x = (box_size[0] - contained.width) // 2
        paste_y = (box_size[1] - contained.height) // 2
        fitted.paste(contained, (paste_x, paste_y), contained if contained.mode == 'RGBA' else None)
        return ImageTk.PhotoImage(fitted)

    def _build_content_slots(self) -> None:
        left_x = spec.MEDIA_ROW_LIVE_PREVIEW_SLOT_LEFT_X
        top_y = spec.MEDIA_ROW_LIVE_PREVIEW_SLOT_TOP_Y
        slot_width, slot_height = spec.MEDIA_ROW_LIVE_PREVIEW_SLOT_SIZE
        right_x = left_x + slot_width + spec.MEDIA_ROW_LIVE_PREVIEW_SLOT_GAP_X

        for row_index, _pair in enumerate(self._slot_keys):
            slot_y = top_y + (row_index * slot_height)
            for slot_x in (left_x, right_x):
                slot = tk.Frame(
                    self.content_area,
                    bg=self._content_bg,
                    bd=0,
                    highlightthickness=0,
                    width=slot_width,
                    height=slot_height,
                )
                slot.place(x=slot_x, y=slot_y)
                slot.pack_propagate(False)
                label = tk.Label(
                    slot,
                    bg=self._content_bg,
                    bd=0,
                    highlightthickness=0,
                )
                label.place(relx=0.5, rely=0.5, anchor='center')
                self._slot_frames.append(slot)
                self._slot_labels.append(label)

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
        self._apply_preview_images()

    def _apply_preview_images(self) -> None:
        mode_images = self._images.get(self._selected_mode, {})
        for row_index, (media_key, container_key) in enumerate(self._slot_keys):
            left_label = self._slot_labels[row_index * 2]
            right_label = self._slot_labels[(row_index * 2) + 1]
            left_label.configure(image=mode_images.get(media_key), bg=self._content_bg)
            right_label.configure(image=mode_images.get(container_key), bg=self._content_bg)

    def set_bg_color(self, color: str) -> None:
        self.configure(bg=color)
        self.mode_strip.configure(bg=color)
