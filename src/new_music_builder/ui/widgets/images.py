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


def load_tk_photoimage(path: str | Path | None, size: tuple[int, int]) -> ImageTk.PhotoImage | None:
    if not path:
        return None
    img_path = Path(path)
    if not img_path.exists():
        return None
    image = Image.open(img_path).resize(size, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image)
