from __future__ import annotations

from new_music_builder.domain.models import ExportPlan, PlannedMediaRow, PlannedSide, PlannedTrack, ProjectConfig


def build_workshop_txt_lines(project: ProjectConfig, plan: ExportPlan) -> list[str]:
    mod_name = (project.mod_name or "").strip()
    lines = [
        "version=1",
        "id=",
        f"title={mod_name}",
        f"description=[h2]{mod_name}[/h2]",
        "description=[i]Generated with New Music Builder[/i]",
        "description=",
    ]

    ordered_rows = sorted(plan.rows, key=lambda row: row.row_id)
    first_table = True
    for row in ordered_rows:
        sections = _row_workshop_sections(row)
        for label, tracks in sections:
            if not first_table:
                lines.append("description=")
            lines.extend(_render_track_table(row, label, tracks))
            first_table = False

    lines.extend(
        [
            "tags=Build 42;Audio",
            "visibility=public",
            "",
        ]
    )
    return lines


def _ordered_sides(row: PlannedMediaRow) -> list[PlannedSide]:
    return sorted(row.sides, key=lambda side: 0 if side.side == "A" else 1)


def _row_workshop_sections(row: PlannedMediaRow) -> list[tuple[str, list[PlannedTrack]]]:
    sides = _ordered_sides(row)
    if not _row_has_split_media(row):
        return [("[b]Full Album[/b]", [track for side in sides for track in side.tracks])]
    return [(f"[b]Side {side.side}[/b]", list(side.tracks)) for side in sides]


def _row_has_split_media(row: PlannedMediaRow) -> bool:
    if len(row.sides) <= 1:
        return False
    return any(
        row.enabled_media.get(kind, False) and row.media_modes.get(kind, "single" if kind == "cd" else "split") == "split"
        for kind in ("cassette", "vinyl", "cd")
    )


def _render_track_table(row: PlannedMediaRow, section_label: str, tracks: list[PlannedTrack]) -> list[str]:
    lines = [
        "description=[table]",
        f"description=[tr][th]{row.media_name}[/th][/tr]",
        f"description=[tr][td]{section_label}[/td][/tr]",
    ]
    for index, track in enumerate(tracks, start=1):
        lines.append(f"description=[tr][td]{index:02d} {track.display_label}[/td][/tr]")
    lines.append("description=[/table]")
    return lines
