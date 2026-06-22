from __future__ import annotations

import ctypes
import logging
import platform
from pathlib import Path

from .paths import assets_root


LOGGER = logging.getLogger("new_music_builder")
_FR_PRIVATE = 0x10


def bundled_font_paths() -> list[Path]:
    font_root = assets_root() / "fonts"
    return [
        font_root / "Orbitron-VariableFont_wght.ttf",
        font_root / "Perfect DOS VGA 437 Win.ttf",
    ]


def register_runtime_fonts() -> None:
    if platform.system() != "Windows":
        return

    add_font_resource = getattr(ctypes.windll.gdi32, "AddFontResourceExW", None)
    if add_font_resource is None:
        return

    add_font_resource.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
    add_font_resource.restype = ctypes.c_int

    for font_path in bundled_font_paths():
        if not font_path.exists():
            LOGGER.warning("Bundled font missing: %s", font_path)
            continue
        added = add_font_resource(str(font_path), _FR_PRIVATE, None)
        if added <= 0:
            LOGGER.warning("Failed to register bundled font: %s", font_path)
