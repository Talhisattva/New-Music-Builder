from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from new_music_builder.domain.models import ProjectConfig, TrackEntry, default_media_row
from new_music_builder.services.asset_catalog import AssetCatalog
from new_music_builder.services.export_planning import build_export_plan
from new_music_builder.services.export_scaffold import (
    _overlay_font_candidate_paths,
    _load_overlay_font,
    _wrap_text,
    render_square_image,
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


def _write_image(path: Path, size: tuple[int, int], color: tuple[int, int, int, int]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGBA', size, color).save(path)
    return path


def test_sanitize_filesystem_component_preserves_spaces_and_removes_invalid_chars() -> None:
    assert sanitize_filesystem_component('My: Fun* Mix?', fallback='X') == 'My_ Fun_ Mix_'
    assert sanitize_filesystem_component('   ', fallback='X') == 'X'


def test_overlay_font_candidates_prefer_explicit_override(monkeypatch) -> None:
    monkeypatch.setenv('NMB_OVERLAY_FONT', '/tmp/custom-font.ttf')

    candidates = _overlay_font_candidate_paths()

    assert candidates[0] == Path('/tmp/custom-font.ttf')


def test_overlay_font_candidates_prefer_bundled_nasalization_when_not_overridden(monkeypatch) -> None:
    monkeypatch.delenv('NMB_OVERLAY_FONT', raising=False)

    candidates = _overlay_font_candidate_paths()

    assert candidates[0] == ASSETS_ROOT / 'fonts' / 'Nasalization Rg.otf'


def test_render_square_image_adds_visible_name_overlay(tmp_path: Path) -> None:
    poster_path = tmp_path / 'poster.png'
    Image.new('RGBA', (300, 200), (255, 0, 0, 255)).save(poster_path)

    plain = render_square_image(poster_path, 1024, 'My Fun Mix', add_name_overlay=False)
    overlaid = render_square_image(poster_path, 1024, 'My Fun Mix', add_name_overlay=True)

    diff = ImageChops.difference(plain.convert('RGB'), overlaid.convert('RGB'))

    assert diff.getbbox() is not None


def test_render_square_image_places_name_overlay_in_lower_right_region(tmp_path: Path) -> None:
    poster_path = tmp_path / 'poster.png'
    Image.new('RGBA', (300, 200), (255, 0, 0, 255)).save(poster_path)

    plain = render_square_image(poster_path, 1024, 'My Fun Mix', add_name_overlay=False)
    overlaid = render_square_image(poster_path, 1024, 'My Fun Mix', add_name_overlay=True)

    bbox = ImageChops.difference(plain.convert('RGB'), overlaid.convert('RGB')).getbbox()

    assert bbox is not None
    assert bbox[0] > 300
    assert bbox[1] > 500


def test_render_square_image_keeps_small_preview_overlay_readable(tmp_path: Path) -> None:
    poster_path = tmp_path / 'poster.png'
    Image.new('RGBA', (300, 200), (255, 0, 0, 255)).save(poster_path)

    plain = render_square_image(poster_path, 132, 'My Fun Mix', add_name_overlay=False)
    overlaid = render_square_image(poster_path, 132, 'My Fun Mix', add_name_overlay=True)

    bbox = ImageChops.difference(plain.convert('RGB'), overlaid.convert('RGB')).getbbox()

    assert bbox is not None
    assert bbox[0] >= 35
    assert bbox[2] <= 124
    assert (bbox[2] - bbox[0]) >= 30
    assert (bbox[3] - bbox[1]) >= 20


def test_wrap_text_keeps_spaced_name_without_early_ellipsis() -> None:
    image = Image.new('RGBA', (132, 132), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = _load_overlay_font(11)

    lines = _wrap_text(
        draw,
        "Tali's Music Time",
        font,
        76,
        max_lines=4,
        truncate_with_ellipsis=False,
    )

    assert '...' not in ''.join(lines)


def test_wrap_text_breaks_long_unspaced_name_before_ellipsis() -> None:
    image = Image.new('RGBA', (132, 132), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = _load_overlay_font(10)

    lines = _wrap_text(
        draw,
        'asdgfasdgdsagasdgasgasdsgasdg',
        font,
        76,
        max_lines=4,
        truncate_with_ellipsis=False,
    )

    assert len(lines) >= 2
    assert all(draw.textlength(line, font=font) <= 76 for line in lines)


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
    workshop_text = (root / 'workshop.txt').read_text(encoding='utf-8')
    assert 'title=My Fun Mix' in workshop_text
    assert 'description=[h2]My Fun Mix[/h2]' in workshop_text
    assert 'description=[table]' in workshop_text
    assert 'description=[tr][td][b]Full Album[/b][/td][/tr]' in workshop_text
    assert 'description=[tr][td]01 Song[/td][/tr]' in workshop_text


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


def test_write_export_scaffold_exports_custom_media_textures_with_expected_sizes(tmp_path: Path) -> None:
    project = _project(tmp_path)
    row = project.media_rows[0]
    row.media_name = 'Album Alpha'
    row.tracks_a.append(_track())
    shared_cover = _write_image(tmp_path / 'custom' / 'jacket-world.png', (640, 400), (255, 0, 255, 255))
    row.cover_path = str(shared_cover)

    row.appearances['cassette'].source = 'custom'
    row.appearances['cassette'].inventory_full = str(_write_image(tmp_path / 'custom' / 'cassette-inv.png', (60, 20), (255, 0, 0, 255)))
    row.appearances['cassette'].world_full = str(_write_image(tmp_path / 'custom' / 'cassette-world.png', (120, 80), (255, 0, 0, 255)))

    row.appearances['case'].source = 'custom'
    row.appearances['case'].inventory_full = str(_write_image(tmp_path / 'custom' / 'case-inv.png', (24, 48), (0, 255, 0, 255)))
    row.appearances['case'].world_full = str(_write_image(tmp_path / 'custom' / 'case-world.png', (300, 200), (0, 255, 0, 255)))

    row.appearances['vinyl'].source = 'custom'
    row.appearances['vinyl'].inventory_full = str(_write_image(tmp_path / 'custom' / 'vinyl-inv.png', (16, 48), (0, 0, 255, 255)))
    row.appearances['vinyl'].world_full = str(_write_image(tmp_path / 'custom' / 'vinyl-world.png', (180, 200), (0, 0, 255, 255)))

    row.appearances['jacket'].source = 'custom'
    row.appearances['jacket'].sprite_mode = 'dual'
    row.appearances['jacket'].inventory_full = str(_write_image(tmp_path / 'custom' / 'jacket-inv.png', (48, 24), (255, 0, 255, 255)))
    row.appearances['jacket'].inventory_empty = str(_write_image(tmp_path / 'custom' / 'jacket-inv-empty.png', (24, 48), (255, 128, 255, 255)))
    row.appearances['jacket'].world_full = str(shared_cover)
    row.appearances['jacket'].world_empty = str(_write_image(tmp_path / 'custom' / 'jacket-world-empty.png', (400, 640), (255, 128, 255, 255)))

    row.appearances['cd'].source = 'custom'
    row.appearances['cd'].inventory_full = str(_write_image(tmp_path / 'custom' / 'cd-inv.png', (20, 20), (255, 128, 0, 255)))
    row.appearances['cd'].world_full = str(_write_image(tmp_path / 'custom' / 'cd-world.png', (180, 220), (255, 128, 0, 255)))

    row.appearances['cd_cover'].source = 'custom'
    row.appearances['cd_cover'].sprite_mode = 'dual'
    row.appearances['cd_cover'].inventory_full = str(_write_image(tmp_path / 'custom' / 'cd-cover-inv.png', (80, 40), (0, 255, 255, 255)))
    row.appearances['cd_cover'].inventory_empty = str(_write_image(tmp_path / 'custom' / 'cd-cover-inv-empty.png', (40, 80), (128, 255, 255, 255)))
    row.appearances['cd_cover'].world_full = str(_write_image(tmp_path / 'custom' / 'cd-cover-world.png', (500, 350), (0, 255, 255, 255)))
    row.appearances['cd_cover'].world_empty = str(_write_image(tmp_path / 'custom' / 'cd-cover-world-empty.png', (350, 500), (128, 255, 255, 255)))

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    textures_root = Path(targets.common) / 'media' / 'textures'
    module_id = 'MyFunMix'
    album_id = 'AlbumAlpha'

    assert Image.open(textures_root / f'Item_NM_Cassette_{module_id}_{album_id}.png').size == (32, 32)
    assert Image.open(textures_root / f'Item_NM_Vinyl_{module_id}_{album_id}.png').size == (32, 32)
    assert Image.open(textures_root / f'Item_NM_CD_{module_id}_{album_id}.png').size == (32, 32)
    assert Image.open(textures_root / f'Item_NM_Jacket_{module_id}_{album_id}.png').size == (32, 32)
    assert Image.open(textures_root / f'Item_NM_Jacket_{module_id}_{album_id}_Empty.png').size == (32, 32)
    assert Image.open(textures_root / f'Item_NM_CDCover_{module_id}_{album_id}.png').size == (32, 32)
    assert Image.open(textures_root / f'Item_NM_CDCover_{module_id}_{album_id}_Empty.png').size == (32, 32)

    assert Image.open(textures_root / 'WorldItems' / 'Cassette' / f'World_NM_Cassette_{module_id}_{album_id}.png').size == (256, 156)
    assert Image.open(textures_root / 'WorldItems' / 'Cassette' / f'World_NM_CassetteCover_{module_id}_{album_id}.png').size == (256, 256)
    assert Image.open(textures_root / 'WorldItems' / 'Vinyl' / f'World_NM_Vinyl_{module_id}_{album_id}.png').size == (256, 256)
    assert Image.open(textures_root / 'WorldItems' / 'Vinyl' / f'World_NM_Cover_{module_id}_{album_id}.png').size == (1024, 1024)
    assert Image.open(textures_root / 'WorldItems' / 'Vinyl' / f'World_NM_Cover_{module_id}_{album_id}_Empty.png').size == (1024, 1024)
    assert Image.open(textures_root / 'WorldItems' / 'CD' / f'World_NM_CD_{module_id}_{album_id}.png').size == (256, 256)
    assert Image.open(textures_root / 'WorldItems' / 'CD' / f'World_NM_CDCover_{module_id}_{album_id}.png').size == (256, 256)
    assert Image.open(textures_root / 'WorldItems' / 'CD' / f'World_NM_CDCover_{module_id}_{album_id}_Empty.png').size == (256, 256)
    assert not (textures_root / 'WorldItems' / 'Vinyl' / 'HR' / f'World_NM_Cover_{module_id}_{album_id}.png').exists()


def test_write_export_scaffold_exports_hr_cover_only_when_row_cover_differs(tmp_path: Path) -> None:
    project = _project(tmp_path)
    row = project.media_rows[0]
    row.media_name = 'Album Beta'
    row.enabled_media['cassette'] = False
    row.enabled_media['cd'] = False
    row.tracks_a.append(_track())
    row.cover_path = str(_write_image(tmp_path / 'cover-a.png', (700, 500), (255, 255, 0, 255)))

    row.appearances['jacket'].source = 'custom'
    row.appearances['jacket'].inventory_full = str(_write_image(tmp_path / 'custom' / 'jacket-beta-inv.png', (30, 60), (255, 0, 255, 255)))
    row.appearances['jacket'].world_full = str(_write_image(tmp_path / 'custom' / 'cover-b.png', (300, 900), (0, 0, 0, 255)))

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    textures_root = Path(targets.common) / 'media' / 'textures'
    hr_cover = textures_root / 'WorldItems' / 'Vinyl' / 'HR' / 'World_NM_Cover_MyFunMix_AlbumBeta.png'
    album_text = (Path(targets.v42) / 'media' / 'lua' / 'shared' / 'MyFunMix_Album_AlbumBeta.lua').read_text(encoding='utf-8')

    assert hr_cover.exists()
    assert Image.open(hr_cover).size == (1024, 1024)
    assert 'texture = "WorldItems/Vinyl/HR/World_NM_Cover_MyFunMix_AlbumBeta"' in album_text
    assert 'includePlayable = { "vinyl" }' in album_text
    assert 'includeContainers = { "vinyl" }' in album_text
    assert 'includeEmptyContainers = { "vinyl" }' in album_text


def test_write_export_scaffold_emits_hr_cover_when_row_cover_differs_from_custom_vinyl_world(tmp_path: Path) -> None:
    project = _project(tmp_path)
    row = project.media_rows[0]
    row.media_name = 'Album Gamma'
    row.enabled_media['cassette'] = False
    row.enabled_media['cd'] = False
    row.tracks_a.append(_track())
    row.cover_path = str(_write_image(tmp_path / 'cover-row.png', (640, 420), (255, 255, 0, 255)))

    row.appearances['vinyl'].source = 'custom'
    row.appearances['vinyl'].inventory_full = str(_write_image(tmp_path / 'custom' / 'vinyl-gamma-inv.png', (30, 60), (0, 0, 255, 255)))
    row.appearances['vinyl'].world_full = str(_write_image(tmp_path / 'custom' / 'vinyl-world-gamma.png', (500, 900), (0, 0, 0, 255)))

    row.appearances['jacket'].source = 'custom'
    row.appearances['jacket'].inventory_full = str(_write_image(tmp_path / 'custom' / 'jacket-gamma-inv.png', (30, 60), (255, 0, 255, 255)))
    row.appearances['jacket'].world_full = str(_write_image(tmp_path / 'custom' / 'jacket-world-gamma.png', (700, 500), (255, 0, 255, 255)))

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    textures_root = Path(targets.common) / 'media' / 'textures'
    hr_cover = textures_root / 'WorldItems' / 'Vinyl' / 'HR' / 'World_NM_Cover_MyFunMix_AlbumGamma.png'
    album_text = (Path(targets.v42) / 'media' / 'lua' / 'shared' / 'MyFunMix_Album_AlbumGamma.lua').read_text(encoding='utf-8')

    assert hr_cover.exists()
    assert 'texture = "WorldItems/Vinyl/HR/World_NM_Cover_MyFunMix_AlbumGamma"' in album_text


def test_write_export_scaffold_uses_one_shared_cover_group_for_all_enabled_media(tmp_path: Path) -> None:
    project = _project(tmp_path)
    row = project.media_rows[0]
    row.media_name = 'Album Shared'
    row.tracks_a.append(_track())
    row.cover_path = str(_write_image(tmp_path / 'cover-row-shared.png', (800, 600), (255, 255, 0, 255)))

    row.appearances['jacket'].source = 'custom'
    row.appearances['jacket'].inventory_full = str(_write_image(tmp_path / 'custom' / 'jacket-shared-inv.png', (30, 60), (255, 0, 255, 255)))
    row.appearances['jacket'].world_full = str(_write_image(tmp_path / 'custom' / 'jacket-shared-world.png', (500, 900), (0, 0, 0, 255)))

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    album_text = (Path(targets.v42) / 'media' / 'lua' / 'shared' / 'MyFunMix_Album_AlbumShared.lua').read_text(encoding='utf-8')

    assert album_text.count('texture = "') == 1
    assert 'texture = "WorldItems/Vinyl/HR/World_NM_Cover_MyFunMix_AlbumShared"' in album_text
    assert 'includePlayable = { "cassette", "vinyl", "cd" }' in album_text
    assert 'includeContainers = { "cassette", "vinyl", "cd" }' in album_text
    assert 'includeEmptyContainers = { "cassette", "vinyl", "cd" }' in album_text


def test_write_export_scaffold_falls_back_to_jacket_cover_when_row_cover_blank(tmp_path: Path) -> None:
    project = _project(tmp_path)
    row = project.media_rows[0]
    row.media_name = 'Album Fallback'
    row.enabled_media['cassette'] = False
    row.enabled_media['cd'] = False
    row.tracks_a.append(_track())
    row.cover_path = ''

    row.appearances['jacket'].source = 'custom'
    row.appearances['jacket'].inventory_full = str(_write_image(tmp_path / 'custom' / 'jacket-fallback-inv.png', (30, 60), (255, 0, 255, 255)))
    row.appearances['jacket'].world_full = str(_write_image(tmp_path / 'custom' / 'jacket-fallback-world.png', (700, 500), (255, 0, 255, 255)))

    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    textures_root = Path(targets.common) / 'media' / 'textures'
    album_text = (Path(targets.v42) / 'media' / 'lua' / 'shared' / 'MyFunMix_Album_AlbumFallback.lua').read_text(encoding='utf-8')

    assert not (textures_root / 'WorldItems' / 'Vinyl' / 'HR' / 'World_NM_Cover_MyFunMix_AlbumFallback.png').exists()
    assert album_text.count('texture = "') == 1
    assert 'texture = "WorldItems/Vinyl/World_NM_Cover_MyFunMix_AlbumFallback"' in album_text


def test_write_export_scaffold_emits_one_workshop_table_per_split_side(tmp_path: Path) -> None:
    project = _project(tmp_path)
    row = project.media_rows[0]
    row.media_name = 'Split Album'
    row.tracks_a = [
        TrackEntry(source_path='C:/a1.ogg', display_label='A One', duration='00:01:00'),
        TrackEntry(source_path='C:/a2.ogg', display_label='A Two', duration='00:02:00'),
    ]
    row.tracks_b = [
        TrackEntry(source_path='C:/b1.ogg', display_label='B One', duration='00:03:00'),
    ]
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    workshop_text = (Path(targets.root) / 'workshop.txt').read_text(encoding='utf-8')
    assert workshop_text.count('description=[table]') == 2
    assert 'description=[tr][th]Split Album[/th][/tr]' in workshop_text
    assert 'description=[tr][td][b]Side A[/b][/td][/tr]' in workshop_text
    assert 'description=[tr][td][b]Side B[/b][/td][/tr]' in workshop_text
    assert 'description=[tr][td]01 A One[/td][/tr]' in workshop_text
    assert 'description=[tr][td]02 A Two[/td][/tr]' in workshop_text
    assert 'description=[tr][td]01 B One[/td][/tr]' in workshop_text


def test_write_export_scaffold_keeps_duplicate_album_titles_as_separate_workshop_sections(tmp_path: Path) -> None:
    project = _project(tmp_path)
    first = project.media_rows[0]
    first.media_name = 'Same Album'
    first.tracks_a = [TrackEntry(source_path='C:/first.ogg', display_label='First Song', duration='00:01:00')]
    second = default_media_row(2)
    second.media_name = 'Same Album'
    second.tracks_a = [TrackEntry(source_path='C:/second.ogg', display_label='Second Song', duration='00:02:00')]
    project.media_rows = [first, second]
    catalog = AssetCatalog(ASSETS_ROOT).scan()
    plan = build_export_plan(project, catalog)
    targets = resolve_export_target(plan, project.workshop_output_folder, mod_name=project.mod_name, mod_id=project.mod_id)

    result = write_export_scaffold(project, plan, targets, catalog)

    assert not result.errors
    workshop_text = (Path(targets.root) / 'workshop.txt').read_text(encoding='utf-8')
    assert workshop_text.count('description=[table]') == 2
    assert workshop_text.count('description=[tr][th]Same Album[/th][/tr]') == 2
    assert workshop_text.find('description=[tr][td]01 First Song[/td][/tr]') < workshop_text.find('description=[tr][td]01 Second Song[/td][/tr]')
