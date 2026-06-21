"""Launch New Music Builder with Explorer-friendly error handling."""

from __future__ import annotations

import os
import sys
from datetime import datetime
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from new_music_builder.platform.paths import startup_fatal_log_path

FATAL_LOG = startup_fatal_log_path()


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
    details = ''.join(traceback.format_exception(exc)).strip()
    lines = [
        f'Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'Working Directory: {ROOT}',
        f'Python: {sys.version.split()[0]}',
        '',
        details,
        '',
    ]
    with FATAL_LOG.open('a', encoding='utf-8') as handle:
        if FATAL_LOG.exists() and FATAL_LOG.stat().st_size > 0:
            handle.write('=' * 80 + '\n\n')
        handle.write('\n'.join(lines))


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
