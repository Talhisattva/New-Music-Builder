from __future__ import annotations

from dataclasses import dataclass, field

from new_music_builder.domain.models import ProjectConfig, default_media_row, next_row_id


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