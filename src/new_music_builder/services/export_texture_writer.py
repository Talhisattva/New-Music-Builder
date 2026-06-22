from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from new_music_builder.domain.models import ExportPlan, ExportTargetPaths, ProjectConfig, TextureExportResult
from new_music_builder.services.export_ids import sanitize_export_id
from new_music_builder.services.export_texture_contract import (
    build_cover_texture_decision,
    exported_inventory_texture_filename,
    exported_world_texture_relative_path,
    normalized_source_identity,
)

_PLAYABLE_KINDS: tuple[str, ...] = ("cassette", "vinyl", "cd")
_CONTAINER_MEDIA_KINDS: tuple[str, ...] = ("cassette", "vinyl", "cd")
_CONTAINER_KIND_BY_MEDIA: dict[str, str] = {
    "cassette": "case",
    "vinyl": "jacket",
    "cd": "cd_cover",
}


@dataclass(slots=True)
class _TextureWriteTask:
    source_path: str
    target_relative_path: str
    transform_kind: str
    description: str


def write_export_textures(project: ProjectConfig, plan: ExportPlan, targets: ExportTargetPaths) -> TextureExportResult:
    module_id = sanitize_export_id(project.mod_id or "NewMusicPack", fallback="NewMusicPack")
    textures_root = Path(targets.common) / "media" / "textures"
    tasks: OrderedDict[str, _TextureWriteTask] = OrderedDict()

    for row in plan.rows:
        _append_row_texture_tasks(tasks, module_id, row)

    for task in tasks.values():
        source = _require_source_path(task.source_path, task.description)
        target = textures_root / Path(task.target_relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        _render_texture_file(source, target, task.transform_kind)

    return TextureExportResult(written_file_count=len(tasks))


def _append_row_texture_tasks(tasks: OrderedDict[str, _TextureWriteTask], module_id: str, row: PlannedMediaRow) -> None:
    album_id = row.export_id or sanitize_export_id(row.media_name, fallback=f"MediaRow{row.row_id}")

    for media_kind in _PLAYABLE_KINDS:
        if not row.enabled_media.get(media_kind, False):
            continue
        appearance = row.appearances.for_kind(media_kind)
        if appearance.source != "custom":
            continue
        _add_task(
            tasks,
            source_path=appearance.inventory_path,
            target_relative_path=exported_inventory_texture_filename(media_kind, module_id, album_id),
            transform_kind="inventory_32",
            description=f"{row.media_name} {media_kind} inventory",
        )
        _add_task(
            tasks,
            source_path=appearance.world_path,
            target_relative_path=exported_world_texture_relative_path(media_kind, module_id, album_id),
            transform_kind="world_cassette_playable" if media_kind == "cassette" else "world_square_256",
            description=f"{row.media_name} {media_kind} world",
        )

    for media_kind in _CONTAINER_MEDIA_KINDS:
        if not row.enabled_media.get(media_kind, False):
            continue
        appearance_kind = _CONTAINER_KIND_BY_MEDIA[media_kind]
        appearance = row.appearances.for_kind(appearance_kind)
        if appearance.source != "custom":
            continue
        _add_task(
            tasks,
            source_path=appearance.inventory_path,
            target_relative_path=exported_inventory_texture_filename(appearance_kind, module_id, album_id),
            transform_kind="inventory_32",
            description=f"{row.media_name} {appearance_kind} inventory",
        )
        if appearance.inventory_empty_path and normalized_source_identity(appearance.inventory_empty_path) != normalized_source_identity(appearance.inventory_path):
            _add_task(
                tasks,
                source_path=appearance.inventory_empty_path,
                target_relative_path=exported_inventory_texture_filename(appearance_kind, module_id, album_id, empty=True),
                transform_kind="inventory_32",
                description=f"{row.media_name} {appearance_kind} inventory empty",
            )
        _add_task(
            tasks,
            source_path=appearance.world_path,
            target_relative_path=exported_world_texture_relative_path(appearance_kind, module_id, album_id),
            transform_kind="world_square_1024" if appearance_kind == "jacket" else "world_square_256",
            description=f"{row.media_name} {appearance_kind} world",
        )
        if appearance.world_empty_path and normalized_source_identity(appearance.world_empty_path) != normalized_source_identity(appearance.world_path):
            _add_task(
                tasks,
                source_path=appearance.world_empty_path,
                target_relative_path=exported_world_texture_relative_path(appearance_kind, module_id, album_id, empty=True),
                transform_kind="world_square_1024" if appearance_kind == "jacket" else "world_square_256",
                description=f"{row.media_name} {appearance_kind} world empty",
            )

    cover_decision = build_cover_texture_decision(module_id, album_id, row)
    if cover_decision.base_source_is_custom and cover_decision.base_source_path:
        _add_task(
            tasks,
            source_path=cover_decision.base_source_path,
            target_relative_path=cover_decision.base_texture_relative_path,
            transform_kind=cover_decision.base_transform_kind,
            description=f"{row.media_name} cover",
        )
    if cover_decision.export_hr_cover and cover_decision.row_cover_source_path:
        _add_task(
            tasks,
            source_path=cover_decision.row_cover_source_path,
            target_relative_path=exported_world_texture_relative_path("jacket", module_id, album_id, hr=True),
            transform_kind="world_square_1024",
            description=f"{row.media_name} HR cover",
        )


def _add_task(
    tasks: OrderedDict[str, _TextureWriteTask],
    *,
    source_path: str,
    target_relative_path: str,
    transform_kind: str,
    description: str,
) -> None:
    if not source_path:
        return
    existing = tasks.get(target_relative_path)
    if existing is not None:
        if normalized_source_identity(existing.source_path) != normalized_source_identity(source_path):
            raise ValueError(f"Conflicting texture sources for {target_relative_path}.")
        return
    tasks[target_relative_path] = _TextureWriteTask(
        source_path=source_path,
        target_relative_path=target_relative_path,
        transform_kind=transform_kind,
        description=description,
    )


def _require_source_path(path: str, description: str) -> Path:
    candidate = Path(path)
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(f"Missing custom texture source for {description}: {path}")
    return candidate.resolve()


def _render_texture_file(source: Path, target: Path, transform_kind: str) -> None:
    if transform_kind == "world_cassette_playable":
        image = _render_cassette_world_image(source)
    elif transform_kind == "world_square_1024":
        image = _render_square_canvas(source, 1024)
    else:
        output_size = 32 if transform_kind == "inventory_32" else 256
        image = _render_square_canvas(source, output_size)
    image.save(target, format="PNG")


def _render_square_canvas(source: Path, out_size: int) -> Image.Image:
    with Image.open(source) as raw:
        image = raw.convert("RGBA")
        side = max(image.width, image.height)
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        x = (side - image.width) // 2
        y = (side - image.height) // 2
        canvas.paste(image, (x, y), image)
        return canvas.resize((out_size, out_size), Image.Resampling.LANCZOS)


def _render_cassette_world_image(source: Path) -> Image.Image:
    square = _render_square_canvas(source, 256)
    top = (256 - 156) // 2
    return square.crop((0, top, 256, top + 156))
