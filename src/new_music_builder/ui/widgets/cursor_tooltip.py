from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import re
import tkinter as tk
import tkinter.font as tkfont

from PIL import Image, ImageTk

from new_music_builder.ui import spec
from new_music_builder.ui.help_tooltip_registry import TooltipSegment
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
    pointer_base_y: int = 0
    pointer_half_width: int = 0


@dataclass(frozen=True, slots=True)
class TooltipLayoutRun:
    tone: str
    text: str


@dataclass(frozen=True, slots=True)
class TooltipLayout:
    lines: tuple[tuple[TooltipLayoutRun, ...], ...]
    max_line_width: int


def pick_inward_tooltip_direction(
    *,
    cursor_x: int,
    cursor_y: int,
    window_left: int,
    window_top: int,
    window_width: int,
    window_height: int,
) -> str:
    center_x = window_left + (window_width / 2)
    center_y = window_top + (window_height / 2)
    delta_x = cursor_x - center_x
    delta_y = cursor_y - center_y
    if abs(delta_x) >= abs(delta_y):
        return 'left' if delta_x > 0 else 'right'
    return 'up' if delta_y > 0 else 'down'


def pick_inward_horizontal_anchor(
    *,
    cursor_x: int,
    window_left: int,
    window_width: int,
) -> str:
    center_x = window_left + (window_width / 2)
    return 'left' if cursor_x <= center_x else 'right'


def pick_inward_horizontal_direction(
    *,
    cursor_x: int,
    window_left: int,
    window_width: int,
) -> str:
    center_x = window_left + (window_width / 2)
    return 'right' if cursor_x <= center_x else 'left'


def compute_tooltip_placement(
    *,
    cursor_x: int,
    cursor_y: int,
    window_left: int,
    window_top: int,
    window_width: int,
    window_height: int,
    body_size: tuple[int, int],
    direction: str,
    cursor_offset: int,
    pointer_protrusion: int,
    pointer_size: int,
) -> TooltipPlacement:
    body_width, body_height = body_size
    pointer_half = pointer_size // 2
    if direction == 'left':
        pointer_tip_x = cursor_x - cursor_offset
        body_x = pointer_tip_x - pointer_protrusion - body_width
        unclamped_body_y = cursor_y - (body_height // 2)
        body_y = max(window_top, min((window_top + window_height) - body_height, unclamped_body_y))
        return TooltipPlacement(
            window_x=body_x,
            window_y=body_y,
            square_x=0,
            square_y=0,
            square_width=body_width,
            square_height=body_height,
            pointer_tip_x=body_width + pointer_protrusion,
            pointer_tip_y=cursor_y - body_y,
            pointer_base_x=body_width,
            pointer_half_height=pointer_half,
        )
    if direction == 'right':
        pointer_tip_x = cursor_x + cursor_offset
        body_x = pointer_tip_x + pointer_protrusion
        unclamped_body_y = cursor_y - (body_height // 2)
        body_y = max(window_top, min((window_top + window_height) - body_height, unclamped_body_y))
        return TooltipPlacement(
            window_x=pointer_tip_x,
            window_y=body_y,
            square_x=pointer_protrusion,
            square_y=0,
            square_width=body_width,
            square_height=body_height,
            pointer_tip_x=0,
            pointer_tip_y=cursor_y - body_y,
            pointer_base_x=pointer_protrusion,
            pointer_half_height=pointer_half,
        )
    if direction == 'up':
        pointer_tip_y = cursor_y - cursor_offset
        body_y = pointer_tip_y - pointer_protrusion - body_height
        horizontal_anchor = pick_inward_horizontal_anchor(
            cursor_x=cursor_x,
            window_left=window_left,
            window_width=window_width,
        )
        unclamped_body_x = (
            cursor_x - pointer_protrusion
            if horizontal_anchor == 'left'
            else cursor_x + pointer_protrusion - body_width
        )
        body_x = max(window_left, min((window_left + window_width) - body_width, unclamped_body_x))
        base_x = 0 if horizontal_anchor == 'left' else body_width - pointer_size
        return TooltipPlacement(
            window_x=body_x,
            window_y=body_y,
            square_x=0,
            square_y=0,
            square_width=body_width,
            square_height=body_height,
            pointer_tip_x=cursor_x - body_x,
            pointer_tip_y=body_height + pointer_protrusion,
            pointer_base_x=base_x,
            pointer_half_height=0,
            pointer_base_y=body_height,
            pointer_half_width=pointer_size,
        )
    if direction == 'down':
        pointer_tip_y = cursor_y + cursor_offset
        body_y = pointer_tip_y + pointer_protrusion
        horizontal_anchor = pick_inward_horizontal_anchor(
            cursor_x=cursor_x,
            window_left=window_left,
            window_width=window_width,
        )
        unclamped_body_x = (
            cursor_x - pointer_protrusion
            if horizontal_anchor == 'left'
            else cursor_x + pointer_protrusion - body_width
        )
        body_x = max(window_left, min((window_left + window_width) - body_width, unclamped_body_x))
        base_x = 0 if horizontal_anchor == 'left' else body_width - pointer_size
        return TooltipPlacement(
            window_x=body_x,
            window_y=pointer_tip_y,
            square_x=0,
            square_y=pointer_protrusion,
            square_width=body_width,
            square_height=body_height,
            pointer_tip_x=cursor_x - body_x,
            pointer_tip_y=0,
            pointer_base_x=base_x,
            pointer_half_height=0,
            pointer_base_y=pointer_protrusion,
            pointer_half_width=pointer_size,
        )
    raise ValueError(f'Unsupported tooltip direction: {direction}')


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
    return compute_tooltip_placement(
        cursor_x=cursor_x,
        cursor_y=cursor_y,
        window_left=window_left,
        window_top=window_top,
        window_width=window_width,
        window_height=window_height,
        body_size=square_size,
        direction='left',
        cursor_offset=spec.MODULE_THREE_TOOLTIP_CURSOR_OFFSET_X,
        pointer_protrusion=pointer_protrusion,
        pointer_size=spec.MODULE_THREE_TOOLTIP_POINTER_SIZE,
    )


def layout_tooltip_segments(
    segments: Sequence[TooltipSegment],
    *,
    max_width: int,
    measure_normal: Callable[[str], int],
    measure_accent: Callable[[str], int],
    measure_tag: Callable[[str], int],
) -> TooltipLayout:
    lines: list[list[TooltipLayoutRun]] = [[]]
    current_width = 0
    max_line_width = 0
    token_pattern = re.compile(r'\S+|\s+')

    def _measure(text: str, tone: str) -> int:
        if tone == 'accent':
            return measure_accent(text)
        if tone == 'tag':
            return measure_tag(text)
        return measure_normal(text)

    auto_wrap_enabled = max_width > 0

    def _append_to_line(text: str, tone: str) -> None:
        nonlocal current_width, max_line_width
        if not text:
            return
        token_width = _measure(text, tone)
        current_line = lines[-1]
        if current_line and current_line[-1].tone == tone:
            current_line[-1] = TooltipLayoutRun(tone, current_line[-1].text + text)
        else:
            current_line.append(TooltipLayoutRun(tone, text))
        current_width += token_width
        max_line_width = max(max_line_width, current_width)

    def _start_new_line() -> None:
        nonlocal current_width
        if lines[-1]:
            lines.append([])
        current_width = 0

    def _split_token(text: str, tone: str) -> list[str]:
        parts: list[str] = []
        chunk = ''
        for character in text:
            candidate = f'{chunk}{character}'
            if chunk and _measure(candidate, tone) > max_width:
                parts.append(chunk)
                chunk = character
            else:
                chunk = candidate
        if chunk:
            parts.append(chunk)
        return parts

    for segment in segments:
        if segment.tone == 'break':
            _start_new_line()
            continue
        for token in token_pattern.findall(segment.text):
            if token.isspace():
                if not lines[-1]:
                    continue
                token_width = _measure(token, segment.tone)
                if auto_wrap_enabled and current_width + token_width > max_width:
                    _start_new_line()
                    continue
                _append_to_line(token, segment.tone)
                continue
            token_width = _measure(token, segment.tone)
            if not auto_wrap_enabled:
                _append_to_line(token, segment.tone)
                continue
            if token_width <= max_width:
                if lines[-1] and current_width + token_width > max_width:
                    _start_new_line()
                _append_to_line(token, segment.tone)
                continue
            for index, part in enumerate(_split_token(token, segment.tone)):
                if index > 0:
                    _start_new_line()
                elif lines[-1] and current_width + _measure(part, segment.tone) > max_width:
                    _start_new_line()
                _append_to_line(part, segment.tone)

    compact_lines = tuple(tuple(line) for line in lines if line)
    return TooltipLayout(lines=compact_lines, max_line_width=max_line_width)


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
        self._pil_image: Image.Image | None = None
        self._image = None
        self._watch_after_id: str | None = None
        self.owner.bind('<Destroy>', self._hide_from_event, add='+')
        self.owner.bind('<FocusOut>', self._hide_from_event, add='+')
        self.owner.bind('<Unmap>', self._hide_from_event, add='+')

    @property
    def content_frame(self) -> tk.Frame | None:
        return self._content_frame

    def set_content_renderer(self, renderer) -> None:
        self._content_renderer = renderer

    def set_image(self, path: str | None) -> None:
        self._image_path = path
        self._pil_image = None
        if self._image_label is None:
            return
        self._image = load_tk_photoimage_contained(path, spec.MODULE_THREE_TOOLTIP_IMAGE_SIZE, allow_upscale=True) if path else None
        self._image_label.configure(image=self._image if self._image is not None else '')
        self._image_label.image = self._image

    def set_pil_image(self, image: Image.Image | None) -> None:
        self._image_path = None
        self._pil_image = image.copy() if image is not None else None
        if self._image_label is None:
            return
        self._image = self._photoimage_for_pil_image(self._pil_image)
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
        self._watch_visibility()

    def move_to_cursor(self, x_root: int, y_root: int) -> None:
        self._last_cursor = (x_root, y_root)
        if self._window is None or self._canvas is None:
            return
        placement = self._compute_placement(x_root, y_root)
        total_width = placement.square_x + placement.square_width + (
            spec.MODULE_THREE_TOOLTIP_POINTER_PROTRUSION if self._direction in {'left', 'right'} else 0
        )
        total_height = placement.square_y + placement.square_height + (
            spec.MODULE_THREE_TOOLTIP_POINTER_PROTRUSION if self._direction in {'up', 'down'} else 0
        )
        self._window.geometry(f'{total_width}x{total_height}+{placement.window_x}+{placement.window_y}')
        self._redraw(placement)

    def hide(self) -> None:
        self._cancel_watch()
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
        if self._pil_image is not None:
            self.set_pil_image(self._pil_image)
        else:
            self.set_image(self._image_path)
        if self._content_renderer is not None:
            self._content_renderer(self._content_frame)
        self._window.withdraw()
        self._window.bind('<Destroy>', self._on_destroy, add='+')
        self._window.bind('<FocusOut>', self._hide_from_event, add='+')
        self._window.bind('<Unmap>', self._hide_from_event, add='+')

    def _compute_placement(self, x_root: int, y_root: int) -> TooltipPlacement:
        if self._direction not in {'left', 'right'}:
            raise ValueError(f'Unsupported tooltip direction: {self._direction}')
        return compute_tooltip_placement(
            cursor_x=x_root,
            cursor_y=y_root,
            window_left=self.owner.winfo_toplevel().winfo_rootx(),
            window_top=self.owner.winfo_toplevel().winfo_rooty(),
            window_width=self.owner.winfo_toplevel().winfo_width(),
            window_height=self.owner.winfo_toplevel().winfo_height(),
            body_size=spec.MODULE_THREE_TOOLTIP_SQUARE_SIZE,
            direction=self._direction,
            cursor_offset=spec.MODULE_THREE_TOOLTIP_CURSOR_OFFSET_X,
            pointer_protrusion=spec.MODULE_THREE_TOOLTIP_POINTER_PROTRUSION,
            pointer_size=spec.MODULE_THREE_TOOLTIP_POINTER_SIZE,
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
        self._cancel_watch()
        self._window = None
        self._canvas = None
        self._content_frame = None
        self._image_label = None

    def _hide_from_event(self, _event: tk.Event | None = None) -> None:
        self.hide()

    def _watch_visibility(self) -> None:
        self._cancel_watch()
        if self._window is None:
            return
        if not self._should_remain_visible():
            self.hide()
            return
        self._watch_after_id = self.owner.after(80, self._watch_visibility)

    def _cancel_watch(self) -> None:
        if self._watch_after_id is None:
            return
        try:
            self.owner.after_cancel(self._watch_after_id)
        except tk.TclError:
            pass
        self._watch_after_id = None

    def _should_remain_visible(self) -> bool:
        try:
            toplevel = self.owner.winfo_toplevel()
            if toplevel.focus_displayof() is None:
                return False
            pointer_x = self.owner.winfo_pointerx()
            pointer_y = self.owner.winfo_pointery()
            hovered = self.owner.winfo_containing(pointer_x, pointer_y)
            return self._is_owner_descendant(hovered)
        except tk.TclError:
            return False

    def _photoimage_for_pil_image(self, image: Image.Image | None) -> tk.PhotoImage | None:
        if image is None:
            return None
        contained = image.convert('RGBA')
        scale_ratio = min(
            spec.MODULE_THREE_TOOLTIP_IMAGE_SIZE[0] / max(1, contained.width),
            spec.MODULE_THREE_TOOLTIP_IMAGE_SIZE[1] / max(1, contained.height),
        )
        contained_size = (
            max(1, int(round(contained.width * scale_ratio))),
            max(1, int(round(contained.height * scale_ratio))),
        )
        contained = contained.resize(contained_size, Image.Resampling.LANCZOS)
        fitted = Image.new('RGBA', spec.MODULE_THREE_TOOLTIP_IMAGE_SIZE, (0, 0, 0, 0))
        paste_x = (fitted.width - contained.width) // 2
        paste_y = (fitted.height - contained.height) // 2
        fitted.paste(contained, (paste_x, paste_y), contained)
        return ImageTk.PhotoImage(fitted)

    def _is_owner_descendant(self, widget: tk.Misc | None) -> bool:
        current = widget
        while current is not None:
            if current == self.owner:
                return True
            current = current.master
        return False


class HelpCursorTooltip:
    def __init__(self, owner: tk.Misc) -> None:
        self.owner = owner
        self._window: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._watch_after_id: str | None = None
        self._last_cursor: tuple[int, int] = (0, 0)
        self._segments: tuple[TooltipSegment, ...] = ()
        self._target_widgets: tuple[tk.Misc, ...] = (owner,)
        self._normal_font = tkfont.Font(
            family=spec.HELP_TOOLTIP_FONT_FAMILY,
            size=spec.HELP_TOOLTIP_FONT_SIZE,
        )
        self._accent_font = tkfont.Font(
            family=spec.HELP_TOOLTIP_ACCENT_FONT_FAMILY,
            size=spec.HELP_TOOLTIP_FONT_SIZE,
        )
        self._tag_font = tkfont.Font(
            family=spec.HELP_TOOLTIP_TAG_FONT_FAMILY,
            size=spec.HELP_TOOLTIP_FONT_SIZE,
        )
        self.owner.bind('<Destroy>', self._hide_from_event, add='+')
        self.owner.bind('<FocusOut>', self._hide_from_event, add='+')
        self.owner.bind('<Unmap>', self._hide_from_event, add='+')

    def set_segments(self, segments: Sequence[TooltipSegment]) -> None:
        self._segments = tuple(
            segment
            for segment in segments
            if segment.text or segment.tone == 'break'
        )

    def set_target_widgets(self, widgets: Sequence[tk.Misc]) -> None:
        self._target_widgets = tuple(widgets) if widgets else (self.owner,)

    def show_at_cursor(self, x_root: int, y_root: int, *, preferred_direction: str | None = None) -> None:
        if not self._segments:
            return
        self._last_cursor = (x_root, y_root)
        self._ensure_window()
        self.move_to_cursor(x_root, y_root, preferred_direction=preferred_direction)
        if self._window is not None:
            self._window.deiconify()
            self._window.lift()
        self._watch_visibility()

    def move_to_cursor(self, x_root: int, y_root: int, *, preferred_direction: str | None = None) -> None:
        self._last_cursor = (x_root, y_root)
        if self._window is None or self._canvas is None or not self._segments:
            return
        body_width, body_height, layout = self._measure_text_body()
        toplevel = self.owner.winfo_toplevel()
        if preferred_direction == 'horizontal-auto':
            direction = pick_inward_horizontal_direction(
                cursor_x=x_root,
                window_left=toplevel.winfo_rootx(),
                window_width=toplevel.winfo_width(),
            )
        else:
            direction = preferred_direction or pick_inward_tooltip_direction(
                cursor_x=x_root,
                cursor_y=y_root,
                window_left=toplevel.winfo_rootx(),
                window_top=toplevel.winfo_rooty(),
                window_width=toplevel.winfo_width(),
                window_height=toplevel.winfo_height(),
            )
        placement = compute_tooltip_placement(
            cursor_x=x_root,
            cursor_y=y_root,
            window_left=toplevel.winfo_rootx(),
            window_top=toplevel.winfo_rooty(),
            window_width=toplevel.winfo_width(),
            window_height=toplevel.winfo_height(),
            body_size=(body_width, body_height),
            direction=direction,
            cursor_offset=spec.HELP_TOOLTIP_CURSOR_OFFSET,
            pointer_protrusion=spec.HELP_TOOLTIP_POINTER_PROTRUSION,
            pointer_size=spec.HELP_TOOLTIP_POINTER_SIZE,
        )
        total_width = placement.square_x + placement.square_width + (
            spec.HELP_TOOLTIP_POINTER_PROTRUSION if direction in {'left', 'right'} else 0
        )
        total_height = placement.square_y + placement.square_height + (
            spec.HELP_TOOLTIP_POINTER_PROTRUSION if direction in {'up', 'down'} else 0
        )
        self._window.geometry(f'{total_width}x{total_height}+{placement.window_x}+{placement.window_y}')
        self._redraw_text_tooltip(placement, layout, direction)

    def hide(self) -> None:
        self._cancel_watch()
        if self._window is not None:
            self._window.withdraw()

    def _measure_text_body(self) -> tuple[int, int, TooltipLayout]:
        layout = layout_tooltip_segments(
            self._segments,
            max_width=spec.HELP_TOOLTIP_WRAP_WIDTH,
            measure_normal=self._normal_font.measure,
            measure_accent=self._accent_font.measure,
            measure_tag=self._tag_font.measure,
        )
        line_height = max(
            self._normal_font.metrics('linespace'),
            self._accent_font.metrics('linespace'),
            self._tag_font.metrics('linespace'),
        )
        width = layout.max_line_width + (spec.HELP_TOOLTIP_PADDING * 2)
        height = (len(layout.lines) * line_height) + (spec.HELP_TOOLTIP_PADDING * 2)
        return width, height, layout

    def _ensure_window(self) -> None:
        if self._window is not None:
            return
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
            bg=spec.MODULE_THREE_TOOLTIP_TRANSPARENT_KEY,
            bd=0,
            highlightthickness=0,
        )
        self._canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self._window.withdraw()
        self._window.bind('<Destroy>', self._on_destroy, add='+')
        self._window.bind('<FocusOut>', self._hide_from_event, add='+')
        self._window.bind('<Unmap>', self._hide_from_event, add='+')

    def _redraw_text_tooltip(self, placement: TooltipPlacement, layout: TooltipLayout, direction: str) -> None:
        if self._canvas is None:
            return
        self._canvas.delete('all')
        total_width = placement.square_x + placement.square_width + (
            spec.HELP_TOOLTIP_POINTER_PROTRUSION if direction in {'left', 'right'} else 0
        )
        total_height = placement.square_y + placement.square_height + (
            spec.HELP_TOOLTIP_POINTER_PROTRUSION if direction in {'up', 'down'} else 0
        )
        self._canvas.configure(width=total_width, height=total_height)
        self._canvas.create_rectangle(
            placement.square_x,
            placement.square_y,
            placement.square_x + placement.square_width,
            placement.square_y + placement.square_height,
            outline='',
            fill=spec.MODULE_THREE_TOOLTIP_BG,
        )
        if direction in {'left', 'right'}:
            edge_x = placement.square_x if direction == 'right' else placement.square_x + placement.square_width
            self._canvas.create_polygon(
                edge_x,
                placement.square_y,
                edge_x,
                placement.square_y + placement.square_height,
                placement.pointer_tip_x,
                placement.pointer_tip_y,
                outline='',
                fill=spec.MODULE_THREE_TOOLTIP_BG,
            )
        else:
            self._canvas.create_polygon(
                placement.square_x + placement.pointer_base_x,
                placement.pointer_base_y,
                placement.square_x + placement.pointer_base_x + placement.pointer_half_width,
                placement.pointer_base_y,
                placement.pointer_tip_x,
                placement.pointer_tip_y,
                outline='',
                fill=spec.MODULE_THREE_TOOLTIP_BG,
            )
        line_height = max(
            self._normal_font.metrics('linespace'),
            self._accent_font.metrics('linespace'),
            self._tag_font.metrics('linespace'),
        )
        y = placement.square_y + spec.HELP_TOOLTIP_PADDING
        for line in layout.lines:
            x = placement.square_x + spec.HELP_TOOLTIP_PADDING
            for run in line:
                if run.tone == 'accent':
                    font = self._accent_font
                    color = spec.HELP_TOOLTIP_ACCENT_COLOR
                elif run.tone == 'tag':
                    font = self._tag_font
                    color = spec.HELP_TOOLTIP_TAG_COLOR
                else:
                    font = self._normal_font
                    color = spec.HELP_TOOLTIP_TEXT_COLOR
                if run.text:
                    self._canvas.create_text(
                        x,
                        y,
                        text=run.text,
                        fill=color,
                        font=font,
                        anchor='nw',
                    )
                    x += font.measure(run.text)
            y += line_height

    def _watch_visibility(self) -> None:
        self._cancel_watch()
        if self._window is None:
            return
        if not self._should_remain_visible():
            self.hide()
            return
        self._watch_after_id = self.owner.after(80, self._watch_visibility)

    def _should_remain_visible(self) -> bool:
        try:
            toplevel = self.owner.winfo_toplevel()
            if toplevel.focus_displayof() is None:
                return False
            pointer_x = self.owner.winfo_pointerx()
            pointer_y = self.owner.winfo_pointery()
            hovered = self.owner.winfo_containing(pointer_x, pointer_y)
            return self._is_target_descendant(hovered)
        except tk.TclError:
            return False

    def _is_target_descendant(self, widget: tk.Misc | None) -> bool:
        current = widget
        while current is not None:
            if any(current == target for target in self._target_widgets):
                return True
            current = current.master
        return False

    def _cancel_watch(self) -> None:
        if self._watch_after_id is None:
            return
        try:
            self.owner.after_cancel(self._watch_after_id)
        except tk.TclError:
            pass
        self._watch_after_id = None

    def _on_destroy(self, _event: tk.Event | None = None) -> None:
        self._cancel_watch()
        self._window = None
        self._canvas = None

    def _hide_from_event(self, _event: tk.Event | None = None) -> None:
        self.hide()
