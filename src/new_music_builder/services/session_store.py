from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from new_music_builder.domain.models import ProjectConfig, project_from_dict, project_to_dict
from new_music_builder.platform.paths import data_root
from new_music_builder.services.dialog_folder_memory import (
    DialogFolderMemory,
    dialog_folder_memory_from_dict,
    dialog_folder_memory_to_dict,
)

LOGGER = logging.getLogger('new_music_builder')


@dataclass(slots=True)
class SessionAudioPreferences:
    sample_rate: int = 44100
    compression_quality: float = 0.5
    reencode_existing_ogg: bool = True


class SessionStore:
    def __init__(self, file_path: Path | None = None) -> None:
        self.file_path = file_path or data_root() / 'last_session.json'
        self.last_load_used_default = False
        self.last_dialog_folder_memory = DialogFolderMemory()
        self.last_audio_preferences = SessionAudioPreferences()
        self.last_automatic_textures_enabled = True
        self.last_regenerate_textures_on_project_load_enabled = False
        self.last_text_tooltips_enabled = True

    def save(
        self,
        project: ProjectConfig,
        current_path: str,
        dialog_folder_memory: DialogFolderMemory | None = None,
        audio_preferences: SessionAudioPreferences | None = None,
    ) -> None:
        memory = dialog_folder_memory or self.last_dialog_folder_memory
        self.last_dialog_folder_memory = DialogFolderMemory(
            song_folder=memory.song_folder,
            image_folder=memory.image_folder,
        )
        preferences = audio_preferences or self.last_audio_preferences
        self.last_audio_preferences = SessionAudioPreferences(
            sample_rate=int(preferences.sample_rate),
            compression_quality=float(preferences.compression_quality),
            reencode_existing_ogg=bool(preferences.reencode_existing_ogg),
        )
        payload = {
            'current_path': current_path,
            'project': project_to_dict(project),
            'dialog_folders': dialog_folder_memory_to_dict(self.last_dialog_folder_memory),
            'audio_preferences': {
                'sample_rate': self.last_audio_preferences.sample_rate,
                'compression_quality': self.last_audio_preferences.compression_quality,
                'reencode_existing_ogg': self.last_audio_preferences.reencode_existing_ogg,
            },
            'automatic_textures_enabled': self.last_automatic_textures_enabled,
            'regenerate_textures_on_project_load_enabled': self.last_regenerate_textures_on_project_load_enabled,
            'text_tooltips_enabled': self.last_text_tooltips_enabled,
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
            self.last_audio_preferences = self._audio_preferences_from_payload(
                payload.get('audio_preferences', {}),
                fallback_project=project,
            )
            self.last_automatic_textures_enabled = bool(
                payload.get('automatic_textures_enabled', project.automatic_textures_enabled)
            )
            self.last_regenerate_textures_on_project_load_enabled = bool(
                payload.get('regenerate_textures_on_project_load_enabled', False)
            )
            self.last_text_tooltips_enabled = bool(payload.get('text_tooltips_enabled', True))
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

    @staticmethod
    def _audio_preferences_from_payload(
        data: object,
        *,
        fallback_project: ProjectConfig,
    ) -> SessionAudioPreferences:
        if isinstance(data, dict):
            try:
                sample_rate = int(data.get('sample_rate', fallback_project.sample_rate))
            except (TypeError, ValueError):
                sample_rate = fallback_project.sample_rate
            try:
                compression_quality = float(data.get('compression_quality', fallback_project.compression_quality))
            except (TypeError, ValueError):
                compression_quality = fallback_project.compression_quality
            return SessionAudioPreferences(
                sample_rate=sample_rate,
                compression_quality=compression_quality,
                reencode_existing_ogg=bool(data.get('reencode_existing_ogg', fallback_project.reencode_existing_ogg)),
            )
        return SessionAudioPreferences(
            sample_rate=fallback_project.sample_rate,
            compression_quality=fallback_project.compression_quality,
            reencode_existing_ogg=fallback_project.reencode_existing_ogg,
        )
