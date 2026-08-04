from __future__ import annotations

from new_music_builder.platform.fonts import register_runtime_fonts
from new_music_builder.platform.i18n import load_translations
from new_music_builder.platform.logging_support import configure_logging, install_runtime_exception_logging
from new_music_builder.services.export_build_runner import cleanup_export_staging_artifacts
from new_music_builder.ui.main_window import MainWindow


def run() -> int:
    logger = configure_logging()
    install_runtime_exception_logging(logger)
    load_translations()
    cleanup_export_staging_artifacts()
    register_runtime_fonts()
    app = MainWindow()
    app.mainloop()
    return 0
