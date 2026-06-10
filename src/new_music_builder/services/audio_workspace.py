from __future__ import annotations

from pathlib import Path

from new_music_builder.platform.binaries import locate_binary
from new_music_builder.platform.paths import app_root, data_root


class AudioWorkspaceService:
    def __init__(self) -> None:
        self.workspace_root = data_root() / 'audio'
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def bundled_ffmpeg_dir(self) -> Path:
        return app_root().parents[1] / 'Simple-Moozic-Builder-Git' / 'ffmpeg'

    def locate_ffmpeg(self) -> str | None:
        return locate_binary('ffmpeg', self.bundled_ffmpeg_dir())

    def locate_ffplay(self) -> str | None:
        return locate_binary('ffplay', self.bundled_ffmpeg_dir())