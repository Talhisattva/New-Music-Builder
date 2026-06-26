from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


DialogFolderLane = Literal["song", "image"]


@dataclass(slots=True)
class DialogFolderMemory:
    song_folder: str = ""
    image_folder: str = ""


def dialog_folder_memory_to_dict(memory: DialogFolderMemory) -> dict[str, str]:
    return {
        "song_folder": str(memory.song_folder or ""),
        "image_folder": str(memory.image_folder or ""),
    }


def dialog_folder_memory_from_dict(data: Any) -> DialogFolderMemory:
    if not isinstance(data, dict):
        return DialogFolderMemory()
    return DialogFolderMemory(
        song_folder=str(data.get("song_folder", "")),
        image_folder=str(data.get("image_folder", "")),
    )


def resolve_initial_dialog_dir(
    memory: DialogFolderMemory,
    lane: DialogFolderLane,
    *,
    current_path: str | None = None,
) -> str:
    candidate = _existing_directory_for_path(current_path)
    if candidate is not None:
        return str(candidate)
    remembered = memory.song_folder if lane == "song" else memory.image_folder
    candidate = _existing_directory_for_path(remembered)
    if candidate is not None:
        return str(candidate)
    return str(Path.home())


def remember_dialog_selection(
    memory: DialogFolderMemory,
    lane: DialogFolderLane,
    selected_path: str | Path,
) -> None:
    selected = str(selected_path).strip()
    if not selected:
        return
    resolved = Path(selected)
    directory = resolved if resolved.is_dir() else resolved.parent
    if lane == "song":
        memory.song_folder = str(directory)
        return
    memory.image_folder = str(directory)


def _existing_directory_for_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    candidate = Path(raw)
    if candidate.exists():
        return candidate if candidate.is_dir() else candidate.parent
    parent = candidate.parent
    if parent and str(parent).strip() and parent.exists():
        return parent
    return None
