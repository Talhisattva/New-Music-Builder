from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
import sys


def app_root() -> Path:
    return runtime_root()


def runtime_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def resource_root() -> Path:
    bundled_root = getattr(sys, '_MEIPASS', None)
    if bundled_root:
        return Path(bundled_root)
    return Path(__file__).resolve().parents[3]


def assets_root() -> Path:
    return resource_root() / 'assets'


def data_root() -> Path:
    root = runtime_root() / 'workspace'
    root.mkdir(parents=True, exist_ok=True)
    return root


def logs_root() -> Path:
    root = runtime_root() / 'logs'
    root.mkdir(parents=True, exist_ok=True)
    return root


def generated_textures_root() -> Path:
    root = runtime_root() / 'Generated Textures'
    root.mkdir(parents=True, exist_ok=True)
    return root


def diagnostic_log_path() -> Path:
    return logs_root() / 'new_music_builder.log'


def startup_fatal_log_path() -> Path:
    return logs_root() / 'startup_fatal.log'


def runtime_fatal_log_path() -> Path:
    return logs_root() / 'runtime_fatal.log'


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
