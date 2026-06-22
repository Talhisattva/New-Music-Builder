from new_music_builder.services.audio_profile import (
    AUDIO_COMPRESSION_PRESETS,
    compression_bucket_name,
    compression_profile_id,
    nearest_compression_preset,
    snap_compression_quality,
)


def test_snap_compression_quality_defaults_and_snaps_to_presets() -> None:
    assert snap_compression_quality("bad") == 0.5
    assert snap_compression_quality(0.57) == 0.5
    assert snap_compression_quality(0.70) == 0.65


def test_nearest_compression_preset_returns_named_label() -> None:
    assert nearest_compression_preset(0.57).label == "Medium"
    assert [preset.label for preset in AUDIO_COMPRESSION_PRESETS] == ["Lowest", "Low", "Medium", "High", "Highest"]


def test_compression_profile_id_and_bucket_name_are_readable() -> None:
    assert compression_profile_id(0.65) == "vorbis-cl65"
    assert compression_bucket_name(44100, 0.57) == "44100hz - Medium"
