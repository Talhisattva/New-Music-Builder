from __future__ import annotations

from pathlib import Path

from new_music_builder.domain.models import AudioRunResult, ExportPlan, ExportTargetPaths, ProjectConfig, ScaffoldResult
from new_music_builder.services.export_build_runner import run_staged_export


def _targets(tmp_path: Path) -> ExportTargetPaths:
    root = tmp_path / "Workshop" / "Pack"
    contents = root / "Contents"
    mods_root = contents / "mods"
    mod_base = mods_root / "PackId"
    common = mod_base / "common"
    v42 = mod_base / "42"
    audio_root = common / "media" / "sound"
    audio_pack_root = audio_root / "PackId"
    return ExportTargetPaths(
        workshop_root=str(tmp_path / "Workshop"),
        outer_folder_name="Pack",
        inner_folder_name="PackId",
        root=str(root),
        contents=str(contents),
        mods_root=str(mods_root),
        mod_base=str(mod_base),
        common=str(common),
        v42=str(v42),
        audio_root=str(audio_root),
        audio_pack_root=str(audio_pack_root),
    )


def test_run_staged_export_marks_empty_output_as_failure(monkeypatch, tmp_path: Path) -> None:
    targets = _targets(tmp_path)
    events: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "new_music_builder.services.export_build_runner.write_export_scaffold",
        lambda *args, **kwargs: ScaffoldResult(output_path=str(Path(targets.root)), mod_size_text="1.0 KB"),
    )
    monkeypatch.setattr(
        "new_music_builder.services.export_build_runner.build_audio_work_plan",
        lambda *args, **kwargs: type("WorkPlan", (), {"items": []})(),
    )
    monkeypatch.setattr(
        "new_music_builder.services.export_build_runner.run_audio_export",
        lambda *args, **kwargs: AudioRunResult(output_path=str(Path(targets.root)), successful_sides=[(1, "A")], built_song_count=1),
    )

    def _promote(_staging_root: Path, final_root: Path) -> None:
        final_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("new_music_builder.services.export_build_runner._promote_staging_export_root", _promote)

    result = run_staged_export(
        ProjectConfig(),
        ExportPlan(),
        targets,
        asset_catalog={},
        cache_root=tmp_path / "cache",
        emit=lambda event: events.append((event.kind, event.message)),
    )

    assert result.fatal_error.startswith("Unknown export error: emitted pack is empty (0 KB).")
    assert result.errors == [result.fatal_error]
    assert result.mod_size_text == "0 B"
    assert ("run_failed", result.fatal_error) in events


def test_run_staged_export_keeps_non_empty_output_successful(monkeypatch, tmp_path: Path) -> None:
    targets = _targets(tmp_path)
    events: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "new_music_builder.services.export_build_runner.write_export_scaffold",
        lambda *args, **kwargs: ScaffoldResult(output_path=str(Path(targets.root)), mod_size_text="1.0 KB"),
    )
    monkeypatch.setattr(
        "new_music_builder.services.export_build_runner.build_audio_work_plan",
        lambda *args, **kwargs: type("WorkPlan", (), {"items": []})(),
    )
    monkeypatch.setattr(
        "new_music_builder.services.export_build_runner.run_audio_export",
        lambda *args, **kwargs: AudioRunResult(output_path=str(Path(targets.root)), successful_sides=[(1, "A")], built_song_count=1),
    )

    def _promote(_staging_root: Path, final_root: Path) -> None:
        final_root.mkdir(parents=True, exist_ok=True)
        (final_root / "workshop.txt").write_text("content", encoding="utf-8")

    monkeypatch.setattr("new_music_builder.services.export_build_runner._promote_staging_export_root", _promote)

    result = run_staged_export(
        ProjectConfig(),
        ExportPlan(),
        targets,
        asset_catalog={},
        cache_root=tmp_path / "cache",
        emit=lambda event: events.append((event.kind, event.message)),
    )

    assert result.fatal_error == ""
    assert result.errors == []
    assert result.mod_size_text != "0 B"
    assert all(kind != "run_failed" for kind, _message in events)
