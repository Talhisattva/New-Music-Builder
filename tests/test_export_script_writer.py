from pathlib import Path

from PIL import Image

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


def _write_image(path: Path, size: tuple[int, int], color: tuple[int, int, int, int]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", size, color).save(path)
    return str(path)


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
    lua_root = Path(targets.v42) / "media" / "lua" / "shared"
    sounds_text = (scripts_root / "NMB_RoadTripMix_Sounds.txt").read_text(encoding="utf-8")
    items_text = (scripts_root / "NMB_RoadTripMix_Items.txt").read_text(encoding="utf-8")
    models_text = (scripts_root / "NMB_RoadTripMix_Models.txt").read_text(encoding="utf-8")
    bootstrap_text = (lua_root / "RoadTripMix_PackBootstrap.lua").read_text(encoding="utf-8")
    album_text = (lua_root / "RoadTripMix_Album_RoadTripVol1.lua").read_text(encoding="utf-8")

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

    assert 'require "NMAlbumPackBuilder"' in bootstrap_text
    assert 'require "RoadTripMix_Album_RoadTripVol1"' in bootstrap_text
    assert "NMAlbumPackBuilder.registerAlbumPack({" in bootstrap_text
    assert "NMRoadTripMixAlbum_RoadTripVol1" in bootstrap_text

    assert 'NMRoadTripMixAlbum_RoadTripVol1 = {' in album_text
    assert 'soundPrefix = "RoadTripMixRoadTripVol1"' in album_text
    assert '"01 Intro"' in album_text
    assert '"02 Finale"' in album_text
    assert 'cassette = {' in album_text
    assert 'mode = "split"' in album_text
    assert 'a = "RoadTripVol1CassetteA"' in album_text
    assert 'b = "RoadTripVol1CassetteB"' in album_text
    assert 'ranges = {' in album_text
    assert 'a = { 1, 1 }' in album_text
    assert 'b = { 2, 2 }' in album_text
    assert 'texture = "WorldItems/Vinyl/World_NM_Cover18_Vinyl"' in album_text
    assert 'includePlayable = { "cassette", "vinyl", "cd" }' in album_text
    assert 'includeContainers = { "cassette", "vinyl", "cd" }' in album_text
    assert 'includeEmptyContainers = { "cassette", "vinyl", "cd" }' in album_text


def test_write_export_scaffold_generates_full_mode_lua_and_custom_texture_refs(tmp_path: Path) -> None:
    workshop_root = tmp_path / "Workshop"
    workshop_root.mkdir()
    project = ProjectConfig(
        mod_name="Night Drive",
        mod_id="NightDrive",
        workshop_output_folder=str(workshop_root),
    )
    row = default_media_row(1)
    row.media_name = "Night Drive"
    row.enabled_media["cd"] = False
    row.tracks_a = [
        _track("C:/music/one.ogg", "One More Song", "00:01:00"),
        _track("C:/music/two.ogg", "Two More Song", "00:02:00"),
    ]
    row.tracks_b = []

    row.appearances["cassette"].source = "custom"
    row.appearances["cassette"].inventory_full = _write_image(tmp_path / "custom" / "Item_NM_Cassette_Custom.png", (40, 20), (255, 0, 0, 255))
    row.appearances["cassette"].world_full = _write_image(tmp_path / "custom" / "World_NM_Cassette_Custom.png", (160, 80), (255, 0, 0, 255))
    row.appearances["case"].source = "custom"
    row.appearances["case"].inventory_full = _write_image(tmp_path / "custom" / "Item_NM_Case_Custom.png", (20, 40), (0, 255, 0, 255))
    row.appearances["case"].world_full = _write_image(tmp_path / "custom" / "World_NM_CassetteCover_Custom.png", (200, 100), (0, 255, 0, 255))
    row.appearances["vinyl"].source = "custom"
    row.appearances["vinyl"].inventory_full = _write_image(tmp_path / "custom" / "Item_NM_Vinyl_Custom.png", (30, 60), (0, 0, 255, 255))
    row.appearances["vinyl"].world_full = _write_image(tmp_path / "custom" / "World_NM_Vinyl_Custom.png", (180, 120), (0, 0, 255, 255))
    row.appearances["jacket"].source = "custom"
    row.appearances["jacket"].sprite_mode = "dual"
    row.appearances["jacket"].inventory_full = _write_image(tmp_path / "custom" / "Item_NM_Jacket_Custom.png", (60, 30), (255, 0, 255, 255))
    row.appearances["jacket"].world_full = _write_image(tmp_path / "custom" / "World_NM_Cover_Custom.png", (320, 200), (255, 0, 255, 255))
    row.appearances["jacket"].inventory_empty = _write_image(tmp_path / "custom" / "Item_NM_Jacket_Custom_Empty.png", (30, 60), (255, 128, 255, 255))
    row.appearances["jacket"].world_empty = _write_image(tmp_path / "custom" / "World_NM_Cover_Custom_Empty.png", (200, 320), (255, 128, 255, 255))
    project.media_rows = [row]

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    scripts_root = Path(targets.v42) / "media" / "scripts"
    lua_root = Path(targets.v42) / "media" / "lua" / "shared"
    items_text = (scripts_root / "NMB_NightDrive_Items.txt").read_text(encoding="utf-8")
    album_text = (lua_root / "NightDrive_Album_NightDrive.lua").read_text(encoding="utf-8")

    assert "item NightDriveCassette" in items_text
    assert "DisplayName = Night Drive (Cassette)" in items_text
    assert "item NightDriveVinyl" in items_text
    assert "item NightDriveJacketEmpty" in items_text
    assert "Icon = NM_Cassette_NightDrive_NightDrive" in items_text
    assert "Icon = NM_Jacket_NightDrive_NightDrive_Empty" in items_text

    assert 'mode = "full"' in album_text
    assert 'full = "NightDriveCassette"' in album_text
    assert 'full = "NightDriveVinyl"' in album_text
    assert "ranges = {" not in album_text
    assert 'cd = {' not in album_text
    assert 'texture = "WorldItems/Vinyl/World_NM_Cover_NightDrive_NightDrive"' in album_text
    assert 'includePlayable = { "cassette", "vinyl" }' in album_text
    assert 'includeContainers = { "cassette", "vinyl" }' in album_text
    assert 'includeEmptyContainers = { "cassette", "vinyl" }' in album_text
