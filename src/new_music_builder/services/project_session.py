from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from new_music_builder.domain.models import MediaRow, ProjectConfig, default_media_row, next_row_id
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
        self.project.media_rows.append(row)
        return row_id

    def remove_media_row(self, row_id: int) -> None:
        self.project.media_rows = [row for row in self.project.media_rows if row.row_id != row_id]
        if not self.project.media_rows:
            self.project.media_rows = [default_media_row(1)]

    def remove_media_rows(self, row_ids: set[int]) -> None:
        self.project.media_rows = [row for row in self.project.media_rows if row.row_id not in row_ids]
        self._renumber_media_rows()

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

        return list(range(adjusted_target, adjusted_target + len(moving_tracks)))

    def _renumber_media_rows(self) -> None:
        for index, row in enumerate(self.project.media_rows, start=1):
            generated_names = {
                f'Media Row {row.row_id}',
                f'Media Mix {row.row_id}',
            }
            media_name = f'Media Mix {index}' if row.media_name in generated_names else row.media_name
            self.project.media_rows[index - 1] = MediaRow(
                row_id=index,
                media_name=media_name,
                selected_side=row.selected_side,
                preview_mode=row.preview_mode,
                enabled_media=dict(row.enabled_media),
                cover_path=row.cover_path,
                tracks_a=list(row.tracks_a),
                tracks_b=list(row.tracks_b),
                appearances=dict(row.appearances),
                expanded=row.expanded,
            )
