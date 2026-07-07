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
from new_music_builder.services.generated_cover_flow import apply_generated_cover_set_result, generate_supported_cover_set_for_row


def test_generate_supported_cover_set_for_row_generates_cassette_case_vinyl_jacket_and_cd_cover_and_selects_all(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    donor_inventory_path = tmp_path / "donor-inventory.png"
    donor_world_path = tmp_path / "donor-world.png"
    case_donor_inventory_path = tmp_path / "case-donor-inventory.png"
    case_donor_world_path = tmp_path / "case-donor-world.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (0, 0, 255, 255)).save(donor_inventory_path)
    Image.new("RGBA", (64, 64), (0, 255, 0, 255)).save(donor_world_path)
    Image.new("RGBA", (32, 32), (255, 255, 0, 255)).save(case_donor_inventory_path)
    Image.new("RGBA", (64, 64), (255, 0, 255, 255)).save(case_donor_world_path)

    row = default_media_row(1)
    row.cover_path = str(cover_path)
    row.appearances["cassette"].selected_asset_key = "cassette:1"
    row.appearances["case"].selected_asset_key = "case:4"
    project = ProjectConfig(media_rows=[row])
    calls: list[str] = []

    def cassette_generator(cover, **kwargs):
        calls.append(f"cassette:{Path(kwargs['donor_inventory_path']).name}:{Path(kwargs['donor_world_path']).name}")
        return _fake_generation_result(tmp_path, "cassette", Path(cover))

    def case_generator(cover, **kwargs):
        calls.append(f"case:{Path(kwargs['donor_inventory_path']).name}:{Path(kwargs['donor_world_path']).name}")
        return _fake_generation_result(tmp_path, "case", Path(cover))

    def vinyl_generator(cover, **_kwargs):
        calls.append("vinyl")
        return _fake_generation_result(tmp_path, "vinyl", Path(cover))

    def jacket_generator(cover, **_kwargs):
        calls.append("jacket")
        return _fake_generation_result(tmp_path, "jacket", Path(cover))

    def cd_cover_generator(cover, **_kwargs):
        calls.append("cd_cover")
        return _fake_generation_result(tmp_path, "cd_cover", Path(cover))

    result = generate_supported_cover_set_for_row(
        project,
        row,
        cassette_donor_inventory_path=donor_inventory_path,
        cassette_donor_world_path=donor_world_path,
        case_donor_inventory_path=case_donor_inventory_path,
        case_donor_world_path=case_donor_world_path,
        cassette_generator=cassette_generator,
        case_generator=case_generator,
        vinyl_generator=vinyl_generator,
        jacket_generator=jacket_generator,
        cd_cover_generator=cd_cover_generator,
    )

    assert result.generated_kinds == ("cassette", "case", "vinyl", "jacket", "cd_cover")
    assert result.skipped_kinds == ()
    assert result.failed_kinds == ()
    assert calls == [
        "cassette:donor-inventory.png:donor-world.png",
        "case:case-donor-inventory.png:case-donor-world.png",
        "vinyl",
        "jacket",
        "cd_cover",
    ]
    assert row.appearances["cassette"].selected_asset_key.startswith("generated:cassette:")
    assert row.appearances["case"].selected_asset_key.startswith("generated:case:")
    assert row.appearances["vinyl"].selected_asset_key.startswith("generated:vinyl:")
    assert row.appearances["jacket"].selected_asset_key.startswith("generated:jacket:")
    assert row.appearances["cd_cover"].selected_asset_key.startswith("generated:cd_cover:")
    assert row.appearances["cassette"].source == "custom"
    assert row.appearances["case"].source == "custom"
    assert row.appearances["vinyl"].source == "custom"
    assert row.appearances["jacket"].source == "custom"
    assert row.appearances["cd_cover"].source == "custom"
    assert [entry.key for entry in visible_generated_entries_for_kind(project, "cassette")] == [
        row.appearances["cassette"].selected_asset_key
    ]
    assert [entry.key for entry in visible_generated_entries_for_kind(project, "case")] == [
        row.appearances["case"].selected_asset_key
    ]
    assert [entry.key for entry in visible_generated_entries_for_kind(project, "vinyl")] == [
        row.appearances["vinyl"].selected_asset_key
    ]
    assert [entry.key for entry in visible_generated_entries_for_kind(project, "jacket")] == [
        row.appearances["jacket"].selected_asset_key
    ]
    assert [entry.key for entry in visible_generated_entries_for_kind(project, "cd_cover")] == [
        row.appearances["cd_cover"].selected_asset_key
    ]


def test_generate_supported_cover_set_for_row_skips_existing_kind_and_selects_existing_record(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    donor_inventory_path = tmp_path / "donor-inventory.png"
    donor_world_path = tmp_path / "donor-world.png"
    case_donor_inventory_path = tmp_path / "case-donor-inventory.png"
    case_donor_world_path = tmp_path / "case-donor-world.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (0, 0, 255, 255)).save(donor_inventory_path)
    Image.new("RGBA", (64, 64), (0, 255, 0, 255)).save(donor_world_path)
    Image.new("RGBA", (32, 32), (255, 255, 0, 255)).save(case_donor_inventory_path)
    Image.new("RGBA", (64, 64), (255, 0, 255, 255)).save(case_donor_world_path)

    row = default_media_row(1)
    row.cover_path = str(cover_path)
    project = ProjectConfig(media_rows=[row])
    existing = _fake_generation_result(tmp_path, "cassette", cover_path).record
    upsert_generated_asset_record(project, existing)
    calls: list[str] = []

    def cassette_generator(_cover, **_kwargs):
        calls.append("cassette")
        return _fake_generation_result(tmp_path, "cassette", cover_path)

    def case_generator(cover, **_kwargs):
        calls.append("case")
        return _fake_generation_result(tmp_path, "case", Path(cover))

    def vinyl_generator(cover, **_kwargs):
        calls.append("vinyl")
        return _fake_generation_result(tmp_path, "vinyl", Path(cover))

    def jacket_generator(cover, **_kwargs):
        calls.append("jacket")
        return _fake_generation_result(tmp_path, "jacket", Path(cover))

    def cd_cover_generator(cover, **_kwargs):
        calls.append("cd_cover")
        return _fake_generation_result(tmp_path, "cd_cover", Path(cover))

    result = generate_supported_cover_set_for_row(
        project,
        row,
        cassette_donor_inventory_path=donor_inventory_path,
        cassette_donor_world_path=donor_world_path,
        case_donor_inventory_path=case_donor_inventory_path,
        case_donor_world_path=case_donor_world_path,
        cassette_generator=cassette_generator,
        case_generator=case_generator,
        vinyl_generator=vinyl_generator,
        jacket_generator=jacket_generator,
        cd_cover_generator=cd_cover_generator,
    )

    assert result.generated_kinds == ("case", "vinyl", "jacket", "cd_cover")
    assert result.skipped_kinds == ("cassette",)
    assert result.failed_kinds == ()
    assert calls == ["case", "vinyl", "jacket", "cd_cover"]
    assert row.appearances["cassette"].selected_asset_key == existing.asset_key
    assert row.appearances["case"].selected_asset_key.startswith("generated:case:")
    assert row.appearances["vinyl"].selected_asset_key.startswith("generated:vinyl:")
    assert row.appearances["jacket"].selected_asset_key.startswith("generated:jacket:")
    assert row.appearances["cd_cover"].selected_asset_key.startswith("generated:cd_cover:")
    assert len(project.generated_assets) == 5


def test_generate_supported_cover_set_for_row_force_refresh_rebuilds_existing_kind(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(cover_path)

    row = default_media_row(1)
    row.cover_path = str(cover_path)
    project = ProjectConfig(media_rows=[row])
    existing = _fake_generation_result(tmp_path, "cassette", cover_path).record
    upsert_generated_asset_record(project, existing)
    calls: list[str] = []

    def cassette_generator(_cover, **_kwargs):
        calls.append("cassette")
        return _fake_generation_result(tmp_path, "cassette", cover_path)

    result = generate_supported_cover_set_for_row(
        project,
        row,
        force_refresh=True,
        cassette_donor_inventory_path="",
        cassette_donor_world_path="",
        case_donor_inventory_path="",
        case_donor_world_path="",
        cassette_generator=cassette_generator,
        case_generator=lambda cover, **_kwargs: _fake_generation_result(tmp_path, "case", Path(cover)),
        vinyl_generator=lambda cover, **_kwargs: _fake_generation_result(tmp_path, "vinyl", Path(cover)),
        jacket_generator=lambda cover, **_kwargs: _fake_generation_result(tmp_path, "jacket", Path(cover)),
        cd_cover_generator=lambda cover, **_kwargs: _fake_generation_result(tmp_path, "cd_cover", Path(cover)),
    )

    assert "cassette" in result.generated_kinds
    assert result.skipped_kinds == ()
    assert calls == ["cassette"]


def test_generate_supported_cover_set_for_row_allows_partial_failure(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(cover_path)

    row = default_media_row(1)
    row.cover_path = str(cover_path)
    row.appearances["cassette"].selected_asset_key = "cassette:1"
    row.appearances["case"].selected_asset_key = "case:4"
    project = ProjectConfig(media_rows=[row])

    def cassette_generator(_cover, **_kwargs):
        raise FileNotFoundError("donor cassette shell was unavailable")

    def case_generator(cover, **_kwargs):
        return _fake_generation_result(tmp_path, "case", Path(cover))

    def vinyl_generator(cover, **_kwargs):
        return _fake_generation_result(tmp_path, "vinyl", Path(cover))

    def jacket_generator(cover, **_kwargs):
        return _fake_generation_result(tmp_path, "jacket", Path(cover))

    def cd_cover_generator(cover, **_kwargs):
        return _fake_generation_result(tmp_path, "cd_cover", Path(cover))

    result = generate_supported_cover_set_for_row(
        project,
        row,
        cassette_donor_inventory_path="",
        cassette_donor_world_path="",
        case_donor_inventory_path="",
        case_donor_world_path="",
        cassette_generator=cassette_generator,
        case_generator=case_generator,
        vinyl_generator=vinyl_generator,
        jacket_generator=jacket_generator,
        cd_cover_generator=cd_cover_generator,
    )

    assert result.generated_kinds == ("case", "vinyl", "jacket", "cd_cover")
    assert result.skipped_kinds == ()
    assert result.failed_kinds == ("cassette",)
    assert row.appearances["cassette"].selected_asset_key == "cassette:1"
    assert row.appearances["cassette"].source == "default"
    assert row.appearances["case"].selected_asset_key.startswith("generated:case:")
    assert row.appearances["vinyl"].selected_asset_key.startswith("generated:vinyl:")
    assert row.appearances["jacket"].selected_asset_key.startswith("generated:jacket:")
    assert row.appearances["cd_cover"].selected_asset_key.startswith("generated:cd_cover:")
    assert [record.kind for record in project.generated_assets] == ["case", "vinyl", "jacket", "cd_cover"]


def test_apply_generated_cover_set_result_applies_worker_records_to_live_project(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(cover_path)

    worker_row = default_media_row(1)
    worker_row.cover_path = str(cover_path)
    worker_project = ProjectConfig(media_rows=[worker_row])
    result = generate_supported_cover_set_for_row(
        worker_project,
        worker_row,
        cassette_donor_inventory_path="",
        cassette_donor_world_path="",
        case_donor_inventory_path="",
        case_donor_world_path="",
        cassette_generator=lambda cover, **_kwargs: _fake_generation_result(tmp_path, "cassette", Path(cover)),
        case_generator=lambda cover, **_kwargs: _fake_generation_result(tmp_path, "case", Path(cover)),
        vinyl_generator=lambda cover, **_kwargs: _fake_generation_result(tmp_path, "vinyl", Path(cover)),
        jacket_generator=lambda cover, **_kwargs: _fake_generation_result(tmp_path, "jacket", Path(cover)),
        cd_cover_generator=lambda cover, **_kwargs: _fake_generation_result(tmp_path, "cd_cover", Path(cover)),
    )

    live_row = default_media_row(1)
    live_row.cover_path = str(cover_path)
    live_project = ProjectConfig(media_rows=[live_row])

    apply_generated_cover_set_result(live_project, live_row, result)

    assert [record.kind for record in live_project.generated_assets] == ["cassette", "case", "vinyl", "jacket", "cd_cover"]
    assert live_row.appearances["cassette"].selected_asset_key.startswith("generated:cassette:")
    assert live_row.appearances["case"].selected_asset_key.startswith("generated:case:")
    assert live_row.appearances["vinyl"].selected_asset_key.startswith("generated:vinyl:")
    assert live_row.appearances["jacket"].selected_asset_key.startswith("generated:jacket:")
    assert live_row.appearances["cd_cover"].selected_asset_key.startswith("generated:cd_cover:")


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
