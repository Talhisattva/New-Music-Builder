from __future__ import annotations

import json
from pathlib import Path

from new_music_builder.domain.models import ProjectConfig, project_from_dict, project_to_dict
from new_music_builder.platform.paths import data_root


class SessionStore:
    def __init__(self, file_path: Path | None = None) -> None:
        self.file_path = file_path or data_root() / 'last_session.json'

    def save(self, project: ProjectConfig, current_path: str) -> None:
        payload = {
            'current_path': current_path,
            'project': project_to_dict(project),
        }
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    def load(self) -> tuple[ProjectConfig, str]:
        if not self.file_path.exists():
            return ProjectConfig(), ''
        try:
            payload = json.loads(self.file_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            return ProjectConfig(), ''
        return project_from_dict(payload.get('project', {})), str(payload.get('current_path', ''))