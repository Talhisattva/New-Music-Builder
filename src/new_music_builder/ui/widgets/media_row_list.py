from __future__ import annotations

from collections.abc import Callable
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
        on_select: Callable[[int], None] | None = None,
        active: bool = False,
        on_background_selected: Callable[[int], None] | None = None,
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
        self._row_id = row.row_id
        self._expanded = expanded
        self._active = active
        self._hovered = False
        self._on_background_selected = on_background_selected

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
        self._bind_background_interactions()
        self._apply_background_state()

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
            self.badge = MediaRowBadge(
                self.surface,
                row_number=row.row_id,
                command=(lambda: on_select(row.row_id)) if on_select is not None else None,
            )
            self.badge.place(x=badge_x, y=badge_y)
        else:
            badge_x, badge_y = spec.MEDIA_ROW_BADGE_COLLAPSED_POS
            self.badge = MediaRowBadge(
                self.surface,
                row_number=row.row_id,
                command=(lambda: on_select(row.row_id)) if on_select is not None else None,
            )
            self.badge.place(x=badge_x, y=badge_y)
            self.cover = CollapsedMediaCover(
                self.surface,
                cover_path=row.cover_path,
            )
            self.cover.place(
                x=spec.MEDIA_ROW_COLLAPSED_COVER_POS[0],
                y=spec.MEDIA_ROW_COLLAPSED_COVER_POS[1],
            )

    def _bind_background_interactions(self) -> None:
        for sequence, handler in (
            ('<Enter>', self._on_background_enter),
            ('<Leave>', self._on_background_leave),
            ('<ButtonPress-1>', self._on_background_press),
        ):
            self.surface.bind(sequence, handler)

    def _on_background_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._apply_background_state()

    def _on_background_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._apply_background_state()

    def _on_background_press(self, _event: tk.Event) -> None:
        if self._on_background_selected is not None:
            self._on_background_selected(self._row_id)

    def _apply_background_state(self) -> None:
        fill_color = spec.MEDIA_ROW_BG
        if self._active:
            fill_color = spec.MEDIA_ROW_ACTIVE_BG
        elif self._hovered:
            fill_color = spec.MEDIA_ROW_HOVER_BG
        self.surface.configure(bg=fill_color)


class MediaRowList(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        rows: list[MediaRow],
        folder_icon_path: str | None = None,
        bg_color: str | None = None,
        on_row_selected: Callable[[int], None] | None = None,
        active_row_id: int | None = None,
        on_background_selected: Callable[[int], None] | None = None,
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
        self._on_row_selected = on_row_selected
        self._active_row_id = active_row_id
        self._on_background_selected = on_background_selected
        self.row_widgets: list[MediaRowShell] = []

        self._build_rows()

    def _normalized_rows(self, rows: list[MediaRow]) -> list[MediaRow]:
        normalized = list(rows)

        if len(normalized) == 1:
            next_row_id = normalized[0].row_id + 1
            while len(normalized) < 3:
                normalized.append(MediaRow(row_id=next_row_id, media_name=f'Media Row {next_row_id}', expanded=False))
                next_row_id += 1

        expanded_seen = False
        for row in normalized:
            if row.expanded and not expanded_seen:
                expanded_seen = True
                continue
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
                on_select=self._on_row_selected,
                active=(row.row_id == self._active_row_id),
                on_background_selected=self._on_background_selected,
            )
            widget.place(x=spec.MEDIA_ROW_INSET_X, y=current_y)
            self.row_widgets.append(widget)
            current_y += widget.winfo_reqheight() + spec.MEDIA_ROW_GAP_Y
