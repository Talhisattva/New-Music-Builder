from pathlib import Path

from PIL import Image

from new_music_builder.domain.models import ProjectConfig, TrackEntry, default_media_row
from new_music_builder.services.asset_catalog import AssetCatalog
from new_music_builder.services.export_planning import build_export_plan
from new_music_builder.services.export_scaffold import (
    resolve_export_target,
    sanitize_filesystem_component,
    validate_export_request,
    write_export_scaffold,
)


ASSETS_ROOT = Path(__file__).resolve().parents[1] / 'assets'


def _track() -> TrackEntry:
    return TrackEntry(source_path='C:/song.ogg', display_label='Song', duration='00:01:00')


def _project(tmp_path: Path) -> ProjectConfig:
    row = default_media_row(1)
    row.tracks_a = []
    project = ProjectConfig(
        mod_name='My Fun Mix',
        mod_id='MyFunMix',
        parent_mod_id='NewMusic',
        author='Tester',
        workshop_output_folder=str(tmp_path / 'Workshop'),
        media_rows=[row],
    )
    (tmp_path / 'Workshop').mkdir()
    return project


def test_sanitize_filesystem_component_preserves_spaces_and_removes_invalid_chars() -> None:
    assert sanitize_filesystem_component('My: Fun* Mix?', fallback='X') == 'My_ Fun_ Mix_'
    assert sanitize_filesystem_component('   ', fallback='X') == 'X'


def test_resolve_export_target_uses_outer_name_and_inner_id(tmp_path: Path) -> None:
    project = _project(tmp_path)
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    row = project.media_rows[0]
    row.tracks_a = []
    row.tracks_b = []
    row.tracks_a.append(_track())
    plan = build_export_plan(project, catalog)

    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    assert Path(targets.root).name == 'My Fun Mix'
    assert Path(targets.mod_base).name == 'MyFunMix'


def test_validate_export_request_blocks_missing_required_inputs(tmp_path: Path) -> None:
    project = ProjectConfig(mod_name='', mod_id='Bad ID', workshop_output_folder=str(tmp_path / 'missing'))
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)

    errors = validate_export_request(project, plan)

    assert any('Workshop folder' in error for error in errors)
    assert any('Mod Name' in error for error in errors)
    assert any('cannot contain spaces' in error for error in errors)
    assert any('At least one media side' in error for error in errors)


def test_write_export_scaffold_creates_expected_files(tmp_path: Path) -> None:
    project = _project(tmp_path)
    poster_path = tmp_path / 'poster.png'
    Image.new('RGBA', (300, 200), (255, 0, 0, 255)).save(poster_path)
    project.workshop_poster_path = str(poster_path)
    row = project.media_rows[0]
    row.tracks_a.append(_track())
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    root = Path(targets.root)
    assert (root / 'Preview.png').exists()
    assert (Path(targets.common) / 'poster.png').exists()
    assert (Path(targets.v42) / 'poster.png').exists()
    assert (Path(targets.common) / 'icon.png').exists()
    assert (Path(targets.v42) / 'icon.png').exists()
    assert Image.open(Path(targets.common) / 'icon.png').size == (32, 32)
    assert Image.open(Path(targets.v42) / 'icon.png').size == (32, 32)
    assert (Path(targets.common) / 'mod.info').read_text(encoding='utf-8').count('require=NewMusic') == 1
    assert 'title=My Fun Mix' in (root / 'workshop.txt').read_text(encoding='utf-8')


def test_write_export_scaffold_omits_require_when_parent_blank(tmp_path: Path) -> None:
    project = _project(tmp_path)
    project.parent_mod_id = ''
    row = project.media_rows[0]
    row.tracks_a.append(_track())
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    assert 'require=' not in (Path(targets.common) / 'mod.info').read_text(encoding='utf-8')
