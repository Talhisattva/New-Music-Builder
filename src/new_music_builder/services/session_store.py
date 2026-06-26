from __future__ import annotations

import json
import logging
from pathlib import Path

from new_music_builder.domain.models import ProjectConfig, project_from_dict, project_to_dict
from new_music_builder.platform.paths import data_root
from new_music_builder.services.dialog_folder_memory import (
    DialogFolderMemory,
    dialog_folder_memory_from_dict,
    dialog_folder_memory_to_dict,
)

LOGGER = logging.getLogger('new_music_builder')


class SessionStore:
    def __init__(self, file_path: Path | None = None) -> None:
        self.file_path = file_path or data_root() / 'last_session.json'
        self.last_load_used_default = False
        self.last_dialog_folder_memory = DialogFolderMemory()

    def save(
        self,
        project: ProjectConfig,
        current_path: str,
        dialog_folder_memory: DialogFolderMemory | None = None,
    ) -> None:
        memory = dialog_folder_memory or self.last_dialog_folder_memory
        self.last_dialog_folder_memory = DialogFolderMemory(
            song_folder=memory.song_folder,
            image_folder=memory.image_folder,
        )
        payload = {
            'current_path': current_path,
            'project': project_to_dict(project),
            'dialog_folders': dialog_folder_memory_to_dict(self.last_dialog_folder_memory),
        }
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    def load(self) -> tuple[ProjectConfig, str]:
        if not self.file_path.exists():
            self.last_load_used_default = True
            return self._default_session_state()
        try:
            payload = json.loads(self.file_path.read_text(encoding='utf-8'))
            project = project_from_dict(payload.get('project', {}))
            current_path = str(payload.get('current_path', ''))
            self.last_dialog_folder_memory = dialog_folder_memory_from_dict(payload.get('dialog_folders', {}))
            self.last_load_used_default = False
            return project, current_path
        except Exception as exc:
            LOGGER.warning('Failed to restore last session from %s: %s', self.file_path, exc)
            self.last_load_used_default = True
            return self._default_session_state()

    @staticmethod
    def _default_session_state() -> tuple[ProjectConfig, str]:
        project = ProjectConfig()
        project.ensure_defaults()
        return project, ''
