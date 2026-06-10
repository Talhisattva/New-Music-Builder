"""Launch New Music Builder."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from new_music_builder.app.application import run


if __name__ == "__main__":
    raise SystemExit(run())