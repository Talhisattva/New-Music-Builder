from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from new_music_builder.ui import spec


class CustomScrollbar(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        size: tuple[int, int] = spec.SCROLLBAR_TRACK_SIZE,
        track_bg: str = spec.SCROLLBAR_TRACK_BG,
        track_outline: str = spec.SCROLLBAR_TRACK_OUTLINE,
        track_outline_width: int = spec.SCROLLBAR_TRACK_OUTLINE_WIDTH,
        thumb_bg: str = spec.SCROLLBAR_THUMB_BG,
        thumb_outline: str = spec.SCROLLBAR_THUMB_OUTLINE,
        thumb_outline_width: int = spec.SCROLLBAR_THUMB_OUTLINE_WIDTH,
        thumb_min_height: int = spec.SCROLLBAR_THUMB_MIN_HEIGHT,
        thumb_max_height: int = spec.SCROLLBAR_THUMB_MAX_HEIGHT,
        command: Callable[[float], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=track_bg,
            width=size[0],
            height=size[1],
            bd=0,
            highlightthickness=0,
        )
        self._size = size
        self._track_bg = track_bg
        self._track_outline = track_outline
        self._track_outline_width = track_outline_width
        self._thumb_bg = thumb_bg
        self._thumb_outline = thumb_outline
        self._thumb_outline_width = thumb_outline_width
        self._thumb_min_height = thumb_min_height
        self._thumb_max_height = thumb_max_height
        self._command = command
        self._thumb_visible = False
        self._drag_active = False
        self._drag_offset_y = 0.0
        self._first_fraction = 0.0
        self._last_fraction = 1.0
        self._visible_fraction = 1.0
        self._thumb_height = 0.0

        self._draw_track()
        self._bind_events()

    def _draw_track(self) -> None:
        self._track_id = self.create_rectangle(
            0,
            0,
            self._size[0],
            self._size[1],
            outline='',
            fill=self._track_outline,
        )
        inset = self._track_outline_width
        self._track_fill_id = self.create_rectangle(
            inset,
            inset,
            self._size[0] - inset,
            self._size[1] - inset,
            outline='',
            fill=self._track_bg,
        )
        self._thumb_id = self.create_rectangle(
            0,
            0,
            self._size[0],
            self._thumb_min_height,
            outline='',
            fill=self._thumb_outline,
            state='hidden',
        )
        thumb_inset = self._thumb_outline_width
        self._thumb_fill_id = self.create_rectangle(
            thumb_inset,
            thumb_inset,
            self._size[0] - thumb_inset,
            self._thumb_min_height - thumb_inset,
            outline='',
            fill=self._thumb_bg,
            state='hidden',
        )

    def _bind_events(self) -> None:
        self.bind('<ButtonPress-1>', self._on_press, add='+')
        self.bind('<B1-Motion>', self._on_drag, add='+')
        self.bind('<ButtonRelease-1>', self._on_release, add='+')

    def set_command(self, command: Callable[[float], None] | None) -> None:
        self._command = command

    def set_metrics(self, *, content_height: int, viewport_height: int) -> None:
        if content_height <= viewport_height or viewport_height <= 0:
            self._thumb_visible = False
            self.itemconfigure(self._thumb_id, state='hidden')
            self.itemconfigure(self._thumb_fill_id, state='hidden')
            self._first_fraction = 0.0
            self._last_fraction = 1.0
            self._visible_fraction = 1.0
            self._thumb_height = 0.0
            return

        self._visible_fraction = viewport_height / content_height
        thumb_height = self._size[1] * self._visible_fraction
        thumb_height = max(self._thumb_min_height, min(self._thumb_max_height, thumb_height))
        self._thumb_height = thumb_height
        self._thumb_visible = True
        self.itemconfigure(self._thumb_id, state='normal')
        self.itemconfigure(self._thumb_fill_id, state='normal')
        self.set_view(0.0, self._visible_fraction)

    def set_view(self, first: float, last: float) -> None:
        self._first_fraction = max(0.0, min(1.0, first))
        self._last_fraction = max(self._first_fraction, min(1.0, last))
        if not self._thumb_visible:
            return

        available = max(0.0, self._size[1] - self._thumb_height)
        max_first = max(0.0, 1.0 - self._visible_fraction)
        if max_first <= 0.0:
            position_fraction = 0.0
        else:
            position_fraction = min(1.0, self._first_fraction / max_first)
        thumb_top = available * position_fraction
        thumb_bottom = thumb_top + self._thumb_height
        self.coords(self._thumb_id, 0, thumb_top, self._size[0], thumb_bottom)
        inset = self._thumb_outline_width
        self.coords(
            self._thumb_fill_id,
            inset,
            thumb_top + inset,
            self._size[0] - inset,
            thumb_bottom - inset,
        )

    def _on_press(self, event: tk.Event) -> str:
        if not self._thumb_visible:
            return 'break'
        thumb_coords = self.coords(self._thumb_id)
        thumb_top = thumb_coords[1]
        thumb_bottom = thumb_coords[3]
        if thumb_top <= event.y <= thumb_bottom:
            self._drag_active = True
            self._drag_offset_y = event.y - thumb_top
        else:
            self._drag_active = True
            self._drag_offset_y = self._thumb_height / 2
            self._move_thumb_to(event.y - self._drag_offset_y)
        return 'break'

    def _on_drag(self, event: tk.Event) -> str:
        if not self._drag_active or not self._thumb_visible:
            return 'break'
        self._move_thumb_to(event.y - self._drag_offset_y)
        return 'break'

    def _on_release(self, _event: tk.Event) -> str:
        self._drag_active = False
        return 'break'

    def _move_thumb_to(self, thumb_top: float) -> None:
        available = max(1.0, self._size[1] - self._thumb_height)
        clamped_top = max(0.0, min(available, thumb_top))
        fraction = clamped_top / available
        if self._command is not None:
            self._command(fraction)


class ScrollViewport(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        size: tuple[int, int] = spec.MODULE_TWO_SCROLL_AREA_SIZE,
        viewport_size: tuple[int, int] = spec.MODULE_TWO_SCROLL_VIEWPORT_SIZE,
        scrollbar_size: tuple[int, int] = spec.SCROLLBAR_TRACK_SIZE,
        viewport_edge_color: str = spec.MODULE_TWO_SCROLL_VIEWPORT_EDGE_COLOR,
        viewport_edge_width: int = spec.MODULE_TWO_SCROLL_VIEWPORT_EDGE_WIDTH,
        bg_color: str | None = None,
    ) -> None:
        resolved_bg = bg_color if bg_color is not None else parent.cget('bg')
        super().__init__(
            parent,
            bg=resolved_bg,
            bd=0,
            highlightthickness=0,
            width=size[0],
            height=size[1],
        )
        self.pack_propagate(False)
        self._viewport_size = viewport_size
        self._scrollbar_size = scrollbar_size
        self._viewport_edge_width = viewport_edge_width
        self._wheel_bound = False

        self.viewport_canvas = tk.Canvas(
            self,
            bg=resolved_bg,
            width=viewport_size[0],
            height=viewport_size[1],
            bd=0,
            highlightthickness=0,
        )
        self.viewport_canvas.place(x=0, y=0)

        self.viewport_left_edge = tk.Frame(
            self,
            bg=viewport_edge_color,
            bd=0,
            highlightthickness=0,
            width=viewport_edge_width,
            height=viewport_size[1],
        )
        self.viewport_left_edge.place(x=0, y=0)

        self.viewport_bottom_edge = tk.Frame(
            self,
            bg=viewport_edge_color,
            bd=0,
            highlightthickness=0,
            width=viewport_size[0],
            height=viewport_edge_width,
        )
        self.viewport_bottom_edge.place(x=0, y=viewport_size[1] - viewport_edge_width)

        self.content_frame = tk.Frame(
            self.viewport_canvas,
            bg=resolved_bg,
            bd=0,
            highlightthickness=0,
            width=viewport_size[0],
        )
        self._content_window_id = self.viewport_canvas.create_window(
            0,
            0,
            anchor='nw',
            window=self.content_frame,
            width=viewport_size[0],
        )

        self.scrollbar = CustomScrollbar(
            self,
            size=scrollbar_size,
            command=self._scroll_to_fraction,
        )
        self.scrollbar.place(x=viewport_size[0], y=0)

        self.viewport_canvas.configure(yscrollcommand=self._on_canvas_scroll)
        self.content_frame.bind('<Configure>', self._on_content_configure, add='+')
        self.viewport_canvas.bind('<Configure>', self._on_canvas_configure, add='+')

        for widget in (self, self.viewport_canvas, self.content_frame, self.scrollbar):
            widget.bind('<Enter>', self._bind_mousewheel, add='+')
            widget.bind('<Leave>', self._unbind_mousewheel, add='+')

    def refresh_scroll_region(self) -> None:
        self.update_idletasks()
        content_height = self.content_frame.winfo_reqheight()
        viewport_height = self._viewport_size[1]
        self.viewport_canvas.itemconfigure(self._content_window_id, width=self._viewport_size[0])
        content_bottom = content_height + spec.SCROLL_CONTENT_BOTTOM_PADDING
        self.viewport_canvas.configure(scrollregion=(0, 0, self._viewport_size[0], content_bottom))
        if content_height <= viewport_height:
            self.viewport_canvas.yview_moveto(0.0)
        self.scrollbar.set_metrics(content_height=content_bottom, viewport_height=viewport_height)
        first, last = self.viewport_canvas.yview()
        self.scrollbar.set_view(first, last)

    def _on_content_configure(self, _event: tk.Event | None = None) -> None:
        self.refresh_scroll_region()

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.viewport_canvas.itemconfigure(self._content_window_id, width=event.width)
        self.refresh_scroll_region()

    def _on_canvas_scroll(self, first: str, last: str) -> None:
        self.scrollbar.set_view(float(first), float(last))

    def _scroll_to_fraction(self, fraction: float) -> None:
        self.viewport_canvas.yview_moveto(fraction)

    def _bind_mousewheel(self, _event: tk.Event | None = None) -> None:
        if self._wheel_bound:
            return
        self.viewport_canvas.bind_all('<MouseWheel>', self._on_mousewheel, add='+')
        self.viewport_canvas.bind_all('<Button-4>', self._on_mousewheel_linux, add='+')
        self.viewport_canvas.bind_all('<Button-5>', self._on_mousewheel_linux, add='+')
        self._wheel_bound = True

    def _unbind_mousewheel(self, _event: tk.Event | None = None) -> None:
        pointer_widget = self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())
        current = pointer_widget
        while current is not None:
            if current == self or current == self.viewport_canvas or current == self.content_frame or current == self.scrollbar:
                return
            current = current.master
        if not self._wheel_bound:
            return
        self.viewport_canvas.unbind_all('<MouseWheel>')
        self.viewport_canvas.unbind_all('<Button-4>')
        self.viewport_canvas.unbind_all('<Button-5>')
        self._wheel_bound = False

    def _on_mousewheel(self, event: tk.Event) -> str:
        if self.content_frame.winfo_reqheight() <= self._viewport_size[1]:
            return 'break'
        delta = 0
        if event.delta != 0:
            delta = -1 if event.delta > 0 else 1
        if delta != 0:
            self.viewport_canvas.yview_scroll(delta, 'units')
        return 'break'

    def _on_mousewheel_linux(self, event: tk.Event) -> str:
        if self.content_frame.winfo_reqheight() <= self._viewport_size[1]:
            return 'break'
        if event.num == 4:
            self.viewport_canvas.yview_scroll(-1, 'units')
        elif event.num == 5:
            self.viewport_canvas.yview_scroll(1, 'units')
        return 'break'
