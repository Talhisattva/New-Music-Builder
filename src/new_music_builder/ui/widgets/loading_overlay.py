from __future__ import annotations

from pathlib import Path
import tkinter as tk

from PIL import Image, ImageTk

from new_music_builder.ui import spec


class LoadingOverlay(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        size: tuple[int, int],
        icon_path: str | None,
        bg_color: str,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=size[0],
            height=size[1],
        )
        self.pack_propagate(False)
        self._size = size
        self._bg_color = bg_color
        self._angle = 0
        self._after_id: str | None = None
        self._base_icon = self._load_base_icon(icon_path)
        self._icon_image = None
        self._label = tk.Label(
            self,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
        )
        self._label.place(
            x=(size[0] - spec.MODULE_THREE_GRID_LOADING_ICON_SIZE[0]) // 2,
            y=(size[1] - spec.MODULE_THREE_GRID_LOADING_ICON_SIZE[1]) // 2,
            width=spec.MODULE_THREE_GRID_LOADING_ICON_SIZE[0],
            height=spec.MODULE_THREE_GRID_LOADING_ICON_SIZE[1],
        )
        self.place_forget()

    def show(self, *, x: int, y: int) -> None:
        self.place(x=x, y=y)
        self.lift()
        self._angle = 0
        self._draw_icon()
        self._schedule_tick()

    def resize(self, size: tuple[int, int]) -> None:
        self._size = size
        self.configure(width=size[0], height=size[1])
        self._label.place_configure(
            x=(size[0] - spec.MODULE_THREE_GRID_LOADING_ICON_SIZE[0]) // 2,
            y=(size[1] - spec.MODULE_THREE_GRID_LOADING_ICON_SIZE[1]) // 2,
            width=spec.MODULE_THREE_GRID_LOADING_ICON_SIZE[0],
            height=spec.MODULE_THREE_GRID_LOADING_ICON_SIZE[1],
        )

    def hide(self) -> None:
        self._cancel_tick()
        self.place_forget()

    def _load_base_icon(self, icon_path: str | None) -> Image.Image | None:
        if not icon_path:
            return None
        path = Path(icon_path)
        if not path.exists():
            return None
        image = Image.open(path).convert('RGBA')
        if image.size != spec.MODULE_THREE_GRID_LOADING_ICON_SIZE:
            image = image.resize(spec.MODULE_THREE_GRID_LOADING_ICON_SIZE, Image.Resampling.LANCZOS)
        return image

    def _draw_icon(self) -> None:
        if self._base_icon is None:
            self._label.configure(image='')
            self._label.image = None
            return
        rotated = self._base_icon.rotate(-self._angle, resample=Image.Resampling.BICUBIC)
        self._icon_image = ImageTk.PhotoImage(rotated)
        self._label.configure(image=self._icon_image)
        self._label.image = self._icon_image

    def _schedule_tick(self) -> None:
        self._cancel_tick()
        self._after_id = self.after(spec.MODULE_THREE_GRID_LOADING_INTERVAL_MS, self._tick)

    def _cancel_tick(self) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _tick(self) -> None:
        self._after_id = None
        self._angle = (self._angle + spec.MODULE_THREE_GRID_LOADING_STEP_DEGREES) % 360
        self._draw_icon()
        self._schedule_tick()
