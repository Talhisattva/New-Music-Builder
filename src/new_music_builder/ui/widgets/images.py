from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageTk


def load_ctk_image(path: str | Path | None, size: tuple[int, int]) -> ctk.CTkImage | None:
    if not path:
        return None
    img_path = Path(path)
    if not img_path.exists():
        return None
    image = Image.open(img_path)
    return ctk.CTkImage(light_image=image, dark_image=image, size=size)


def load_contained_pil_image(
    path: str | Path | None,
    size: tuple[int, int],
    *,
    background: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> Image.Image | None:
    if not path:
        return None
    img_path = Path(path)
    if not img_path.exists():
        return None
    image = Image.open(img_path).convert('RGBA')
    fitted = Image.new('RGBA', size, background)
    contained = image.copy()
    contained.thumbnail(size, Image.Resampling.LANCZOS)
    paste_x = (size[0] - contained.width) // 2
    paste_y = (size[1] - contained.height) // 2
    fitted.paste(contained, (paste_x, paste_y), contained)
    return fitted


def load_tk_photoimage(path: str | Path | None, size: tuple[int, int] | None = None) -> ImageTk.PhotoImage | None:
    if not path:
        return None
    img_path = Path(path)
    if not img_path.exists():
        return None
    image = Image.open(img_path)
    if size is not None:
        image = image.resize(size, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image)


def load_tk_photoimage_contained(
    path: str | Path | None,
    size: tuple[int, int],
    *,
    background: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> ImageTk.PhotoImage | None:
    image = load_contained_pil_image(path, size, background=background)
    if image is None:
        return None
    return ImageTk.PhotoImage(image)
