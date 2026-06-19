from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import tkinter as tk

from new_music_builder.domain.models import AppearanceKind, MediaKind, MediaRow
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.collapsed_row_chevron import CollapsedRowChevron
from new_music_builder.ui.widgets.collapsed_row_details import CollapsedRowDetails
from new_music_builder.ui.widgets.media_live_preview import MediaLivePreview
from new_music_builder.ui.widgets.media_rename_field import MediaRenameField
from new_music_builder.ui.widgets.media_row_badge import MediaRowBadge
from new_music_builder.ui.widgets.media_row_cover import CollapsedMediaCover, ExpandedMediaCover
from new_music_builder.ui.widgets.media_song_actions import MediaSongActions
from new_music_builder.ui.widgets.media_side_toggle import MediaSideToggle
from new_music_builder.ui.widgets.media_songlist_viewport import MediaSonglistViewport
from new_music_builder.ui.widgets.media_songlist_table import TrackSelectionModifiers
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
        check_icon_path: str | None = None,
        edit_icon_path: str | None = None,
        ear_icon_path: str | None = None,
        grab_icon_path: str | None = None,
        table_check_icon_path: str | None = None,
        preview_audio_icon_path: str | None = None,
        resolve_live_preview_path: Callable[[MediaRow, AppearanceKind, str], str | None] | None = None,
        resolve_media_strip_path: Callable[[MediaRow, MediaKind, str], str | None] | None = None,
        on_select: Callable[[int], None] | None = None,
        selected: bool = False,
        selected_count: int = 0,
        on_background_selected: Callable[[int, RowSelectionModifiers], None] | None = None,
        on_enabled_media_changed: Callable[[int, MediaKind, bool], None] | None = None,
        on_name_committed: Callable[[int, str], None] | None = None,
        on_side_selected: Callable[[int, str], None] | None = None,
        on_preview_mode_selected: Callable[[int, str], None] | None = None,
        on_cover_selected: Callable[[int], None] | None = None,
        on_add_song: Callable[[int], None] | None = None,
        on_remove_song: Callable[[int], None] | None = None,
        selected_song_indices: set[int] | None = None,
        on_song_selected: Callable[[int, int, TrackSelectionModifiers], None] | None = None,
        on_song_remove_requested: Callable[[int, int], None] | None = None,
        on_song_drag_started: Callable[[int, int, int, int], None] | None = None,
        on_song_drag_moved: Callable[[int, int, int], None] | None = None,
        on_song_drag_finished: Callable[[int, int, int], None] | None = None,
        dnd_type: str | None = None,
        can_accept_song_drop: Callable[[list[str]], bool] | None = None,
        on_song_drop: Callable[[int, list[str]], None] | None = None,
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
        self._row = row
        self._expanded = expanded
        self._row_expanded = row.expanded
        self._selected = selected
        self._selected_count = selected_count
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

        self.expanded_container = tk.Frame(self.surface, bg=spec.MEDIA_ROW_BG, bd=0, highlightthickness=0)
        self.collapsed_container = tk.Frame(self.surface, bg=spec.MEDIA_ROW_BG, bd=0, highlightthickness=0)

        self.expanded_cover = ExpandedMediaCover(
            self.expanded_container,
            folder_icon_path=folder_icon_path,
            cover_path=row.cover_path,
            command=(lambda: on_cover_selected(row.row_id)) if on_cover_selected is not None else None,
        )
        self.expanded_cover.place(
            x=spec.MEDIA_ROW_EXPANDED_COVER_POS[0],
            y=spec.MEDIA_ROW_EXPANDED_COVER_POS[1],
        )
        self.expanded_badge = MediaRowBadge(
            self.expanded_container,
            row_number=row.row_id,
            command=(lambda: on_select(row.row_id)) if on_select is not None else None,
        )
        self.expanded_badge.place(x=spec.MEDIA_ROW_BADGE_EXPANDED_POS[0], y=spec.MEDIA_ROW_BADGE_EXPANDED_POS[1])
        self.rename_field = MediaRenameField(
            self.expanded_container,
            row=row,
            edit_icon_path=edit_icon_path,
            bg_color=spec.MEDIA_ROW_RENAME_BG,
            on_name_committed=on_name_committed,
        )
        self.rename_field.place(x=spec.MEDIA_ROW_RENAME_POS[0], y=spec.MEDIA_ROW_RENAME_POS[1])
        self.side_toggle = MediaSideToggle(
            self.expanded_container,
            row=row,
            bg_color=spec.MEDIA_ROW_BG,
            on_side_selected=on_side_selected,
        )
        self.side_toggle.place(x=spec.MEDIA_ROW_SIDE_TOGGLE_POS[0], y=spec.MEDIA_ROW_SIDE_TOGGLE_POS[1])
        self.songlist_viewport = MediaSonglistViewport(
            self.expanded_container,
            row=row,
            bg_color=spec.MEDIA_ROW_BG,
            ear_icon_path=ear_icon_path,
            grab_icon_path=grab_icon_path,
            table_check_icon_path=table_check_icon_path,
            preview_audio_icon_path=preview_audio_icon_path,
            selected_track_indices=selected_song_indices,
            on_track_selected=(lambda track_index, modifiers: on_song_selected(row.row_id, track_index, modifiers)) if on_song_selected is not None else None,
            on_track_remove_requested=(lambda track_index: on_song_remove_requested(row.row_id, track_index)) if on_song_remove_requested is not None else None,
            on_track_drag_started=(lambda track_index, x_root, y_root: on_song_drag_started(row.row_id, track_index, x_root, y_root)) if on_song_drag_started is not None else None,
            on_track_drag_moved=(lambda x_root, y_root: on_song_drag_moved(row.row_id, x_root, y_root)) if on_song_drag_moved is not None else None,
            on_track_drag_finished=(lambda x_root, y_root: on_song_drag_finished(row.row_id, x_root, y_root)) if on_song_drag_finished is not None else None,
            dnd_type=dnd_type,
            can_accept_drop=can_accept_song_drop,
            on_drop_files=(lambda paths: on_song_drop(row.row_id, paths)) if on_song_drop is not None else None,
        )
        self.songlist_viewport.place(x=spec.MEDIA_ROW_SONGLIST_VIEWPORT_POS[0], y=spec.MEDIA_ROW_SONGLIST_VIEWPORT_POS[1])
        self.song_actions = MediaSongActions(
            self.expanded_container,
            bg_color=spec.MEDIA_ROW_BG,
            on_add_song=(lambda: on_add_song(row.row_id)) if on_add_song is not None else None,
            on_remove_song=(lambda: on_remove_song(row.row_id)) if on_remove_song is not None else None,
        )
        self.song_actions.place(x=spec.MEDIA_ROW_SONG_ACTIONS_POS[0], y=spec.MEDIA_ROW_SONG_ACTIONS_POS[1])
        self.live_preview = MediaLivePreview(
            self.expanded_container,
            row=row,
            bg_color=spec.MEDIA_ROW_BG,
            resolve_preview_path=resolve_live_preview_path,
            on_mode_selected=on_preview_mode_selected,
        )
        self.live_preview.place(x=spec.MEDIA_ROW_LIVE_PREVIEW_POS[0], y=spec.MEDIA_ROW_LIVE_PREVIEW_POS[1])
        self.expanded_media_type_strip = MediaTypeStrip(
            self.expanded_container,
            row=row,
            expanded=True,
            check_icon_path=check_icon_path,
            bg_color=spec.MEDIA_ROW_BG,
            resolve_media_strip_path=resolve_media_strip_path,
            on_enabled_media_changed=on_enabled_media_changed,
        )
        self.expanded_media_type_strip.place(
            x=spec.MEDIA_ROW_MEDIA_STRIP_EXPANDED_POS[0],
            y=spec.MEDIA_ROW_MEDIA_STRIP_EXPANDED_POS[1],
        )

        self.collapsed_badge = MediaRowBadge(
            self.collapsed_container,
            row_number=row.row_id,
            command=(lambda: on_select(row.row_id)) if on_select is not None else None,
        )
        self.collapsed_badge.place(x=spec.MEDIA_ROW_BADGE_COLLAPSED_POS[0], y=spec.MEDIA_ROW_BADGE_COLLAPSED_POS[1])
        self.collapsed_cover = CollapsedMediaCover(
            self.collapsed_container,
            cover_path=row.cover_path,
        )
        self.collapsed_cover.place(x=spec.MEDIA_ROW_COLLAPSED_COVER_POS[0], y=spec.MEDIA_ROW_COLLAPSED_COVER_POS[1])
        self.collapsed_media_type_strip = MediaTypeStrip(
            self.collapsed_container,
            row=row,
            expanded=False,
            check_icon_path=check_icon_path,
            bg_color=spec.MEDIA_ROW_BG,
            resolve_media_strip_path=resolve_media_strip_path,
            on_enabled_media_changed=on_enabled_media_changed,
        )
        self.collapsed_media_type_strip.place(
            x=spec.MEDIA_ROW_MEDIA_STRIP_COLLAPSED_POS[0],
            y=spec.MEDIA_ROW_MEDIA_STRIP_COLLAPSED_POS[1],
        )
        self.collapsed_chevron = CollapsedRowChevron(
            self.collapsed_container,
            bg_color=spec.MEDIA_ROW_BG,
        )
        self.collapsed_chevron.place(
            x=spec.MEDIA_ROW_COLLAPSED_CHEVRON_POS[0],
            y=spec.MEDIA_ROW_COLLAPSED_CHEVRON_POS[1],
        )
        self.collapsed_details = CollapsedRowDetails(
            self.collapsed_container,
            row=row,
            bg_color=spec.MEDIA_ROW_BG,
        )
        self.collapsed_details.place(
            x=spec.MEDIA_ROW_COLLAPSED_DETAILS_POS[0],
            y=spec.MEDIA_ROW_COLLAPSED_DETAILS_POS[1],
        )
        for background_widget in (
            self.collapsed_cover,
            self.collapsed_media_type_strip,
            self.collapsed_chevron,
            self.collapsed_details,
        ):
            self._bind_widget_to_background_interactions(background_widget)
        self.badge = self.expanded_badge if expanded else self.collapsed_badge
        self.cover = self.expanded_cover if expanded else self.collapsed_cover
        self.media_type_strip = self.expanded_media_type_strip if expanded else self.collapsed_media_type_strip
        self.set_expanded(expanded)
        self._apply_background_state()

    def _bind_background_interactions(self) -> None:
        for sequence, handler in (
            ('<Enter>', self._on_background_enter),
            ('<Leave>', self._on_background_leave),
            ('<ButtonRelease-1>', self._on_background_release),
        ):
            self.surface.bind(sequence, handler)

    def _bind_widget_to_background_interactions(self, widget: tk.Misc) -> None:
        for sequence, handler in (
            ('<Enter>', self._on_background_enter),
            ('<Leave>', self._on_background_leave),
            ('<ButtonRelease-1>', self._on_background_release),
        ):
            widget.bind(sequence, handler, add='+')
        for child in widget.winfo_children():
            self._bind_widget_to_background_interactions(child)

    def _on_background_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._apply_background_state()

    def _on_background_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._apply_background_state()

    def _on_background_release(self, event: tk.Event) -> None:
        modifiers = self._decode_selection_modifiers(event)
        self._emit_background_selection(modifiers)

    def _apply_background_state(self) -> None:
        fill_color = spec.MEDIA_ROW_BG
        if self._selected and (self._selected_count > 1 or not self._row_expanded):
            fill_color = spec.MEDIA_ROW_ACTIVE_BG
        elif self._hovered:
            fill_color = spec.MEDIA_ROW_HOVER_BG
        self.surface.configure(bg=fill_color)
        self.expanded_container.configure(bg=fill_color)
        self.collapsed_container.configure(bg=fill_color)
        self.expanded_media_type_strip.set_bg_color(fill_color)
        self.collapsed_media_type_strip.set_bg_color(fill_color)
        self.side_toggle.set_bg_color(fill_color)
        self.song_actions.set_bg_color(fill_color)
        self.live_preview.set_bg_color(fill_color)
        self.collapsed_chevron.set_bg_color(fill_color)
        self.collapsed_details.set_bg_color(fill_color)

    def set_selection_state(self, *, selected: bool, selected_count: int) -> None:
        self._selected = selected
        self._selected_count = selected_count
        self._apply_background_state()

    def refresh_live_preview(self) -> None:
        if hasattr(self, 'live_preview'):
            self.live_preview.refresh_content()

    def refresh_cover(self, cover_path: str) -> None:
        self.expanded_cover.set_cover_path(cover_path)
        self.collapsed_cover.set_cover_path(cover_path)

    def refresh_song_table(self) -> None:
        self.songlist_viewport.refresh_content()

    def refresh_media_type_strip(self) -> None:
        self.expanded_media_type_strip.refresh_content()
        self.collapsed_media_type_strip.refresh_content()

    def set_song_selection_state(self, selected_song_indices: set[int]) -> None:
        self.songlist_viewport.set_selection_state(selected_song_indices)

    def begin_song_drag(self, dragged_indices: set[int], x_root: int, y_root: int) -> None:
        self.songlist_viewport.begin_drag(dragged_indices, x_root, y_root)

    def update_song_drag(self, x_root: int, y_root: int) -> None:
        self.songlist_viewport.update_drag(x_root, y_root)

    def finish_song_drag(self, x_root: int, y_root: int) -> int | None:
        return self.songlist_viewport.finish_drag(x_root, y_root)

    def current_song_insertion_index(self) -> int | None:
        return self.songlist_viewport.table.current_insertion_index()

    def cancel_song_drag(self) -> None:
        self.songlist_viewport.cancel_drag()

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._row_expanded = expanded
        self._row.expanded = expanded
        size = spec.MEDIA_ROW_EXPANDED_SIZE if expanded else spec.MEDIA_ROW_COLLAPSED_SIZE
        inner_width = size[0] - (spec.MEDIA_ROW_OUTLINE_WIDTH * 2)
        inner_height = size[1] - (spec.MEDIA_ROW_OUTLINE_WIDTH * 2)
        self.configure(width=size[0], height=size[1])
        self.surface.configure(width=inner_width, height=inner_height)
        if expanded:
            self.collapsed_container.place_forget()
            self.expanded_container.place(x=0, y=0, width=inner_width, height=inner_height)
            self.badge = self.expanded_badge
            self.cover = self.expanded_cover
            self.media_type_strip = self.expanded_media_type_strip
        else:
            self.expanded_container.place_forget()
            self.collapsed_container.place(x=0, y=0, width=inner_width, height=inner_height)
            self.badge = self.collapsed_badge
            self.cover = self.collapsed_cover
            self.media_type_strip = self.collapsed_media_type_strip
        self._apply_background_state()

    def _decode_selection_modifiers(self, event: tk.Event) -> RowSelectionModifiers:
        state = int(getattr(event, 'state', 0))
        shift = bool(state & 0x0001)
        additive = bool(state & 0x0004)
        return RowSelectionModifiers(shift=shift, additive=additive)

    def _emit_background_selection(self, modifiers: RowSelectionModifiers) -> None:
        if self._on_background_selected is not None:
            self._on_background_selected(self._row_id, modifiers)


class MediaRowList(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        rows: list[MediaRow],
        folder_icon_path: str | None = None,
        check_icon_path: str | None = None,
        edit_icon_path: str | None = None,
        ear_icon_path: str | None = None,
        grab_icon_path: str | None = None,
        table_check_icon_path: str | None = None,
        preview_audio_icon_path: str | None = None,
        resolve_live_preview_path: Callable[[MediaRow, AppearanceKind, str], str | None] | None = None,
        resolve_media_strip_path: Callable[[MediaRow, MediaKind, str], str | None] | None = None,
        bg_color: str | None = None,
        on_row_selected: Callable[[int], None] | None = None,
        selected_row_ids: set[int] | None = None,
        on_background_selected: Callable[[int, RowSelectionModifiers], None] | None = None,
        on_enabled_media_changed: Callable[[int, MediaKind, bool], None] | None = None,
        on_name_committed: Callable[[int, str], None] | None = None,
        on_side_selected: Callable[[int, str], None] | None = None,
        on_preview_mode_selected: Callable[[int, str], None] | None = None,
        on_cover_selected: Callable[[int], None] | None = None,
        on_add_song: Callable[[int], None] | None = None,
        on_remove_song: Callable[[int], None] | None = None,
        selected_song_indices_by_key: dict[tuple[int, str], set[int]] | None = None,
        on_song_selected: Callable[[int, int, TrackSelectionModifiers], None] | None = None,
        on_song_remove_requested: Callable[[int, int], None] | None = None,
        on_song_drag_started: Callable[[int, int, int, int], None] | None = None,
        on_song_drag_moved: Callable[[int, int, int], None] | None = None,
        on_song_drag_finished: Callable[[int, int, int], None] | None = None,
        dnd_type: str | None = None,
        can_accept_song_drop: Callable[[list[str]], bool] | None = None,
        on_song_drop: Callable[[int, list[str]], None] | None = None,
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
        self._check_icon_path = check_icon_path
        self._edit_icon_path = edit_icon_path
        self._ear_icon_path = ear_icon_path
        self._grab_icon_path = grab_icon_path
        self._table_check_icon_path = table_check_icon_path
        self._preview_audio_icon_path = preview_audio_icon_path
        self._resolve_live_preview_path = resolve_live_preview_path
        self._resolve_media_strip_path = resolve_media_strip_path
        self._on_row_selected = on_row_selected
        self._selected_row_ids = set(selected_row_ids or set())
        self._selected_count = len(self._selected_row_ids)
        self._on_background_selected = on_background_selected
        self._on_enabled_media_changed = on_enabled_media_changed
        self._on_name_committed = on_name_committed
        self._on_side_selected = on_side_selected
        self._on_preview_mode_selected = on_preview_mode_selected
        self._on_cover_selected = on_cover_selected
        self._on_add_song = on_add_song
        self._on_remove_song = on_remove_song
        self._selected_song_indices_by_key = {
            (row_id, side): set(indices)
            for (row_id, side), indices in (selected_song_indices_by_key or {}).items()
        }
        self._on_song_selected = on_song_selected
        self._on_song_remove_requested = on_song_remove_requested
        self._on_song_drag_started = on_song_drag_started
        self._on_song_drag_moved = on_song_drag_moved
        self._on_song_drag_finished = on_song_drag_finished
        self._dnd_type = dnd_type
        self._can_accept_song_drop = can_accept_song_drop
        self._on_song_drop = on_song_drop
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
        for row in self.rows:
            widget = MediaRowShell(
                self,
                row=row,
                expanded=row.expanded,
                folder_icon_path=self._folder_icon_path,
                check_icon_path=self._check_icon_path,
                edit_icon_path=self._edit_icon_path,
                ear_icon_path=self._ear_icon_path,
                grab_icon_path=self._grab_icon_path,
                table_check_icon_path=self._table_check_icon_path,
                preview_audio_icon_path=self._preview_audio_icon_path,
                resolve_live_preview_path=self._resolve_live_preview_path,
                resolve_media_strip_path=self._resolve_media_strip_path,
                on_select=self._on_row_selected,
                selected=(row.row_id in self._selected_row_ids),
                selected_count=self._selected_count,
                on_background_selected=self._on_background_selected,
                on_enabled_media_changed=self._on_enabled_media_changed,
                on_name_committed=self._on_name_committed,
                on_side_selected=self._on_side_selected,
                on_preview_mode_selected=self._on_preview_mode_selected,
                on_cover_selected=self._on_cover_selected,
                on_add_song=self._on_add_song,
                on_remove_song=self._on_remove_song,
                selected_song_indices=self._selected_song_indices_by_key.get((row.row_id, row.selected_side), set()),
                on_song_selected=self._on_song_selected,
                on_song_remove_requested=self._on_song_remove_requested,
                on_song_drag_started=self._on_song_drag_started,
                on_song_drag_moved=self._on_song_drag_moved,
                on_song_drag_finished=self._on_song_drag_finished,
                dnd_type=self._dnd_type,
                can_accept_song_drop=self._can_accept_song_drop,
                on_song_drop=self._on_song_drop,
            )
            self.row_widgets.append(widget)
        self.refresh_row_layouts()

    def set_selection_state(self, selected_row_ids: set[int]) -> None:
        self._selected_row_ids = set(selected_row_ids)
        self._selected_count = len(self._selected_row_ids)
        for row_widget in self.row_widgets:
            row_widget.set_selection_state(
                selected=(row_widget._row_id in self._selected_row_ids),
                selected_count=self._selected_count,
            )

    def refresh_media_type_strips_for_row(self, row_id: int) -> None:
        for row_widget in self.row_widgets:
            if row_widget._row_id == row_id:
                row_widget.refresh_media_type_strip()

    def set_expanded_row(self, row_id: int | None) -> None:
        for row, row_widget in zip(self.rows, self.row_widgets):
            row.expanded = row.row_id == row_id if row_id is not None else False
            row_widget.set_expanded(row.expanded)
        self.refresh_row_layouts()

    def refresh_row_layouts(self) -> None:
        current_y = spec.MEDIA_ROW_INSET_Y
        for row, row_widget in zip(self.rows, self.row_widgets):
            row_widget.set_expanded(row.expanded)
            row_widget.place(x=spec.MEDIA_ROW_INSET_X, y=current_y)
            current_y += row_widget.winfo_reqheight() + spec.MEDIA_ROW_GAP_Y
        self.configure(height=self._total_height_for_rows(self.rows))
