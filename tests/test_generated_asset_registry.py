from pathlib import Path

from PIL import Image

from new_music_builder.domain.models import GeneratedAssetRecord, ProjectConfig, default_media_row
from new_music_builder.services.generated_asset_registry import (
    can_generate_cover_for_kind,
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
    assert can_generate_cover_for_kind(project, row, "vinyl") is False
    assert can_generate_cover_for_kind(project, row, "cassette") is False

    row.cover_path = str(cover_path)
    assert can_generate_cover_for_kind(project, row, "cassette") is True

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
