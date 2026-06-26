from pathlib import Path

from PIL import Image

from new_music_builder.domain.models import GeneratedAssetRecord, ProjectConfig, default_media_row
from new_music_builder.services.generated_asset_registry import (
    can_generate_cover_for_row,
    can_generate_cover_for_kind,
    delete_generated_cover_set_files,
    generated_records_for_asset_key,
    remove_generated_cover_set,
    upsert_generated_asset_record,
    visible_generated_entries_for_kind,
)


def test_visible_generated_entries_follow_active_cover_usage(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(cover_path)
    inventory_path = tmp_path / "inventory.png"
    world_path = tmp_path / "world.png"
    Image.new("RGBA", (32, 32), (255, 255, 255, 255)).save(inventory_path)
    Image.new("RGBA", (256, 156), (255, 255, 255, 255)).save(world_path)

    row = default_media_row(1)
    row.cover_path = str(cover_path)
    project = ProjectConfig(media_rows=[row])
    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="cassette",
            cover_path=str(cover_path),
            asset_key="generated:cassette:abc",
            label="cover Generated",
            inventory_full=str(inventory_path),
            world_full=str(world_path),
            source_name="cover.png",
        ),
    )

    visible = visible_generated_entries_for_kind(project, "cassette")
    assert [entry.key for entry in visible] == ["generated:cassette:abc"]

    row.cover_path = ""
    assert visible_generated_entries_for_kind(project, "cassette") == []

    row.cover_path = str(cover_path)
    visible_again = visible_generated_entries_for_kind(project, "cassette")
    assert [entry.key for entry in visible_again] == ["generated:cassette:abc"]


def test_can_generate_cover_for_kind_requires_cassette_cover_and_no_existing_generation(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(cover_path)
    inventory_path = tmp_path / "inventory.png"
    world_path = tmp_path / "world.png"
    Image.new("RGBA", (32, 32), (255, 255, 255, 255)).save(inventory_path)
    Image.new("RGBA", (256, 156), (255, 255, 255, 255)).save(world_path)

    row = default_media_row(1)
    project = ProjectConfig(media_rows=[row])

    assert can_generate_cover_for_kind(project, None, "cassette") is False
    assert can_generate_cover_for_kind(project, row, "case") is False
    assert can_generate_cover_for_kind(project, row, "cassette") is False

    row.cover_path = str(cover_path)
    assert can_generate_cover_for_kind(project, row, "cassette") is True
    assert can_generate_cover_for_kind(project, row, "case") is True

    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="cassette",
            cover_path=str(cover_path),
            asset_key="generated:cassette:abc",
            label="cover Generated",
            inventory_full=str(inventory_path),
            world_full=str(world_path),
            source_name="cover.png",
        ),
    )
    assert can_generate_cover_for_kind(project, row, "cassette") is False
    assert can_generate_cover_for_kind(project, row, "case") is True


def test_can_generate_cover_for_kind_allows_vinyl_cover_and_blocks_existing_generation(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(cover_path)
    inventory_path = tmp_path / "inventory.png"
    world_path = tmp_path / "world.png"
    Image.new("RGBA", (32, 32), (255, 255, 255, 255)).save(inventory_path)
    Image.new("RGBA", (256, 256), (255, 255, 255, 255)).save(world_path)

    row = default_media_row(1)
    project = ProjectConfig(media_rows=[row])

    assert can_generate_cover_for_kind(project, row, "vinyl") is False
    assert can_generate_cover_for_kind(project, row, "jacket") is False

    row.cover_path = str(cover_path)
    assert can_generate_cover_for_kind(project, row, "vinyl") is True
    assert can_generate_cover_for_kind(project, row, "jacket") is True

    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="vinyl",
            cover_path=str(cover_path),
            asset_key="generated:vinyl:abc",
            label="cover Generated",
            inventory_full=str(inventory_path),
            world_full=str(world_path),
            source_name="cover.png",
        ),
    )
    assert can_generate_cover_for_kind(project, row, "vinyl") is False
    assert can_generate_cover_for_kind(project, row, "jacket") is True


def test_can_generate_cover_for_kind_allows_cd_cover_and_blocks_existing_generation(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    inventory_path = tmp_path / "inventory.png"
    world_path = tmp_path / "world.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (255, 255, 255, 255)).save(inventory_path)
    Image.new("RGBA", (256, 256), (255, 255, 255, 255)).save(world_path)

    row = default_media_row(1)
    project = ProjectConfig(media_rows=[row])

    assert can_generate_cover_for_kind(project, row, "cd_cover") is False

    row.cover_path = str(cover_path)
    assert can_generate_cover_for_kind(project, row, "cd_cover") is True

    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="cd_cover",
            cover_path=str(cover_path),
            asset_key="generated:cd_cover:abc",
            label="cover Generated",
            inventory_full=str(inventory_path),
            world_full=str(world_path),
            source_name="cover.png",
        ),
    )
    assert can_generate_cover_for_kind(project, row, "cd_cover") is False


def test_can_generate_cover_for_row_requires_valid_cover_and_any_missing_supported_kind(tmp_path: Path) -> None:
    cover_path = tmp_path / "cover.png"
    inventory_path = tmp_path / "inventory.png"
    world_path = tmp_path / "world.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(cover_path)
    Image.new("RGBA", (32, 32), (255, 255, 255, 255)).save(inventory_path)
    Image.new("RGBA", (256, 256), (255, 255, 255, 255)).save(world_path)

    row = default_media_row(1)
    project = ProjectConfig(media_rows=[row])

    assert can_generate_cover_for_row(project, None) is False
    assert can_generate_cover_for_row(project, row) is False

    row.cover_path = str(cover_path)
    assert can_generate_cover_for_row(project, row) is True

    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="cassette",
            cover_path=str(cover_path),
            asset_key="generated:cassette:abc",
            label="cover Generated",
            inventory_full=str(inventory_path),
            world_full=str(world_path),
            source_name="cover.png",
        ),
    )
    assert can_generate_cover_for_row(project, row) is True

    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="case",
            cover_path=str(cover_path),
            asset_key="generated:case:abc",
            label="cover Generated",
            inventory_full=str(inventory_path),
            world_full=str(world_path),
            source_name="cover.png",
        ),
    )
    assert can_generate_cover_for_row(project, row) is True

    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="vinyl",
            cover_path=str(cover_path),
            asset_key="generated:vinyl:abc",
            label="cover Generated",
            inventory_full=str(inventory_path),
            world_full=str(world_path),
            source_name="cover.png",
        ),
    )
    assert can_generate_cover_for_row(project, row) is True

    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="jacket",
            cover_path=str(cover_path),
            asset_key="generated:jacket:abc",
            label="cover Generated",
            inventory_full=str(inventory_path),
            world_full=str(world_path),
            source_name="cover.png",
        ),
    )
    assert can_generate_cover_for_row(project, row) is True

    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="cd_cover",
            cover_path=str(cover_path),
            asset_key="generated:cd_cover:abc",
            label="cover Generated",
            inventory_full=str(inventory_path),
            world_full=str(world_path),
            source_name="cover.png",
        ),
    )
    assert can_generate_cover_for_row(project, row) is False


def test_remove_generated_cover_set_removes_all_records_for_same_cover(tmp_path: Path) -> None:
    first_cover = tmp_path / "cover-a.png"
    second_cover = tmp_path / "cover-b.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(first_cover)
    Image.new("RGBA", (300, 300), (0, 255, 0, 255)).save(second_cover)

    project = ProjectConfig()
    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="cassette",
            cover_path=str(first_cover),
            asset_key="generated:cassette:first",
            label="first Generated",
            inventory_full="C:/generated/first-inventory.png",
            world_full="C:/generated/first-world.png",
            source_name="cover-a.png",
        ),
    )
    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="case",
            cover_path=str(first_cover),
            asset_key="generated:case:first",
            label="first Case",
            inventory_full="C:/generated/first-case-inventory.png",
            world_full="C:/generated/first-case-world.png",
            source_name="cover-a.png",
        ),
    )
    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="jacket",
            cover_path=str(first_cover),
            asset_key="generated:jacket:first",
            label="first Jacket",
            inventory_full="C:/generated/first-jacket-inventory.png",
            world_full="C:/generated/first-jacket-world.png",
            source_name="cover-a.png",
        ),
    )
    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="cd_cover",
            cover_path=str(first_cover),
            asset_key="generated:cd_cover:first",
            label="first CD Cover",
            inventory_full="C:/generated/first-cd-cover-inventory.png",
            world_full="C:/generated/first-cd-cover-world.png",
            source_name="cover-a.png",
        ),
    )
    upsert_generated_asset_record(
        project,
        GeneratedAssetRecord(
            kind="cassette",
            cover_path=str(second_cover),
            asset_key="generated:cassette:second",
            label="second Generated",
            inventory_full="C:/generated/second-inventory.png",
            world_full="C:/generated/second-world.png",
            source_name="cover-b.png",
        ),
    )

    cover_set = generated_records_for_asset_key(project, "generated:cassette:first")
    assert {record.asset_key for record in cover_set} == {
        "generated:cassette:first",
        "generated:case:first",
        "generated:jacket:first",
        "generated:cd_cover:first",
    }

    removed = remove_generated_cover_set(project, "generated:cassette:first")

    assert {record.asset_key for record in removed} == {
        "generated:cassette:first",
        "generated:case:first",
        "generated:jacket:first",
        "generated:cd_cover:first",
    }
    assert [record.asset_key for record in project.generated_assets] == ["generated:cassette:second"]


def test_delete_generated_cover_set_files_removes_files_and_empty_directories(tmp_path: Path) -> None:
    managed_root = tmp_path / "Generated Textures"
    cover_dir = managed_root / "Cassette" / "abc123"
    cover_dir.mkdir(parents=True)
    inventory_path = cover_dir / "inventory.png"
    world_path = cover_dir / "world.png"
    inventory_path.write_bytes(b"inventory")
    world_path.write_bytes(b"world")

    deleted_count = delete_generated_cover_set_files(
        [
            GeneratedAssetRecord(
                kind="cassette",
                cover_path="C:/covers/cover.png",
                asset_key="generated:cassette:abc123",
                label="cover Generated",
                inventory_full=str(inventory_path),
                world_full=str(world_path),
                source_name="cover.png",
            )
        ],
        managed_root=managed_root,
    )

    assert deleted_count == 2
    assert inventory_path.exists() is False
    assert world_path.exists() is False
    assert cover_dir.exists() is False


def test_delete_generated_cover_set_files_ignores_missing_and_outside_root(tmp_path: Path) -> None:
    managed_root = tmp_path / "Generated Textures"
    managed_root.mkdir(parents=True)
    outside_path = tmp_path / "outside.png"
    outside_path.write_bytes(b"outside")

    deleted_count = delete_generated_cover_set_files(
        [
            GeneratedAssetRecord(
                kind="cassette",
                cover_path="C:/covers/cover.png",
                asset_key="generated:cassette:abc123",
                label="cover Generated",
                inventory_full=str(outside_path),
                world_full=str(managed_root / "missing-world.png"),
                source_name="cover.png",
            )
        ],
        managed_root=managed_root,
    )

    assert deleted_count == 0
    assert outside_path.exists() is True
