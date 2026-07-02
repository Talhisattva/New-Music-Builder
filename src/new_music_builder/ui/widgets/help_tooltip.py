from __future__ import annotations

from collections.abc import Callable, Sequence
import tkinter as tk
import weakref

from new_music_builder.ui import spec
from new_music_builder.ui.help_tooltip_registry import TooltipSegment, tooltip_segments_for_id
from new_music_builder.ui.widgets.cursor_tooltip import HelpCursorTooltip

_TEXT_TOOLTIPS_ENABLED = True
_HELP_TOOLTIP_BINDINGS: weakref.WeakSet[HelpTooltipBinding] = weakref.WeakSet()


def set_text_tooltips_enabled(enabled: bool) -> None:
    global _TEXT_TOOLTIPS_ENABLED
    _TEXT_TOOLTIPS_ENABLED = bool(enabled)
    if not _TEXT_TOOLTIPS_ENABLED:
        for binding in tuple(_HELP_TOOLTIP_BINDINGS):
            binding.hide()


def text_tooltips_enabled() -> bool:
    return _TEXT_TOOLTIPS_ENABLED


class HelpTooltipBinding:
    def __init__(
        self,
        widgets: Sequence[tk.Misc],
        *,
        segments: Sequence[TooltipSegment],
        segments_getter: Callable[[], Sequence[TooltipSegment]] | None = None,
        delay_ms: int = spec.HELP_TOOLTIP_SHOW_DELAY_MS,
        should_show: Callable[[tk.Event | None], bool] | None = None,
        preferred_direction: str | None = None,
    ) -> None:
        self._widgets = tuple(widgets)
        self._segments = tuple(segments)
        self._segments_getter = segments_getter
        self._delay_ms = delay_ms
        self._should_show = should_show
        self._preferred_direction = preferred_direction
        self._tooltip = HelpCursorTooltip(self._widgets[0])
        self._tooltip.set_segments(self._segments)
        self._tooltip.set_target_widgets(self._widgets)
        self._show_after_id: str | None = None
        self._hide_after_id: str | None = None
        self._last_pointer: tuple[int, int] = (0, 0)
        _HELP_TOOLTIP_BINDINGS.add(self)
        for widget in self._widgets:
            widget.bind('<Enter>', self._on_enter, add='+')
            widget.bind('<Motion>', self._on_motion, add='+')
            widget.bind('<Leave>', self._on_leave, add='+')
            widget.bind('<ButtonPress>', self._on_press, add='+')
            widget.bind('<Destroy>', self._on_destroy, add='+')

    def set_segments(self, segments: Sequence[TooltipSegment]) -> None:
        self._segments = tuple(segments)
        self._tooltip.set_segments(self._segments)

    def hide(self) -> None:
        self._cancel_show()
        self._cancel_hide()
        self._tooltip.hide()

    def _capture_pointer(self, event: tk.Event | None = None) -> None:
        owner = self._widgets[0]
        if event is not None and hasattr(event, 'x_root') and hasattr(event, 'y_root'):
            self._last_pointer = (int(event.x_root), int(event.y_root))
            return
        self._last_pointer = (owner.winfo_pointerx(), owner.winfo_pointery())

    def _on_enter(self, event: tk.Event | None = None) -> None:
        self._capture_pointer(event)
        self._refresh_segments()
        if not self._can_show_for_event(event):
            self._cancel_show()
            self._cancel_hide()
            self._tooltip.hide()
            return
        self._cancel_hide()
        self._schedule_show()

    def _on_motion(self, event: tk.Event | None = None) -> None:
        self._capture_pointer(event)
        self._refresh_segments()
        if not self._can_show_for_event(event):
            self._cancel_show()
            self._schedule_hide()
            return
        self._cancel_hide()
        if self._show_after_id is not None:
            return
        self._tooltip.move_to_cursor(*self._last_pointer, preferred_direction=self._preferred_direction)

    def _on_leave(self, _event: tk.Event | None = None) -> None:
        self._cancel_show()
        self._schedule_hide()

    def _on_press(self, _event: tk.Event | None = None) -> None:
        self._cancel_show()
        self._cancel_hide()
        self._tooltip.hide()

    def _schedule_show(self) -> None:
        self._cancel_show()
        owner = self._widgets[0]
        self._show_after_id = owner.after(self._delay_ms, self._show_now)

    def _show_now(self) -> None:
        self._show_after_id = None
        self._refresh_segments()
        self._tooltip.show_at_cursor(*self._last_pointer, preferred_direction=self._preferred_direction)

    def _schedule_hide(self) -> None:
        self._cancel_hide()
        owner = self._widgets[0]
        self._hide_after_id = owner.after(spec.MODULE_THREE_GRID_HOVER_HIDE_DELAY_MS, self._hide_now)

    def _hide_now(self) -> None:
        self._hide_after_id = None
        self._tooltip.hide()

    def _cancel_show(self) -> None:
        if self._show_after_id is None:
            return
        try:
            self._widgets[0].after_cancel(self._show_after_id)
        except tk.TclError:
            pass
        self._show_after_id = None

    def _cancel_hide(self) -> None:
        if self._hide_after_id is None:
            return
        try:
            self._widgets[0].after_cancel(self._hide_after_id)
        except tk.TclError:
            pass
        self._hide_after_id = None

    def _can_show_for_event(self, event: tk.Event | None) -> bool:
        if not _TEXT_TOOLTIPS_ENABLED:
            return False
        if self._should_show is None:
            return True
        return bool(self._should_show(event))

    def _refresh_segments(self) -> None:
        if self._segments_getter is None:
            return
        self.set_segments(self._segments_getter())

    def _on_destroy(self, _event: tk.Event | None = None) -> None:
        self.hide()


def bind_help_tooltip(
    widgets: Sequence[tk.Misc],
    *,
    tooltip_id: str | None,
    segments_getter: Callable[[], Sequence[TooltipSegment]] | None = None,
    delay_ms: int = spec.HELP_TOOLTIP_SHOW_DELAY_MS,
    should_show: Callable[[tk.Event | None], bool] | None = None,
    preferred_direction: str | None = None,
) -> HelpTooltipBinding | None:
    segments = tooltip_segments_for_id(tooltip_id)
    if segments is None and segments_getter is not None:
        resolved_segments = tuple(segments_getter())
        segments = resolved_segments if any(segment.text.strip() or segment.tone == 'break' for segment in resolved_segments) else None
    if not widgets or not segments:
        return None
    return HelpTooltipBinding(
        widgets,
        segments=segments,
        segments_getter=segments_getter,
        delay_ms=delay_ms,
        should_show=should_show,
        preferred_direction=preferred_direction,
    )
