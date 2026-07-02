from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from new_music_builder.services.audio_profile import DEFAULT_COMPRESSION_QUALITY, snap_compression_quality

MediaKind = Literal["cassette", "vinyl", "cd"]
AppearanceKind = Literal["cassette", "vinyl", "cd", "case", "jacket", "cd_cover"]
SpriteMode = Literal["single", "dual"]
RegistrationMode = Literal["single", "split"]
SongSortColumn = Literal["ogg", "song_name", "length"]
SongSortDirection = Literal["asc", "desc"]
ConversionSongStatus = Literal["queued", "converting", "done", "failed"]
ExportLogColorRole = Literal["neutral", "queued", "converting", "done", "error"]
AudioBuildAction = Literal["copy_ogg", "convert_to_ogg", "error"]
AudioRunEventKind = Literal[
    "run_preparing",
    "scaffold_started",
    "scaffold_completed",
    "run_aborted",
    "run_failed",
    "side_started",
    "song_started",
    "song_progress",
    "song_succeeded",
    "song_failed",
    "side_completed",
    "run_completed",
]

_APPEARANCE_KINDS: tuple[AppearanceKind, ...] = ("cassette", "vinyl", "cd", "case", "jacket", "cd_cover")


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
class GeneratedAssetRecord:
    kind: AppearanceKind
    cover_path: str = ""
    asset_key: str = ""
    label: str = ""
    inventory_full: str = ""
    world_full: str = ""
    source_name: str = ""


@dataclass(slots=True)
class MediaRow:
    row_id: int
    media_name: str = "New Album"
    selected_side: Literal["A", "B"] = "A"
    preview_mode: Literal["inventory", "world"] = "inventory"
    enabled_media: dict[MediaKind, bool] = field(
        default_factory=lambda: {"cassette": True, "vinyl": True, "cd": True}
    )
    media_modes: dict[MediaKind, RegistrationMode] = field(
        default_factory=lambda: {"cassette": "split", "vinyl": "split", "cd": "single"}
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
    write_mod_name_on_poster: bool = True
    ogg_output_folder: str = ""
    workshop_output_folder: str = ""
    sample_rate: int = 44100
    compression_quality: float = DEFAULT_COMPRESSION_QUALITY
    reencode_existing_ogg: bool = True
    automatic_textures_enabled: bool = True
    media_rows: list[MediaRow] = field(default_factory=list)
    custom_assets: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    generated_assets: list[GeneratedAssetRecord] = field(default_factory=list)

    def ensure_defaults(self) -> None:
        self.sample_rate = _coerce_int(self.sample_rate, 44100, minimum=1)
        self.compression_quality = snap_compression_quality(self.compression_quality)
        self.custom_assets = _coerce_custom_assets(self.custom_assets)
        self.generated_assets = _coerce_generated_assets(self.generated_assets)
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
    empty_slot_paths: tuple[str | None, ...] = ()


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
    built_songs: int = 0
    planned_media_rows: int = 0
    planned_total_sides: int = 0
    planned_total_songs: int = 0
    converted: int = 0
    mod_size_text: str = "0 KB"
    errors: int = 0


@dataclass(slots=True)
class BuildPreviewScenario:
    queue_groups: list[ConversionSideGroup] = field(default_factory=list)
    log_lines: list[ExportLogLine] = field(default_factory=list)
    preview_rows: list[GeneratedPreviewRow] = field(default_factory=list)
    stats: BuildSummaryStats = field(default_factory=BuildSummaryStats)


@dataclass(slots=True)
class ResolvedAppearance:
    kind: AppearanceKind
    selected_asset_key: str = ""
    source: Literal["default", "custom"] = "default"
    inventory_path: str = ""
    world_path: str = ""
    sprite_mode: SpriteMode = "single"
    inventory_empty_path: str = ""
    world_empty_path: str = ""


@dataclass(slots=True)
class ResolvedAppearanceSet:
    cassette: ResolvedAppearance = field(default_factory=lambda: ResolvedAppearance(kind="cassette"))
    vinyl: ResolvedAppearance = field(default_factory=lambda: ResolvedAppearance(kind="vinyl"))
    cd: ResolvedAppearance = field(default_factory=lambda: ResolvedAppearance(kind="cd"))
    case: ResolvedAppearance = field(default_factory=lambda: ResolvedAppearance(kind="case"))
    jacket: ResolvedAppearance = field(default_factory=lambda: ResolvedAppearance(kind="jacket"))
    cd_cover: ResolvedAppearance = field(default_factory=lambda: ResolvedAppearance(kind="cd_cover"))

    def for_kind(self, kind: AppearanceKind) -> ResolvedAppearance:
        return getattr(self, kind)


@dataclass(slots=True)
class PlannedTrack:
    track_number: int
    source_path: str
    display_label: str
    duration_text: str
    duration_seconds: int
    needs_conversion: bool
    export_file_name: str = ""
    export_relative_path: str = ""
    track_id: str = ""
    sound_id: str = ""


@dataclass(slots=True)
class PlannedSide:
    row_id: int
    side: Literal["A", "B"]
    media_name: str
    cover_path: str
    side_id: str = ""
    export_folder_name: str = ""
    export_relative_dir: str = ""
    tracks: list[PlannedTrack] = field(default_factory=list)

    @property
    def song_count(self) -> int:
        return len(self.tracks)

    @property
    def duration_seconds(self) -> int:
        return sum(track.duration_seconds for track in self.tracks)

    @property
    def duration_text(self) -> str:
        total_seconds = self.duration_seconds
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def display_label(self) -> str:
        return f"{self.media_name}\n{self.side}-SIDE"


@dataclass(slots=True)
class PlannedMediaRow:
    row_id: int
    media_name: str
    cover_path: str
    export_id: str = ""
    enabled_media: dict[MediaKind, bool] = field(default_factory=dict)
    media_modes: dict[MediaKind, RegistrationMode] = field(default_factory=dict)
    appearances: ResolvedAppearanceSet = field(default_factory=ResolvedAppearanceSet)
    sides: list[PlannedSide] = field(default_factory=list)


@dataclass(slots=True)
class ExportPlan:
    rows: list[PlannedMediaRow] = field(default_factory=list)
    sides: list[PlannedSide] = field(default_factory=list)
    stats: BuildSummaryStats = field(default_factory=BuildSummaryStats)


@dataclass(slots=True)
class RegisteredTrack:
    sequence_number: int
    track_id: str
    sound_id: str
    display_label: str
    export_audio_relative_path: str


@dataclass(slots=True)
class RegisteredSide:
    side: Literal["A", "B"]
    side_id: str
    start_track_number: int
    end_track_number: int
    tracks: list[RegisteredTrack] = field(default_factory=list)


@dataclass(slots=True)
class RegisteredMediaVariant:
    media_kind: MediaKind
    mode: RegistrationMode
    full_item_id: str = ""
    full_display_name: str = ""
    item_ids: dict[Literal["A", "B"], str] = field(default_factory=dict)
    display_names: dict[Literal["A", "B"], str] = field(default_factory=dict)
    icon_reference: str = ""
    model_reference: str = ""
    selected_asset_key: str = ""
    asset_source: Literal["default", "custom"] = "default"


@dataclass(slots=True)
class RegisteredContainerVariant:
    media_kind: MediaKind
    container_kind: AppearanceKind
    empty_item_id: str
    full_item_id: str
    empty_display_name: str
    full_display_name: str
    empty_icon_reference: str = ""
    full_icon_reference: str = ""
    empty_model_reference: str = ""
    full_model_reference: str = ""
    selected_asset_key: str = ""
    asset_source: Literal["default", "custom"] = "default"


@dataclass(slots=True)
class RegisteredAlbum:
    row_id: int
    album_id: str
    title: str
    module_id: str
    mode: RegistrationMode
    sound_prefix: str
    sides: list[RegisteredSide] = field(default_factory=list)
    media_variants: list[RegisteredMediaVariant] = field(default_factory=list)
    container_variants: list[RegisteredContainerVariant] = field(default_factory=list)


@dataclass(slots=True)
class ExportRegistrationPlan:
    module_id: str
    albums: list[RegisteredAlbum] = field(default_factory=list)


@dataclass(slots=True)
class LuaAlbumMediaItems:
    full: str = ""
    a: str = ""
    b: str = ""
    container_empty: str = ""
    container_full: str = ""


@dataclass(slots=True)
class LuaAlbumMediaRegistration:
    media_kind: MediaKind
    mode: Literal["full", "split"]
    items: LuaAlbumMediaItems = field(default_factory=LuaAlbumMediaItems)
    range_a: tuple[int, int] | None = None
    range_b: tuple[int, int] | None = None


@dataclass(slots=True)
class LuaCoverGroup:
    texture: str
    include_playable: tuple[MediaKind, ...] = ()
    include_containers: tuple[MediaKind, ...] = ()
    include_empty_containers: tuple[MediaKind, ...] = ()


@dataclass(slots=True)
class LuaTrackLabel:
    key: str
    text: str


@dataclass(slots=True)
class LuaAlbumRegistration:
    album_id: str
    title: str
    module_id: str
    sound_prefix: str
    table_name: str
    require_name: str
    track_labels: list[LuaTrackLabel] = field(default_factory=list)
    media: list[LuaAlbumMediaRegistration] = field(default_factory=list)
    cover_groups: list[LuaCoverGroup] = field(default_factory=list)


@dataclass(slots=True)
class LuaPackRegistration:
    module_id: str
    bootstrap_require_names: list[str] = field(default_factory=list)
    album_table_names: list[str] = field(default_factory=list)
    albums: list[LuaAlbumRegistration] = field(default_factory=list)


@dataclass(slots=True)
class PlannedAudioWorkItem:
    row_id: int
    side: Literal["A", "B"]
    track_number: int
    display_label: str
    duration_seconds: int
    source_path: str
    target_relative_path: str
    target_path: str
    action: AudioBuildAction
    reason: str
    sample_rate: int
    compression_quality: float


@dataclass(slots=True)
class AudioWorkPlan:
    items: list[PlannedAudioWorkItem] = field(default_factory=list)

    @property
    def copy_count(self) -> int:
        return sum(1 for item in self.items if item.action == "copy_ogg")

    @property
    def convert_count(self) -> int:
        return sum(1 for item in self.items if item.action == "convert_to_ogg")

    @property
    def error_count(self) -> int:
        return sum(1 for item in self.items if item.action == "error")


@dataclass(slots=True)
class AudioRunEvent:
    kind: AudioRunEventKind
    row_id: int
    side: Literal["A", "B"]
    song_index: int | None = None
    track_number: int | None = None
    display_label: str = ""
    cached_ogg_path: str = ""
    percent: int = 0
    message: str = ""
    size_text: str = ""


@dataclass(slots=True)
class AudioRunResult:
    output_path: str = ""
    successful_sides: list[tuple[int, Literal["A", "B"]]] = field(default_factory=list)
    built_song_count: int = 0
    failed_song_count: int = 0
    converted_count: int = 0
    errors: list[str] = field(default_factory=list)
    fatal_error: str = ""
    aborted: bool = False
    abort_message: str = ""
    mod_size_text: str = "0 KB"


@dataclass(slots=True)
class ExportTargetPaths:
    workshop_root: str
    outer_folder_name: str
    inner_folder_name: str
    root: str
    contents: str
    mods_root: str
    mod_base: str
    common: str
    v42: str
    audio_root: str
    audio_pack_root: str


@dataclass(slots=True)
class ScaffoldResult:
    output_path: str = ""
    mod_size_text: str = "0 KB"
    errors: list[str] = field(default_factory=list)
    log_lines: list[ExportLogLine] = field(default_factory=list)


@dataclass(slots=True)
class TextureExportResult:
    written_file_count: int = 0


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


def _coerce_int(value: Any, default: int, *, minimum: int | None = None) -> int:
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None and resolved < minimum:
        return default
    return resolved


def _coerce_custom_assets(data: Any) -> dict[str, list[dict[str, str]]]:
    raw_assets = data if isinstance(data, dict) else {}
    normalized: dict[str, list[dict[str, str]]] = {}
    for kind in _APPEARANCE_KINDS:
        entries = raw_assets.get(kind, [])
        if not isinstance(entries, list):
            continue
        normalized_entries: list[dict[str, str]] = []
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                continue
            inventory_full = str(entry.get("inventory_full", ""))
            asset = {
                "key": str(entry.get("key", "")).strip() or f"custom:{kind}:{index}",
                "label": str(entry.get("label", "")).strip() or Path(inventory_full).stem or f"Custom {index}",
                "inventory_full": inventory_full,
                "world_full": str(entry.get("world_full", "")),
                "inventory_empty": str(entry.get("inventory_empty", "")),
                "world_empty": str(entry.get("world_empty", "")),
                "sprite_mode": str(entry.get("sprite_mode", "single")) if str(entry.get("sprite_mode", "single")) in {"single", "dual"} else "single",
            }
            normalized_entries.append(asset)
        if normalized_entries:
            normalized[kind] = normalized_entries
    return normalized


def _coerce_generated_assets(data: Any) -> list[GeneratedAssetRecord]:
    entries = data if isinstance(data, list) else []
    normalized: list[GeneratedAssetRecord] = []
    for entry in entries:
        if isinstance(entry, GeneratedAssetRecord):
            normalized.append(
                GeneratedAssetRecord(
                    kind=entry.kind,
                    cover_path=str(entry.cover_path),
                    asset_key=str(entry.asset_key),
                    label=str(entry.label),
                    inventory_full=str(entry.inventory_full),
                    world_full=str(entry.world_full),
                    source_name=str(entry.source_name),
                )
            )
            continue
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("kind", "")).strip()
        if kind not in _APPEARANCE_KINDS:
            continue
        normalized.append(
            GeneratedAssetRecord(
                kind=kind,
                cover_path=str(entry.get("cover_path", "")),
                asset_key=str(entry.get("asset_key", "")),
                label=str(entry.get("label", "")),
                inventory_full=str(entry.get("inventory_full", "")),
                world_full=str(entry.get("world_full", "")),
                source_name=str(entry.get("source_name", "")),
            )
        )
    return normalized


def project_from_dict(data: dict[str, Any]) -> ProjectConfig:
    rows: list[MediaRow] = []
    for raw_row in data.get("media_rows", []):
        row = MediaRow(
            row_id=_coerce_int(raw_row.get("row_id", len(rows) + 1), len(rows) + 1, minimum=1),
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
            media_modes={
                "cassette": (
                    str(raw_row.get("media_modes", {}).get("cassette", "split"))
                    if str(raw_row.get("media_modes", {}).get("cassette", "split")) in {"single", "split"}
                    else "split"
                ),
                "vinyl": (
                    str(raw_row.get("media_modes", {}).get("vinyl", "split"))
                    if str(raw_row.get("media_modes", {}).get("vinyl", "split")) in {"single", "split"}
                    else "split"
                ),
                "cd": (
                    str(raw_row.get("media_modes", {}).get("cd", "single"))
                    if str(raw_row.get("media_modes", {}).get("cd", "single")) in {"single", "split"}
                    else "single"
                ),
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
        schema_version=_coerce_int(data.get("schema_version", 1), 1, minimum=1),
        mod_name=str(data.get("mod_name", "")),
        mod_id=str(data.get("mod_id", "")),
        parent_mod_id=str(data.get("parent_mod_id", "NewMusic")),
        author=str(data.get("author", "")),
        workshop_poster_path=str(data.get("workshop_poster_path", "")),
        write_mod_name_on_poster=bool(data.get("write_mod_name_on_poster", True)),
        ogg_output_folder=str(data.get("ogg_output_folder", "")),
        workshop_output_folder=str(data.get("workshop_output_folder", "")),
        sample_rate=_coerce_int(data.get("sample_rate", 44100), 44100, minimum=1),
        compression_quality=snap_compression_quality(data.get("compression_quality", DEFAULT_COMPRESSION_QUALITY)),
        reencode_existing_ogg=bool(data.get("reencode_existing_ogg", True)),
        automatic_textures_enabled=bool(data.get("automatic_textures_enabled", True)),
        media_rows=rows,
        custom_assets=_coerce_custom_assets(data.get("custom_assets", {})),
        generated_assets=_coerce_generated_assets(data.get("generated_assets", [])),
    )
    project.ensure_defaults()
    return project


def next_row_id(project: ProjectConfig) -> int:
    if not project.media_rows:
        return 1
    return max(row.row_id for row in project.media_rows) + 1
