from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage_contained


@dataclass(slots=True)
class TooltipPlacement:
    window_x: int
    window_y: int
    square_x: int
    square_y: int
    square_width: int
    square_height: int
    pointer_tip_x: int
    pointer_tip_y: int
    pointer_base_x: int
    pointer_half_height: int


def compute_left_tooltip_placement(
    *,
    cursor_x: int,
    cursor_y: int,
    window_left: int,
    window_top: int,
    window_width: int,
    window_height: int,
    square_size: tuple[int, int] = spec.MODULE_THREE_TOOLTIP_SQUARE_SIZE,
    pointer_protrusion: int = spec.MODULE_THREE_TOOLTIP_POINTER_PROTRUSION,
) -> TooltipPlacement:
    square_width, square_height = square_size
    pointer_tip_x = cursor_x - spec.MODULE_THREE_TOOLTIP_CURSOR_OFFSET_X
    square_x = pointer_tip_x - pointer_protrusion - square_width
    unclamped_square_y = cursor_y - (square_height // 2)
    min_square_y = window_top
    max_square_y = max(window_top, (window_top + window_height) - square_height)
    square_y = max(min_square_y, min(max_square_y, unclamped_square_y))
    pointer_half_height = spec.MODULE_THREE_TOOLTIP_POINTER_SIZE // 2
    pointer_tip_y = cursor_y
    pointer_base_x = square_x + square_width
    return TooltipPlacement(
        window_x=square_x,
        window_y=square_y,
        square_x=0,
        square_y=0,
        square_width=square_width,
        square_height=square_height,
        pointer_tip_x=(pointer_base_x - square_x) + pointer_protrusion,
        pointer_tip_y=pointer_tip_y - square_y,
        pointer_base_x=pointer_base_x - square_x,
        pointer_half_height=pointer_half_height,
    )


class CursorTooltip:
    def __init__(self, owner: tk.Misc) -> None:
        self.owner = owner
        self._window: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._content_frame: tk.Frame | None = None
        self._image_label: tk.Label | None = None
        self._direction = 'left'
        self._last_cursor: tuple[int, int] = (0, 0)
        self._content_renderer = None
        self._image_path: str | None = None
        self._image = None

    @property
    def content_frame(self) -> tk.Frame | None:
        return self._content_frame

    def set_content_renderer(self, renderer) -> None:
        self._content_renderer = renderer

    def set_image(self, path: str | None) -> None:
        self._image_path = path
        if self._image_label is None:
            return
        self._image = load_tk_photoimage_contained(path, spec.MODULE_THREE_TOOLTIP_IMAGE_SIZE) if path else None
        self._image_label.configure(image=self._image if self._image is not None else '')
        self._image_label.image = self._image

    def show_at_cursor(self, x_root: int, y_root: int, *, direction: str = 'left') -> None:
        self._direction = direction
        self._last_cursor = (x_root, y_root)
        self._ensure_window()
        self.move_to_cursor(x_root, y_root)
        if self._window is not None:
            self._window.deiconify()
            self._window.lift()

    def move_to_cursor(self, x_root: int, y_root: int) -> None:
        self._last_cursor = (x_root, y_root)
        if self._window is None or self._canvas is None:
            return
        placement = self._compute_placement(x_root, y_root)
        total_width = placement.square_width + spec.MODULE_THREE_TOOLTIP_POINTER_PROTRUSION
        total_height = placement.square_height
        self._window.geometry(f'{total_width}x{total_height}+{placement.window_x}+{placement.window_y}')
        self._redraw(placement)

    def hide(self) -> None:
        if self._window is not None:
            self._window.withdraw()

    def _ensure_window(self) -> None:
        if self._window is not None:
            return
        total_width = spec.MODULE_THREE_TOOLTIP_SQUARE_SIZE[0] + spec.MODULE_THREE_TOOLTIP_POINTER_PROTRUSION
        total_height = spec.MODULE_THREE_TOOLTIP_SQUARE_SIZE[1]
        self._window = tk.Toplevel(self.owner.winfo_toplevel())
        self._window.overrideredirect(True)
        self._window.attributes('-topmost', True)
        self._window.configure(bg=spec.MODULE_THREE_TOOLTIP_TRANSPARENT_KEY)
        try:
            self._window.wm_attributes('-transparentcolor', spec.MODULE_THREE_TOOLTIP_TRANSPARENT_KEY)
        except tk.TclError:
            self._window.configure(bg=spec.MODULE_THREE_TOOLTIP_BG)
        self._canvas = tk.Canvas(
            self._window,
            width=total_width,
            height=total_height,
            bg=spec.MODULE_THREE_TOOLTIP_TRANSPARENT_KEY,
            bd=0,
            highlightthickness=0,
        )
        self._canvas.place(x=0, y=0)
        self._content_frame = tk.Frame(
            self._window,
            bg=spec.MODULE_THREE_TOOLTIP_BG,
            bd=0,
            highlightthickness=0,
            width=spec.MODULE_THREE_TOOLTIP_SQUARE_SIZE[0],
            height=spec.MODULE_THREE_TOOLTIP_SQUARE_SIZE[1],
        )
        self._content_frame.place(x=0, y=0)
        self._image_label = tk.Label(
            self._content_frame,
            bg=spec.MODULE_THREE_TOOLTIP_BG,
            bd=0,
            highlightthickness=0,
        )
        self._image_label.place(
            x=1,
            y=1,
            width=spec.MODULE_THREE_TOOLTIP_IMAGE_SIZE[0],
            height=spec.MODULE_THREE_TOOLTIP_IMAGE_SIZE[1],
        )
        self.set_image(self._image_path)
        if self._content_renderer is not None:
            self._content_renderer(self._content_frame)
        self._window.withdraw()
        self._window.bind('<Destroy>', self._on_destroy, add='+')

    def _compute_placement(self, x_root: int, y_root: int) -> TooltipPlacement:
        if self._direction != 'left':
            raise ValueError(f'Unsupported tooltip direction: {self._direction}')
        return compute_left_tooltip_placement(
            cursor_x=x_root,
            cursor_y=y_root,
            window_left=self.owner.winfo_toplevel().winfo_rootx(),
            window_top=self.owner.winfo_toplevel().winfo_rooty(),
            window_width=self.owner.winfo_toplevel().winfo_width(),
            window_height=self.owner.winfo_toplevel().winfo_height(),
        )

    def _redraw(self, placement: TooltipPlacement) -> None:
        if self._canvas is None or self._content_frame is None:
            return
        self._canvas.delete('all')
        self._content_frame.place(x=placement.square_x, y=placement.square_y)
        self._canvas.create_rectangle(
            placement.square_x,
            placement.square_y,
            placement.square_x + placement.square_width,
            placement.square_y + placement.square_height,
            outline='',
            fill=spec.MODULE_THREE_TOOLTIP_BG,
        )
        self._canvas.create_polygon(
            placement.pointer_base_x,
            placement.pointer_tip_y - placement.pointer_half_height,
            placement.pointer_base_x,
            placement.pointer_tip_y + placement.pointer_half_height,
            placement.pointer_tip_x,
            placement.pointer_tip_y,
            outline='',
            fill=spec.MODULE_THREE_TOOLTIP_BG,
        )

    def _on_destroy(self, _event: tk.Event | None = None) -> None:
        self._window = None
        self._canvas = None
        self._content_frame = None
        self._image_label = None
