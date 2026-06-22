from __future__ import annotations

from pathlib import Path

from new_music_builder.domain.models import AudioWorkPlan, ExportPlan, ExportTargetPaths, PlannedAudioWorkItem, ProjectConfig
from new_music_builder.services.audio_profile import effective_export_compression_quality
from new_music_builder.services.track_import import SUPPORTED_AUDIO_SUFFIXES


def build_audio_work_plan(project: ProjectConfig, plan: ExportPlan, targets: ExportTargetPaths) -> AudioWorkPlan:
    items: list[PlannedAudioWorkItem] = []
    audio_pack_root = Path(targets.audio_pack_root)
    export_compression_quality = effective_export_compression_quality(project.compression_quality)

    for side in plan.sides:
        for track in side.tracks:
            source_path = Path(track.source_path) if track.source_path else None
            action, reason = _classify_audio_action(source_path, project.reencode_existing_ogg)
            target_relative_path = track.export_relative_path.replace("\\", "/")
            target_path = audio_pack_root / Path(track.export_relative_path)
            items.append(
                PlannedAudioWorkItem(
                    row_id=side.row_id,
                    side=side.side,
                    track_number=track.track_number,
                    display_label=track.display_label,
                    duration_seconds=track.duration_seconds,
                    source_path=str(source_path) if source_path is not None else "",
                    target_relative_path=target_relative_path,
                    target_path=str(target_path),
                    action=action,
                    reason=reason,
                    sample_rate=int(project.sample_rate),
                    compression_quality=export_compression_quality,
                )
            )

    return AudioWorkPlan(items=items)


def _classify_audio_action(source_path: Path | None, reencode_existing_ogg: bool = True) -> tuple[str, str]:
    if source_path is None or not str(source_path).strip():
        return "error", "Missing source path."
    if not source_path.exists() or not source_path.is_file():
        return "error", "Source file is missing."

    suffix = source_path.suffix.lower()
    if suffix == ".ogg":
        if reencode_existing_ogg:
            return "convert_to_ogg", "Re-encoding existing .ogg to match audio settings."
        return "copy_ogg", "Source audio is already .ogg."
    if suffix in SUPPORTED_AUDIO_SUFFIXES:
        return "convert_to_ogg", "Source audio requires conversion."
    return "error", "Unsupported audio format."


def summarize_audio_work_plan(project: ProjectConfig, work_plan: AudioWorkPlan) -> list[str]:
    settings_summary = (
        f"Audio settings: sample_rate={int(project.sample_rate)}Hz "
        f"export_quality={effective_export_compression_quality(project.compression_quality):.2f} "
        f"reencode_existing_ogg={'true' if project.reencode_existing_ogg else 'false'}"
    )
    plan_summary = (
        f"Audio plan: convert={work_plan.convert_count} "
        f"copy={work_plan.copy_count} error={work_plan.error_count}"
    )
    item_lines = [
        (
            f"Planned audio: row={item.row_id} side={item.side} track={item.track_number:02d} "
            f"{item.display_label} -> {item.action} ({item.reason})"
        )
        for item in work_plan.items
    ]
    return [settings_summary, plan_summary, *item_lines]
