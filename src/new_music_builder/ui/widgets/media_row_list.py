from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import tkinter as tk

from new_music_builder.domain.models import MediaKind, MediaRow
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.collapsed_row_chevron import CollapsedRowChevron
from new_music_builder.ui.widgets.collapsed_row_details import CollapsedRowDetails
from new_music_builder.ui.widgets.media_rename_field import MediaRenameField
from new_music_builder.ui.widgets.media_row_badge import MediaRowBadge
from new_music_builder.ui.widgets.media_row_cover import CollapsedMediaCover, ExpandedMediaCover
from new_music_builder.ui.widgets.media_side_toggle import MediaSideToggle
from new_music_builder.ui.widgets.media_type_strip import MediaTypeStrip


@dataclass(frozen=True, slots=True)
class RowSelectionModifiers:
    shift: bool = False
    additive: bool = False


class MediaRowShell(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        row: MediaRow,
        expanded: bool,
        folder_icon_path: str | None = None,
        cassette_icon_path: str | None = None,
        vinyl_icon_path: str | None = None,
        cd_icon_path: str | None = None,
        check_icon_path: str | None = None,
        edit_icon_path: str | None = None,
        on_select: Callable[[int], None] | None = None,
        selected: bool = False,
        selected_count: int = 0,
        on_background_selected: Callable[[int, RowSelectionModifiers], None] | None = None,
        on_background_toggle: Callable[[int], None] | None = None,
        on_enabled_media_changed: Callable[[int, MediaKind, bool], None] | None = None,
        on_name_committed: Callable[[int, str], None] | None = None,
        on_side_selected: Callable[[int, str], None] | None = None,
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
        self._row_expanded = row.expanded
        self._selected = selected
        self._selected_count = selected_count
        self._hovered = False
        self._on_background_selected = on_background_selected
        self._on_background_toggle = on_background_toggle
        self._pending_single_click_after_id: str | None = None
        self._suppress_next_release = False

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
            self.rename_field = MediaRenameField(
                self.surface,
                row=row,
                edit_icon_path=edit_icon_path,
                bg_color=spec.MEDIA_ROW_RENAME_BG,
                on_name_committed=on_name_committed,
            )
            self.rename_field.place(
                x=spec.MEDIA_ROW_RENAME_POS[0],
                y=spec.MEDIA_ROW_RENAME_POS[1],
            )
            self.side_toggle = MediaSideToggle(
                self.surface,
                row=row,
                on_side_selected=on_side_selected,
            )
            self.side_toggle.place(
                x=spec.MEDIA_ROW_SIDE_TOGGLE_POS[0],
                y=spec.MEDIA_ROW_SIDE_TOGGLE_POS[1],
            )
            self.media_type_strip = MediaTypeStrip(
                self.surface,
                row=row,
                expanded=True,
                cassette_icon_path=cassette_icon_path,
                vinyl_icon_path=vinyl_icon_path,
                cd_icon_path=cd_icon_path,
                check_icon_path=check_icon_path,
                bg_color=spec.MEDIA_ROW_BG,
                on_enabled_media_changed=on_enabled_media_changed,
            )
            self.media_type_strip.place(
                x=spec.MEDIA_ROW_MEDIA_STRIP_EXPANDED_POS[0],
                y=spec.MEDIA_ROW_MEDIA_STRIP_EXPANDED_POS[1],
            )
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
            self.media_type_strip = MediaTypeStrip(
                self.surface,
                row=row,
                expanded=False,
                cassette_icon_path=cassette_icon_path,
                vinyl_icon_path=vinyl_icon_path,
                cd_icon_path=cd_icon_path,
                check_icon_path=check_icon_path,
                bg_color=spec.MEDIA_ROW_BG,
                on_enabled_media_changed=on_enabled_media_changed,
            )
            self.media_type_strip.place(
                x=spec.MEDIA_ROW_MEDIA_STRIP_COLLAPSED_POS[0],
                y=spec.MEDIA_ROW_MEDIA_STRIP_COLLAPSED_POS[1],
            )
            self.collapsed_chevron = CollapsedRowChevron(
                self.surface,
                bg_color=spec.MEDIA_ROW_BG,
            )
            self.collapsed_chevron.place(
                x=spec.MEDIA_ROW_COLLAPSED_CHEVRON_POS[0],
                y=spec.MEDIA_ROW_COLLAPSED_CHEVRON_POS[1],
            )
            self.collapsed_details = CollapsedRowDetails(
                self.surface,
                row=row,
                bg_color=spec.MEDIA_ROW_BG,
            )
            self.collapsed_details.place(
                x=spec.MEDIA_ROW_COLLAPSED_DETAILS_POS[0],
                y=spec.MEDIA_ROW_COLLAPSED_DETAILS_POS[1],
            )
        self._apply_background_state()

    def _bind_background_interactions(self) -> None:
        for sequence, handler in (
            ('<Enter>', self._on_background_enter),
            ('<Leave>', self._on_background_leave),
            ('<ButtonRelease-1>', self._on_background_release),
            ('<Double-Button-1>', self._on_background_double_press),
        ):
            self.surface.bind(sequence, handler)

    def _on_background_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._apply_background_state()

    def _on_background_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._apply_background_state()

    def _on_background_release(self, event: tk.Event) -> None:
        if self._suppress_next_release:
            self._suppress_next_release = False
            return
        self._cancel_pending_single_click()
        modifiers = self._decode_selection_modifiers(event)
        self._pending_single_click_after_id = self.after(
            spec.MEDIA_ROW_DOUBLE_CLICK_DELAY_MS,
            lambda: self._emit_background_selection(modifiers),
        )

    def _on_background_double_press(self, event: tk.Event) -> None:
        self._cancel_pending_single_click()
        self._suppress_next_release = True
        modifiers = self._decode_selection_modifiers(event)
        if (modifiers.shift or modifiers.additive) or self._on_background_toggle is None:
            return
        self._on_background_toggle(self._row_id)

    def _apply_background_state(self) -> None:
        fill_color = spec.MEDIA_ROW_BG
        if self._selected and (self._selected_count > 1 or not self._row_expanded):
            fill_color = spec.MEDIA_ROW_ACTIVE_BG
        elif self._hovered:
            fill_color = spec.MEDIA_ROW_HOVER_BG
        self.surface.configure(bg=fill_color)
        if hasattr(self, 'media_type_strip'):
            self.media_type_strip.set_bg_color(fill_color)
        if hasattr(self, 'collapsed_chevron'):
            self.collapsed_chevron.set_bg_color(fill_color)
        if hasattr(self, 'collapsed_details'):
            self.collapsed_details.set_bg_color(fill_color)

    def _decode_selection_modifiers(self, event: tk.Event) -> RowSelectionModifiers:
        state = int(getattr(event, 'state', 0))
        shift = bool(state & 0x0001)
        additive = bool(state & 0x0004)
        return RowSelectionModifiers(shift=shift, additive=additive)

    def _emit_background_selection(self, modifiers: RowSelectionModifiers) -> None:
        self._pending_single_click_after_id = None
        if self._on_background_selected is not None:
            self._on_background_selected(self._row_id, modifiers)

    def _cancel_pending_single_click(self) -> None:
        if self._pending_single_click_after_id is None:
            return
        self.after_cancel(self._pending_single_click_after_id)
        self._pending_single_click_after_id = None


class MediaRowList(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        rows: list[MediaRow],
        folder_icon_path: str | None = None,
        cassette_icon_path: str | None = None,
        vinyl_icon_path: str | None = None,
        cd_icon_path: str | None = None,
        check_icon_path: str | None = None,
        edit_icon_path: str | None = None,
        bg_color: str | None = None,
        on_row_selected: Callable[[int], None] | None = None,
        selected_row_ids: set[int] | None = None,
        on_background_selected: Callable[[int, RowSelectionModifiers], None] | None = None,
        on_background_toggle: Callable[[int], None] | None = None,
        on_enabled_media_changed: Callable[[int, MediaKind, bool], None] | None = None,
        on_name_committed: Callable[[int, str], None] | None = None,
        on_side_selected: Callable[[int, str], None] | None = None,
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
        self._cassette_icon_path = cassette_icon_path
        self._vinyl_icon_path = vinyl_icon_path
        self._cd_icon_path = cd_icon_path
        self._check_icon_path = check_icon_path
        self._edit_icon_path = edit_icon_path
        self._on_row_selected = on_row_selected
        self._selected_row_ids = set(selected_row_ids or set())
        self._selected_count = len(self._selected_row_ids)
        self._on_background_selected = on_background_selected
        self._on_background_toggle = on_background_toggle
        self._on_enabled_media_changed = on_enabled_media_changed
        self._on_name_committed = on_name_committed
        self._on_side_selected = on_side_selected
        self.row_widgets: list[MediaRowShell] = []

        self._build_rows()

    def _normalized_rows(self, rows: list[MediaRow]) -> list[MediaRow]:
        normalized = list(rows)

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
                cassette_icon_path=self._cassette_icon_path,
                vinyl_icon_path=self._vinyl_icon_path,
                cd_icon_path=self._cd_icon_path,
                check_icon_path=self._check_icon_path,
                edit_icon_path=self._edit_icon_path,
                on_select=self._on_row_selected,
                selected=(row.row_id in self._selected_row_ids),
                selected_count=self._selected_count,
                on_background_selected=self._on_background_selected,
                on_background_toggle=self._on_background_toggle,
                on_enabled_media_changed=self._on_enabled_media_changed,
                on_name_committed=self._on_name_committed,
                on_side_selected=self._on_side_selected,
            )
            widget.place(x=spec.MEDIA_ROW_INSET_X, y=current_y)
            self.row_widgets.append(widget)
            current_y += widget.winfo_reqheight() + spec.MEDIA_ROW_GAP_Y
