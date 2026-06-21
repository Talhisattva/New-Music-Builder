from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path


def app_root() -> Path:
    return Path(__file__).resolve().parents[3]


def data_root() -> Path:
    root = app_root() / 'workspace'
    root.mkdir(parents=True, exist_ok=True)
    return root


def logs_root() -> Path:
    root = app_root() / 'logs'
    root.mkdir(parents=True, exist_ok=True)
    return root


def detect_workshop_dir() -> Path | None:
    for candidate in _zomboid_root_candidates():
        workshop = candidate / 'Workshop'
        if workshop.exists() and workshop.is_dir():
            return workshop
    return None


def _zomboid_root_candidates() -> list[Path]:
    home = Path.home()
    raw_candidates = [
        home / 'Zomboid',
        home / 'Documents' / 'Zomboid',
        home / 'OneDrive' / 'Documents' / 'Zomboid',
        home / 'OneDrive' / 'Zomboid',
        home / 'Saved Games' / 'Zomboid',
        home / 'My Documents' / 'Zomboid',
    ]

    candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in raw_candidates:
        normalized = str(candidate.resolve(strict=False))
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(candidate)
    return candidates


def open_folder(path: str | Path) -> None:
    target = Path(path)
    if not target.exists():
        return
    system = platform.system()
    if system == 'Windows':
        os.startfile(target)  # type: ignore[attr-defined]
    elif system == 'Darwin':
        subprocess.Popen(['open', str(target)])
    else:
        subprocess.Popen(['xdg-open', str(target)])
