from __future__ import annotations

import tkinter as tk

from new_music_builder.domain.models import MediaRow
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.media_row_badge import MediaRowBadge
from new_music_builder.ui.widgets.media_row_cover import CollapsedMediaCover, ExpandedMediaCover


class MediaRowShell(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        row: MediaRow,
        expanded: bool,
        folder_icon_path: str | None = None,
    ) -> None:
        size = spec.MEDIA_ROW_EXPANDED_SIZE if expanded else spec.MEDIA_ROW_COLLAPSED_SIZE
        super().__init__(
            parent,
            bg=spec.MEDIA_ROW_OUTLINE,
            bd=0,
            highlightthickness=0,
            width=size[0],
            height=size[1],
        )
        self.pack_propagate(False)
        self._expanded = expanded

        inner_width = size[0] - (spec.MEDIA_ROW_OUTLINE_WIDTH * 2)
        inner_height = size[1] - (spec.MEDIA_ROW_OUTLINE_WIDTH * 2)
        self.surface = tk.Frame(
            self,
            bg=spec.MEDIA_ROW_BG,
            bd=0,
            highlightthickness=0,
            width=inner_width,
            height=inner_height,
        )
        self.surface.place(x=spec.MEDIA_ROW_OUTLINE_WIDTH, y=spec.MEDIA_ROW_OUTLINE_WIDTH)
        self.surface.pack_propagate(False)

        if expanded:
            self.cover = ExpandedMediaCover(
                self.surface,
                folder_icon_path=folder_icon_path,
                cover_path=row.cover_path,
            )
            self.cover.place(
                x=spec.MEDIA_ROW_EXPANDED_COVER_POS[0],
                y=spec.MEDIA_ROW_EXPANDED_COVER_POS[1],
            )
            badge_x, badge_y = spec.MEDIA_ROW_BADGE_EXPANDED_POS
            self.badge = MediaRowBadge(self.surface, row_number=row.row_id)
            self.badge.place(x=badge_x, y=badge_y)
        else:
            badge_x, badge_y = spec.MEDIA_ROW_BADGE_COLLAPSED_POS
            self.badge = MediaRowBadge(self.surface, row_number=row.row_id)
            self.badge.place(x=badge_x, y=badge_y)
            self.cover = CollapsedMediaCover(
                self.surface,
                cover_path=row.cover_path,
            )
            self.cover.place(
                x=spec.MEDIA_ROW_COLLAPSED_COVER_POS[0],
                y=spec.MEDIA_ROW_COLLAPSED_COVER_POS[1],
            )


class MediaRowList(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        rows: list[MediaRow],
        folder_icon_path: str | None = None,
        bg_color: str | None = None,
    ) -> None:
        resolved_bg = bg_color if bg_color is not None else parent.cget('bg')
        normalized_rows = self._normalized_rows(rows)
        total_height = self._total_height_for_rows(normalized_rows)
        super().__init__(
            parent,
            bg=resolved_bg,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIST_WIDTH,
            height=total_height,
        )
        self.pack_propagate(False)
        self.rows = normalized_rows
        self._folder_icon_path = folder_icon_path
        self.row_widgets: list[MediaRowShell] = []

        self._build_rows()

    def _normalized_rows(self, rows: list[MediaRow]) -> list[MediaRow]:
        if len(rows) >= 3:
            if not any(row.expanded for row in rows):
                rows[0].expanded = True
            for row in rows[1:]:
                if rows[0].expanded:
                    row.expanded = False
            return rows

        normalized = list(rows)
        next_row_id = max((row.row_id for row in normalized), default=0) + 1
        while len(normalized) < 3:
            normalized.append(MediaRow(row_id=next_row_id, media_name=f'Media Row {next_row_id}', expanded=False))
            next_row_id += 1
        if not any(row.expanded for row in normalized):
            normalized[0].expanded = True
        for row in normalized[1:]:
            if normalized[0].expanded:
                row.expanded = False
        return normalized

    def _total_height_for_rows(self, rows: list[MediaRow]) -> int:
        height = spec.MEDIA_ROW_INSET_Y
        for index, row in enumerate(rows):
            height += spec.MEDIA_ROW_EXPANDED_SIZE[1] if row.expanded else spec.MEDIA_ROW_COLLAPSED_SIZE[1]
            if index < len(rows) - 1:
                height += spec.MEDIA_ROW_GAP_Y
        height += spec.MEDIA_ROW_INSET_Y
        return height

    def _build_rows(self) -> None:
        current_y = spec.MEDIA_ROW_INSET_Y
        for row in self.rows:
            widget = MediaRowShell(
                self,
                row=row,
                expanded=row.expanded,
                folder_icon_path=self._folder_icon_path,
            )
            widget.place(x=spec.MEDIA_ROW_INSET_X, y=current_y)
            self.row_widgets.append(widget)
            current_y += widget.winfo_reqheight() + spec.MEDIA_ROW_GAP_Y
