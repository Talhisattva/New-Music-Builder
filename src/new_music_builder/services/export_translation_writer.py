from __future__ import annotations

import json
from pathlib import Path

from new_music_builder.domain.models import ExportPlan, ExportTargetPaths, LuaTrackLabel, ProjectConfig
from new_music_builder.services.export_lua_plan import build_export_lua_plan
SUPPORTED_TRANSLATION_LOCALES: tuple[str, ...] = ("CH", "CN", "DE", "EN", "ES", "FR", "JP", "KO", "PL", "PTBR", "RU")


def write_export_translations(
    project: ProjectConfig,
    plan: ExportPlan,
    targets: ExportTargetPaths,
) -> list[Path]:
    lua_pack = build_export_lua_plan(project, plan)
    track_labels = [
        label
        for album in lua_pack.albums
        for label in album.track_labels
    ]
    translation_root = Path(targets.common) / "media" / "lua" / "shared" / "Translate"
    written_paths: list[Path] = []
    for locale in SUPPORTED_TRANSLATION_LOCALES:
        locale_root = translation_root / locale
        locale_root.mkdir(parents=True, exist_ok=True)
        ui_txt_path = locale_root / f"UI_{locale}.txt"
        ui_json_path = locale_root / "UI.json"
        ui_txt_path.write_text(_render_ui_table(locale, track_labels), encoding="utf-8")
        ui_json_path.write_text(_render_ui_json(track_labels), encoding="utf-8")
        written_paths.extend((ui_txt_path, ui_json_path))
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

def _escape_text_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
