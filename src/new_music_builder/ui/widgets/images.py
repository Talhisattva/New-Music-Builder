from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageTk

_RAW_IMAGE_CACHE: dict[tuple[str, tuple[int, int] | None], ImageTk.PhotoImage] = {}
_CONTAINED_IMAGE_CACHE: dict[tuple[str, tuple[int, int], tuple[int, int, int, int]], ImageTk.PhotoImage] = {}
_PIL_CONTAINED_CACHE: dict[tuple[str, tuple[int, int], tuple[int, int, int, int]], Image.Image] = {}


def _normalize_path(path: str | Path | None) -> Path | None:
    if not path:
        return None
    img_path = Path(path)
    if not img_path.exists():
        return None
    return img_path.resolve()


def load_ctk_image(path: str | Path | None, size: tuple[int, int]) -> ctk.CTkImage | None:
    if not path:
        return None
    img_path = _normalize_path(path)
    if img_path is None:
        return None
    image = Image.open(img_path)
    return ctk.CTkImage(light_image=image, dark_image=image, size=size)


def load_contained_pil_image(
    path: str | Path | None,
    size: tuple[int, int],
    *,
    background: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> Image.Image | None:
    img_path = _normalize_path(path)
    if img_path is None:
        return None
    cache_key = (str(img_path), size, background)
    cached = _PIL_CONTAINED_CACHE.get(cache_key)
    if cached is not None:
        return cached.copy()
    image = Image.open(img_path).convert('RGBA')
    fitted = Image.new('RGBA', size, background)
    contained = image.copy()
    contained.thumbnail(size, Image.Resampling.LANCZOS)
    paste_x = (size[0] - contained.width) // 2
    paste_y = (size[1] - contained.height) // 2
    fitted.paste(contained, (paste_x, paste_y), contained)
    _PIL_CONTAINED_CACHE[cache_key] = fitted
    return fitted.copy()


def load_tk_photoimage(path: str | Path | None, size: tuple[int, int] | None = None) -> ImageTk.PhotoImage | None:
    img_path = _normalize_path(path)
    if img_path is None:
        return None
    cache_key = (str(img_path), size)
    cached = _RAW_IMAGE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    image = Image.open(img_path)
    if size is not None:
        image = image.resize(size, Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(image)
    _RAW_IMAGE_CACHE[cache_key] = photo
    return photo


def load_tk_photoimage_contained(
    path: str | Path | None,
    size: tuple[int, int],
    *,
    background: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> ImageTk.PhotoImage | None:
    img_path = _normalize_path(path)
    if img_path is None:
        return None
    cache_key = (str(img_path), size, background)
    cached = _CONTAINED_IMAGE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    image = load_contained_pil_image(img_path, size, background=background)
    if image is None:
        return None
    photo = ImageTk.PhotoImage(image)
    _CONTAINED_IMAGE_CACHE[cache_key] = photo
    return photo
