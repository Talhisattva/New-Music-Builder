from pathlib import Path

import numpy as np

from new_music_builder.domain.models import AudioWorkPlan, PlannedAudioWorkItem
from new_music_builder.services import audio_conversion, audio_export_runner
from new_music_builder.services.audio_profile import compression_bucket_name, compression_profile_id


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
        0.65,
        emit_progress=lambda _percent, _message: None,
    )

    assert recorded["format"] == "OGG"
    assert recorded["subtype"] == "VORBIS"
    assert recorded["compression_level"] == 0.65


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
        compression_quality=0.65,
    )

    cache_path = audio_export_runner._cache_path_for_item(tmp_path, item)

    assert cache_path.suffix == ".ogg"
    assert cache_path.parent.name == compression_bucket_name(item.sample_rate, item.compression_quality)
    assert compression_profile_id(item.compression_quality) not in cache_path.name

    stat = source.stat()
    expected_key = "|".join(
        (
            str(source.resolve()),
            str(stat.st_mtime_ns),
            str(stat.st_size),
            str(item.sample_rate),
            compression_profile_id(item.compression_quality),
        )
    )
    expected_digest = audio_export_runner.hashlib.sha1(expected_key.encode("utf-8")).hexdigest()[:12]
    assert cache_path.name == f"Song-{expected_digest}.ogg"


def test_run_audio_export_copies_source_ogg_directly_without_cache(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source.ogg"
    source.write_bytes(b"source-ogg")
    output_root = tmp_path / "out"
    cache_root = tmp_path / "cache"
    target = output_root / "Pack" / "Song.ogg"
    item = PlannedAudioWorkItem(
        row_id=1,
        side="A",
        track_number=1,
        display_label="Song",
        duration_seconds=60,
        source_path=str(source),
        target_relative_path="Pack/Song.ogg",
        target_path=str(target),
        action="copy_ogg",
        reason="Source audio is already .ogg.",
        sample_rate=44100,
        compression_quality=0.5,
    )
    events = []

    monkeypatch.setattr(
        audio_export_runner,
        "ensure_cached_ogg",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("copy_ogg should bypass cache")),
    )

    result = audio_export_runner.run_audio_export(
        AudioWorkPlan(items=[item]),
        cache_root=cache_root,
        output_root=output_root,
        emit=events.append,
    )

    assert result.built_song_count == 1
    assert result.converted_count == 0
    assert target.read_bytes() == b"source-ogg"
    assert list(cache_root.rglob("*.ogg")) == []
    assert [event.cached_ogg_path for event in events if event.kind == "song_succeeded"] == [""]


def test_run_audio_export_mixed_passthrough_and_conversion_behaviors(tmp_path: Path, monkeypatch) -> None:
    source_ogg = tmp_path / "source.ogg"
    source_ogg.write_bytes(b"source-ogg")
    source_wav = tmp_path / "source.wav"
    source_wav.write_bytes(b"source-wav")
    output_root = tmp_path / "out"
    cache_root = tmp_path / "cache"
    target_ogg = output_root / "Pack" / "Source.ogg"
    target_wav = output_root / "Pack" / "Converted.ogg"
    items = [
        PlannedAudioWorkItem(
            row_id=1,
            side="A",
            track_number=1,
            display_label="Source",
            duration_seconds=60,
            source_path=str(source_ogg),
            target_relative_path="Pack/Source.ogg",
            target_path=str(target_ogg),
            action="copy_ogg",
            reason="Source audio is already .ogg.",
            sample_rate=44100,
            compression_quality=0.5,
        ),
        PlannedAudioWorkItem(
            row_id=1,
            side="A",
            track_number=2,
            display_label="Converted",
            duration_seconds=60,
            source_path=str(source_wav),
            target_relative_path="Pack/Converted.ogg",
            target_path=str(target_wav),
            action="convert_to_ogg",
            reason="Source audio requires conversion.",
            sample_rate=44100,
            compression_quality=0.5,
        ),
    ]
    conversion_calls: list[str] = []
    events = []

    def _fake_ensure_cached_ogg(item, cache_path, **_kwargs):
        conversion_calls.append(item.action)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(b"converted-ogg")
        return True

    monkeypatch.setattr(audio_export_runner, "ensure_cached_ogg", _fake_ensure_cached_ogg)

    result = audio_export_runner.run_audio_export(
        AudioWorkPlan(items=items),
        cache_root=cache_root,
        output_root=output_root,
        emit=events.append,
    )

    assert conversion_calls == ["convert_to_ogg"]
    assert result.built_song_count == 2
    assert result.converted_count == 1
    assert target_ogg.read_bytes() == b"source-ogg"
    assert target_wav.read_bytes() == b"converted-ogg"
    succeeded_paths = [event.cached_ogg_path for event in events if event.kind == "song_succeeded"]
    assert succeeded_paths[0] == ""
    assert succeeded_paths[1].endswith(".ogg")
    assert Path(succeeded_paths[1]).exists()
