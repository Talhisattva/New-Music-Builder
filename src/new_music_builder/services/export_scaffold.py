from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from new_music_builder.domain.models import (
    BuildSummaryStats,
    ExportLogLine,
    ExportPlan,
    ExportTargetPaths,
    ProjectConfig,
    ScaffoldResult,
)
from new_music_builder.platform.paths import assets_root
from new_music_builder.services.asset_catalog import AssetEntry
from new_music_builder.services.export_lua_writer import write_export_lua
from new_music_builder.services.export_naming import sanitize_filesystem_component
from new_music_builder.services.export_script_writer import write_export_scripts
from new_music_builder.services.export_texture_writer import write_export_textures
from new_music_builder.services.export_workshop_writer import build_workshop_txt_lines


def validate_export_request(project: ProjectConfig, plan: ExportPlan) -> list[str]:
    errors: list[str] = []
    ogg_folder = (project.ogg_output_folder or "").strip()
    workshop_folder = (project.workshop_output_folder or "").strip()
    mod_name = (project.mod_name or "").strip()
    mod_id = (project.mod_id or "").strip()

    if not ogg_folder:
        errors.append(".ogg Output Folder is required before Build & Export can run.")
    else:
        ogg_path = Path(ogg_folder)
        if not ogg_path.exists() or not ogg_path.is_dir():
            errors.append(".ogg Output Folder must exist and be a valid directory.")

    if not workshop_folder:
        errors.append("Workshop folder is required before Build & Export can run.")
    else:
        workshop_path = Path(workshop_folder)
        if not workshop_path.exists() or not workshop_path.is_dir():
            errors.append("Workshop folder must exist and be a valid directory.")

    if not mod_name:
        errors.append("Mod Name is required before Build & Export can run.")
    if not mod_id:
        errors.append("Mod ID is required before Build & Export can run.")
    elif " " in mod_id:
        errors.append("Mod ID cannot contain spaces.")

    if not plan.sides:
        errors.append("At least one media side with songs is required before Build & Export can run.")

    return errors


def resolve_export_target(plan: ExportPlan, workshop_root: str | Path, *, mod_name: str, mod_id: str) -> ExportTargetPaths:
    workshop_path = Path(workshop_root).resolve()
    outer_folder_name = sanitize_filesystem_component(mod_name, fallback="New Music Pack")
    inner_folder_name = sanitize_filesystem_component(mod_id, fallback="NewMusicPack")
    root = workshop_path / outer_folder_name
    contents = root / "Contents"
    mods_root = contents / "mods"
    mod_base = mods_root / inner_folder_name
    common = mod_base / "common"
    v42 = mod_base / "42"
    audio_root = common / "media" / "sound"
    audio_pack_root = audio_root / inner_folder_name
    return ExportTargetPaths(
        workshop_root=str(workshop_path),
        outer_folder_name=outer_folder_name,
        inner_folder_name=inner_folder_name,
        root=str(root),
        contents=str(contents),
        mods_root=str(mods_root),
        mod_base=str(mod_base),
        common=str(common),
        v42=str(v42),
        audio_root=str(audio_root),
        audio_pack_root=str(audio_pack_root),
    )


def write_export_scaffold(
    project: ProjectConfig,
    plan: ExportPlan,
    targets: ExportTargetPaths,
    asset_catalog: dict[str, list[AssetEntry]],
) -> ScaffoldResult:
    root = Path(targets.root)
    common = Path(targets.common)
    v42 = Path(targets.v42)
    result = ScaffoldResult(output_path=str(root))

    try:
        _ensure_layout(root, common, v42)
        _write_mod_info(project, common / "mod.info")
        _write_mod_info(project, v42 / "mod.info")
        _write_workshop_txt(project, plan, root / "workshop.txt")
        _write_images(project, plan, targets, asset_catalog)
        write_export_scripts(project, plan, targets)
        write_export_lua(project, plan, targets)
        texture_result = write_export_textures(project, plan, targets)
        result.mod_size_text = _format_size_text(_directory_size_bytes(root))
        result.log_lines = _success_log_lines(root, result.mod_size_text, texture_result.written_file_count)
    except Exception as exc:
        result.errors.append(str(exc))
        result.log_lines = _error_log_lines(root, result.errors)

    return result


def _ensure_layout(root: Path, common: Path, v42: Path) -> None:
    (common / "media").mkdir(parents=True, exist_ok=True)
    (v42 / "media" / "lua" / "shared").mkdir(parents=True, exist_ok=True)
    (v42 / "media" / "scripts").mkdir(parents=True, exist_ok=True)


def _write_mod_info(project: ProjectConfig, target: Path) -> None:
    lines = [
        f"name={(project.mod_name or '').strip()}",
        "poster=poster.png",
        f"id={(project.mod_id or '').strip()}",
        "versionMin=42.13",
        "icon=icon.png",
        "description=Generated with New Music Builder",
        f"author={(project.author or '').strip()}",
    ]
    parent_mod_id = (project.parent_mod_id or "").strip()
    if parent_mod_id:
        lines.append(f"require={parent_mod_id}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_workshop_txt(project: ProjectConfig, plan: ExportPlan, target: Path) -> None:
    lines = build_workshop_txt_lines(project, plan)
    target.write_text("\n".join(lines), encoding="utf-8")


def _write_images(
    project: ProjectConfig,
    plan: ExportPlan,
    targets: ExportTargetPaths,
    asset_catalog: dict[str, list[AssetEntry]],
) -> None:
    root = Path(targets.root)
    common = Path(targets.common)
    v42 = Path(targets.v42)

    poster_source = _poster_source(project)
    preview_image = render_square_image(
        poster_source,
        256,
        (project.mod_name or "").strip(),
        add_name_overlay=bool(project.write_mod_name_on_poster),
    )
    poster_image = render_square_image(
        poster_source,
        1024,
        (project.mod_name or "").strip(),
        add_name_overlay=bool(project.write_mod_name_on_poster),
    )

    icon_source = _icon_source(plan, asset_catalog)
    icon_image = render_square_image(icon_source, 32, "", add_name_overlay=False)

    preview_image.save(root / "Preview.png", format="PNG")
    poster_image.save(common / "poster.png", format="PNG")
    poster_image.save(v42 / "poster.png", format="PNG")
    icon_image.save(common / "icon.png", format="PNG")
    icon_image.save(v42 / "icon.png", format="PNG")


def _poster_source(project: ProjectConfig) -> Path | None:
    poster_path = (project.workshop_poster_path or "").strip()
    if not poster_path:
        return None
    candidate = Path(poster_path)
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate.resolve()


def _icon_source(plan: ExportPlan, asset_catalog: dict[str, list[AssetEntry]]) -> Path | None:
    for row in plan.rows:
        if not row.enabled_media.get("cassette", False):
            continue
        inventory_path = row.appearances.cassette.inventory_path
        if inventory_path and Path(inventory_path).exists():
            return Path(inventory_path).resolve()
    cassette_assets = asset_catalog.get("cassette", [])
    if cassette_assets:
        candidate = Path(cassette_assets[0].inventory_path)
        if candidate.exists():
            return candidate.resolve()
    return None


def render_square_image(
    source: Path | None,
    out_size: int,
    mod_name: str,
    *,
    add_name_overlay: bool,
) -> Image.Image:
    image = _square_letterbox(source, out_size)
    if add_name_overlay and mod_name.strip():
        image = _apply_mod_name_overlay(image, mod_name.strip())
    return image


def _square_letterbox(source: Path | None, out_size: int) -> Image.Image:
    if source is None:
        return Image.new("RGBA", (out_size, out_size), (0, 0, 0, 0))
    with Image.open(source) as raw:
        image = raw.convert("RGBA")
        side = max(image.width, image.height)
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        x = (side - image.width) // 2
        y = (side - image.height) // 2
        canvas.paste(image, (x, y), image)
        return canvas.resize((out_size, out_size), Image.Resampling.LANCZOS)


def _load_overlay_font(size: int) -> ImageFont.ImageFont:
    for font_path in _overlay_font_candidate_paths():
        if not font_path.exists():
            continue
        try:
            return ImageFont.truetype(str(font_path), size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _overlay_font_candidate_paths() -> list[Path]:
    configured = os.getenv("NMB_OVERLAY_FONT", "").strip()
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured))

    candidates.extend(
        [
            assets_root() / "fonts" / "Orbitron-VariableFont_wght.ttf",
            Path(r"C:\Windows\Fonts\segoeuib.ttf"),
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
            Path(r"C:\Windows\Fonts\calibrib.ttf"),
            Path(r"C:\Windows\Fonts\impact.ttf"),
            Path(r"C:\Windows\Fonts\segoeui.ttf"),
            Path(r"C:\Windows\Fonts\arial.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
            Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/System/Library/Fonts/Supplemental/Helvetica.ttc"),
            Path("/Library/Fonts/Arial Bold.ttf"),
            Path("/Library/Fonts/Arial.ttf"),
        ]
    )
    return candidates


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    *,
    max_lines: int | None = None,
    truncate_with_ellipsis: bool = False,
) -> list[str]:
    words = text.strip().split()
    if not words:
        return [text.strip() or "Untitled"]

    lines: list[str] = []
    index = 0
    while index < len(words) and (max_lines is None or len(lines) < max_lines):
        line = words[index]
        index += 1
        while index < len(words):
            candidate = f"{line} {words[index]}"
            if draw.textlength(candidate, font=font) <= max_width:
                line = candidate
                index += 1
            else:
                break
        lines.append(line)

    if truncate_with_ellipsis and index < len(words) and lines:
        ellipsis = "..."
        last = lines[-1]
        while last and draw.textlength(last + ellipsis, font=font) > max_width:
            parts = last.split(" ")
            if len(parts) <= 1:
                last = last[:-1]
            else:
                last = " ".join(parts[:-1])
        lines[-1] = (last + ellipsis).strip()

    return lines


def _apply_mod_name_overlay(image: Image.Image, mod_name: str) -> Image.Image:
    output = image.convert("RGBA")
    draw = ImageDraw.Draw(output, "RGBA")
    width, height = output.size
    margin = max(16, width // 24)
    overlay_width = max(width // 3, width // 2)
    overlay_height = max(120, height // 5)
    box = (
        width - overlay_width - margin,
        height - overlay_height - margin,
        width - margin,
        height - margin,
    )
    inner = max(14, width // 40)
    max_width = max(40, (box[2] - box[0]) - inner * 2)
    max_height = max(40, (box[3] - box[1]) - inner * 2)
    stroke = max(2, height // 256)
    line_spacing = max(4, height // 170)

    draw.rounded_rectangle(
        box,
        radius=max(12, width // 48),
        fill=(0, 0, 0, 170),
        outline=(255, 255, 255, 90),
        width=max(1, width // 256),
    )

    lines: list[str] = [mod_name]
    font: ImageFont.ImageFont = ImageFont.load_default()
    min_size = max(14, width // 36)
    for size in range(max(22, width // 10), min_size - 1, -1):
        trial_font = _load_overlay_font(size)
        trial_lines = _wrap_text(
            draw,
            mod_name,
            trial_font,
            max_width,
            max_lines=3,
            truncate_with_ellipsis=True,
        )
        bounds = draw.multiline_textbbox(
            (0, 0),
            "\n".join(trial_lines),
            font=trial_font,
            spacing=line_spacing,
            align="right",
            stroke_width=stroke,
        )
        text_width = bounds[2] - bounds[0]
        text_height = bounds[3] - bounds[1]
        if text_width <= max_width and text_height <= max_height:
            lines = trial_lines
            font = trial_font
            break
    else:
        font = _load_overlay_font(min_size)
        lines = _wrap_text(
            draw,
            mod_name,
            font,
            max_width,
            max_lines=3,
            truncate_with_ellipsis=True,
        )

    rendered = "\n".join(lines)
    bounds = draw.multiline_textbbox(
        (0, 0),
        rendered,
        font=font,
        spacing=line_spacing,
        align="right",
        stroke_width=stroke,
    )
    text_width = bounds[2] - bounds[0]
    text_height = bounds[3] - bounds[1]
    text_x = box[2] - inner - text_width
    text_y = box[1] + ((box[3] - box[1] - text_height) // 2)
    draw.multiline_text(
        (text_x, text_y),
        rendered,
        font=font,
        fill=(255, 255, 255, 245),
        spacing=line_spacing,
        align="right",
        stroke_width=stroke,
        stroke_fill=(0, 0, 0, 235),
    )
    return output


def _directory_size_bytes(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    return total


def _format_size_text(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def _success_log_lines(output_root: Path, mod_size_text: str, texture_file_count: int) -> list[ExportLogLine]:
    timestamp = datetime.now().strftime("%H:%M:%S")
    lines = [
        ExportLogLine(timestamp=timestamp, prefix_text="Exporting scaffold to:", color_role="neutral"),
        ExportLogLine(timestamp="", prefix_text=str(output_root), color_role="neutral"),
    ]
    if texture_file_count:
        lines.append(
            ExportLogLine(
                timestamp="",
                prefix_text=f"Custom textures exported: {texture_file_count}",
                color_role="neutral",
            )
        )
    lines.append(
        ExportLogLine(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            prefix_text="Export scaffold complete.",
            trailing_text=f"Size: {mod_size_text}",
            color_role="done",
        )
    )
    return lines


def _error_log_lines(output_root: Path, errors: list[str]) -> list[ExportLogLine]:
    lines = [
        ExportLogLine(timestamp=datetime.now().strftime("%H:%M:%S"), prefix_text="Export failed.", color_role="error"),
    ]
    if output_root:
        lines.append(ExportLogLine(timestamp="", prefix_text=str(output_root), color_role="error"))
    for error in errors:
        lines.append(ExportLogLine(timestamp="", prefix_text=error, color_role="error"))
    return lines


def build_scaffold_stats(plan: ExportPlan, result: ScaffoldResult) -> BuildSummaryStats:
    return BuildSummaryStats(
        media_rows=0,
        exported_media_rows=0,
        total_sides=0,
        total_songs=0,
        built_songs=0,
        planned_media_rows=plan.stats.planned_media_rows,
        planned_total_sides=plan.stats.planned_total_sides,
        planned_total_songs=plan.stats.planned_total_songs,
        converted=0,
        mod_size_text=result.mod_size_text,
        errors=len(result.errors),
    )


def build_validation_log_lines(errors: list[str]) -> list[ExportLogLine]:
    lines = [
        ExportLogLine(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            prefix_text="Build & Export could not start.",
            color_role="error",
        )
    ]
    for error in errors:
        lines.append(ExportLogLine(timestamp="", prefix_text=error, color_role="error"))
    return lines
