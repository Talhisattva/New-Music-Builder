from pathlib import Path

import numpy as np

from new_music_builder.domain.models import PlannedAudioWorkItem
from new_music_builder.services import audio_conversion, audio_export_runner


def test_write_ogg_vorbis_uses_fixed_export_profile(tmp_path: Path, monkeypatch) -> None:
    recorded: dict[str, object] = {}

    class _FakeSoundFile:
        def __init__(self, file: str, mode: str = "r", **kwargs: object) -> None:
            recorded["file"] = file
            recorded["mode"] = mode
            recorded.update(kwargs)

        def __enter__(self) -> "_FakeSoundFile":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def buffer_write(self, _data: bytes, *, dtype: str) -> None:
            recorded["dtype"] = dtype

    monkeypatch.setattr(audio_conversion.sf, "SoundFile", _FakeSoundFile)

    audio_conversion._write_ogg_vorbis(
        tmp_path / "out.ogg",
        np.zeros((32, 2), dtype=np.int16),
        44100,
        emit_progress=lambda _percent, _message: None,
    )

    assert recorded["format"] == "OGG"
    assert recorded["subtype"] == "VORBIS"
    assert recorded["bitrate_mode"] == audio_conversion.OGG_BITRATE_MODE
    assert recorded["compression_level"] == audio_conversion.OGG_COMPRESSION_LEVEL


def test_cache_path_includes_ogg_profile_id(tmp_path: Path) -> None:
    source = tmp_path / "song.wav"
    source.write_bytes(b"pcm")
    item = PlannedAudioWorkItem(
        row_id=1,
        side="A",
        track_number=1,
        display_label="Song",
        duration_seconds=60,
        source_path=str(source),
        target_relative_path="unused.ogg",
        target_path=str(tmp_path / "unused.ogg"),
        action="convert_to_ogg",
        reason="test",
        sample_rate=44100,
    )

    cache_path = audio_export_runner._cache_path_for_item(tmp_path, item)

    assert cache_path.suffix == ".ogg"
    assert audio_conversion.OGG_PROFILE_ID not in cache_path.name

    stat = source.stat()
    expected_key = "|".join(
        (
            str(source.resolve()),
            str(stat.st_mtime_ns),
            str(stat.st_size),
            str(item.sample_rate),
            audio_conversion.OGG_PROFILE_ID,
        )
    )
    expected_digest = audio_export_runner.hashlib.sha1(expected_key.encode("utf-8")).hexdigest()[:12]
    assert cache_path.name == f"Song-{expected_digest}.ogg"
