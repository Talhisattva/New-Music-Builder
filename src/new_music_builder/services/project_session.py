from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from new_music_builder.domain.models import ProjectConfig, SongSortColumn, SongSortState, TrackEntry, default_media_row, next_row_id
from new_music_builder.services.default_appearance_selection import apply_preferred_row_defaults
from new_music_builder.services.track_import import build_track_entry, filter_supported_audio_paths


@dataclass(slots=True)
class ProjectSession:
    project: ProjectConfig = field(default_factory=ProjectConfig)
    current_path: str = ''

    def __post_init__(self) -> None:
        self.project.ensure_defaults()

    def reset(self) -> None:
        self.project = ProjectConfig()
        self.project.ensure_defaults()
        self.current_path = ''

    def add_media_row(self) -> int:
        row_id = next_row_id(self.project)
        row = default_media_row(row_id)
        apply_preferred_row_defaults(row)
        self.project.media_rows.append(row)
        return row_id

    def remove_media_row(self, row_id: int) -> None:
        self.project.media_rows = [row for row in self.project.media_rows if row.row_id != row_id]
        if not self.project.media_rows:
            row = default_media_row(1)
            apply_preferred_row_defaults(row)
            self.project.media_rows = [row]

    def remove_media_rows(self, row_ids: set[int]) -> None:
        self.project.media_rows = [row for row in self.project.media_rows if row.row_id not in row_ids]

    def move_media_rows(self, selected_row_ids: set[int], target_index: int) -> list[int]:
        rows = list(self.project.media_rows)
        moving_rows = [row for row in rows if row.row_id in selected_row_ids]
        if not moving_rows:
            return []

        moving_id_set = {row.row_id for row in moving_rows}
        remaining_rows = [row for row in rows if row.row_id not in moving_id_set]
        adjusted_target = max(0, min(len(rows), target_index))
        adjusted_target -= sum(
            1
            for index, row in enumerate(rows)
            if row.row_id in moving_id_set and index < target_index
        )
        adjusted_target = max(0, min(len(remaining_rows), adjusted_target))

        original_block_start = min(
            index for index, row in enumerate(rows) if row.row_id in moving_id_set
        )
        if adjusted_target == original_block_start:
            return []

        reordered = (
            remaining_rows[:adjusted_target]
            + moving_rows
            + remaining_rows[adjusted_target:]
        )
        if [row.row_id for row in reordered] == [row.row_id for row in rows]:
            return []

        self.project.media_rows = reordered
        return [row.row_id for row in moving_rows]

    def add_tracks_to_media_row(self, row_id: int, side: str, source_paths: list[str | Path]) -> list[int]:
        target_row = next((row for row in self.project.media_rows if row.row_id == row_id), None)
        if target_row is None or side not in {'A', 'B'}:
            return []

        supported_paths = filter_supported_audio_paths(source_paths)
        tracks = target_row.tracks_a if side == 'A' else target_row.tracks_b
        inserted_indices: list[int] = []
        for path in supported_paths:
            tracks.append(build_track_entry(path))
            inserted_indices.append(len(tracks) - 1)
        target_row.song_sort_for_side(side).column = None
        target_row.song_sort_for_side(side).direction = 'asc'
        return inserted_indices

    def remove_tracks_from_media_row(self, row_id: int, side: str, indices: set[int]) -> list[int]:
        target_row = next((row for row in self.project.media_rows if row.row_id == row_id), None)
        if target_row is None or side not in {'A', 'B'}:
            return []

        tracks = target_row.tracks_a if side == 'A' else target_row.tracks_b
        removable = sorted({index for index in indices if 0 <= index < len(tracks)}, reverse=True)
        if not removable:
            return []
        for index in removable:
            del tracks[index]
        if not tracks:
            target_row.song_sort_for_side(side).column = None
            target_row.song_sort_for_side(side).direction = 'asc'
        return sorted(removable)

    def move_tracks_within_media_row(
        self,
        row_id: int,
        side: str,
        selected_indices: set[int],
        target_index: int,
    ) -> list[int]:
        target_row = next((row for row in self.project.media_rows if row.row_id == row_id), None)
        if target_row is None or side not in {'A', 'B'}:
            return []

        tracks = target_row.tracks_a if side == 'A' else target_row.tracks_b
        selected = sorted({index for index in selected_indices if 0 <= index < len(tracks)})
        if not selected:
            return []

        moving_tracks = [tracks[index] for index in selected]
        moving_set = set(selected)
        remaining_tracks = [track for index, track in enumerate(tracks) if index not in moving_set]
        adjusted_target = target_index - sum(1 for index in selected if index < target_index)
        adjusted_target = max(0, min(len(remaining_tracks), adjusted_target))
        original_block_start = min(selected)
        equivalent_block_start = adjusted_target
        if equivalent_block_start == original_block_start:
            return []

        reordered = (
            remaining_tracks[:adjusted_target]
            + moving_tracks
            + remaining_tracks[adjusted_target:]
        )
        if reordered == tracks:
            return []

        if side == 'A':
            target_row.tracks_a = reordered
        else:
            target_row.tracks_b = reordered
        target_row.song_sort_for_side(side).column = None
        target_row.song_sort_for_side(side).direction = 'asc'

        return list(range(adjusted_target, adjusted_target + len(moving_tracks)))

    def sort_tracks_in_media_row(self, row_id: int, side: str, column: SongSortColumn) -> SongSortState | None:
        target_row = next((row for row in self.project.media_rows if row.row_id == row_id), None)
        if target_row is None or side not in {'A', 'B'}:
            return None

        tracks = target_row.tracks_a if side == 'A' else target_row.tracks_b
        sort_state = target_row.song_sort_for_side(side)
        direction = self._next_sort_direction(sort_state, column)
        reverse = direction == 'desc'
        indexed_tracks = list(enumerate(tracks))
        indexed_tracks.sort(key=lambda item: self._track_sort_key(item[1], column), reverse=reverse)
        reordered = [track for _index, track in indexed_tracks]

        if side == 'A':
            target_row.tracks_a = reordered
        else:
            target_row.tracks_b = reordered

        sort_state.column = column
        sort_state.direction = direction
        return sort_state

    def _next_sort_direction(self, state: SongSortState, column: SongSortColumn) -> str:
        if state.column == column:
            return 'desc' if state.direction == 'asc' else 'asc'
        if column == 'ogg':
            return 'desc'
        return 'asc'

    def _track_sort_key(self, track: TrackEntry, column: SongSortColumn) -> tuple[object, ...]:
        if column == 'ogg':
            return (Path(track.source_path).suffix.lower() == '.ogg',)
        if column == 'song_name':
            return ((track.display_label or Path(track.source_path).stem).casefold(),)
        return (self._duration_seconds(track.duration),)

    def _duration_seconds(self, duration: str) -> int:
        parts = duration.split(':')
        if not parts or any(not part.isdigit() for part in parts):
            return -1
        total = 0
        for part in parts:
            total = (total * 60) + int(part)
        return total
