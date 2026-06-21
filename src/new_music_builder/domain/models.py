from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

MediaKind = Literal["cassette", "vinyl", "cd"]
AppearanceKind = Literal["cassette", "vinyl", "cd", "case", "jacket", "cd_cover"]
SpriteMode = Literal["single", "dual"]
SongSortColumn = Literal["ogg", "song_name", "length"]
SongSortDirection = Literal["asc", "desc"]
ConversionSongStatus = Literal["queued", "converting", "done"]
ExportLogColorRole = Literal["neutral", "queued", "converting", "done"]


@dataclass(slots=True)
class TrackEntry:
    source_path: str = ""
    cached_ogg_path: str = ""
    display_label: str = ""
    duration: str = ""
    conversion_status: str = "pending"


@dataclass(slots=True)
class SongSortState:
    column: SongSortColumn | None = None
    direction: SongSortDirection = "asc"


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
    preview_mode: Literal["inventory", "world"] = "inventory"
    enabled_media: dict[MediaKind, bool] = field(
        default_factory=lambda: {"cassette": True, "vinyl": True, "cd": True}
    )
    cover_path: str = ""
    tracks_a: list[TrackEntry] = field(default_factory=list)
    tracks_b: list[TrackEntry] = field(default_factory=list)
    song_sort_a: SongSortState = field(default_factory=SongSortState)
    song_sort_b: SongSortState = field(default_factory=SongSortState)
    appearances: dict[AppearanceKind, AppearanceSelection] = field(default_factory=dict)
    expanded: bool = False

    def ensure_appearances(self) -> None:
        for kind in ("cassette", "vinyl", "cd", "case", "jacket", "cd_cover"):
            if kind not in self.appearances:
                self.appearances[kind] = AppearanceSelection(kind=kind)

    def song_sort_for_side(self, side: Literal["A", "B"]) -> SongSortState:
        return self.song_sort_a if side == "A" else self.song_sort_b


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


@dataclass(slots=True)
class ConversionSongProgress:
    song_label: str
    queue_index: int
    percent: int = 0
    status: ConversionSongStatus = "queued"
    size_label: str = ""


@dataclass(slots=True)
class ConversionSideGroup:
    row_id: int
    side: Literal["A", "B"]
    display_label: str
    songs: list[ConversionSongProgress] = field(default_factory=list)


@dataclass(slots=True)
class ExportLogLine:
    timestamp: str
    prefix_text: str = ""
    subject_text: str = ""
    trailing_text: str = ""
    size_text: str = ""
    color_role: ExportLogColorRole = "neutral"


@dataclass(slots=True)
class ExportRunHistoryEntry:
    divider_label: str
    lines: list[ExportLogLine] = field(default_factory=list)


@dataclass(slots=True)
class ExportRunState:
    ordered_groups: list[ConversionSideGroup] = field(default_factory=list)
    active_group_index: int | None = None
    active_song_index: int | None = None
    current_run_log_lines: list[ExportLogLine] = field(default_factory=list)
    history_runs: list[ExportRunHistoryEntry] = field(default_factory=list)
    output_path: str = ""


@dataclass(slots=True)
class GeneratedPreviewCell:
    label_text: str
    section_text: str
    song_count: int = 0
    duration_text: str = "00:00:00"
    cover_path: str = ""
    slot_paths: tuple[str | None, ...] = ()


@dataclass(slots=True)
class GeneratedPreviewRow:
    row_id: int
    side: Literal["A", "B"]
    inventory_cell: GeneratedPreviewCell
    world_cell: GeneratedPreviewCell


@dataclass(slots=True)
class BuildSummaryStats:
    media_rows: int = 0
    exported_media_rows: int = 0
    total_sides: int = 0
    total_songs: int = 0
    converted: int = 0
    mod_size_text: str = "0 KB"
    errors: int = 0


@dataclass(slots=True)
class BuildPreviewScenario:
    queue_groups: list[ConversionSideGroup] = field(default_factory=list)
    log_lines: list[ExportLogLine] = field(default_factory=list)
    preview_rows: list[GeneratedPreviewRow] = field(default_factory=list)
    stats: BuildSummaryStats = field(default_factory=BuildSummaryStats)


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


def _coerce_song_sort(data: dict[str, Any] | None) -> SongSortState:
    data = data or {}
    raw_column = data.get("column")
    raw_direction = str(data.get("direction", "asc"))
    return SongSortState(
        column=str(raw_column) if raw_column in {"ogg", "song_name", "length"} else None,
        direction=raw_direction if raw_direction in {"asc", "desc"} else "asc",
    )


def project_from_dict(data: dict[str, Any]) -> ProjectConfig:
    rows: list[MediaRow] = []
    for raw_row in data.get("media_rows", []):
        row = MediaRow(
            row_id=int(raw_row.get("row_id", len(rows) + 1)),
            media_name=str(raw_row.get("media_name", f"Media Row {len(rows) + 1}")),
            selected_side=str(raw_row.get("selected_side", "A")) if str(raw_row.get("selected_side", "A")) in {"A", "B"} else "A",
            preview_mode=(
                str(raw_row.get("preview_mode", "inventory"))
                if str(raw_row.get("preview_mode", "inventory")) in {"inventory", "world"}
                else "inventory"
            ),
            enabled_media={
                "cassette": bool(raw_row.get("enabled_media", {}).get("cassette", True)),
                "vinyl": bool(raw_row.get("enabled_media", {}).get("vinyl", True)),
                "cd": bool(raw_row.get("enabled_media", {}).get("cd", True)),
            },
            cover_path=str(raw_row.get("cover_path", "")),
            tracks_a=[_coerce_track(item) for item in raw_row.get("tracks_a", [])],
            tracks_b=[_coerce_track(item) for item in raw_row.get("tracks_b", [])],
            song_sort_a=_coerce_song_sort(raw_row.get("song_sort_a")),
            song_sort_b=_coerce_song_sort(raw_row.get("song_sort_b")),
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
