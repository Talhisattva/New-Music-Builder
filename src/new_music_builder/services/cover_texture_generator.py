from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from new_music_builder.domain.models import GeneratedAssetRecord
from new_music_builder.platform.paths import assets_root, generated_textures_root
from new_music_builder.services.generated_asset_registry import build_generated_asset_key, build_generated_cover_id, normalize_cover_path


@dataclass(frozen=True, slots=True)
class CoverGenerationResult:
    record: GeneratedAssetRecord
    successful_outputs: int
    total_outputs: int


def generate_cassette_textures_from_cover(
    cover_path: str | Path,
    *,
    mask_root: Path | None = None,
    output_root: Path | None = None,
) -> CoverGenerationResult:
    normalized_cover = normalize_cover_path(cover_path)
    if not normalized_cover:
        raise FileNotFoundError("Cover image was not provided.")

    source_path = Path(normalized_cover)
    if not source_path.is_file():
        raise FileNotFoundError(f"Cover image was not found: {source_path}")

    resolved_mask_root = mask_root or (assets_root() / "Mask")
    resolved_output_root = output_root or generated_textures_root()
    cover_id = build_generated_cover_id(normalized_cover)
    cassette_output_root = resolved_output_root / "Cassette" / cover_id
    cassette_output_root.mkdir(parents=True, exist_ok=True)

    inventory_mask = resolved_mask_root / "Inventory" / "Cassette" / "Item_NM_Cassette_Mask.png"
    inventory_outer = resolved_mask_root / "Inventory" / "Cassette" / "Item_NM_Cassette_Outer.png"
    world_mask = resolved_mask_root / "World" / "Cassette" / "Cassette_World_Mask.png"
    world_outer = resolved_mask_root / "World" / "Cassette" / "Cassette_World_01.png"
    world_overlay = resolved_mask_root / "World" / "Cassette" / "Cassette_World_Overlay.png"
    world_overlay_detail = resolved_mask_root / "World" / "Cassette" / "Cassette_World_Overlay_02.png"

    inventory_output = cassette_output_root / "Item_NM_Cassette_Generated.png"
    world_output = cassette_output_root / "World_NM_Cassette_Generated.png"

    _render_cassette_inventory(
        source_path=source_path,
        mask_path=inventory_mask,
        outer_path=inventory_outer,
        output_path=inventory_output,
    )
    _render_cassette_world(
        source_path=source_path,
        mask_path=world_mask,
        outer_path=world_outer,
        overlay_paths=(world_overlay, world_overlay_detail),
        output_path=world_output,
    )

    record = GeneratedAssetRecord(
        kind="cassette",
        cover_path=normalized_cover,
        asset_key=build_generated_asset_key("cassette", normalized_cover),
        label=f"{source_path.stem} Generated",
        inventory_full=str(inventory_output),
        world_full=str(world_output),
        source_name=source_path.name,
    )
    return CoverGenerationResult(record=record, successful_outputs=2, total_outputs=2)


def _render_cassette_inventory(
    *,
    source_path: Path,
    mask_path: Path,
    outer_path: Path,
    output_path: Path,
) -> None:
    masked_cover = _build_masked_cover(source_path=source_path, mask_path=mask_path)
    base = Image.new("RGBA", masked_cover.size, (0, 0, 0, 0))
    base.alpha_composite(masked_cover)
    base.alpha_composite(Image.open(outer_path).convert("RGBA"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)


def _render_cassette_world(
    *,
    source_path: Path,
    mask_path: Path,
    outer_path: Path,
    overlay_paths: tuple[Path, ...],
    output_path: Path,
) -> None:
    masked_cover = _build_masked_cover(source_path=source_path, mask_path=mask_path)
    base = Image.new("RGBA", masked_cover.size, (0, 0, 0, 0))
    base.alpha_composite(masked_cover)
    base.alpha_composite(Image.open(outer_path).convert("RGBA"))
    for overlay_path in overlay_paths:
        base.alpha_composite(Image.open(overlay_path).convert("RGBA"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path)


def _build_masked_cover(*, source_path: Path, mask_path: Path) -> Image.Image:
    mask_image = Image.open(mask_path).convert("RGBA")
    fitted_cover = _fit_cover_to_canvas(source_path, mask_image.size)
    alpha_mask = _alpha_mask(mask_image)
    fitted_cover.putalpha(alpha_mask)
    return fitted_cover


def _fit_cover_to_canvas(source_path: Path, size: tuple[int, int]) -> Image.Image:
    source = Image.open(source_path).convert("RGBA")
    fitted = Image.new("RGBA", size, (0, 0, 0, 0))
    contained = source.copy()
    contained.thumbnail(size, Image.Resampling.LANCZOS)
    paste_x = (size[0] - contained.width) // 2
    paste_y = (size[1] - contained.height) // 2
    fitted.paste(contained, (paste_x, paste_y), contained)
    return fitted


def _alpha_mask(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    if alpha.getbbox() is not None:
        return alpha
    return image.convert("L")
