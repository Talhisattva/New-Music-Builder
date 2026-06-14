from pathlib import Path

from new_music_builder.services.project_session import ProjectSession
from new_music_builder.services.track_import import build_track_entry, filter_supported_audio_paths


def test_filter_supported_audio_paths_keeps_supported_existing_files_in_order(tmp_path: Path) -> None:
    mp3 = tmp_path / 'b.mp3'
    wav = tmp_path / 'a.wav'
    txt = tmp_path / 'c.txt'
    mp3.write_bytes(b'mp3')
    wav.write_bytes(b'wav')
    txt.write_bytes(b'txt')

    result = filter_supported_audio_paths([mp3, txt, wav, tmp_path / 'missing.flac'])

    assert result == [mp3.resolve(), wav.resolve()]


def test_build_track_entry_uses_file_stem_and_ogg_status(tmp_path: Path) -> None:
    ogg = tmp_path / 'Tall Mix 2.ogg'
    ogg.write_bytes(b'ogg')

    entry = build_track_entry(ogg)

    assert entry.source_path == str(ogg.resolve())
    assert entry.display_label == 'Tall Mix 2'
    assert entry.conversion_status == 'source_ogg'


def test_project_session_add_tracks_to_media_row_preserves_order(tmp_path: Path) -> None:
    first = tmp_path / '01 Intro.wav'
    second = tmp_path / '02 Outro.mp3'
    first.write_bytes(b'wav')
    second.write_bytes(b'mp3')
    session = ProjectSession()

    inserted = session.add_tracks_to_media_row(1, 'A', [first, second])

    assert inserted == [0, 1]
    assert [track.display_label for track in session.project.media_rows[0].tracks_a] == ['01 Intro', '02 Outro']
