from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

MediaKind = Literal["cassette", "vinyl", "cd"]
AppearanceKind = Literal["cassette", "vinyl", "cd", "case", "jacket", "cd_cover"]
SpriteMode = Literal["single", "dual"]


@dataclass(slots=True)
class TrackEntry:
    source_path: str = ""
    cached_ogg_path: str = ""
    display_label: str = ""
    duration: str = ""
    conversion_status: str = "pending"


@dataclass(slots=True)
class AppearanceSelection:
    kind: AppearanceKind
    selected_asset_key: str = ""
    source: Literal["default", "custom"] = "default"
    sprite_mode: SpriteMode = "single"
    inventory_full: str = ""
    world_full: str = ""
    inventory_empty: str = ""
    world_empty: str = ""


@dataclass(slots=True)
class MediaRow:
    row_id: int
    media_name: str = "New Album"
    selected_side: Literal["A", "B"] = "A"
    enabled_media: dict[MediaKind, bool] = field(
        default_factory=lambda: {"cassette": True, "vinyl": True, "cd": True}
    )
    cover_path: str = ""
    tracks_a: list[TrackEntry] = field(default_factory=list)
    tracks_b: list[TrackEntry] = field(default_factory=list)
    appearances: dict[AppearanceKind, AppearanceSelection] = field(default_factory=dict)
    expanded: bool = False

    def ensure_appearances(self) -> None:
        for kind in ("cassette", "vinyl", "cd", "case", "jacket", "cd_cover"):
            if kind not in self.appearances:
                self.appearances[kind] = AppearanceSelection(kind=kind)


@dataclass(slots=True)
class ProjectConfig:
    schema_version: int = 1
    mod_name: str = ""
    mod_id: str = ""
    parent_mod_id: str = "NewMusic"
    author: str = ""
    workshop_poster_path: str = ""
    write_mod_name_on_poster: bool = False
    ogg_output_folder: str = ""
    workshop_output_folder: str = ""
    sample_rate: int = 44100
    media_rows: list[MediaRow] = field(default_factory=list)
    custom_assets: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    def ensure_defaults(self) -> None:
        if not self.media_rows:
            self.media_rows = [default_media_row(1)]
        for row in self.media_rows:
            row.ensure_appearances()


@dataclass(slots=True)
class BuildResult:
    output_path: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    sides_built: int = 0
    songs_built: int = 0


@dataclass(slots=True)
class BuildEvent:
    row_id: int
    side: Literal["A", "B"]
    status: str
    message: str
    percent: int = 0


def default_media_row(row_id: int) -> MediaRow:
    row = MediaRow(row_id=row_id, media_name=f"Media Mix {row_id}", expanded=(row_id == 1))
    row.ensure_appearances()
    return row


def project_to_dict(project: ProjectConfig) -> dict[str, Any]:
    return asdict(project)


def _coerce_track(data: dict[str, Any]) -> TrackEntry:
    return TrackEntry(
        source_path=str(data.get("source_path", "")),
        cached_ogg_path=str(data.get("cached_ogg_path", "")),
        display_label=str(data.get("display_label", "")),
        duration=str(data.get("duration", "")),
        conversion_status=str(data.get("conversion_status", "pending")),
    )


def _coerce_appearance(kind: AppearanceKind, data: dict[str, Any] | None) -> AppearanceSelection:
    data = data or {}
    return AppearanceSelection(
        kind=kind,
        selected_asset_key=str(data.get("selected_asset_key", "")),
        source=str(data.get("source", "default")) or "default",
        sprite_mode=str(data.get("sprite_mode", "single")) or "single",
        inventory_full=str(data.get("inventory_full", "")),
        world_full=str(data.get("world_full", "")),
        inventory_empty=str(data.get("inventory_empty", "")),
        world_empty=str(data.get("world_empty", "")),
    )


def project_from_dict(data: dict[str, Any]) -> ProjectConfig:
    rows: list[MediaRow] = []
    for raw_row in data.get("media_rows", []):
        row = MediaRow(
            row_id=int(raw_row.get("row_id", len(rows) + 1)),
            media_name=str(raw_row.get("media_name", f"Media Row {len(rows) + 1}")),
            selected_side=str(raw_row.get("selected_side", "A")) if str(raw_row.get("selected_side", "A")) in {"A", "B"} else "A",
            enabled_media={
                "cassette": bool(raw_row.get("enabled_media", {}).get("cassette", True)),
                "vinyl": bool(raw_row.get("enabled_media", {}).get("vinyl", True)),
                "cd": bool(raw_row.get("enabled_media", {}).get("cd", True)),
            },
            cover_path=str(raw_row.get("cover_path", "")),
            tracks_a=[_coerce_track(item) for item in raw_row.get("tracks_a", [])],
            tracks_b=[_coerce_track(item) for item in raw_row.get("tracks_b", [])],
            appearances={},
            expanded=bool(raw_row.get("expanded", False)),
        )
        for kind in ("cassette", "vinyl", "cd", "case", "jacket", "cd_cover"):
            row.appearances[kind] = _coerce_appearance(kind, raw_row.get("appearances", {}).get(kind))
        row.ensure_appearances()
        rows.append(row)

    project = ProjectConfig(
        schema_version=int(data.get("schema_version", 1)),
        mod_name=str(data.get("mod_name", "")),
        mod_id=str(data.get("mod_id", "")),
        parent_mod_id=str(data.get("parent_mod_id", "NewMusic")),
        author=str(data.get("author", "")),
        workshop_poster_path=str(data.get("workshop_poster_path", "")),
        write_mod_name_on_poster=bool(data.get("write_mod_name_on_poster", False)),
        ogg_output_folder=str(data.get("ogg_output_folder", "")),
        workshop_output_folder=str(data.get("workshop_output_folder", "")),
        sample_rate=int(data.get("sample_rate", 44100)),
        media_rows=rows,
        custom_assets=dict(data.get("custom_assets", {})),
    )
    project.ensure_defaults()
    return project


def next_row_id(project: ProjectConfig) -> int:
    if not project.media_rows:
        return 1
    return max(row.row_id for row in project.media_rows) + 1
