from __future__ import annotations

from new_music_builder.ui.main_window import (
    MENU_SHORTCUT_SPECS,
    MainWindow,
    build_menu_action_map,
    build_project_mutation_actions,
)
from new_music_builder.ui.widgets.menu_strip import MenuAction, measure_menu_action_width


class _WindowStub:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.bindings: list[tuple[str, object, str]] = []
        for spec in MENU_SHORTCUT_SPECS:
            setattr(self, spec.handler_name, self._build_handler(spec.handler_name))

    def _build_handler(self, name: str):
        def _handler() -> None:
            self.calls.append(name)

        return _handler

    def bind_all(self, sequence: str, callback: object, add: str | None = None) -> None:
        self.bindings.append((sequence, callback, add or ""))

    def _handle_app_shortcut(self, action):
        return MainWindow._handle_app_shortcut(self, action)


def test_build_menu_action_map_uses_open_label_and_shortcuts() -> None:
    window = _WindowStub()
    window._toggle_automatic_textures_preference = lambda: window.calls.append("toggle_auto")
    window._automatic_textures_enabled = lambda: True
    window._toggle_regenerate_textures_on_project_load_preference = lambda: window.calls.append("toggle_auto_load")
    window._regenerate_textures_on_project_load_enabled = lambda: False
    window._toggle_text_tooltips_preference = lambda: window.calls.append("toggle_tooltips")
    window._text_tooltips_enabled = lambda: True

    action_map = build_menu_action_map(window)

    assert [action.label for action in action_map["FILE"]] == [
        "New",
        "Open",
        "Save",
        "Save As...",
        "Exit",
    ]
    assert action_map["FILE"][1].shortcut_label == "(Ctrl + O)"
    assert action_map["PREFERENCES"][0].shortcut_label == ""
    assert [action.label for action in action_map["PREFERENCES"]] == [
        "Audio Settings",
        "Automatic Textures",
        "Regenerate on Load",
        "Tooltips",
    ]
    assert action_map["PREFERENCES"][0].show_check_column is True
    assert action_map["PREFERENCES"][1].show_check_column is True
    assert action_map["PREFERENCES"][2].show_check_column is True
    assert action_map["PREFERENCES"][3].show_check_column is True
    assert action_map["PREFERENCES"][2].close_after_invoke is False
    assert action_map["PREFERENCES"][3].close_after_invoke is False
    assert action_map["PREFERENCES"][2].checked_getter is not None
    assert action_map["PREFERENCES"][3].checked_getter is not None
    action_map["FILE"][1].command()
    assert window.calls == ["load_project"]


def test_build_project_mutation_actions_use_open_not_load() -> None:
    actions = build_project_mutation_actions()

    assert ("FILE", "Open") in actions
    assert ("FILE", "Load") not in actions
    assert ("HELP", "Tutorial") not in actions


def test_measure_menu_action_width_includes_shortcut_text() -> None:
    action = MenuAction(label="Save", command=lambda: None, shortcut_label="(Ctrl + S)")

    width = measure_menu_action_width(
        action,
        label_measure=lambda text: len(text) * 10,
        accelerator_measure=lambda text: len(text) * 5,
    )

    assert width == (4 * 10) + (10 * 5) + 8


def test_measure_menu_action_width_includes_check_column_when_requested() -> None:
    action = MenuAction(label="Automatic Textures", command=lambda: None, show_check_column=True)

    width = measure_menu_action_width(
        action,
        label_measure=lambda text: len(text) * 10,
        accelerator_measure=lambda text: len(text) * 5,
    )

    assert width == (18 * 10) + 24 + 8


def test_bind_app_shortcuts_registers_sequences_and_dispatches_handlers() -> None:
    window = _WindowStub()

    MainWindow._bind_app_shortcuts(window)

    expected_sequences = {
        sequence
        for spec in MENU_SHORTCUT_SPECS
        for sequence in spec.shortcut_sequences
    }
    bound_sequences = {sequence for sequence, _callback, _add in window.bindings}
    assert bound_sequences == expected_sequences
    assert all(add == "+" for _sequence, _callback, add in window.bindings)

    callbacks = {sequence: callback for sequence, callback, _add in window.bindings}
    assert callbacks["<Control-KeyPress-s>"](None) == "break"
    assert callbacks["<Control-KeyPress-S>"](None) == "break"
    assert callbacks["<Control-KeyPress-o>"](None) == "break"
    assert window.calls == ["save_project", "save_project_as", "load_project"]
