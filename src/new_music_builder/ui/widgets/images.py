from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageTk

ImageCacheToken = tuple[str, int, int]

_RAW_IMAGE_CACHE: dict[tuple[ImageCacheToken, tuple[int, int] | None], ImageTk.PhotoImage] = {}
_CONTAINED_IMAGE_CACHE: dict[tuple[ImageCacheToken, tuple[int, int], tuple[int, int, int, int]], ImageTk.PhotoImage] = {}
_PIL_CONTAINED_CACHE: dict[tuple[ImageCacheToken, tuple[int, int], tuple[int, int, int, int]], Image.Image] = {}
_HORIZONTAL_FILL_IMAGE_CACHE: dict[tuple[object, ...], ImageTk.PhotoImage] = {}


def _normalize_path(path: str | Path | None) -> Path | None:
    if not path:
        return None
    img_path = Path(path)
    if not img_path.exists():
        return None
    return img_path.resolve()


def cache_token_for_path(path: str | Path | None) -> ImageCacheToken | None:
    img_path = _normalize_path(path)
    if img_path is None:
        return None
    stat = img_path.stat()
    return (str(img_path), stat.st_mtime_ns, stat.st_size)


def load_ctk_image(path: str | Path | None, size: tuple[int, int]) -> ctk.CTkImage | None:
    if not path:
        return None
    img_path = _normalize_path(path)
    if img_path is None:
        return None
    image = Image.open(img_path)
    return ctk.CTkImage(light_image=image, dark_image=image, size=size)


def ctk_image_from_pil(image: Image.Image, size: tuple[int, int]) -> ctk.CTkImage:
    rgba = image.convert('RGBA')
    return ctk.CTkImage(light_image=rgba, dark_image=rgba.copy(), size=size)


def load_contained_pil_image(
    path: str | Path | None,
    size: tuple[int, int],
    *,
    background: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> Image.Image | None:
    token = cache_token_for_path(path)
    if token is None:
        return None
    img_path = Path(token[0])
    cache_key = (token, size, background)
    cached = _PIL_CONTAINED_CACHE.get(cache_key)
    if cached is not None:
        return cached.copy()
    image = Image.open(img_path).convert('RGBA')
    fitted = Image.new('RGBA', size, background)
    scale_ratio = min(size[0] / max(1, image.width), size[1] / max(1, image.height))
    contained_size = (
        max(1, int(round(image.width * scale_ratio))),
        max(1, int(round(image.height * scale_ratio))),
    )
    contained = image.resize(contained_size, Image.Resampling.LANCZOS)
    paste_x = (size[0] - contained.width) // 2
    paste_y = (size[1] - contained.height) // 2
    fitted.paste(contained, (paste_x, paste_y), contained)
    _PIL_CONTAINED_CACHE[cache_key] = fitted
    return fitted.copy()


def load_tk_photoimage(path: str | Path | None, size: tuple[int, int] | None = None) -> ImageTk.PhotoImage | None:
    token = cache_token_for_path(path)
    if token is None:
        return None
    img_path = Path(token[0])
    cache_key = (token, size)
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
    token = cache_token_for_path(path)
    if token is None:
        return None
    cache_key = (token, size, background)
    cached = _CONTAINED_IMAGE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    image = load_contained_pil_image(token[0], size, background=background)
    if image is None:
        return None
    photo = ImageTk.PhotoImage(image)
    _CONTAINED_IMAGE_CACHE[cache_key] = photo
    return photo


def load_tk_photoimage_horizontal_fill(
    path: str | Path | None,
    size: tuple[int, int],
    *,
    opacity_percent: int = 100,
    composite_background: tuple[int, int, int] | None = None,
) -> ImageTk.PhotoImage | None:
    token = cache_token_for_path(path)
    if token is None:
        return None
    img_path = Path(token[0])
    opacity_percent = max(0, min(100, opacity_percent))
    cache_key = (token, size, opacity_percent, *(composite_background or ()))
    cached = _HORIZONTAL_FILL_IMAGE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    image = Image.open(img_path).convert('RGBA')
    target_width, target_height = size
    if target_width <= 0 or target_height <= 0:
        return None

    scale_ratio = target_width / max(1, image.width)
    scaled_height = max(1, int(round(image.height * scale_ratio)))
    scaled = image.resize((target_width, scaled_height), Image.Resampling.LANCZOS)

    if opacity_percent < 100:
        alpha = scaled.getchannel('A')
        alpha = alpha.point(lambda value: int(value * (opacity_percent / 100.0)))
        scaled.putalpha(alpha)

    base_fill = (*composite_background, 255) if composite_background is not None else (0, 0, 0, 0)
    composed = Image.new('RGBA', size, base_fill)
    if scaled_height <= target_height:
        offset_y = (target_height - scaled_height) // 2
        composed.paste(scaled, (0, offset_y), scaled)
    else:
        crop_top = (scaled_height - target_height) // 2
        cropped = scaled.crop((0, crop_top, target_width, crop_top + target_height))
        composed.paste(cropped, (0, 0), cropped)

    photo = ImageTk.PhotoImage(composed)
    _HORIZONTAL_FILL_IMAGE_CACHE[cache_key] = photo
    return photo
