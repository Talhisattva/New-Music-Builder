from __future__ import annotations

import json
from pathlib import Path

from new_music_builder.platform.paths import data_root


class RecentProjectsStore:
    def __init__(self, file_path: Path | None = None) -> None:
        self.file_path = file_path or data_root() / 'recent.json'

    def load(self) -> list[str]:
        if not self.file_path.exists():
            return []
        try:
            payload = json.loads(self.file_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            return []
        recent = payload.get('recent', [])
        return [str(item) for item in recent if item]

    def push(self, project_path: Path, limit: int = 10) -> list[str]:
        current = [item for item in self.load() if item != str(project_path)]
        current.insert(0, str(project_path))
        trimmed = current[:limit]
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps({'recent': trimmed}, indent=2), encoding='utf-8')
        return trimmed