from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from new_music_builder.domain.models import AudioRunEvent, AudioRunResult, ExportPlan, ExportTargetPaths, ProjectConfig
from new_music_builder.services.asset_catalog import AssetEntry
from new_music_builder.services.audio_export_runner import run_audio_export
from new_music_builder.services.audio_work_plan import build_audio_work_plan
from new_music_builder.services.export_cancellation import ExportAbortedError
from new_music_builder.services.export_scaffold import write_export_scaffold


BuildEventEmitter = Callable[[AudioRunEvent], None]
CancelCheck = Callable[[], bool]
LOGGER = logging.getLogger('new_music_builder')


def run_staged_export(
    project: ProjectConfig,
    plan: ExportPlan,
    final_targets: ExportTargetPaths,
    *,
    asset_catalog: dict[str, list[AssetEntry]],
    cache_root: str | Path,
    emit: BuildEventEmitter | None = None,
    cancel_requested: CancelCheck | None = None,
    run_id: str = "",
) -> AudioRunResult:
    final_root = Path(final_targets.root)
    log_run_id = run_id or "-"
    LOGGER.info("[run=%s] run_staged_export start final_root=%s", log_run_id, final_root)
    result = AudioRunResult(output_path=str(final_root))
    staging_targets = create_staging_targets(final_targets)
    staging_root = Path(staging_targets.root)

    try:
        LOGGER.info("[run=%s] run_staged_export emit preparing staging_root=%s", log_run_id, staging_root)
        _emit(emit, "run_preparing", message="Preparing export...")
        _raise_if_cancelled(cancel_requested)

        LOGGER.info("[run=%s] run_staged_export scaffold start staging_root=%s", log_run_id, staging_root)
        _emit(emit, "scaffold_started", message="Writing export scaffold...")
        scaffold_result = write_export_scaffold(project, plan, staging_targets, asset_catalog)
        LOGGER.info(
            "[run=%s] run_staged_export scaffold complete errors=%s size=%s",
            log_run_id,
            len(scaffold_result.errors),
            scaffold_result.mod_size_text,
        )
        if scaffold_result.errors:
            result.errors.extend(scaffold_result.errors)
            result.fatal_error = scaffold_result.errors[0]
            result.mod_size_text = scaffold_result.mod_size_text
            _emit(emit, "run_failed", message=result.fatal_error)
            return result

        _emit(
            emit,
            "scaffold_completed",
            message=f"Export scaffold complete. Size: {scaffold_result.mod_size_text}",
            size_text=scaffold_result.mod_size_text,
        )
        _raise_if_cancelled(cancel_requested)

        LOGGER.info("[run=%s] run_staged_export build_audio_work_plan start", log_run_id)
        work_plan = build_audio_work_plan(project, plan, staging_targets)
        LOGGER.info("[run=%s] run_staged_export audio_export start songs=%s", log_run_id, len(work_plan.items))
        audio_result = run_audio_export(
            work_plan,
            cache_root=cache_root,
            output_root=staging_targets.root,
            emit=emit,
            cancel_requested=cancel_requested,
        )
        result = audio_result
        result.output_path = str(final_root)

        if result.aborted:
            LOGGER.info("[run=%s] run_staged_export audio aborted message=%s", log_run_id, result.abort_message)
            _emit(emit, "run_aborted", message=result.abort_message or "Build aborted by user.")
            return result

        _raise_if_cancelled(cancel_requested)
        LOGGER.info("[run=%s] run_staged_export promote start staging=%s final=%s", log_run_id, staging_root, final_root)
        _promote_staging_export_root(staging_root, final_root)
        result.mod_size_text = _format_size_text(_directory_size_bytes(final_root))
        LOGGER.info("[run=%s] run_staged_export promote complete size=%s", log_run_id, result.mod_size_text)
        return result
    except ExportAbortedError as exc:
        LOGGER.info("[run=%s] run_staged_export caught abort: %s", log_run_id, exc)
        result.aborted = True
        result.abort_message = str(exc)
        result.fatal_error = str(exc)
        _emit(emit, "run_aborted", message=result.abort_message)
        return result
    except Exception as exc:
        LOGGER.exception("[run=%s] run_staged_export failed: %s", log_run_id, exc)
        result.fatal_error = str(exc)
        _emit(emit, "run_failed", message=result.fatal_error)
        raise
    finally:
        if staging_root.exists():
            LOGGER.info("[run=%s] run_staged_export cleanup staging_root=%s", log_run_id, staging_root)
            shutil.rmtree(staging_root, ignore_errors=True)
        LOGGER.info("[run=%s] run_staged_export end final_root=%s", log_run_id, final_root)


def create_staging_targets(final_targets: ExportTargetPaths) -> ExportTargetPaths:
    staging_root = Path(final_targets.workshop_root) / f".nmb_staging_{uuid4().hex}"
    contents = staging_root / "Contents"
    mods_root = contents / "mods"
    mod_base = mods_root / final_targets.inner_folder_name
    common = mod_base / "common"
    v42 = mod_base / "42"
    audio_root = common / "media" / "sound"
    audio_pack_root = audio_root / final_targets.inner_folder_name
    return ExportTargetPaths(
        workshop_root=final_targets.workshop_root,
        outer_folder_name=final_targets.outer_folder_name,
        inner_folder_name=final_targets.inner_folder_name,
        root=str(staging_root),
        contents=str(contents),
        mods_root=str(mods_root),
        mod_base=str(mod_base),
        common=str(common),
        v42=str(v42),
        audio_root=str(audio_root),
        audio_pack_root=str(audio_pack_root),
    )


def _promote_staging_export_root(staging_root: Path, final_root: Path) -> None:
    if final_root.exists():
        shutil.rmtree(final_root)
    if staging_root.exists():
        shutil.move(str(staging_root), str(final_root))


def _emit(
    emit: BuildEventEmitter | None,
    kind: str,
    *,
    message: str = "",
    size_text: str = "",
) -> None:
    if emit is None:
        return
    emit(
        AudioRunEvent(
            kind=kind,  # type: ignore[arg-type]
            row_id=0,
            side="A",
            message=message,
            size_text=size_text,
        )
    )


def _raise_if_cancelled(cancel_requested: CancelCheck | None) -> None:
    if cancel_requested is not None and cancel_requested():
        raise ExportAbortedError("Build aborted by user.")


def _directory_size_bytes(root: Path) -> int:
    total = 0
    if not root.exists():
        return total
    for path in root.rglob("*"):
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:
                continue
    return total


def _format_size_text(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"
