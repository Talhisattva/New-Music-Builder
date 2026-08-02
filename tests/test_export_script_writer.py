from pathlib import Path
import re

from PIL import Image

from new_music_builder.domain.models import ProjectConfig, TrackEntry, default_media_row
from new_music_builder.services.asset_catalog import AssetCatalog
from new_music_builder.services.export_planning import build_export_plan
from new_music_builder.services.export_scaffold import resolve_export_target, write_export_scaffold
from new_music_builder.services.export_script_writer import _pz_safe_display_name


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
    assert "file = media/sound/RoadTripMix/RoadTripVol1/A-Side/RoadTripVol1SideA1Intro.ogg" in sounds_text

    assert "item RoadTripVol1CassetteA" in items_text
    assert "item RoadTripVol1CassetteB" in items_text
    assert "item RoadTripVol1CD" in items_text
    assert "item RoadTripVol1CDA" not in items_text
    assert "item RoadTripVol1CDB" not in items_text
    assert "item RoadTripVol1JacketEmpty" in items_text
    assert "item RoadTripVol1JacketFull" in items_text
    assert "WorldStaticModel = RoadTripMix.SharedJacket" in items_text

    assert "model SharedCassette" in models_text
    assert "model SharedJacket" in models_text
    assert "mesh = WorldItems/NM_Jacket" in models_text

    assert 'require "NMAlbumPackBuilder"' in bootstrap_text
    assert 'require "RoadTripMix_Album_RoadTripVol1"' in bootstrap_text
    assert "NMAlbumPackBuilder.registerAlbumPack({" in bootstrap_text
    assert "NMRoadTripMixAlbum_RoadTripVol1" in bootstrap_text

    assert 'NMRoadTripMixAlbum_RoadTripVol1 = {' in album_text
    assert 'soundPrefix = "RoadTripMixRoadTripVol1"' in album_text
    assert '"UI_RoadTripMix_RoadTripVol1_Song_01"' in album_text
    assert '"UI_RoadTripMix_RoadTripVol1_Song_02"' in album_text
    assert '"01 Intro"' not in album_text
    assert '"02 Finale"' not in album_text
    assert 'cassette = {' in album_text
    assert 'mode = "split"' in album_text
    assert 'a = "RoadTripVol1CassetteA"' in album_text
    assert 'b = "RoadTripVol1CassetteB"' in album_text
    assert 'cd = {' in album_text
    assert 'full = "RoadTripVol1CD"' in album_text
    assert 'ranges = {' in album_text
    assert 'a = { 1, 1 }' in album_text
    assert 'b = { 2, 2 }' in album_text
    assert 'texture = "WorldItems/Vinyl/World_NM_Cover18_Vinyl"' in album_text
    assert 'includePlayable = { "cassette", "vinyl", "cd" }' in album_text
    assert 'includeContainers = { "cassette", "vinyl", "cd" }' in album_text
    assert 'includeEmptyContainers = { "cassette", "vinyl", "cd" }' in album_text


def test_write_export_scaffold_respects_mixed_per_media_modes(tmp_path: Path) -> None:
    workshop_root = tmp_path / "Workshop"
    workshop_root.mkdir()
    project = ProjectConfig(
        mod_name="Mode Mix",
        mod_id="ModeMix",
        workshop_output_folder=str(workshop_root),
    )
    row = default_media_row(1)
    row.media_name = "Mode Mix"
    row.media_modes["cassette"] = "single"
    row.media_modes["vinyl"] = "split"
    row.media_modes["cd"] = "split"
    row.tracks_a = [_track("C:/music/a.ogg", "A Song", "00:01:00")]
    row.tracks_b = [_track("C:/music/b.ogg", "B Song", "00:02:00")]
    project.media_rows = [row]

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    scripts_root = Path(targets.v42) / "media" / "scripts"
    lua_root = Path(targets.v42) / "media" / "lua" / "shared"
    items_text = (scripts_root / "NMB_ModeMix_Items.txt").read_text(encoding="utf-8")
    album_text = (lua_root / "ModeMix_Album_ModeMix.lua").read_text(encoding="utf-8")

    assert "item ModeMixCassette" in items_text
    assert "item ModeMixCassetteA" not in items_text
    assert "item ModeMixCassetteB" not in items_text
    assert "item ModeMixVinylA" in items_text
    assert "item ModeMixVinylB" in items_text
    assert "item ModeMixCDA" in items_text
    assert "item ModeMixCDB" in items_text
    assert 'full = "ModeMixCassette"' in album_text
    assert 'a = "ModeMixVinylA"' in album_text
    assert 'b = "ModeMixVinylB"' in album_text
    assert 'a = "ModeMixCDA"' in album_text
    assert 'b = "ModeMixCDB"' in album_text


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
    assert '"UI_NightDrive_NightDrive_Song_01"' in album_text
    assert '"UI_NightDrive_NightDrive_Song_02"' in album_text
    assert '"01 One More Song"' not in album_text
    assert '"02 Two More Song"' not in album_text
    assert "ranges = {" not in album_text
    assert 'cd = {' not in album_text
    assert 'texture = "WorldItems/Vinyl/World_NM_Cover_NightDrive_NightDrive"' in album_text
    assert 'includePlayable = { "cassette", "vinyl" }' in album_text
    assert 'includeContainers = { "cassette", "vinyl" }' in album_text
    assert 'includeEmptyContainers = { "cassette", "vinyl" }' in album_text


def test_pz_safe_display_name_normalizes_commas_and_whitespace() -> None:
    assert _pz_safe_display_name("Rock,  Pop\t& Rap Hits Vol 1") == "Rock - Pop & Rap Hits Vol 1"
    assert _pz_safe_display_name("伟大的2") == "伟大的2"


def test_write_export_scaffold_normalizes_comma_bearing_item_display_names(tmp_path: Path) -> None:
    workshop_root = tmp_path / "Workshop"
    workshop_root.mkdir()
    project = ProjectConfig(
        mod_name="Road Trip Mix",
        mod_id="RoadTripMix",
        workshop_output_folder=str(workshop_root),
    )
    row = default_media_row(1)
    row.media_name = "Rock, Pop & Rap Hits Vol 1"
    row.tracks_a = [_track("C:/music/intro.ogg", "КИНО - Пачка сигарет", "00:01:00")]
    project.media_rows = [row]

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    items_text = (Path(targets.v42) / "media" / "scripts" / "NMB_RoadTripMix_Items.txt").read_text(encoding="utf-8")
    sounds_text = (Path(targets.v42) / "media" / "scripts" / "NMB_RoadTripMix_Sounds.txt").read_text(encoding="utf-8")

    assert "DisplayName = Rock, Pop & Rap Hits Vol 1 (Cassette)" not in items_text
    assert "DisplayName = Rock - Pop & Rap Hits Vol 1 (Cassette)" in items_text
    assert "media/sound/RoadTripMix/Rock, Pop & Rap Hits Vol 1/" not in sounds_text


def test_write_export_scaffold_keeps_audio_folder_in_sync_with_sanitized_module_id(tmp_path: Path) -> None:
    workshop_root = tmp_path / "Workshop"
    workshop_root.mkdir()
    project = ProjectConfig(
        mod_name="Underscore Pack",
        mod_id="TM_NewGuppy",
        workshop_output_folder=str(workshop_root),
    )
    row = default_media_row(1)
    row.media_name = "Single Test"
    row.tracks_a = [_track("C:/music/test.ogg", "Test Song", "00:01:00")]
    project.media_rows = [row]

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    scripts_root = Path(targets.v42) / "media" / "scripts"
    lua_root = Path(targets.v42) / "media" / "lua" / "shared"
    sounds_text = (scripts_root / "NMB_TM_NewGuppy_Sounds.txt").read_text(encoding="utf-8")
    bootstrap_text = (lua_root / "TM_NewGuppy_PackBootstrap.lua").read_text(encoding="utf-8")
    album_text = (lua_root / "TM_NewGuppy_Album_SingleTest.lua").read_text(encoding="utf-8")
    ui_en = (Path(targets.common) / "media" / "lua" / "shared" / "Translate" / "EN" / "UI_EN.txt").read_text(encoding="utf-8")

    assert "module TM_NewGuppy" in sounds_text
    assert "file = media/sound/TM_NewGuppy/SingleTest/A-Side/SingleTestSideA1TestSong.ogg" in sounds_text
    assert 'local PACK_MODULE = "TM_NewGuppy"' in bootstrap_text
    assert 'NMTM_NewGuppyAlbum_SingleTest = {' in album_text
    assert '"UI_TM_NewGuppy_SingleTest_Song_01"' in album_text
    assert 'UI_EN = {' in ui_en
    assert 'UI_TM_NewGuppy_SingleTest_Song_01 = "Test Song"' in ui_en
    assert Path(targets.audio_pack_root).name == "TM_NewGuppy"


def test_write_export_scaffold_legacy_mode_uses_clean_song_ids_for_lua_and_scripts(tmp_path: Path) -> None:
    workshop_root = tmp_path / "Workshop"
    workshop_root.mkdir()
    project = ProjectConfig(
        mod_name="Legacy Pack",
        mod_id="LegacyPack",
        workshop_output_folder=str(workshop_root),
        legacy_mode_enabled=True,
    )
    row = default_media_row(1)
    row.row_mode = "singles"
    row.tracks_a = [_track("C:/music/intro.ogg", "Kiasmos Looped", "00:01:00")]
    project.media_rows = [row]

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    scripts_root = Path(targets.v42) / "media" / "scripts"
    lua_root = Path(targets.v42) / "media" / "lua" / "shared"
    sounds_text = (scripts_root / "NMB_LegacyPack_Sounds.txt").read_text(encoding="utf-8")
    items_text = (scripts_root / "NMB_LegacyPack_Items.txt").read_text(encoding="utf-8")
    models_text = (scripts_root / "NMB_LegacyPack_Models.txt").read_text(encoding="utf-8")
    album_text = (lua_root / "LegacyPack_Album_SinglesGroup1.lua").read_text(encoding="utf-8")

    assert "11KiasmosLooped" not in album_text
    assert "11KiasmosLooped" not in sounds_text
    assert "11KiasmosLooped" not in items_text
    assert "11KiasmosLooped" not in models_text
    assert "sound KiasmosLoopedCassette" in sounds_text
    assert "sound KiasmosLoopedVinyl" in sounds_text
    assert "sound KiasmosLoopedCD" in sounds_text
    assert 'local CASSETTE_CARRIER = "tsarcraft_music_01_62"' in album_text
    assert 'local VINYL_CARRIER = "tsarcraft_music_01_63"' in album_text
    assert 'local CD_CARRIER = "tsarcraft_music_01_64"' in album_text
    assert 'GlobalMusic["KiasmosLoopedCassette"] = CASSETTE_CARRIER' in album_text
    assert 'GlobalMusic["KiasmosLoopedVinyl"] = VINYL_CARRIER' in album_text
    assert 'GlobalMusic["KiasmosLoopedCD"] = CD_CARRIER' in album_text
    assert 'registerMediaTypeAlias' not in album_text
    assert 'registerLinkedCover' not in album_text


def test_write_export_scaffold_reuses_shared_model_definitions_pack_wide(tmp_path: Path) -> None:
    workshop_root = tmp_path / "Workshop"
    workshop_root.mkdir()
    project = ProjectConfig(
        mod_name="Shared Model Pack",
        mod_id="SharedModelPack",
        workshop_output_folder=str(workshop_root),
        legacy_mode_enabled=True,
    )
    row = default_media_row(1)
    row.row_mode = "singles"
    row.media_name = "Shared Models"
    row.tracks_a = [
        _track("C:/music/one.ogg", "Song One", "00:01:00"),
        _track("C:/music/two.ogg", "Song Two", "00:02:00"),
    ]
    project.media_rows = [row]

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    scripts_root = Path(targets.v42) / "media" / "scripts"
    items_text = (scripts_root / "NMB_SharedModelPack_Items.txt").read_text(encoding="utf-8")
    models_text = (scripts_root / "NMB_SharedModelPack_Models.txt").read_text(encoding="utf-8")

    cassette_model_refs = re.findall(r"WorldStaticModel = SharedModelPack\.(SharedCassette\w+),", items_text)
    vinyl_model_refs = re.findall(r"WorldStaticModel = SharedModelPack\.(SharedVinyl\w+),", items_text)
    cd_model_refs = re.findall(r"WorldStaticModel = SharedModelPack\.(SharedCD\w+),", items_text)
    assert len(set(cassette_model_refs)) == 1
    assert len(set(vinyl_model_refs)) == 1
    assert len(set(cd_model_refs)) == 1

    assert models_text.count("model SharedCassette") == 1
    assert models_text.count("model SharedVinyl") == 1
    assert models_text.count("model SharedCD") == 1


def test_write_export_scaffold_reuses_shared_container_model_definitions_pack_wide(tmp_path: Path) -> None:
    workshop_root = tmp_path / "Workshop"
    workshop_root.mkdir()
    project = ProjectConfig(
        mod_name="Shared Container Pack",
        mod_id="SharedContainerPack",
        workshop_output_folder=str(workshop_root),
    )
    row_one = default_media_row(1)
    row_one.media_name = "Container One"
    row_one.tracks_a = [_track("C:/music/a.ogg", "Track A", "00:01:00")]
    row_two = default_media_row(2)
    row_two.media_name = "Container Two"
    row_two.tracks_a = [_track("C:/music/b.ogg", "Track B", "00:02:00")]
    project.media_rows = [row_one, row_two]

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    scripts_root = Path(targets.v42) / "media" / "scripts"
    items_text = (scripts_root / "NMB_SharedContainerPack_Items.txt").read_text(encoding="utf-8")
    models_text = (scripts_root / "NMB_SharedContainerPack_Models.txt").read_text(encoding="utf-8")

    case_model_refs = re.findall(r"WorldStaticModel = SharedContainerPack\.(SharedCassetteCase\w+),", items_text)
    jacket_model_refs = re.findall(r"WorldStaticModel = SharedContainerPack\.(SharedJacket\w+),", items_text)
    cover_model_refs = re.findall(r"WorldStaticModel = SharedContainerPack\.(SharedCDCover\w+),", items_text)

    assert len(set(case_model_refs)) == 1
    assert len(set(jacket_model_refs)) == 1
    assert len(set(cover_model_refs)) == 1

    assert models_text.count("model SharedCassetteCase") == 1
    assert models_text.count("model SharedJacket") == 1
    assert models_text.count("model SharedCDCover") == 1


def test_write_export_scaffold_groups_singles_lua_tables_into_one_file_per_source_row(tmp_path: Path) -> None:
    workshop_root = tmp_path / "Workshop"
    workshop_root.mkdir()
    project = ProjectConfig(
        mod_name="Legacy Pack",
        mod_id="LegacyPack",
        workshop_output_folder=str(workshop_root),
        legacy_mode_enabled=True,
    )
    row = default_media_row(1)
    row.media_name = "Legacy Singles"
    row.row_mode = "singles"
    row.tracks_a = [
        _track("C:/music/intro.ogg", "Kiasmos Looped", "00:01:00"),
        _track("C:/music/next.ogg", "Lemon Jelly Space Walk", "00:02:00"),
    ]
    project.media_rows = [row]

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    lua_root = Path(targets.v42) / "media" / "lua" / "shared"
    bootstrap_text = (lua_root / "LegacyPack_PackBootstrap.lua").read_text(encoding="utf-8")
    grouped_album_text = (lua_root / "LegacyPack_Album_LegacySingles.lua").read_text(encoding="utf-8")

    assert bootstrap_text.count('require "LegacyPack_Album_LegacySingles"') == 1
    assert 'require "NMSinglesPackBuilder"' not in bootstrap_text
    assert 'registerSinglesPack' not in bootstrap_text
    assert 'entries = {' not in grouped_album_text
    assert 'NMTrackCatalog.registerEntry' not in grouped_album_text
    assert 'GlobalMusic["KiasmosLoopedCassette"] = CASSETTE_CARRIER' in grouped_album_text
    assert 'GlobalMusic["KiasmosLoopedCD"] = CD_CARRIER' in grouped_album_text
    assert 'registerMediaTypeAlias' not in grouped_album_text
    assert 'registerLinkedCover' not in grouped_album_text
    assert not (lua_root / "LegacyPack_Album_KiasmosLooped.lua").exists()
    assert not (lua_root / "LegacyPack_Album_LemonJellySpaceWalk.lua").exists()


def test_write_export_scaffold_preserves_mixed_bootstrap_require_order(tmp_path: Path) -> None:
    workshop_root = tmp_path / "Workshop"
    workshop_root.mkdir()
    project = ProjectConfig(
        mod_name="Mixed Pack",
        mod_id="MixedPack",
        workshop_output_folder=str(workshop_root),
        legacy_mode_enabled=True,
    )
    singles = default_media_row(1)
    singles.media_name = "Legacy Singles"
    singles.row_mode = "singles"
    singles.enabled_media = {"cassette": True, "vinyl": False, "cd": False}
    singles.tracks_a = [_track("C:/music/intro.ogg", "Single Song", "00:01:00")]

    mixtape = default_media_row(2)
    mixtape.media_name = "Road Trip"
    mixtape.row_mode = "mixtape"
    mixtape.enabled_media = {"cassette": True, "vinyl": False, "cd": False}
    mixtape.tracks_a = [_track("C:/music/a.ogg", "Track A", "00:01:00")]
    mixtape.tracks_b = [_track("C:/music/b.ogg", "Track B", "00:01:00")]
    project.media_rows = [singles, mixtape]

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    lua_root = Path(targets.v42) / "media" / "lua" / "shared"
    bootstrap_text = (lua_root / "MixedPack_PackBootstrap.lua").read_text(encoding="utf-8")

    singles_require = 'require "MixedPack_Album_LegacySingles"'
    mixtape_require = 'require "MixedPack_Album_RoadTrip"'
    assert singles_require in bootstrap_text
    assert mixtape_require in bootstrap_text
    assert bootstrap_text.index(singles_require) < bootstrap_text.index(mixtape_require)
    assert 'registerSinglesPack' not in bootstrap_text
    assert 'NMAlbumPackBuilder.registerAlbumPack({' in bootstrap_text
    singles_text = (lua_root / "MixedPack_Album_LegacySingles.lua").read_text(encoding="utf-8")
    mixtape_text = (lua_root / "MixedPack_Album_RoadTrip.lua").read_text(encoding="utf-8")
    assert 'GlobalMusic["SingleSongCassette"] = CASSETTE_CARRIER' in singles_text
    assert 'registerMediaTypeAlias' not in singles_text
    assert 'registerLinkedCover' not in singles_text
    assert 'coverGroups = {' in mixtape_text
