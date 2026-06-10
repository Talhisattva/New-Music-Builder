from __future__ import annotations

import shutil
from pathlib import Path


def locate_binary(binary_name: str, bundled_dir: Path | None = None) -> str | None:
    if bundled_dir is not None:
        bundled = bundled_dir / binary_name
        if bundled.exists():
            return str(bundled)
        if Path(str(bundled) + '.exe').exists():
            return str(Path(str(bundled) + '.exe'))
    resolved = shutil.which(binary_name)
    if resolved:
        return resolved
    return None