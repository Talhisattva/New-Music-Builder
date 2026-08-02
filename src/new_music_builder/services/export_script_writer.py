from __future__ import annotations

import hashlib
import re
from pathlib import Path

from new_music_builder.domain.models import (
    ExportPlan,
    ExportTargetPaths,
    ProjectConfig,
    RegisteredContainerVariant,
    RegisteredMediaVariant,
)
from new_music_builder.services.export_ids import sanitize_export_id
from new_music_builder.services.export_registration_plan import build_export_registration_plan

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

_SCRIPT_DISPLAY_WHITESPACE_RE = re.compile(r"\s+")

_MODEL_NAME_PREFIX: dict[str, str] = {
    "cassette": "Cassette",
    "vinyl": "Vinyl",
    "cd": "CD",
    "case": "CassetteCase",
    "jacket": "Jacket",
    "cd_cover": "CDCover",
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
    rendered_sound_ids: set[str] = set()
    for album in registration.albums:
        for side in album.sides:
            for track in side.tracks:
                sound_ids = track.singles_sound_ids.values() if track.singles_sound_ids else (track.sound_id,)
                for sound_id in sound_ids:
                    if sound_id in rendered_sound_ids:
                        continue
                    rendered_sound_ids.add(sound_id)
                    lines.extend(
                        [
                            f"    sound {sound_id}",
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
    shared_models = _collect_shared_model_names(registration)
    lines = [
        f"module {module_name}",
        "{",
        "    imports { Base }",
    ]
    for album in registration.albums:
        for variant in album.media_variants:
            model_name = _playable_model_name(variant, shared_models)
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
                    model_name=_container_model_name(variant, variant.empty_model_reference, shared_models),
                    module_name=module_name,
                    weight=_CONTAINER_WEIGHT[variant.media_kind],
                )
            )
            lines.extend(
                _render_item_block(
                    item_id=variant.full_item_id,
                    display_name=variant.full_display_name,
                    icon_reference=variant.full_icon_reference,
                    model_name=_container_model_name(variant, variant.full_model_reference, shared_models),
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
        f"        DisplayName = {_pz_safe_display_name(display_name)},",
        f"        WorldStaticModel = {module_name}.{model_name},",
        "        CanSpawn = true,",
        "    }",
    ]


def _pz_safe_display_name(value: str) -> str:
    normalized = str(value).replace(",", " - ")
    return _SCRIPT_DISPLAY_WHITESPACE_RE.sub(" ", normalized).strip()


def _render_models(registration) -> str:
    module_name = registration.module_id
    shared_models = _collect_shared_model_names(registration)
    lines = [
        f"module {module_name}",
        "{",
        "    imports { Base }",
    ]
    rendered: set[str] = set()
    for album in registration.albums:
        for variant in album.media_variants:
            signature = _playable_model_signature(variant)
            if signature not in rendered:
                lines.extend(
                    _render_model_block(
                        model_name=shared_models[signature],
                        kind=variant.media_kind,
                        texture_reference=variant.model_reference,
                    )
                )
                rendered.add(signature)
        for variant in album.container_variants:
            for texture_reference in (variant.empty_model_reference, variant.full_model_reference):
                signature = _container_model_signature(variant, texture_reference)
                if signature not in rendered:
                    lines.extend(
                        _render_model_block(
                            model_name=shared_models[signature],
                            kind=variant.container_kind,
                            texture_reference=texture_reference,
                        )
                    )
                    rendered.add(signature)
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
                f"        attachment world {{ offset = {offset}, rotate = {rotate}, }}",
            ]
        )
    lines.append("    }")
    return lines


def _collect_shared_model_names(registration) -> dict[str, str]:
    shared_models: dict[str, str] = {}
    for album in registration.albums:
        for variant in album.media_variants:
            signature = _playable_model_signature(variant)
            shared_models.setdefault(signature, _shared_model_name(variant.media_kind, variant.model_reference))
        for variant in album.container_variants:
            empty_signature = _container_model_signature(variant, variant.empty_model_reference)
            shared_models.setdefault(
                empty_signature,
                _shared_model_name(variant.container_kind, variant.empty_model_reference),
            )
            full_signature = _container_model_signature(variant, variant.full_model_reference)
            shared_models.setdefault(
                full_signature,
                _shared_model_name(variant.container_kind, variant.full_model_reference),
            )
    return shared_models


def _playable_model_name(
    variant: RegisteredMediaVariant,
    shared_models: dict[str, str],
) -> str:
    return shared_models[_playable_model_signature(variant)]


def _container_model_name(
    variant: RegisteredContainerVariant,
    texture_reference: str,
    shared_models: dict[str, str],
) -> str:
    return shared_models[_container_model_signature(variant, texture_reference)]


def _playable_model_signature(variant: RegisteredMediaVariant) -> str:
    return f"{variant.media_kind}|{variant.model_reference}"


def _container_model_signature(variant: RegisteredContainerVariant, texture_reference: str) -> str:
    return f"{variant.container_kind}|{texture_reference}"


def _shared_model_name(kind: str, texture_reference: str) -> str:
    prefix = _MODEL_NAME_PREFIX[kind]
    normalized = sanitize_export_id(texture_reference, fallback=prefix)[:24]
    digest = hashlib.sha1(f"{kind}:{texture_reference}".encode("utf-8")).hexdigest().upper()[:8]
    return f"Shared{prefix}{normalized}{digest}"
