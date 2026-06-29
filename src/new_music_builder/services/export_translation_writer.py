from __future__ import annotations

import json
from pathlib import Path

from new_music_builder.domain.models import ExportPlan, ExportTargetPaths, LuaTrackLabel, ProjectConfig
from new_music_builder.services.export_lua_plan import build_export_lua_plan
from new_music_builder.services.export_registration_plan import build_export_registration_plan

SUPPORTED_TRANSLATION_LOCALES: tuple[str, ...] = ("CN", "DE", "EN", "ES", "FR", "JP", "KO", "PL", "PTBR", "RU")


def write_export_translations(
    project: ProjectConfig,
    plan: ExportPlan,
    targets: ExportTargetPaths,
) -> list[Path]:
    lua_pack = build_export_lua_plan(project, plan)
    registration = build_export_registration_plan(project, plan)
    track_labels = [
        label
        for album in lua_pack.albums
        for label in album.track_labels
    ]
    item_labels = _build_item_name_labels(registration)
    translation_root = Path(targets.common) / "media" / "lua" / "shared" / "Translate"
    written_paths: list[Path] = []
    for locale in SUPPORTED_TRANSLATION_LOCALES:
        locale_root = translation_root / locale
        locale_root.mkdir(parents=True, exist_ok=True)
        ui_txt_path = locale_root / f"UI_{locale}.txt"
        ui_json_path = locale_root / "UI.json"
        item_name_txt_path = locale_root / f"ItemName_{locale}.txt"
        item_name_json_path = locale_root / "ItemName.json"
        ui_txt_path.write_text(_render_ui_table(locale, track_labels), encoding="utf-8")
        ui_json_path.write_text(_render_ui_json(track_labels), encoding="utf-8")
        item_name_txt_path.write_text(_render_item_name_table(locale, item_labels), encoding="utf-8")
        item_name_json_path.write_text(_render_item_name_json(item_labels), encoding="utf-8")
        written_paths.extend((ui_txt_path, ui_json_path, item_name_txt_path, item_name_json_path))
    return written_paths


def _render_ui_table(locale: str, track_labels: list[LuaTrackLabel]) -> str:
    lines = [f"UI_{locale} = {{"]
    lines.extend(
        f'    {label.key} = "{_escape_text_value(label.text)}",'
        for label in track_labels
    )
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def _render_ui_json(track_labels: list[LuaTrackLabel]) -> str:
    payload = {label.key: label.text for label in track_labels}
    return json.dumps(payload, ensure_ascii=False, indent=4) + "\n"


def build_item_name_key(module_id: str, item_id: str) -> str:
    return f"ItemName_{module_id}_{item_id}"


def _build_item_name_labels(registration) -> list[tuple[str, str]]:
    labels: list[tuple[str, str]] = []
    for album in registration.albums:
        for variant in album.media_variants:
            if variant.mode == "single":
                labels.append((build_item_name_key(registration.module_id, variant.full_item_id), variant.full_display_name))
            else:
                for side_name in sorted(variant.item_ids):
                    item_id = variant.item_ids[side_name]
                    labels.append((build_item_name_key(registration.module_id, item_id), variant.display_names[side_name]))
        for variant in album.container_variants:
            labels.append((build_item_name_key(registration.module_id, variant.empty_item_id), variant.empty_display_name))
            labels.append((build_item_name_key(registration.module_id, variant.full_item_id), variant.full_display_name))
    return labels


def _render_item_name_table(locale: str, item_labels: list[tuple[str, str]]) -> str:
    lines = [f"ItemName_{locale} = {{"]
    lines.extend(
        f'    {key} = "{_escape_text_value(text)}",'
        for key, text in item_labels
    )
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def _render_item_name_json(item_labels: list[tuple[str, str]]) -> str:
    payload = {key: text for key, text in item_labels}
    return json.dumps(payload, ensure_ascii=False, indent=4) + "\n"


def _escape_text_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
