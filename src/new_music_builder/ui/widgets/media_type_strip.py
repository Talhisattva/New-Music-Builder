from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk

from new_music_builder.domain.models import MediaKind, MediaRow
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage
from new_music_builder.ui.widgets.labeled_checkbox import ImageCheckbox


MEDIA_KIND_ORDER: tuple[MediaKind, ...] = ('cassette', 'vinyl', 'cd')


class MediaTypeStrip(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        row: MediaRow,
        expanded: bool,
        cassette_icon_path: str | Path | None,
        vinyl_icon_path: str | Path | None,
        cd_icon_path: str | Path | None,
        check_icon_path: str | Path | None,
        bg_color: str | None = None,
        on_enabled_media_changed: Callable[[int, MediaKind, bool], None] | None = None,
    ) -> None:
        resolved_bg = bg_color if bg_color is not None else parent.cget('bg')
        size = spec.MEDIA_ROW_MEDIA_STRIP_EXPANDED_SIZE if expanded else spec.MEDIA_ROW_MEDIA_STRIP_COLLAPSED_SIZE
        super().__init__(
            parent,
            bg=resolved_bg,
            bd=0,
            highlightthickness=0,
            width=size[0],
            height=size[1],
        )
        self.pack_propagate(False)
        self._row = row
        self._expanded = expanded
        self._bg_color = resolved_bg
        self._check_icon_path = check_icon_path
        self._on_enabled_media_changed = on_enabled_media_changed
        self._icon_paths: dict[MediaKind, str | Path | None] = {
            'cassette': cassette_icon_path,
            'vinyl': vinyl_icon_path,
            'cd': cd_icon_path,
        }
        self._icon_images: dict[MediaKind, tk.PhotoImage | None] = {
            kind: load_tk_photoimage(path)
            for kind, path in self._icon_paths.items()
        }
        self.icon_frames: dict[MediaKind, tk.Frame] = {}
        self.icon_labels: dict[MediaKind, tk.Label] = {}
        self.checkboxes: dict[MediaKind, ImageCheckbox] = {}

        self._build()

    def _build(self) -> None:
        slot_width, slot_height = spec.MEDIA_ROW_MEDIA_STRIP_SLOT_SIZE
        for index, kind in enumerate(MEDIA_KIND_ORDER):
            slot_x = index * (slot_width + spec.MEDIA_ROW_MEDIA_STRIP_GAP_X)
            slot = tk.Frame(
                self,
                bg=self._bg_color,
                bd=0,
                highlightthickness=0,
                width=slot_width,
                height=slot_height,
            )
            slot.place(x=slot_x, y=0)
            slot.pack_propagate(False)
            self.icon_frames[kind] = slot

            label = tk.Label(
                slot,
                bg=self._bg_color,
                bd=0,
                highlightthickness=0,
                image=self._icon_images[kind],
            )
            self.icon_labels[kind] = label
            if self._expanded or self._row.enabled_media[kind]:
                label.place(relx=0.5, rely=0.5, anchor='center')

            if not self._expanded:
                continue

            checkbox = ImageCheckbox(
                self,
                icon_path=self._check_icon_path,
                checked=self._row.enabled_media[kind],
                command=lambda checked, media_kind=kind: self._on_checkbox_toggled(media_kind, checked),
            )
            checkbox.place(
                x=slot_x + ((slot_width - spec.POSTER_NAME_CHECKBOX_SIZE[0]) // 2),
                y=slot_height + spec.MEDIA_ROW_MEDIA_STRIP_CHECKBOX_GAP_Y,
            )
            self.checkboxes[kind] = checkbox

    def _on_checkbox_toggled(self, kind: MediaKind, checked: bool) -> None:
        if self._on_enabled_media_changed is not None:
            self._on_enabled_media_changed(self._row.row_id, kind, checked)

    def set_bg_color(self, bg_color: str) -> None:
        self._bg_color = bg_color
        self.configure(bg=bg_color)
        for frame in self.icon_frames.values():
            frame.configure(bg=bg_color)
        for label in self.icon_labels.values():
            label.configure(bg=bg_color)
