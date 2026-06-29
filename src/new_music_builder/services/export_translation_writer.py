from __future__ import annotations

import json
from pathlib import Path

from new_music_builder.domain.models import ExportPlan, ExportTargetPaths, LuaTrackLabel, ProjectConfig
from new_music_builder.services.export_lua_plan import build_export_lua_plan


def write_export_translations(
    project: ProjectConfig,
    plan: ExportPlan,
    targets: ExportTargetPaths,
) -> None:
    lua_pack = build_export_lua_plan(project, plan)
    translation_root = Path(targets.common) / "media" / "lua" / "shared" / "Translate" / "EN"
    translation_root.mkdir(parents=True, exist_ok=True)

    track_labels = [
        label
        for album in lua_pack.albums
        for label in album.track_labels
    ]
    (translation_root / "UI_EN.txt").write_text(_render_ui_en(track_labels), encoding="utf-8")
    (translation_root / "UI.json").write_text(_render_ui_json(track_labels), encoding="utf-8")


def _render_ui_en(track_labels: list[LuaTrackLabel]) -> str:
    lines = ["UI_EN = {"]
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
