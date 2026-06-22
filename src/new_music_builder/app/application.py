from __future__ import annotations

from new_music_builder.platform.fonts import register_runtime_fonts
from new_music_builder.platform.logging_support import configure_logging, install_runtime_exception_logging
from new_music_builder.ui.main_window import MainWindow


def run() -> int:
    logger = configure_logging()
    install_runtime_exception_logging(logger)
    register_runtime_fonts()
    app = MainWindow()
    app.mainloop()
    return 0
