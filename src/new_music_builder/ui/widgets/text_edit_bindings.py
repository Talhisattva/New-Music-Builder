from __future__ import annotations

from typing import Protocol
import tkinter as tk


class EditableWidget(Protocol):
    def bind(self, sequence: str, func, add: str | None = None): ...
    def event_generate(self, sequence: str) -> None: ...
    def selection_range(self, start, end) -> None: ...
    def icursor(self, index) -> None: ...
    def focus_set(self) -> None: ...


def bind_standard_text_shortcuts(widget: EditableWidget) -> None:
    widget.bind('<Control-a>', _select_all, add='+')
    widget.bind('<Control-A>', _select_all, add='+')
    widget.bind('<Control-c>', _copy_selection, add='+')
    widget.bind('<Control-C>', _copy_selection, add='+')
    widget.bind('<Control-x>', _cut_selection, add='+')
    widget.bind('<Control-X>', _cut_selection, add='+')
    widget.bind('<Control-v>', _paste_clipboard, add='+')
    widget.bind('<Control-V>', _paste_clipboard, add='+')


def _select_all(event: tk.Event | None = None) -> str:
    widget = _editable_widget_from_event(event)
    if widget is None:
        return 'break'
    widget.focus_set()
    widget.selection_range(0, 'end')
    widget.icursor('end')
    return 'break'


def _copy_selection(event: tk.Event | None = None) -> str:
    widget = _editable_widget_from_event(event)
    if widget is not None:
        widget.event_generate('<<Copy>>')
    return 'break'


def _cut_selection(event: tk.Event | None = None) -> str:
    widget = _editable_widget_from_event(event)
    if widget is not None:
        widget.event_generate('<<Cut>>')
    return 'break'


def _paste_clipboard(event: tk.Event | None = None) -> str:
    widget = _editable_widget_from_event(event)
    if widget is not None:
        widget.event_generate('<<Paste>>')
    return 'break'


def _editable_widget_from_event(event: tk.Event | None) -> EditableWidget | None:
    if event is None:
        return None
    widget = getattr(event, 'widget', None)
    return widget if widget is not None else None
