from __future__ import annotations

import json
import logging
from pathlib import Path

from new_music_builder.domain.models import ProjectConfig, project_from_dict, project_to_dict
from new_music_builder.platform.paths import data_root

LOGGER = logging.getLogger('new_music_builder')


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
            return self._default_session_state()
        try:
            payload = json.loads(self.file_path.read_text(encoding='utf-8'))
            project = project_from_dict(payload.get('project', {}))
            current_path = str(payload.get('current_path', ''))
            return project, current_path
        except Exception as exc:
            LOGGER.warning('Failed to restore last session from %s: %s', self.file_path, exc)
            return self._default_session_state()

    @staticmethod
    def _default_session_state() -> tuple[ProjectConfig, str]:
        project = ProjectConfig()
        project.ensure_defaults()
        return project, ''
