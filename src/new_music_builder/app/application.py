from __future__ import annotations

from new_music_builder.platform.logging_support import configure_logging
from new_music_builder.ui.main_window import MainWindow


def run() -> int:
    configure_logging()
    app = MainWindow()
    app.mainloop()
    return 0