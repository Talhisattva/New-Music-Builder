from __future__ import annotations

from pathlib import Path

from new_music_builder.domain.models import (
    ExportPlan,
    ExportTargetPaths,
    ProjectConfig,
    RegisteredAlbum,
    RegisteredContainerVariant,
    RegisteredMediaVariant,
)
from new_music_builder.services.export_registration_plan import build_export_registration_plan

_PLAYABLE_MODEL_SUFFIX: dict[str, str] = {
    "cassette": "Cassette",
    "vinyl": "Vinyl",
    "cd": "CD",
}

_CONTAINER_MODEL_SUFFIX: dict[str, str] = {
    "cassette": "CassetteCase",
    "vinyl": "Jacket",
    "cd": "CDCover",
}

_MODEL_SPECS: dict[str, dict[str, object]] = {
    "cassette": {
        "mesh": "WorldItems/NM_Cassette",
        "texture_dir": "WorldItems/Cassette",
        "scale": "0.0005",
        "attachment": ("0.0 0.10 0.0", "180.0 0.0 0.0"),
    },
    "vinyl": {
        "mesh": "WorldItems/NM_Vinyl",
        "texture_dir": "WorldItems/Vinyl",
        "scale": "0.12",
    },
    "cd": {
        "mesh": "WorldItems/NM_CD",
        "texture_dir": "WorldItems/CD",
        "scale": "0.4",
    },
    "case": {
        "mesh": "WorldItems/NM_CassetteCase",
        "texture_dir": "WorldItems/Cassette",
        "scale": "0.0005",
        "attachment": ("0.0 0.0 0.0", "0.0 0.0 0.0"),
    },
    "jacket": {
        "mesh": "WorldItems/NM_Jacket",
        "texture_dir": "WorldItems/Vinyl",
        "scale": "0.1",
    },
    "cd_cover": {
        "mesh": "WorldItems/NM_CDCover",
        "texture_dir": "WorldItems/CD",
        "scale": "0.06",
    },
}

_PLAYABLE_WEIGHT: dict[str, str] = {
    "cassette": "0.02",
    "vinyl": "0.03",
    "cd": "0.03",
}

_CONTAINER_WEIGHT: dict[str, str] = {
    "cassette": "0.10",
    "vinyl": "0.12",
    "cd": "0.10",
}


def write_export_scripts(
    project: ProjectConfig,
    plan: ExportPlan,
    targets: ExportTargetPaths,
) -> None:
    registration = build_export_registration_plan(project, plan)
    scripts_root = Path(targets.v42) / "media" / "scripts"
    scripts_root.mkdir(parents=True, exist_ok=True)
    file_prefix = f"NMB_{registration.module_id}"
    (scripts_root / f"{file_prefix}_Sounds.txt").write_text(_render_sounds(registration), encoding="utf-8")
    (scripts_root / f"{file_prefix}_Items.txt").write_text(_render_items(registration), encoding="utf-8")
    (scripts_root / f"{file_prefix}_Models.txt").write_text(_render_models(registration), encoding="utf-8")


def _render_sounds(registration) -> str:
    lines = [
        f"module {registration.module_id}",
        "{",
    ]
    for album in registration.albums:
        for side in album.sides:
            for track in side.tracks:
                lines.extend(
                    [
                        f"    sound {track.sound_id}",
                        "    {",
                        "        category = Music,",
                        "        master = Music,",
                        f"        clip {{ file = {track.export_audio_relative_path}, distanceMax = 30, }}",
                        "    }",
                    ]
                )
    lines.append("}")
    return "\n".join(lines) + "\n"


def _render_items(registration) -> str:
    module_name = registration.module_id
    lines = [
        f"module {module_name}",
        "{",
        "    imports",
        "    {",
        "        Base",
        "    }",
        "",
    ]
    for album in registration.albums:
        for variant in album.media_variants:
            model_name = _playable_model_name(album, variant)
            if variant.mode == "single":
                lines.extend(
                        _render_item_block(
                            item_id=variant.full_item_id,
                            display_name=variant.full_display_name,
                            icon_reference=variant.icon_reference,
                            model_name=model_name,
                            module_name=module_name,
                        weight=_PLAYABLE_WEIGHT[variant.media_kind],
                    )
                )
            else:
                for side_name in sorted(variant.item_ids):
                    lines.extend(
                        _render_item_block(
                            item_id=variant.item_ids[side_name],
                            display_name=variant.display_names[side_name],
                            icon_reference=variant.icon_reference,
                            model_name=model_name,
                            module_name=module_name,
                            weight=_PLAYABLE_WEIGHT[variant.media_kind],
                        )
                    )
        for variant in album.container_variants:
            lines.extend(
                _render_item_block(
                    item_id=variant.empty_item_id,
                    display_name=variant.empty_display_name,
                    icon_reference=variant.empty_icon_reference,
                    model_name=_container_model_name(album, variant, "Empty"),
                    module_name=module_name,
                    weight=_CONTAINER_WEIGHT[variant.media_kind],
                )
            )
            lines.extend(
                _render_item_block(
                    item_id=variant.full_item_id,
                    display_name=variant.full_display_name,
                    icon_reference=variant.full_icon_reference,
                    model_name=_container_model_name(album, variant, "Full"),
                    module_name=module_name,
                    weight=_CONTAINER_WEIGHT[variant.media_kind],
                )
            )
    lines.append("}")
    return "\n".join(lines) + "\n"


def _render_item_block(
    *,
    item_id: str,
    display_name: str,
    icon_reference: str,
    model_name: str,
    module_name: str,
    weight: str,
) -> list[str]:
    return [
        f"    item {item_id}",
        "    {",
        "        ItemType = base:normal,",
        "        DisplayCategory = Entertainment,",
        f"        Weight = {weight},",
        f"        Icon = {icon_reference},",
        f"        DisplayName = {display_name},",
        f"        WorldStaticModel = {module_name}.{model_name},",
        "        CanSpawn = true,",
        "    }",
        "",
    ]


def _render_models(registration) -> str:
    module_name = registration.module_id
    lines = [
        f"module {module_name}",
        "{",
        "    imports",
        "    {",
        "        Base",
        "    }",
        "",
    ]
    for album in registration.albums:
        for variant in album.media_variants:
            lines.extend(
                _render_model_block(
                    model_name=_playable_model_name(album, variant),
                    kind=variant.media_kind,
                    texture_reference=variant.model_reference,
                )
            )
        for variant in album.container_variants:
            lines.extend(
                _render_model_block(
                    model_name=_container_model_name(album, variant, "Empty"),
                    kind=variant.container_kind,
                    texture_reference=variant.empty_model_reference,
                )
            )
            lines.extend(
                _render_model_block(
                    model_name=_container_model_name(album, variant, "Full"),
                    kind=variant.container_kind,
                    texture_reference=variant.full_model_reference,
                )
            )
    lines.append("}")
    return "\n".join(lines) + "\n"


def _render_model_block(*, model_name: str, kind: str, texture_reference: str) -> list[str]:
    spec = _MODEL_SPECS[kind]
    lines = [
        f"    model {model_name}",
        "    {",
        f"        mesh = {spec['mesh']},",
        f"        texture = {spec['texture_dir']}/{texture_reference},",
        f"        scale = {spec['scale']},",
    ]
    attachment = spec.get("attachment")
    if isinstance(attachment, tuple):
        offset, rotate = attachment
        lines.extend(
            [
                "        attachment world",
                "        {",
                f"            offset = {offset},",
                f"            rotate = {rotate},",
                "        }",
            ]
        )
    lines.extend(
        [
            "    }",
            "",
        ]
    )
    return lines


def _playable_model_name(album: RegisteredAlbum, variant: RegisteredMediaVariant) -> str:
    return f"{album.album_id}{_PLAYABLE_MODEL_SUFFIX[variant.media_kind]}"


def _container_model_name(album: RegisteredAlbum, variant: RegisteredContainerVariant, state: str) -> str:
    return f"{album.album_id}{_CONTAINER_MODEL_SUFFIX[variant.media_kind]}{state}"
