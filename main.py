"""Launch New Music Builder with Explorer-friendly error handling."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'
LOG_DIR = ROOT / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
FATAL_LOG = LOG_DIR / 'startup_fatal.log'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _show_error_dialog(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('New Music Builder Startup Error', message)
        root.destroy()
    except Exception:
        pass


def _write_fatal_log(exc: BaseException) -> None:
    details = ''.join(traceback.format_exception(exc))
    FATAL_LOG.write_text(details, encoding='utf-8')


def main() -> int:
    os.chdir(ROOT)
    from new_music_builder.app.application import run

    return run()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        _write_fatal_log(exc)
        _show_error_dialog(
            'New Music Builder failed to start.\n\n'
            f'See: {FATAL_LOG}'
        )
        raise