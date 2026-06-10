from __future__ import annotations

import json
from pathlib import Path

from new_music_builder.domain.models import ProjectConfig, project_from_dict, project_to_dict


class ProjectStore:
    def save(self, project: ProjectConfig, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(project_to_dict(project), indent=2), encoding='utf-8')

    def load(self, source: Path) -> ProjectConfig:
        data = json.loads(source.read_text(encoding='utf-8'))
        return project_from_dict(data)