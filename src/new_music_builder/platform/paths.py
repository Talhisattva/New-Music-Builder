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
    home = Path.home()
    candidates = [
        home / 'Zomboid' / 'Workshop',
        home / 'Documents' / 'Zomboid' / 'Workshop',
        home / 'OneDrive' / 'Documents' / 'Zomboid' / 'Workshop',
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


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