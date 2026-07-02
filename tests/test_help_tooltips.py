from __future__ import annotations

from new_music_builder.ui import spec
from new_music_builder.ui.help_tooltip_registry import TooltipSegment, media_mode_tooltip_segments, tooltip_segments_for_id
from new_music_builder.ui.main_window import build_menu_action_map
from new_music_builder.ui.widgets.cursor_tooltip import (
    compute_tooltip_placement,
    layout_tooltip_segments,
    pick_inward_horizontal_direction,
    pick_inward_tooltip_direction,
)
from new_music_builder.ui.widgets.help_tooltip import HelpTooltipBinding


class _WindowStub:
    def __init__(self) -> None:
        self._toggle_automatic_textures_preference = lambda: None
        self._automatic_textures_enabled = lambda: True
        self._toggle_text_tooltips_preference = lambda: None
        self._text_tooltips_enabled = lambda: True
        self._show_audio_settings_dialog = lambda: None
        self.new_project = lambda: None
        self.load_project = lambda: None
        self.save_project = lambda: None
        self.save_project_as = lambda: None
        self.on_close = lambda: None
        self._show_tutorial_placeholder = lambda: None


class _TooltipWidgetStub:
    def __init__(self) -> None:
        self.bindings: list[tuple[str, object, str]] = []
        self.cancelled: list[str] = []

    def bind(self, sequence, handler, add=None):
        self.bindings.append((sequence, handler, add))

    def after_cancel(self, after_id):
        self.cancelled.append(after_id)

    def winfo_pointerx(self):
        return 100

    def winfo_pointery(self):
        return 200


def test_pick_inward_tooltip_direction_chooses_cardinal_side_toward_window_center() -> None:
    assert pick_inward_tooltip_direction(cursor_x=120, cursor_y=300, window_left=100, window_top=100, window_width=800, window_height=600) == 'right'
    assert pick_inward_tooltip_direction(cursor_x=860, cursor_y=300, window_left=100, window_top=100, window_width=800, window_height=600) == 'left'
    assert pick_inward_tooltip_direction(cursor_x=500, cursor_y=120, window_left=100, window_top=100, window_width=800, window_height=600) == 'down'
    assert pick_inward_tooltip_direction(cursor_x=500, cursor_y=660, window_left=100, window_top=100, window_width=800, window_height=600) == 'up'


def test_pick_inward_horizontal_direction_uses_left_right_only() -> None:
    assert pick_inward_horizontal_direction(cursor_x=120, window_left=100, window_width=800) == 'right'
    assert pick_inward_horizontal_direction(cursor_x=860, window_left=100, window_width=800) == 'left'


def test_compute_tooltip_placement_supports_vertical_tooltips() -> None:
    placement = compute_tooltip_placement(
        cursor_x=500,
        cursor_y=160,
        window_left=100,
        window_top=100,
        window_width=900,
        window_height=700,
        body_size=(200, 80),
        direction='down',
        cursor_offset=spec.HELP_TOOLTIP_CURSOR_OFFSET,
        pointer_protrusion=spec.HELP_TOOLTIP_POINTER_PROTRUSION,
        pointer_size=spec.HELP_TOOLTIP_POINTER_SIZE,
    )

    assert placement.window_y == 160 + spec.HELP_TOOLTIP_CURSOR_OFFSET
    assert placement.square_y == spec.HELP_TOOLTIP_POINTER_PROTRUSION
    assert placement.pointer_tip_y == 0
    assert placement.pointer_base_x == 0
    assert placement.pointer_half_width == spec.HELP_TOOLTIP_POINTER_SIZE


def test_compute_tooltip_placement_anchors_vertical_pointer_to_right_edge_when_cursor_is_on_right_half() -> None:
    placement = compute_tooltip_placement(
        cursor_x=860,
        cursor_y=640,
        window_left=100,
        window_top=100,
        window_width=900,
        window_height=700,
        body_size=(200, 80),
        direction='up',
        cursor_offset=spec.HELP_TOOLTIP_CURSOR_OFFSET,
        pointer_protrusion=spec.HELP_TOOLTIP_POINTER_PROTRUSION,
        pointer_size=spec.HELP_TOOLTIP_POINTER_SIZE,
    )

    assert placement.pointer_base_x == 200 - spec.HELP_TOOLTIP_POINTER_SIZE
    assert placement.pointer_half_width == spec.HELP_TOOLTIP_POINTER_SIZE


def test_layout_tooltip_segments_keeps_accent_and_tag_runs_inline_without_auto_wrap() -> None:
    layout = layout_tooltip_segments(
        (
            tooltip_segments_for_id('module_one.workshop_preview')[0],
            tooltip_segments_for_id('module_one.workshop_preview')[1],
            tooltip_segments_for_id('module_one.workshop_preview')[2],
            tooltip_segments_for_id('module_one.workshop_preview')[4],
        ),
        max_width=0,
        measure_normal=len,
        measure_accent=len,
        measure_tag=len,
    )

    assert layout.lines
    assert any(any(run.tone == 'accent' for run in line) for line in layout.lines)
    assert any(any(run.tone == 'tag' for run in line) for line in layout.lines)
    assert len(layout.lines) == 1


def test_layout_tooltip_segments_respects_explicit_break_segments() -> None:
    layout = layout_tooltip_segments(
        tooltip_segments_for_id('module_one.workshop_preview'),
        max_width=0,
        measure_normal=len,
        measure_accent=len,
        measure_tag=len,
    )

    assert len(layout.lines) == 2


def test_tooltip_registry_returns_none_for_blank_placeholder() -> None:
    assert tooltip_segments_for_id('module_three.appearance_grid') is None


def test_tooltip_registry_returns_module_two_media_segments() -> None:
    collapsed = tooltip_segments_for_id('module_two.collapsed_media.cassette')
    expanded = tooltip_segments_for_id('module_two.media_checkbox.vinyl')
    song_table = tooltip_segments_for_id('module_two.song_table')
    live_preview = tooltip_segments_for_id('module_two.live_preview')

    assert collapsed is not None
    assert expanded is not None
    assert song_table is not None
    assert live_preview is not None
    assert collapsed[0].tone == 'accent'
    assert any(segment.tone == 'tag' for segment in expanded)
    assert song_table[0].tone == 'accent'
    assert any(segment.tone == 'tag' for segment in live_preview)


def test_media_mode_tooltip_segments_describe_split_mode() -> None:
    segments = media_mode_tooltip_segments('cassette', 'split')

    assert ''.join(segment.text for segment in segments if segment.tone != 'break') == (
        'Click to toggle Flip / Full for CassetteFlip: Side A and Side B separated'
    )
    assert segments[-1].tone == 'tag'


def test_media_mode_tooltip_segments_describe_single_mode() -> None:
    segments = media_mode_tooltip_segments('cd', 'single')

    assert ''.join(segment.text for segment in segments if segment.tone != 'break') == (
        'Click to toggle Flip / Full for CDFull: Side A and Side B combined'
    )
    assert segments[-1].tone == 'tag'


def test_help_tooltip_binding_refresh_now_uses_dynamic_segments(monkeypatch) -> None:
    widget = _TooltipWidgetStub()
    shown: list[tuple[tuple[int, int], str | None]] = []
    segment_state = {'text': 'before'}

    class _FakeTooltip:
        def __init__(self, _owner) -> None:
            self.segments = ()

        def set_segments(self, segments) -> None:
            self.segments = tuple(segments)

        def set_target_widgets(self, _widgets) -> None:
            pass

        def hide(self) -> None:
            pass

        def show_at_cursor(self, x, y, preferred_direction=None) -> None:
            shown.append(((x, y), preferred_direction))

        def move_to_cursor(self, *_args, **_kwargs) -> None:
            pass

    monkeypatch.setattr('new_music_builder.ui.widgets.help_tooltip.HelpCursorTooltip', _FakeTooltip)
    binding = HelpTooltipBinding(
        (widget,),
        segments=(TooltipSegment('before'),),
        segments_getter=lambda: (TooltipSegment(segment_state['text']),),
        preferred_direction='down',
    )
    segment_state['text'] = 'after'

    binding.refresh_now(show=True)

    assert binding._segments == (TooltipSegment('after'),)
    assert shown == [((0, 0), 'down')]


def test_tooltip_registry_returns_module_three_segments() -> None:
    tab = tooltip_segments_for_id('module_three.tab.case')
    preview_mode = tooltip_segments_for_id('module_three.preview_mode_toggle')
    dual_sprite = tooltip_segments_for_id('module_three.dual_sprite')
    generate = tooltip_segments_for_id('module_three.generate_from_cover')
    dual_custom = tooltip_segments_for_id('module_three.custom.dual.world_empty')

    assert tab is not None
    assert preview_mode is not None
    assert dual_sprite is not None
    assert generate is not None
    assert dual_custom is not None
    assert any(segment.tone == 'accent' for segment in tab)
    assert any(segment.tone == 'accent' for segment in preview_mode)
    assert any(segment.tone == 'tag' for segment in dual_sprite)
    assert any(segment.tone == 'accent' for segment in generate)
    assert any(segment.tone == 'accent' for segment in dual_custom)


def test_build_menu_action_map_assigns_submenu_tooltip_ids() -> None:
    action_map = build_menu_action_map(_WindowStub())

    assert action_map['PREFERENCES'][0].tooltip_id == 'menu.preferences.audio_settings'
    assert action_map['PREFERENCES'][1].tooltip_id == 'menu.preferences.automatic_textures'
    assert action_map['PREFERENCES'][2].tooltip_id == 'menu.preferences.tooltips'
