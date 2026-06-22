from pathlib import Path

from new_music_builder.domain.models import ExportTargetPaths, ProjectConfig, TrackEntry, default_media_row
from new_music_builder.services.asset_catalog import AssetCatalog
from new_music_builder.services.audio_work_plan import build_audio_work_plan, summarize_audio_work_plan
from new_music_builder.services.export_planning import build_export_plan


ASSETS_ROOT = Path(__file__).resolve().parents[1] / "assets"


def _targets(tmp_path: Path) -> ExportTargetPaths:
    root = tmp_path / "Out"
    mod_base = root / "Contents" / "mods" / "MyPack"
    common = mod_base / "common"
    v42 = mod_base / "42"
    return ExportTargetPaths(
        workshop_root=str(tmp_path),
        outer_folder_name="Out",
        inner_folder_name="MyPack",
        root=str(root),
        contents=str(root / "Contents"),
        mods_root=str(root / "Contents" / "mods"),
        mod_base=str(mod_base),
        common=str(common),
        v42=str(v42),
        audio_root=str(common / "media" / "sound"),
        audio_pack_root=str(common / "media" / "sound" / "MyPack"),
    )


def test_build_audio_work_plan_reencodes_existing_ogg_when_enabled(tmp_path: Path) -> None:
    ogg_path = tmp_path / "song.ogg"
    ogg_path.write_bytes(b"ogg")
    row = default_media_row(1)
    row.tracks_a = [TrackEntry(source_path=str(ogg_path), display_label="Song", duration="00:01:00")]
    project = ProjectConfig(mod_name="Pack", mod_id="Pack", reencode_existing_ogg=True, media_rows=[row])
    plan = build_export_plan(project, AssetCatalog(ASSETS_ROOT).scan())

    work_plan = build_audio_work_plan(project, plan, _targets(tmp_path))

    assert work_plan.items[0].action == "convert_to_ogg"
    assert "Re-encoding existing .ogg" in work_plan.items[0].reason


def test_build_audio_work_plan_copies_existing_ogg_when_reencode_disabled(tmp_path: Path) -> None:
    ogg_path = tmp_path / "song.ogg"
    ogg_path.write_bytes(b"ogg")
    row = default_media_row(1)
    row.tracks_a = [TrackEntry(source_path=str(ogg_path), display_label="Song", duration="00:01:00")]
    project = ProjectConfig(mod_name="Pack", mod_id="Pack", reencode_existing_ogg=False, media_rows=[row])
    plan = build_export_plan(project, AssetCatalog(ASSETS_ROOT).scan())

    work_plan = build_audio_work_plan(project, plan, _targets(tmp_path))

    assert work_plan.items[0].action == "copy_ogg"
    assert work_plan.items[0].reason == "Source audio is already .ogg."


def test_build_audio_work_plan_uses_effective_export_compression_quality(tmp_path: Path) -> None:
    wav_path = tmp_path / "song.wav"
    wav_path.write_bytes(b"wav")
    row = default_media_row(1)
    row.tracks_a = [TrackEntry(source_path=str(wav_path), display_label="Song", duration="00:01:00")]
    project = ProjectConfig(
        mod_name="Pack",
        mod_id="Pack",
        compression_quality=0.80,
        media_rows=[row],
    )
    plan = build_export_plan(project, AssetCatalog(ASSETS_ROOT).scan())

    work_plan = build_audio_work_plan(project, plan, _targets(tmp_path))

    assert work_plan.items[0].compression_quality == 0.8


def test_summarize_audio_work_plan_reports_settings_and_actions(tmp_path: Path) -> None:
    ogg_path = tmp_path / "song.ogg"
    ogg_path.write_bytes(b"ogg")
    row = default_media_row(1)
    row.tracks_a = [TrackEntry(source_path=str(ogg_path), display_label="Song", duration="00:01:00")]
    project = ProjectConfig(mod_name="Pack", mod_id="Pack", reencode_existing_ogg=True, media_rows=[row])
    plan = build_export_plan(project, AssetCatalog(ASSETS_ROOT).scan())
    work_plan = build_audio_work_plan(project, plan, _targets(tmp_path))

    summary = summarize_audio_work_plan(project, work_plan)

    assert summary[0] == "Audio settings: sample_rate=44100Hz export_quality=0.50 reencode_existing_ogg=true"
    assert summary[1] == "Audio plan: convert=1 copy=0 error=0"
    assert "Song -> convert_to_ogg" in summary[2]
