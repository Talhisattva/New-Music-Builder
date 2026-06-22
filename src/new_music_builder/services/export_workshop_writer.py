from __future__ import annotations

from new_music_builder.domain.models import ExportPlan, PlannedMediaRow, PlannedSide, ProjectConfig


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
        for side in _ordered_sides(row):
            if not first_table:
                lines.append("description=")
            lines.extend(_render_side_table(row, side))
            first_table = False

    lines.extend(
        [
            "tags=Build 42;Audio",
            "visibility=private",
            "",
        ]
    )
    return lines


def _ordered_sides(row: PlannedMediaRow) -> list[PlannedSide]:
    return sorted(row.sides, key=lambda side: 0 if side.side == "A" else 1)


def _render_side_table(row: PlannedMediaRow, side: PlannedSide) -> list[str]:
    is_full = len(row.sides) == 1
    lines = [
        "description=[table]",
        f"description=[tr][th]{row.media_name}[/th][/tr]",
        f"description=[tr][td]{_section_label(side, is_full=is_full)}[/td][/tr]",
    ]
    for index, track in enumerate(side.tracks, start=1):
        lines.append(f"description=[tr][td]{index:02d} {track.display_label}[/td][/tr]")
    lines.append("description=[/table]")
    return lines


def _section_label(side: PlannedSide, *, is_full: bool) -> str:
    if is_full:
        return "[b]Full Album[/b]"
    return f"[b]Side {side.side}[/b]"
