from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import tkinter as tk

from new_music_builder.domain.models import AppearanceKind, MediaKind, MediaRow, SongSortColumn
from new_music_builder.ui import spec
from new_music_builder.ui.help_tooltip_registry import TooltipSegment, tooltip_segments_for_id
from new_music_builder.ui.widgets.help_tooltip import bind_help_tooltip
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


class _CollapsedRowRemoveButton(tk.Label):
    def __init__(self, parent: tk.Misc, *, bg_color: str, command: Callable[[], None] | None = None) -> None:
        super().__init__(
            parent,
            text=spec.MEDIA_ROW_COLLAPSED_REMOVE_TEXT,
            bg=bg_color,
            fg=spec.MEDIA_ROW_COLLAPSED_REMOVE_TEXT_COLOR,
            font=(spec.MEDIA_ROW_COLLAPSED_REMOVE_FONT_FAMILY, spec.MEDIA_ROW_COLLAPSED_REMOVE_FONT_SIZE),
            bd=0,
            highlightthickness=0,
            cursor='hand2',
        )
        self._bg_color = bg_color
        self._command = command
        self._hovered = False
        self._pressed = False
        self._enabled = True
        for sequence, handler in (
            ('<Enter>', self._on_enter),
            ('<Leave>', self._on_leave),
            ('<ButtonPress-1>', self._on_press),
            ('<ButtonRelease-1>', self._on_release),
        ):
            self.bind(sequence, handler, add='+')

    def set_bg_color(self, color: str) -> None:
        self._bg_color = color
        self.configure(bg=color)

    def _current_fg(self) -> str:
        if self._pressed:
            return spec.MEDIA_ROW_COLLAPSED_REMOVE_PRESSED_COLOR
        if self._hovered:
            return spec.MEDIA_ROW_COLLAPSED_REMOVE_HOVER_COLOR
        return spec.MEDIA_ROW_COLLAPSED_REMOVE_TEXT_COLOR

    def _redraw(self) -> None:
        self.configure(bg=self._bg_color, fg=self._current_fg())

    def _on_enter(self, _event: tk.Event | None = None) -> str:
        if not self._enabled:
            return 'break'
        self._hovered = True
        self._redraw()
        return 'break'

    def _on_leave(self, _event: tk.Event | None = None) -> str:
        if not self._enabled:
            return 'break'
        self._hovered = False
        self._pressed = False
        self._redraw()
        return 'break'

    def _on_press(self, _event: tk.Event | None = None) -> str:
        if not self._enabled:
            return 'break'
        self._pressed = True
        self._redraw()
        return 'break'

    def _on_release(self, event: tk.Event | None = None) -> str:
        if not self._enabled:
            return 'break'
        was_pressed = self._pressed
        self._pressed = False
        inside = False
        if event is not None:
            inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self._redraw()
        if was_pressed and inside and self._command is not None:
            self._command()
        return 'break'

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self._hovered = False
        self._pressed = False
        self.configure(fg=spec.MEDIA_ROW_COLLAPSED_REMOVE_TEXT_COLOR if enabled else '#8f8a92')


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
        automatic_textures_enabled_getter: Callable[[], bool] | None = None,
        can_accept_cover_drop: Callable[[list[str]], bool] | None = None,
        on_cover_drop: Callable[[int, list[str]], None] | None = None,
        on_remove_row: Callable[[int], None] | None = None,
        on_add_song: Callable[[int], None] | None = None,
        on_remove_song: Callable[[int], None] | None = None,
        selected_song_indices: set[int] | None = None,
        on_song_selected: Callable[[int, int, TrackSelectionModifiers], None] | None = None,
        on_song_remove_requested: Callable[[int, int], None] | None = None,
        on_song_sort_requested: Callable[[int, SongSortColumn], None] | None = None,
        on_song_drag_started: Callable[[int, int, int, int], None] | None = None,
        on_song_drag_moved: Callable[[int, int, int], None] | None = None,
        on_song_drag_finished: Callable[[int, int, int], None] | None = None,
        on_row_drag_started: Callable[[int, int, int], None] | None = None,
        on_row_drag_moved: Callable[[int, int, int], None] | None = None,
        on_row_drag_finished: Callable[[int, int, int], None] | None = None,
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
        self._automatic_textures_enabled_getter = automatic_textures_enabled_getter
        self._hovered = False
        self._on_select = on_select
        self._on_background_selected = on_background_selected
        self._on_enabled_media_changed = on_enabled_media_changed
        self._on_name_committed = on_name_committed
        self._on_side_selected = on_side_selected
        self._on_preview_mode_selected = on_preview_mode_selected
        self._on_cover_selected = on_cover_selected
        self._can_accept_cover_drop = can_accept_cover_drop
        self._on_cover_drop = on_cover_drop
        self._on_remove_row = on_remove_row
        self._on_add_song = on_add_song
        self._on_remove_song = on_remove_song
        self._on_song_selected = on_song_selected
        self._on_song_remove_requested = on_song_remove_requested
        self._on_song_sort_requested = on_song_sort_requested
        self._on_song_drag_started = on_song_drag_started
        self._on_song_drag_moved = on_song_drag_moved
        self._on_song_drag_finished = on_song_drag_finished
        self._on_row_drag_started = on_row_drag_started
        self._on_row_drag_moved = on_row_drag_moved
        self._on_row_drag_finished = on_row_drag_finished
        self._pending_collapsed_drag = False
        self._collapsed_drag_active = False
        self._locked = False
        self._collapsed_drag_press_x_root = 0
        self._collapsed_drag_press_y_root = 0
        self._collapsed_drag_modifiers = RowSelectionModifiers()
        self._collapsed_drag_motion_bind_id: str | None = None
        self._collapsed_drag_release_bind_id: str | None = None

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

        self.expanded_container = tk.Frame(self.surface, bg=spec.MEDIA_ROW_BG, bd=0, highlightthickness=0)
        self.collapsed_container = tk.Frame(self.surface, bg=spec.MEDIA_ROW_BG, bd=0, highlightthickness=0)

        self.expanded_cover = ExpandedMediaCover(
            self.expanded_container,
            folder_icon_path=folder_icon_path,
            cover_path=row.cover_path,
            command=self._handle_cover_selected if on_cover_selected is not None else None,
            dnd_type=dnd_type,
            can_accept_drop=can_accept_cover_drop,
            on_drop_files=self._handle_cover_drop if on_cover_drop is not None else None,
        )
        self.expanded_cover.place(
            x=spec.MEDIA_ROW_EXPANDED_COVER_POS[0],
            y=spec.MEDIA_ROW_EXPANDED_COVER_POS[1],
        )
        self._expanded_cover_tooltip = bind_help_tooltip(
            self.expanded_cover.tooltip_widgets(),
            tooltip_id='module_two.media_cover',
            segments_getter=self._media_cover_tooltip_segments,
        )
        self.expanded_badge = MediaRowBadge(
            self.expanded_container,
            row_number=row.row_id,
            command=self._handle_select if on_select is not None else None,
        )
        self.expanded_badge.place(x=spec.MEDIA_ROW_BADGE_EXPANDED_POS[0], y=spec.MEDIA_ROW_BADGE_EXPANDED_POS[1])
        self._expanded_badge_tooltip = bind_help_tooltip(
            (self.expanded_badge,),
            tooltip_id='module_two.row_badge',
        )
        self.rename_field = MediaRenameField(
            self.expanded_container,
            row=row,
            edit_icon_path=edit_icon_path,
            bg_color=spec.MEDIA_ROW_RENAME_BG,
            on_name_committed=self._handle_name_committed,
        )
        self.rename_field.place(x=spec.MEDIA_ROW_RENAME_POS[0], y=spec.MEDIA_ROW_RENAME_POS[1])
        self._rename_field_tooltip = bind_help_tooltip(
            self.rename_field.tooltip_widgets(),
            tooltip_id='module_two.media_name',
        )
        self.side_toggle = MediaSideToggle(
            self.expanded_container,
            row=row,
            bg_color=spec.MEDIA_ROW_BG,
            on_side_selected=self._handle_side_selected,
        )
        self.side_toggle.place(x=spec.MEDIA_ROW_SIDE_TOGGLE_POS[0], y=spec.MEDIA_ROW_SIDE_TOGGLE_POS[1])
        self._side_a_tooltip = bind_help_tooltip(
            self.side_toggle.tooltip_widgets_for_side('A'),
            tooltip_id='module_two.side_a',
        )
        self._side_b_tooltip = bind_help_tooltip(
            self.side_toggle.tooltip_widgets_for_side('B'),
            tooltip_id='module_two.side_b',
        )
        self.songlist_viewport = MediaSonglistViewport(
            self.expanded_container,
            row=row,
            bg_color=spec.MEDIA_ROW_BG,
            ear_icon_path=ear_icon_path,
            grab_icon_path=grab_icon_path,
            table_check_icon_path=table_check_icon_path,
            preview_audio_icon_path=preview_audio_icon_path,
            selected_track_indices=selected_song_indices,
            on_track_selected=self._handle_song_selected,
            on_track_remove_requested=self._handle_song_remove_requested,
            on_header_sort_requested=self._handle_song_sort_requested,
            on_track_drag_started=self._handle_song_drag_started,
            on_track_drag_moved=self._handle_song_drag_moved,
            on_track_drag_finished=self._handle_song_drag_finished,
            dnd_type=dnd_type,
            can_accept_drop=can_accept_song_drop,
            on_drop_files=self._handle_song_drop if on_song_drop is not None else None,
        )
        self.songlist_viewport.place(x=spec.MEDIA_ROW_SONGLIST_VIEWPORT_POS[0], y=spec.MEDIA_ROW_SONGLIST_VIEWPORT_POS[1])
        self._song_table_tooltip = bind_help_tooltip(
            self.songlist_viewport.header_tooltip_widgets(),
            tooltip_id='module_two.song_table',
            should_show=self.songlist_viewport.is_pointer_in_header,
        )
        self.song_actions = MediaSongActions(
            self.expanded_container,
            bg_color=spec.MEDIA_ROW_BG,
            on_add_song=self._handle_add_song if on_add_song is not None else None,
            on_remove_song=self._handle_remove_song if on_remove_song is not None else None,
        )
        self.song_actions.place(x=spec.MEDIA_ROW_SONG_ACTIONS_POS[0], y=spec.MEDIA_ROW_SONG_ACTIONS_POS[1])
        self._add_song_tooltip = bind_help_tooltip(
            self.song_actions.tooltip_widgets_for_add(),
            tooltip_id='module_two.add_song',
            preferred_direction='down',
        )
        self._remove_song_tooltip = bind_help_tooltip(
            self.song_actions.tooltip_widgets_for_remove(),
            tooltip_id='module_two.remove_song',
            preferred_direction='down',
        )
        self.live_preview = MediaLivePreview(
            self.expanded_container,
            row=row,
            bg_color=spec.MEDIA_ROW_BG,
            resolve_preview_path=resolve_live_preview_path,
            on_mode_selected=self._handle_preview_mode_selected,
        )
        self.live_preview.place(x=spec.MEDIA_ROW_LIVE_PREVIEW_POS[0], y=spec.MEDIA_ROW_LIVE_PREVIEW_POS[1])
        self._live_preview_tooltip = bind_help_tooltip(
            self.live_preview.help_tooltip_widgets(),
            tooltip_id='module_two.live_preview',
            preferred_direction='down',
        )
        self.expanded_media_type_strip = MediaTypeStrip(
            self.expanded_container,
            row=row,
            expanded=True,
            check_icon_path=check_icon_path,
            bg_color=spec.MEDIA_ROW_BG,
            resolve_media_strip_path=resolve_media_strip_path,
            on_enabled_media_changed=self._handle_enabled_media_changed,
        )
        self.expanded_media_type_strip.place(
            x=spec.MEDIA_ROW_MEDIA_STRIP_EXPANDED_POS[0],
            y=spec.MEDIA_ROW_MEDIA_STRIP_EXPANDED_POS[1],
        )
        self._expanded_media_checkbox_tooltips = {
            'cassette': bind_help_tooltip(
                self.expanded_media_type_strip.checkbox_tooltip_widgets_for_kind('cassette'),
                tooltip_id='module_two.media_checkbox.cassette',
            ),
            'vinyl': bind_help_tooltip(
                self.expanded_media_type_strip.checkbox_tooltip_widgets_for_kind('vinyl'),
                tooltip_id='module_two.media_checkbox.vinyl',
            ),
            'cd': bind_help_tooltip(
                self.expanded_media_type_strip.checkbox_tooltip_widgets_for_kind('cd'),
                tooltip_id='module_two.media_checkbox.cd',
            ),
        }

        self.collapsed_badge = MediaRowBadge(
            self.collapsed_container,
            row_number=row.row_id,
            command=self._handle_select if on_select is not None else None,
        )
        self.collapsed_badge.place(x=spec.MEDIA_ROW_BADGE_COLLAPSED_POS[0], y=spec.MEDIA_ROW_BADGE_COLLAPSED_POS[1])
        self._collapsed_badge_tooltip = bind_help_tooltip(
            (self.collapsed_badge,),
            tooltip_id='module_two.row_badge',
        )
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
            on_enabled_media_changed=self._handle_enabled_media_changed,
        )
        self.collapsed_media_type_strip.place(
            x=spec.MEDIA_ROW_MEDIA_STRIP_COLLAPSED_POS[0],
            y=spec.MEDIA_ROW_MEDIA_STRIP_COLLAPSED_POS[1],
        )
        self._collapsed_media_icon_tooltips = {
            'cassette': bind_help_tooltip(
                self.collapsed_media_type_strip.collapsed_tooltip_widgets_for_kind('cassette'),
                tooltip_id='module_two.collapsed_media.cassette',
            ),
            'vinyl': bind_help_tooltip(
                self.collapsed_media_type_strip.collapsed_tooltip_widgets_for_kind('vinyl'),
                tooltip_id='module_two.collapsed_media.vinyl',
            ),
            'cd': bind_help_tooltip(
                self.collapsed_media_type_strip.collapsed_tooltip_widgets_for_kind('cd'),
                tooltip_id='module_two.collapsed_media.cd',
            ),
        }
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
        self.collapsed_remove_button = _CollapsedRowRemoveButton(
            self.collapsed_container,
            bg_color=spec.MEDIA_ROW_BG,
            command=self._handle_remove_row if on_remove_row is not None else None,
        )
        for background_widget in (
            self.collapsed_cover,
            self.collapsed_media_type_strip,
            self.collapsed_chevron,
            self.collapsed_details,
        ):
            self._bind_widget_to_background_interactions(background_widget)
        for sequence, handler in (
            ('<Enter>', self._on_background_enter),
            ('<Leave>', self._on_background_leave),
            ('<ButtonPress-1>', self._on_collapsed_background_press),
            ('<B1-Motion>', self._on_collapsed_background_motion),
            ('<ButtonRelease-1>', self._on_background_release),
        ):
            self.collapsed_container.bind(sequence, handler, add='+')
        self.badge = self.expanded_badge if expanded else self.collapsed_badge
        self.cover = self.expanded_cover if expanded else self.collapsed_cover
        self.media_type_strip = self.expanded_media_type_strip if expanded else self.collapsed_media_type_strip
        self._last_resized_width: int | None = None
        self._last_live_preview_x: int | None = None
        self._last_songlist_width: int | None = None
        self.set_expanded(expanded)
        self._apply_background_state()

    def _media_cover_tooltip_segments(self) -> tuple[TooltipSegment, ...]:
        base_segments = tooltip_segments_for_id('module_two.media_cover') or ()
        if self._automatic_textures_enabled_getter is None or self._automatic_textures_enabled_getter():
            return base_segments
        return tuple(
            segment
            for segment in base_segments
            if segment.tone not in {'tag', 'break'}
        )

    def resize(self, width: int) -> None:
        if self._last_resized_width == width:
            return
        self._last_resized_width = width
        size = (width, spec.MEDIA_ROW_EXPANDED_SIZE[1]) if self._expanded else (width, spec.MEDIA_ROW_COLLAPSED_SIZE[1])
        inner_width = size[0] - (spec.MEDIA_ROW_OUTLINE_WIDTH * 2)
        inner_height = size[1] - (spec.MEDIA_ROW_OUTLINE_WIDTH * 2)
        self.configure(width=size[0], height=size[1])
        self.surface.configure(width=inner_width, height=inner_height)
        self.surface.place_configure(x=spec.MEDIA_ROW_OUTLINE_WIDTH, y=spec.MEDIA_ROW_OUTLINE_WIDTH, width=inner_width, height=inner_height)
        if self._expanded:
            self.expanded_container.place_configure(x=0, y=0, width=inner_width, height=inner_height)
            live_preview_right_inset = (
                spec.MEDIA_ROW_EXPANDED_SIZE[0]
                - spec.MEDIA_ROW_LIVE_PREVIEW_POS[0]
                - spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[0]
                - (spec.MEDIA_ROW_OUTLINE_WIDTH * 2)
            )
            songlist_gap_to_preview = (
                spec.MEDIA_ROW_LIVE_PREVIEW_POS[0]
                - spec.MEDIA_ROW_SONGLIST_VIEWPORT_POS[0]
                - spec.MEDIA_ROW_SONGLIST_VIEWPORT_SIZE[0]
            )
            live_preview_x = inner_width - spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[0] - live_preview_right_inset
            songlist_width = max(
                spec.MEDIA_ROW_SONGLIST_VIEWPORT_SIZE[0],
                live_preview_x - spec.MEDIA_ROW_SONGLIST_VIEWPORT_POS[0] - songlist_gap_to_preview,
            )
            if self._last_songlist_width != songlist_width:
                self.songlist_viewport.resize(songlist_width)
                self.songlist_viewport.place_configure(
                    x=spec.MEDIA_ROW_SONGLIST_VIEWPORT_POS[0],
                    y=spec.MEDIA_ROW_SONGLIST_VIEWPORT_POS[1],
                    width=songlist_width,
                    height=spec.MEDIA_ROW_SONGLIST_VIEWPORT_SIZE[1],
                )
                self._last_songlist_width = songlist_width
            if self._last_live_preview_x != live_preview_x:
                self.live_preview.place_configure(
                    x=live_preview_x,
                    y=spec.MEDIA_ROW_LIVE_PREVIEW_POS[1],
                    width=spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[0],
                    height=spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[1],
                )
                self._last_live_preview_x = live_preview_x
        else:
            self.collapsed_container.place_configure(x=0, y=0, width=inner_width, height=inner_height)
            self.collapsed_remove_button.place_configure(
                x=inner_width - spec.MEDIA_ROW_COLLAPSED_REMOVE_RIGHT_INSET,
                y=inner_height / 2,
                anchor='center',
            )

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
            ('<ButtonPress-1>', self._on_collapsed_background_press),
            ('<B1-Motion>', self._on_collapsed_background_motion),
            ('<ButtonRelease-1>', self._on_background_release),
        ):
            widget.bind(sequence, handler, add='+')
        for child in widget.winfo_children():
            self._bind_widget_to_background_interactions(child)

    def _on_background_enter(self, _event: tk.Event) -> None:
        if self._locked:
            return
        self._hovered = True
        self._apply_background_state()

    def _on_background_leave(self, _event: tk.Event) -> None:
        if self._locked:
            return
        self._hovered = False
        self._apply_background_state()

    def _on_background_release(self, event: tk.Event) -> None:
        if self._locked:
            return
        if not self._expanded:
            x_root = int(getattr(event, 'x_root', 0))
            y_root = int(getattr(event, 'y_root', 0))
            if self._collapsed_drag_active:
                if self._on_row_drag_finished is not None:
                    self._on_row_drag_finished(self._row_id, x_root, y_root)
                self._cancel_collapsed_row_drag()
                return
            if self._pending_collapsed_drag:
                modifiers = self._collapsed_drag_modifiers
                self._cancel_collapsed_row_drag()
                self._emit_background_selection(modifiers)
                return
        modifiers = self._decode_selection_modifiers(event)
        self._emit_background_selection(modifiers)

    def _on_collapsed_background_press(self, event: tk.Event) -> str:
        if self._locked:
            return 'break'
        if self._expanded:
            return 'break'
        self._pending_collapsed_drag = True
        self._collapsed_drag_active = False
        self._collapsed_drag_press_x_root = int(getattr(event, 'x_root', 0))
        self._collapsed_drag_press_y_root = int(getattr(event, 'y_root', 0))
        self._collapsed_drag_modifiers = self._decode_selection_modifiers(event)
        return 'break'

    def _on_collapsed_background_motion(self, event: tk.Event) -> str:
        if self._locked:
            return 'break'
        if self._expanded or not self._pending_collapsed_drag:
            return 'break'
        x_root = int(getattr(event, 'x_root', 0))
        y_root = int(getattr(event, 'y_root', 0))
        if not self._collapsed_drag_active:
            dx = abs(x_root - self._collapsed_drag_press_x_root)
            dy = abs(y_root - self._collapsed_drag_press_y_root)
            if max(dx, dy) < spec.MEDIA_ROW_SONGLIST_DRAG_THRESHOLD_PX:
                return 'break'
            self._collapsed_drag_active = True
            self._bind_collapsed_drag_capture()
            if self._on_row_drag_started is not None:
                self._on_row_drag_started(self._row_id, x_root, y_root)
        if self._on_row_drag_moved is not None:
            self._on_row_drag_moved(self._row_id, x_root, y_root)
        return 'break'

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
        self.collapsed_remove_button.set_bg_color(fill_color)

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

    def refresh_collapsed_details(self) -> None:
        self.collapsed_details.refresh_content(self._row)

    def set_song_selection_state(self, selected_song_indices: set[int]) -> None:
        self.songlist_viewport.set_selection_state(selected_song_indices)


    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        self.collapsed_remove_button.set_enabled(not locked)
        self.rename_field.set_enabled(not locked)
        self.song_actions.set_enabled(not locked)
        self.expanded_media_type_strip.set_enabled(not locked)
        self.collapsed_media_type_strip.set_enabled(not locked)
        self.expanded_cover.set_enabled(not locked)
        if locked:
            self._hovered = False
        self._apply_background_state()

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

    def cancel_row_drag(self) -> None:
        self._cancel_collapsed_row_drag()

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._row_expanded = expanded
        self._row.expanded = expanded
        self._last_resized_width = None
        self._last_live_preview_x = None
        self._last_songlist_width = None
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
            self.collapsed_remove_button.place(
                x=inner_width - spec.MEDIA_ROW_COLLAPSED_REMOVE_RIGHT_INSET,
                y=inner_height / 2,
                anchor='center',
            )
            self.badge = self.collapsed_badge
            self.cover = self.collapsed_cover
            self.media_type_strip = self.collapsed_media_type_strip
        self._apply_background_state()

    def set_row(self, row: MediaRow) -> None:
        self._row = row
        self._row_id = row.row_id
        self.rename_field.set_row(row)
        self.side_toggle.set_row(row)
        self.songlist_viewport.set_row(row)
        self.live_preview.set_row(row)
        self.expanded_media_type_strip.set_row(row)
        self.collapsed_media_type_strip.set_row(row)
        self.refresh_cover(row.cover_path)
        self.refresh_collapsed_details()

    def _handle_select(self) -> None:
        if self._on_select is not None:
            self._on_select(self._row_id)

    def _handle_cover_selected(self) -> None:
        if self._on_cover_selected is not None:
            self._on_cover_selected(self._row_id)

    def _handle_cover_drop(self, paths: list[str]) -> None:
        if self._on_cover_drop is not None:
            self._on_cover_drop(self._row_id, paths)

    def _handle_enabled_media_changed(self, kind: MediaKind, enabled: bool) -> None:
        if self._on_enabled_media_changed is not None:
            self._on_enabled_media_changed(self._row_id, kind, enabled)

    def _handle_name_committed(self, value: str) -> None:
        if self._on_name_committed is not None:
            self._on_name_committed(self._row_id, value)

    def _handle_side_selected(self, side: str) -> None:
        if self._on_side_selected is not None:
            self._on_side_selected(self._row_id, side)

    def _handle_preview_mode_selected(self, mode: str) -> None:
        if self._on_preview_mode_selected is not None:
            self._on_preview_mode_selected(self._row_id, mode)

    def _handle_remove_row(self) -> None:
        if self._on_remove_row is not None:
            self._on_remove_row(self._row_id)

    def _handle_add_song(self) -> None:
        if self._on_add_song is not None:
            self._on_add_song(self._row_id)

    def _handle_remove_song(self) -> None:
        if self._on_remove_song is not None:
            self._on_remove_song(self._row_id)

    def _handle_song_selected(self, track_index: int, modifiers: TrackSelectionModifiers) -> None:
        if self._on_song_selected is not None:
            self._on_song_selected(self._row_id, track_index, modifiers)

    def _handle_song_remove_requested(self, track_index: int) -> None:
        if self._on_song_remove_requested is not None:
            self._on_song_remove_requested(self._row_id, track_index)

    def _handle_song_sort_requested(self, column: SongSortColumn) -> None:
        if self._on_song_sort_requested is not None:
            self._on_song_sort_requested(self._row_id, column)

    def _handle_song_drag_started(self, track_index: int, x_root: int, y_root: int) -> None:
        if self._on_song_drag_started is not None:
            self._on_song_drag_started(self._row_id, track_index, x_root, y_root)

    def _handle_song_drag_moved(self, x_root: int, y_root: int) -> None:
        if self._on_song_drag_moved is not None:
            self._on_song_drag_moved(self._row_id, x_root, y_root)

    def _handle_song_drag_finished(self, x_root: int, y_root: int) -> None:
        if self._on_song_drag_finished is not None:
            self._on_song_drag_finished(self._row_id, x_root, y_root)

    def _handle_song_drop(self, paths: list[str]) -> None:
        if self._on_song_drop is not None:
            self._on_song_drop(self._row_id, paths)

    def _decode_selection_modifiers(self, event: tk.Event) -> RowSelectionModifiers:
        state = int(getattr(event, 'state', 0))
        shift = bool(state & 0x0001)
        additive = bool(state & 0x0004)
        return RowSelectionModifiers(shift=shift, additive=additive)

    def _emit_background_selection(self, modifiers: RowSelectionModifiers) -> None:
        if self._on_background_selected is not None:
            self._on_background_selected(self._row_id, modifiers)

    def _cancel_collapsed_row_drag(self) -> None:
        self._pending_collapsed_drag = False
        self._collapsed_drag_active = False
        self._unbind_collapsed_drag_capture()

    def _bind_collapsed_drag_capture(self) -> None:
        owner = self.winfo_toplevel()
        self._unbind_collapsed_drag_capture()
        self._collapsed_drag_motion_bind_id = owner.bind('<B1-Motion>', self._on_captured_collapsed_drag_motion, add='+')
        self._collapsed_drag_release_bind_id = owner.bind('<ButtonRelease-1>', self._on_captured_collapsed_drag_release, add='+')

    def _unbind_collapsed_drag_capture(self) -> None:
        owner = self.winfo_toplevel()
        if self._collapsed_drag_motion_bind_id is not None:
            owner.unbind('<B1-Motion>', self._collapsed_drag_motion_bind_id)
            self._collapsed_drag_motion_bind_id = None
        if self._collapsed_drag_release_bind_id is not None:
            owner.unbind('<ButtonRelease-1>', self._collapsed_drag_release_bind_id)
            self._collapsed_drag_release_bind_id = None

    def _on_captured_collapsed_drag_motion(self, event: tk.Event) -> str | None:
        if not self._collapsed_drag_active:
            return None
        if self._on_row_drag_moved is not None:
            self._on_row_drag_moved(
                self._row_id,
                int(getattr(event, 'x_root', 0)),
                int(getattr(event, 'y_root', 0)),
            )
        return 'break'

    def _on_captured_collapsed_drag_release(self, event: tk.Event) -> str | None:
        if not self._collapsed_drag_active:
            return None
        if self._on_row_drag_finished is not None:
            self._on_row_drag_finished(
                self._row_id,
                int(getattr(event, 'x_root', 0)),
                int(getattr(event, 'y_root', 0)),
            )
        self._cancel_collapsed_row_drag()
        return 'break'


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
        automatic_textures_enabled_getter: Callable[[], bool] | None = None,
        can_accept_cover_drop: Callable[[list[str]], bool] | None = None,
        on_cover_drop: Callable[[int, list[str]], None] | None = None,
        on_remove_row: Callable[[int], None] | None = None,
        on_add_song: Callable[[int], None] | None = None,
        on_remove_song: Callable[[int], None] | None = None,
        selected_song_indices_by_key: dict[tuple[int, str], set[int]] | None = None,
        on_song_selected: Callable[[int, int, TrackSelectionModifiers], None] | None = None,
        on_song_remove_requested: Callable[[int, int], None] | None = None,
        on_song_sort_requested: Callable[[int, SongSortColumn], None] | None = None,
        on_song_drag_started: Callable[[int, int, int, int], None] | None = None,
        on_song_drag_moved: Callable[[int, int, int], None] | None = None,
        on_song_drag_finished: Callable[[int, int, int], None] | None = None,
        on_row_drag_started: Callable[[int, int, int], None] | None = None,
        on_row_drag_moved: Callable[[int, int, int], None] | None = None,
        on_row_drag_finished: Callable[[int, int, int], None] | None = None,
        dnd_type: str | None = None,
        can_accept_song_drop: Callable[[list[str]], bool] | None = None,
        on_song_drop: Callable[[int, list[str]], None] | None = None,
    ) -> None:
        resolved_bg = bg_color if bg_color is not None else parent.cget('bg')
        self._display_expanded_row_id: int | None = None
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
        self._automatic_textures_enabled_getter = automatic_textures_enabled_getter
        self._can_accept_cover_drop = can_accept_cover_drop
        self._on_cover_drop = on_cover_drop
        self._on_remove_row = on_remove_row
        self._on_add_song = on_add_song
        self._on_remove_song = on_remove_song
        self._selected_song_indices_by_key = {
            (row_id, side): set(indices)
            for (row_id, side), indices in (selected_song_indices_by_key or {}).items()
        }
        self._on_song_selected = on_song_selected
        self._on_song_remove_requested = on_song_remove_requested
        self._on_song_sort_requested = on_song_sort_requested
        self._on_song_drag_started = on_song_drag_started
        self._on_song_drag_moved = on_song_drag_moved
        self._on_song_drag_finished = on_song_drag_finished
        self._on_row_drag_started = on_row_drag_started
        self._on_row_drag_moved = on_row_drag_moved
        self._on_row_drag_finished = on_row_drag_finished
        self._bg_color = resolved_bg
        self._dnd_type = dnd_type
        self._can_accept_song_drop = can_accept_song_drop
        self._on_song_drop = on_song_drop
        self.row_widgets: list[MediaRowShell] = []
        self._last_width = spec.MEDIA_ROW_LIST_WIDTH
        self._row_drag_ids: list[int] = []
        self._row_drag_active = False
        self._row_drag_pointer_offset_y = 0
        self._row_drag_cursor_local_y: int | None = None
        self._row_drag_insertion_index: int | None = None
        self._drag_insertion_outline = tk.Frame(
            self,
            bg=resolved_bg,
            bd=0,
            highlightbackground=spec.MEDIA_ROW_SONGLIST_DRAG_INSERT_COLOR,
            highlightcolor=spec.MEDIA_ROW_SONGLIST_DRAG_INSERT_COLOR,
            highlightthickness=1,
            width=spec.MEDIA_ROW_COLLAPSED_SIZE[0],
            height=spec.MEDIA_ROW_COLLAPSED_SIZE[1],
        )

        self._build_rows()
        self._locked = False

    def _create_row_widget(self, row: MediaRow) -> MediaRowShell:
        return MediaRowShell(
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
            automatic_textures_enabled_getter=self._automatic_textures_enabled_getter,
            can_accept_cover_drop=self._can_accept_cover_drop,
            on_cover_drop=self._on_cover_drop,
            on_remove_row=self._on_remove_row,
            on_add_song=self._on_add_song,
            on_remove_song=self._on_remove_song,
            selected_song_indices=self._selected_song_indices_by_key.get((row.row_id, row.selected_side), set()),
            on_song_selected=self._on_song_selected,
            on_song_remove_requested=self._on_song_remove_requested,
            on_song_sort_requested=self._on_song_sort_requested,
            on_song_drag_started=self._on_song_drag_started,
            on_song_drag_moved=self._on_song_drag_moved,
            on_song_drag_finished=self._on_song_drag_finished,
            on_row_drag_started=self._on_row_drag_started,
            on_row_drag_moved=self._on_row_drag_moved,
            on_row_drag_finished=self._on_row_drag_finished,
            dnd_type=self._dnd_type,
            can_accept_song_drop=self._can_accept_song_drop,
            on_song_drop=self._on_song_drop,
        )

    def resize(self, width: int) -> None:
        if self._last_width == width:
            return
        self._last_width = width
        self.configure(width=width)
        self.refresh_row_layouts()

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
            height += spec.MEDIA_ROW_EXPANDED_SIZE[1] if self._expansion_state_for_row(row) else spec.MEDIA_ROW_COLLAPSED_SIZE[1]
            if index < len(rows) - 1:
                height += spec.MEDIA_ROW_GAP_Y
        height += spec.MEDIA_ROW_INSET_Y
        return max(height, spec.MODULE_TWO_SCROLL_VIEWPORT_SIZE[1])

    def _build_rows(self) -> None:
        for row in self.rows:
            widget = self._create_row_widget(row)
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

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        for row_widget in self.row_widgets:
            row_widget.set_locked(locked)

    def reorder_rows(self, rows: list[MediaRow]) -> None:
        self.rows = list(rows)
        widget_by_id = {widget._row_id: widget for widget in self.row_widgets}
        self.row_widgets = [widget_by_id[row.row_id] for row in self.rows if row.row_id in widget_by_id]
        self.refresh_row_layouts()

    def refresh_badge_numbers(self, start_index: int = 0) -> None:
        start_index = max(0, min(start_index, len(self.row_widgets)))
        for index, row_widget in enumerate(self.row_widgets[start_index:], start=start_index + 1):
            row_widget.expanded_badge.set_row_number(index)
            row_widget.collapsed_badge.set_row_number(index)

    def refresh_media_type_strips_for_row(self, row_id: int) -> None:
        for row_widget in self.row_widgets:
            if row_widget._row_id == row_id:
                row_widget.refresh_media_type_strip()

    def refresh_media_type_strips(self) -> None:
        for row_widget in self.row_widgets:
            row_widget.refresh_media_type_strip()

    def refresh_collapsed_details_for_row(self, row_id: int) -> None:
        for row_widget in self.row_widgets:
            if row_widget._row_id == row_id:
                row_widget.refresh_collapsed_details()

    def refresh_collapsed_details(self) -> None:
        for row_widget in self.row_widgets:
            row_widget.refresh_collapsed_details()

    def set_expanded_row(self, row_id: int | None) -> None:
        self._display_expanded_row_id = None
        affected_indices: list[int] = []
        for index, (row, row_widget) in enumerate(zip(self.rows, self.row_widgets)):
            should_expand = row.row_id == row_id if row_id is not None else False
            if row.expanded == should_expand and row_widget._expanded == should_expand:
                continue
            row.expanded = should_expand
            row_widget.set_expanded(should_expand)
            affected_indices.append(index)
        if not affected_indices:
            return
        start_index = min(affected_indices)
        self.refresh_badge_numbers(start_index)
        self.refresh_row_layouts(start_index=start_index, refresh_badges=False)

    def set_browse_expanded_row(self, row_id: int | None) -> None:
        previous_row_id = self._display_expanded_row_id
        self._display_expanded_row_id = row_id
        if previous_row_id == row_id:
            return
        affected_indices = [
            index
            for index, row in enumerate(self.rows)
            if row.row_id == previous_row_id or row.row_id == row_id
        ]
        self.refresh_row_layouts(start_index=min(affected_indices) if affected_indices else 0)

    def refresh_row_layouts(self, start_index: int = 0, *, refresh_badges: bool = True) -> None:
        start_index = max(0, min(start_index, len(self.row_widgets)))
        if refresh_badges:
            self.refresh_badge_numbers(start_index)
        if self._row_drag_active:
            self._layout_during_row_drag()
            return
        current_y = self._row_y_for_index(start_index)
        row_width = int(self.cget('width')) - spec.MEDIA_ROW_INSET_X
        for row, row_widget in zip(self.rows[start_index:], self.row_widgets[start_index:]):
            target_expanded = self._expansion_state_for_row(row)
            if row_widget._expanded != target_expanded:
                row_widget.set_expanded(target_expanded)
            row_widget.resize(row_width)
            row_widget.place(x=spec.MEDIA_ROW_INSET_X, y=current_y)
            current_y += row_widget.winfo_reqheight() + spec.MEDIA_ROW_GAP_Y
        self.configure(height=self._total_height_for_rows(self.rows))

    def append_row(self, row: MediaRow) -> None:
        self.rows.append(row)
        widget = self._create_row_widget(row)
        if self._locked:
            widget.set_locked(True)
        self.row_widgets.append(widget)
        start_index = max(0, len(self.row_widgets) - 1)
        self.refresh_badge_numbers(start_index)
        self.refresh_row_layouts(start_index=start_index, refresh_badges=False)

    def remove_rows(self, row_ids: set[int], rows: list[MediaRow] | None = None) -> None:
        if not row_ids:
            return
        kept_rows: list[MediaRow] = []
        kept_widgets: list[MediaRowShell] = []
        first_removed_index: int | None = None
        for index, (row, row_widget) in enumerate(zip(self.rows, self.row_widgets)):
            if row.row_id in row_ids:
                if first_removed_index is None:
                    first_removed_index = index
                row_widget.destroy()
                continue
            kept_rows.append(row)
            kept_widgets.append(row_widget)
        if first_removed_index is None:
            return
        self.rows = list(rows) if rows is not None else kept_rows
        self.row_widgets = kept_widgets
        self.refresh_badge_numbers(first_removed_index)
        self.refresh_row_layouts(start_index=first_removed_index, refresh_badges=False)

    def begin_row_drag(self, dragged_row_ids: set[int], anchor_row_id: int, x_root: int, y_root: int) -> None:
        ordered_drag_ids = [
            row.row_id
            for row in self.rows
            if row.row_id in dragged_row_ids and not row.expanded
        ]
        if not ordered_drag_ids or anchor_row_id not in ordered_drag_ids:
            return
        widget_by_id = {widget._row_id: widget for widget in self.row_widgets}
        anchor_widget = widget_by_id.get(anchor_row_id)
        if anchor_widget is None:
            return
        local_y = self._local_y_from_root(y_root)
        block_offset_before_anchor = 0
        for row_id in ordered_drag_ids:
            if row_id == anchor_row_id:
                break
            widget = widget_by_id.get(row_id)
            if widget is None:
                continue
            block_offset_before_anchor += widget.winfo_height() + spec.MEDIA_ROW_GAP_Y
        self._row_drag_ids = ordered_drag_ids
        self._row_drag_active = True
        self._row_drag_pointer_offset_y = block_offset_before_anchor + max(0, local_y - anchor_widget.winfo_y())
        self._row_drag_cursor_local_y = local_y
        self.update_row_drag(x_root, y_root)

    def update_row_drag(self, x_root: int, y_root: int) -> None:
        if not self._row_drag_active:
            return
        self._row_drag_cursor_local_y = self._local_y_from_root(y_root)
        self._row_drag_insertion_index = self._row_insertion_index_from_local_y(self._row_drag_cursor_local_y)
        self._layout_during_row_drag()

    def finish_row_drag(self, x_root: int, y_root: int) -> int | None:
        if not self._row_drag_active:
            return None
        self.update_row_drag(x_root, y_root)
        insertion_index = self._row_drag_insertion_index
        self.cancel_row_drag()
        return insertion_index

    def cancel_row_drag(self) -> None:
        if not self._row_drag_active:
            return
        self._row_drag_ids = []
        self._row_drag_active = False
        self._row_drag_pointer_offset_y = 0
        self._row_drag_cursor_local_y = None
        self._row_drag_insertion_index = None
        self._drag_insertion_outline.place_forget()
        for row_widget in self.row_widgets:
            row_widget.cancel_row_drag()
        self.refresh_row_layouts()

    def _layout_during_row_drag(self) -> None:
        row_width = int(self.cget('width')) - spec.MEDIA_ROW_INSET_X
        widget_by_id = {widget._row_id: widget for widget in self.row_widgets}
        dragged_id_set = set(self._row_drag_ids)
        current_y = spec.MEDIA_ROW_INSET_Y
        insertion_index = self._row_drag_insertion_index if self._row_drag_insertion_index is not None else len(self.rows)
        insertion_y = current_y
        line_placed = False
        insertion_height = spec.MEDIA_ROW_COLLAPSED_SIZE[1]

        for full_index, row in enumerate(self.rows):
            if full_index == insertion_index and not line_placed:
                insertion_y = current_y
                insertion_height = spec.MEDIA_ROW_EXPANDED_SIZE[1] if row.expanded else spec.MEDIA_ROW_COLLAPSED_SIZE[1]
                line_placed = True
                current_y += insertion_height + spec.MEDIA_ROW_GAP_Y
            if row.row_id in dragged_id_set:
                continue
            widget = widget_by_id[row.row_id]
            target_expanded = self._expansion_state_for_row(row)
            if widget._expanded != target_expanded:
                widget.set_expanded(target_expanded)
            widget.resize(row_width)
            widget.place(x=spec.MEDIA_ROW_INSET_X, y=current_y)
            current_y += widget.winfo_reqheight() + spec.MEDIA_ROW_GAP_Y
        if not line_placed:
            insertion_y = current_y
            if self._row_drag_ids:
                first_dragged_widget = widget_by_id.get(self._row_drag_ids[0])
                if first_dragged_widget is not None:
                    insertion_height = first_dragged_widget.winfo_height() or first_dragged_widget.winfo_reqheight()
            current_y += insertion_height + spec.MEDIA_ROW_GAP_Y

        dragged_block_top = (self._row_drag_cursor_local_y or spec.MEDIA_ROW_INSET_Y) - self._row_drag_pointer_offset_y
        current_drag_y = dragged_block_top
        for row_id in self._row_drag_ids:
            widget = widget_by_id.get(row_id)
            if widget is None:
                continue
            widget.resize(row_width)
            widget.place(x=spec.MEDIA_ROW_INSET_X, y=current_drag_y)
            widget.lift()
            current_drag_y += widget.winfo_reqheight() + spec.MEDIA_ROW_GAP_Y

        self._drag_insertion_outline.place(
            x=spec.MEDIA_ROW_INSET_X,
            y=insertion_y,
            width=row_width,
            height=insertion_height,
        )
        self._drag_insertion_outline.lower()
        self.configure(height=self._total_height_for_rows(self.rows))

    def _expansion_state_for_row(self, row: MediaRow) -> bool:
        if self._display_expanded_row_id is None:
            return row.expanded
        return row.row_id == self._display_expanded_row_id

    def _row_y_for_index(self, index: int) -> int:
        if index <= 0:
            return spec.MEDIA_ROW_INSET_Y
        previous_widget = self.row_widgets[index - 1]
        previous_height = previous_widget.winfo_height() or previous_widget.winfo_reqheight()
        return previous_widget.winfo_y() + previous_height + spec.MEDIA_ROW_GAP_Y

    def _row_insertion_index_from_local_y(self, local_y: int) -> int:
        dragged_id_set = set(self._row_drag_ids)
        remaining_positions: list[tuple[int, int, int]] = []
        current_y = spec.MEDIA_ROW_INSET_Y
        for index, (row, widget) in enumerate(zip(self.rows, self.row_widgets)):
            if row.row_id in dragged_id_set:
                continue
            row_height = widget.winfo_height() or widget.winfo_reqheight()
            remaining_positions.append((index, current_y, row_height))
            current_y += row_height + spec.MEDIA_ROW_GAP_Y
        if not remaining_positions:
            return len(self.rows)
        if local_y <= remaining_positions[0][1]:
            return 0
        for full_index, row_top, row_height in remaining_positions:
            if local_y < row_top + (row_height / 2):
                return full_index
        return len(self.rows)

    def _local_y_from_root(self, y_root: int) -> int:
        return int(y_root - self.winfo_rooty())
