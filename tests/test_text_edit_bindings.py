from __future__ import annotations

from new_music_builder.ui.widgets.text_edit_bindings import (
    _copy_selection,
    _cut_selection,
    _paste_clipboard,
    _select_all,
    bind_standard_text_shortcuts,
)


class _WidgetStub:
    def __init__(self) -> None:
        self.bound_sequences: list[tuple[str, str]] = []
        self.generated: list[str] = []
        self.selection_calls: list[tuple[object, object]] = []
        self.cursor_positions: list[object] = []
        self.focus_calls = 0

    def bind(self, sequence: str, func, add: str | None = None):
        self.bound_sequences.append((sequence, add or ''))

    def event_generate(self, sequence: str) -> None:
        self.generated.append(sequence)

    def selection_range(self, start, end) -> None:
        self.selection_calls.append((start, end))

    def icursor(self, index) -> None:
        self.cursor_positions.append(index)

    def focus_set(self) -> None:
        self.focus_calls += 1


class _EventStub:
    def __init__(self, widget: _WidgetStub) -> None:
        self.widget = widget


def test_bind_standard_text_shortcuts_registers_copy_cut_paste_and_select_all() -> None:
    widget = _WidgetStub()

    bind_standard_text_shortcuts(widget)

    assert {sequence for sequence, _add in widget.bound_sequences} == {
        '<Control-a>',
        '<Control-A>',
        '<Control-c>',
        '<Control-C>',
        '<Control-x>',
        '<Control-X>',
        '<Control-v>',
        '<Control-V>',
    }
    assert all(add == '+' for _sequence, add in widget.bound_sequences)


def test_select_all_focuses_and_selects_entire_widget() -> None:
    widget = _WidgetStub()

    result = _select_all(_EventStub(widget))

    assert result == 'break'
    assert widget.focus_calls == 1
    assert widget.selection_calls == [(0, 'end')]
    assert widget.cursor_positions == ['end']


def test_copy_cut_and_paste_generate_standard_virtual_events() -> None:
    widget = _WidgetStub()
    event = _EventStub(widget)

    assert _copy_selection(event) == 'break'
    assert _cut_selection(event) == 'break'
    assert _paste_clipboard(event) == 'break'
    assert widget.generated == ['<<Copy>>', '<<Cut>>', '<<Paste>>']
