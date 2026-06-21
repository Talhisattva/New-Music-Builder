from pathlib import Path

from new_music_builder.domain.models import ProjectConfig, TrackEntry, default_media_row
from new_music_builder.services.asset_catalog import AssetCatalog
from new_music_builder.services.export_planning import build_export_plan
from new_music_builder.services.export_scaffold import resolve_export_target, write_export_scaffold


ASSETS_ROOT = Path(__file__).resolve().parents[1] / "assets"


def _track(source_path: str, label: str, duration: str) -> TrackEntry:
    return TrackEntry(
        source_path=source_path,
        display_label=label,
        duration=duration,
        conversion_status="source_ogg" if source_path.endswith(".ogg") else "needs_convert",
    )


def test_write_export_scaffold_generates_script_files_for_registered_media(tmp_path: Path) -> None:
    workshop_root = tmp_path / "Workshop"
    workshop_root.mkdir()
    project = ProjectConfig(
        mod_name="Road Trip Mix",
        mod_id="RoadTripMix",
        workshop_output_folder=str(workshop_root),
    )
    row = default_media_row(1)
    row.media_name = "Road Trip Vol 1"
    row.tracks_a = [_track("C:/music/intro.ogg", "Intro", "00:01:00")]
    row.tracks_b = [_track("C:/music/finale.mp3", "Finale", "00:02:00")]
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    jacket_key = next(
        (key for key in ("jacket:18", "jacket:_Zomboid") if any(entry.key == key for entry in catalog["jacket"])),
        catalog["jacket"][0].key,
    )
    row.appearances["jacket"].selected_asset_key = jacket_key
    project.media_rows = [row]

    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    scripts_root = Path(targets.v42) / "media" / "scripts"
    sounds_text = (scripts_root / "NMB_RoadTripMix_Sounds.txt").read_text(encoding="utf-8")
    items_text = (scripts_root / "NMB_RoadTripMix_Items.txt").read_text(encoding="utf-8")
    models_text = (scripts_root / "NMB_RoadTripMix_Models.txt").read_text(encoding="utf-8")

    assert "module RoadTripMix" in sounds_text
    assert "sound RoadTripMixRoadTripVol101" in sounds_text
    assert "file = media/sound/RoadTripMix/Road Trip Vol 1/A-Side/01 Intro.ogg" in sounds_text

    assert "item RoadTripVol1CassetteA" in items_text
    assert "item RoadTripVol1CassetteB" in items_text
    assert "item RoadTripVol1JacketEmpty" in items_text
    assert "item RoadTripVol1JacketFull" in items_text
    assert "WorldStaticModel = RoadTripMix.RoadTripVol1JacketFull" in items_text

    assert "model RoadTripVol1Cassette" in models_text
    assert "model RoadTripVol1JacketEmpty" in models_text
    assert "model RoadTripVol1JacketFull" in models_text
    assert "mesh = WorldItems/NM_Jacket" in models_text
