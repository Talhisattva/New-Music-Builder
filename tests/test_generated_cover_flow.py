from pathlib import Path

from PIL import Image

from new_music_builder.domain.models import GeneratedAssetRecord, ProjectConfig, default_media_row
from new_music_builder.services.cover_texture_generator import CoverGenerationResult
from new_music_builder.services.generated_asset_registry import (
    build_generated_asset_key,
    normalize_cover_path,
    upsert_generated_asset_record,
    visible_generated_entries_for_kind,
)
from new_music_builder.services.generated_cover_flow import generate_supported_cover_set_for_row


def test_generate_supported_cover_set_for_row_generates_cassette_and_vinyl_and_selects_both(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    donor_inventory_path = tmp_path / "donor-inventory.png"
    donor_world_path = tmp_path / "donor-world.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (0, 0, 255, 255)).save(donor_inventory_path)
    Image.new("RGBA", (64, 64), (0, 255, 0, 255)).save(donor_world_path)

    row = default_media_row(1)
    row.cover_path = str(cover_path)
    row.appearances["cassette"].selected_asset_key = "cassette:1"
    project = ProjectConfig(media_rows=[row])
    calls: list[str] = []

    def cassette_generator(cover, **kwargs):
        calls.append(f"cassette:{Path(kwargs['donor_inventory_path']).name}:{Path(kwargs['donor_world_path']).name}")
        return _fake_generation_result(tmp_path, "cassette", Path(cover))

    def vinyl_generator(cover, **_kwargs):
        calls.append("vinyl")
        return _fake_generation_result(tmp_path, "vinyl", Path(cover))

    result = generate_supported_cover_set_for_row(
        project,
        row,
        cassette_donor_inventory_path=donor_inventory_path,
        cassette_donor_world_path=donor_world_path,
        cassette_generator=cassette_generator,
        vinyl_generator=vinyl_generator,
    )

    assert result.generated_kinds == ("cassette", "vinyl")
    assert result.skipped_kinds == ()
    assert result.failed_kinds == ()
    assert calls == ["cassette:donor-inventory.png:donor-world.png", "vinyl"]
    assert row.appearances["cassette"].selected_asset_key.startswith("generated:cassette:")
    assert row.appearances["vinyl"].selected_asset_key.startswith("generated:vinyl:")
    assert row.appearances["cassette"].source == "custom"
    assert row.appearances["vinyl"].source == "custom"
    assert [entry.key for entry in visible_generated_entries_for_kind(project, "cassette")] == [
        row.appearances["cassette"].selected_asset_key
    ]
    assert [entry.key for entry in visible_generated_entries_for_kind(project, "vinyl")] == [
        row.appearances["vinyl"].selected_asset_key
    ]


def test_generate_supported_cover_set_for_row_skips_existing_kind_and_selects_existing_record(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    donor_inventory_path = tmp_path / "donor-inventory.png"
    donor_world_path = tmp_path / "donor-world.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (0, 0, 255, 255)).save(donor_inventory_path)
    Image.new("RGBA", (64, 64), (0, 255, 0, 255)).save(donor_world_path)

    row = default_media_row(1)
    row.cover_path = str(cover_path)
    project = ProjectConfig(media_rows=[row])
    existing = _fake_generation_result(tmp_path, "cassette", cover_path).record
    upsert_generated_asset_record(project, existing)
    calls: list[str] = []

    def cassette_generator(_cover, **_kwargs):
        calls.append("cassette")
        return _fake_generation_result(tmp_path, "cassette", cover_path)

    def vinyl_generator(cover, **_kwargs):
        calls.append("vinyl")
        return _fake_generation_result(tmp_path, "vinyl", Path(cover))

    result = generate_supported_cover_set_for_row(
        project,
        row,
        cassette_donor_inventory_path=donor_inventory_path,
        cassette_donor_world_path=donor_world_path,
        cassette_generator=cassette_generator,
        vinyl_generator=vinyl_generator,
    )

    assert result.generated_kinds == ("vinyl",)
    assert result.skipped_kinds == ("cassette",)
    assert result.failed_kinds == ()
    assert calls == ["vinyl"]
    assert row.appearances["cassette"].selected_asset_key == existing.asset_key
    assert row.appearances["vinyl"].selected_asset_key.startswith("generated:vinyl:")
    assert len(project.generated_assets) == 2


def test_generate_supported_cover_set_for_row_allows_partial_failure(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(cover_path)

    row = default_media_row(1)
    row.cover_path = str(cover_path)
    row.appearances["cassette"].selected_asset_key = "cassette:1"
    project = ProjectConfig(media_rows=[row])

    def cassette_generator(_cover, **_kwargs):
        raise FileNotFoundError("donor cassette shell was unavailable")

    def vinyl_generator(cover, **_kwargs):
        return _fake_generation_result(tmp_path, "vinyl", Path(cover))

    result = generate_supported_cover_set_for_row(
        project,
        row,
        cassette_donor_inventory_path="",
        cassette_donor_world_path="",
        cassette_generator=cassette_generator,
        vinyl_generator=vinyl_generator,
    )

    assert result.generated_kinds == ("vinyl",)
    assert result.skipped_kinds == ()
    assert result.failed_kinds == ("cassette",)
    assert row.appearances["cassette"].selected_asset_key == "cassette:1"
    assert row.appearances["cassette"].source == "default"
    assert row.appearances["vinyl"].selected_asset_key.startswith("generated:vinyl:")
    assert [record.kind for record in project.generated_assets] == ["vinyl"]


def _fake_generation_result(tmp_path: Path, kind: str, cover_path: Path) -> CoverGenerationResult:
    output_dir = tmp_path / "Generated Textures" / kind.capitalize() / cover_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = output_dir / f"{kind}-inventory.png"
    world_path = output_dir / f"{kind}-world.png"
    Image.new("RGBA", (32, 32), (255, 255, 255, 255)).save(inventory_path)
    Image.new("RGBA", (64, 64), (255, 255, 255, 255)).save(world_path)
    normalized_cover = normalize_cover_path(cover_path)
    record = GeneratedAssetRecord(
        kind=kind,
        cover_path=normalized_cover,
        asset_key=build_generated_asset_key(kind, normalized_cover),
        label=f"{cover_path.stem} Generated",
        inventory_full=str(inventory_path),
        world_full=str(world_path),
        source_name=cover_path.name,
    )
    return CoverGenerationResult(record=record, successful_outputs=2, total_outputs=2)
