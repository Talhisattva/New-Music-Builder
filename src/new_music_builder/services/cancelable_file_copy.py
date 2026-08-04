from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shutil

from new_music_builder.platform.i18n import t
from new_music_builder.services.export_cancellation import ExportAbortedError


CancelCheck = Callable[[], bool] | None
ProgressCallback = Callable[[int, str], None] | None
_COPY_CHUNK_SIZE = 1024 * 1024


def copy_file_with_cancel(
    source: Path,
    destination: Path,
    *,
    cancel_requested: CancelCheck = None,
    emit_progress: ProgressCallback = None,
    progress_message: str | None = None,
    emit_every_percent: int = 1,
) -> None:
    if progress_message is None:
        progress_message = t("Copying file...")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _raise_if_cancelled(cancel_requested)
    total_size = max(1, source.stat().st_size)
    bytes_written = 0
    last_emitted_percent = -1

    try:
        with source.open("rb") as src_handle, destination.open("wb") as dst_handle:
            while True:
                _raise_if_cancelled(cancel_requested)
                chunk = src_handle.read(_COPY_CHUNK_SIZE)
                if not chunk:
                    break
                dst_handle.write(chunk)
                bytes_written += len(chunk)
                if emit_progress is not None:
                    percent = max(0, min(100, int(round((bytes_written / total_size) * 100))))
                    percent_step = max(1, int(emit_every_percent))
                    if percent == 100 or last_emitted_percent < 0 or percent - last_emitted_percent >= percent_step:
                        emit_progress(percent, progress_message)
                        last_emitted_percent = percent
        shutil.copystat(source, destination)
    except ExportAbortedError:
        destination.unlink(missing_ok=True)
        raise


def _raise_if_cancelled(cancel_requested: CancelCheck) -> None:
    if cancel_requested is not None and cancel_requested():
        raise ExportAbortedError(t("Build aborted by user."))
