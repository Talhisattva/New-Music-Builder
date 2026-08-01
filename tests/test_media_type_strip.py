from __future__ import annotations

from types import SimpleNamespace

from new_music_builder.domain.models import default_media_row
from new_music_builder.ui.widgets.media_type_strip import MediaTypeStrip


def test_media_type_strip_hides_mode_overlays_and_tooltips_in_legacy_mode() -> None:
    row = default_media_row(1)
    row.media_modes["cassette"] = "single"
    strip = MediaTypeStrip.__new__(MediaTypeStrip)
    strip._row = row
    strip._single_side_icon_path = "single.png"
    strip._double_side_icon_path = "double.png"
    strip._legacy_mode_enabled_getter = lambda: True
    strip.icon_labels = {"cassette": SimpleNamespace()}

    assert strip._overlay_path_for_kind("cassette") is None
    assert strip.mode_toggle_tooltip_widgets_for_kind("cassette") == ()


def test_media_type_strip_ignores_mode_toggle_clicks_in_legacy_mode() -> None:
    row = default_media_row(1)
    strip = MediaTypeStrip.__new__(MediaTypeStrip)
    strip._row = row
    strip._enabled = True
    strip._legacy_mode_enabled_getter = lambda: True
    strip._on_media_mode_changed = None
    strip.refresh_content = lambda: (_ for _ in ()).throw(AssertionError("refresh should not run"))

    result = strip._on_overlay_clicked("cassette")

    assert result == "break"
    assert row.media_modes["cassette"] == "split"
