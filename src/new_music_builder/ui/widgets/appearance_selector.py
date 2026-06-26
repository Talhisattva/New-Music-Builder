from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk

from new_music_builder.domain.models import AppearanceKind, AppearanceSelection, MediaRow
from new_music_builder.services.asset_catalog import AssetEntry
from new_music_builder.services.default_appearance_selection import preferred_default_asset_key
from new_music_builder.ui import spec, theme
from new_music_builder.ui.widgets.buttons import make_builder_button
from new_music_builder.ui.widgets.appearance_entries import (
    BUILT_IN_DUAL_EMPTY_TO_FULL,
    TAB_KINDS,
    AppearanceGridEntry,
    PreviewMode,
    appearance_tab_order,
    apply_selection_from_grid_entry,
    can_commit_dual_custom,
    can_commit_single_custom,
    fallback_selected_asset_key_after_delete,
    merge_appearance_grid_entries,
    should_show_dual_sprite_controls,
    visible_tab_kinds_for_enabled_media,
)
from new_music_builder.ui.widgets.appearance_custom_footer import AppearanceDualCustomFooter, AppearanceSingleCustomFooter
from new_music_builder.ui.widgets.appearance_panel_shell import AppearancePanelShell
from new_music_builder.ui.widgets.cursor_tooltip import CursorTooltip
from new_music_builder.ui.widgets.images import load_tk_photoimage_contained
from new_music_builder.ui.widgets.loading_overlay import LoadingOverlay
from new_music_builder.ui.widgets.preview_mode_toggle import PreviewModeToggle


def generate_button_text_for_state(
    *,
    locked: bool,
    row: MediaRow | None,
    kind: AppearanceKind | None,
    enabled: bool,
) -> str:
    if enabled:
        return 'GENERATE FROM COVER'
    if locked or row is None:
        return 'GENERATE FROM COVER'
    cover_path = str(row.cover_path or '').strip()
    if cover_path and Path(cover_path).is_file():
        return ''
    return 'GENERATE FROM COVER'


@dataclass(frozen=True, slots=True)
class ModuleThreeControlLayout:
    show_generate: bool
    preview_row_y: int
    preview_row_size: tuple[int, int]
    dual_row_y: int
    dual_left_x: int
    generate_row_size: tuple[int, int]


@dataclass(frozen=True, slots=True)
class ModuleThreeVerticalMetrics:
    grid_viewport_size: tuple[int, int]
    grid_mask_size: tuple[int, int]
    grid_scrollbar_size: tuple[int, int]
    loading_overlay_size: tuple[int, int]
    footer_y: int


def resolve_module_three_control_layout(
    *,
    automatic_textures_enabled: bool,
    dual_visible: bool,
) -> ModuleThreeControlLayout:
    if automatic_textures_enabled:
        return ModuleThreeControlLayout(
            show_generate=False,
            preview_row_y=spec.MODULE_THREE_DUAL_SPRITE_ROW_Y,
            preview_row_size=spec.MODULE_THREE_PREVIEW_MODE_ROW_SIZE if dual_visible else spec.MODULE_THREE_PREVIEW_MODE_FULL_SIZE,
            dual_row_y=spec.MODULE_THREE_DUAL_SPRITE_ROW_Y,
            dual_left_x=spec.MODULE_THREE_PREVIEW_MODE_ROW_SIZE[0],
            generate_row_size=spec.MODULE_THREE_DUAL_SPRITE_ROW_SIZE,
        )
    return ModuleThreeControlLayout(
        show_generate=True,
        preview_row_y=spec.MODULE_THREE_PREVIEW_MODE_ROW_Y,
        preview_row_size=spec.MODULE_THREE_PREVIEW_MODE_FULL_SIZE,
        dual_row_y=spec.MODULE_THREE_DUAL_SPRITE_ROW_Y,
        dual_left_x=spec.MODULE_THREE_GENERATE_BUTTON_ROW_SIZE[0],
        generate_row_size=spec.MODULE_THREE_GENERATE_BUTTON_ROW_SIZE if dual_visible else spec.MODULE_THREE_DUAL_SPRITE_ROW_SIZE,
    )


def resolve_module_three_vertical_metrics(*, automatic_textures_enabled: bool) -> ModuleThreeVerticalMetrics:
    if automatic_textures_enabled:
        return ModuleThreeVerticalMetrics(
            grid_viewport_size=spec.MODULE_THREE_GRID_VIEWPORT_TALL_SIZE,
            grid_mask_size=spec.MODULE_THREE_GRID_MASK_TALL_SIZE,
            grid_scrollbar_size=spec.MODULE_THREE_GRID_SCROLLBAR_TALL_SIZE,
            loading_overlay_size=spec.MODULE_THREE_GRID_LOADING_OVERLAY_TALL_SIZE,
            footer_y=spec.MODULE_THREE_FOOTER_Y,
        )
    return ModuleThreeVerticalMetrics(
        grid_viewport_size=spec.MODULE_THREE_GRID_VIEWPORT_SIZE,
        grid_mask_size=spec.MODULE_THREE_GRID_MASK_SIZE,
        grid_scrollbar_size=spec.MODULE_THREE_GRID_SCROLLBAR_SIZE,
        loading_overlay_size=spec.MODULE_THREE_GRID_LOADING_OVERLAY_SIZE,
        footer_y=spec.MODULE_THREE_FOOTER_Y,
    )


class _BorderSurface(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        size: tuple[int, int],
        fill_color: str,
        border_color: str,
        border_width: int = 1,
    ) -> None:
        super().__init__(parent, bg=fill_color, bd=0, highlightthickness=0, width=size[0], height=size[1])
        self.pack_propagate(False)
        self._fill_color = fill_color
        self._border_color = border_color
        self._border_width = border_width
        self._size = size
        self.top = tk.Frame(self, bg=border_color, bd=0, highlightthickness=0, width=size[0], height=border_width)
        self.top.place(x=0, y=0)
        self.bottom = tk.Frame(self, bg=border_color, bd=0, highlightthickness=0, width=size[0], height=border_width)
        self.bottom.place(x=0, y=size[1] - border_width)
        self.left = tk.Frame(self, bg=border_color, bd=0, highlightthickness=0, width=border_width, height=size[1])
        self.left.place(x=0, y=0)
        self.right = tk.Frame(self, bg=border_color, bd=0, highlightthickness=0, width=border_width, height=size[1])
        self.right.place(x=size[0] - border_width, y=0)
        self.content = tk.Frame(
            self,
            bg=fill_color,
            bd=0,
            highlightthickness=0,
            width=size[0] - (border_width * 2),
            height=size[1] - (border_width * 2),
        )
        self.content.place(x=border_width, y=border_width)

    def set_colors(self, *, fill_color: str, border_color: str) -> None:
        self._fill_color = fill_color
        self._border_color = border_color
        self.configure(bg=fill_color)
        self.content.configure(bg=fill_color)
        for edge in (self.top, self.bottom, self.left, self.right):
            edge.configure(bg=border_color)


class _SmallCheckBox(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        check_icon_path: str | None,
        command: Callable[[], None],
    ) -> None:
        super().__init__(
            parent,
            bg=spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_BG,
            bd=0,
            highlightthickness=0,
            width=spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_SIZE[0],
            height=spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_SIZE[1],
        )
        self.pack_propagate(False)
        self._command = command
        self._checked = False
        self._enabled = True
        self._check_image = load_tk_photoimage_contained(check_icon_path, spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_SIZE)
        self._image_label = tk.Label(self, bg=spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_BG, bd=0, highlightthickness=0)
        self._image_label.place(x=0, y=0, width=spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_SIZE[0], height=spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_SIZE[1])
        for widget in (self, self._image_label):
            widget.bind('<ButtonPress-1>', self._on_press, add='+')
        self.set_checked(False)

    def set_checked(self, checked: bool) -> None:
        self._checked = checked
        self._image_label.configure(image=self._check_image if checked else '')
        self._image_label.image = self._check_image if checked else None

    def _on_press(self, _event: tk.Event) -> str:
        if not self._enabled:
            return 'break'
        self._command()
        return 'break'

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled


class _AppearanceTab(_BorderSurface):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        kind: AppearanceKind,
        label: str,
        on_selected: Callable[[AppearanceKind], None],
        loading_icon_path: str | None = None,
    ) -> None:
        super().__init__(
            parent,
            size=spec.MODULE_THREE_TAB_SIZE,
            fill_color=spec.MODULE_THREE_TAB_BG,
            border_color=spec.MODULE_THREE_TAB_BORDER_COLOR,
            border_width=spec.MODULE_THREE_TAB_BORDER_WIDTH,
        )
        self.kind = kind
        self._on_selected = on_selected
        self._image = None
        label_font = (spec.MODULE_THREE_TAB_LABEL_FONT_FAMILY, spec.MODULE_THREE_TAB_LABEL_FONT_SIZE)
        icon_center_y = spec.MODULE_THREE_TAB_SIZE[1] - spec.MODULE_THREE_TAB_ICON_BOTTOM_INSET - (spec.MODULE_THREE_TAB_ICON_SIZE[1] / 2)

        self.icon_label = tk.Label(self, bg=spec.MODULE_THREE_TAB_BG, bd=0, highlightthickness=0)
        self.icon_label.place(
            x=(spec.MODULE_THREE_TAB_SIZE[0] - spec.MODULE_THREE_TAB_ICON_SIZE[0]) // 2,
            y=int(icon_center_y - (spec.MODULE_THREE_TAB_ICON_SIZE[1] / 2)),
            width=spec.MODULE_THREE_TAB_ICON_SIZE[0],
            height=spec.MODULE_THREE_TAB_ICON_SIZE[1],
        )
        self.text_label = tk.Label(
            self.content,
            text=label,
            bg=spec.MODULE_THREE_TAB_BG,
            fg=spec.MODULE_THREE_TAB_LABEL_COLOR,
            bd=0,
            highlightthickness=0,
            font=label_font,
            anchor='center',
        )
        self.text_label.place(
            x=((spec.MODULE_THREE_TAB_SIZE[0] - (spec.MODULE_THREE_TAB_BORDER_WIDTH * 2)) - spec.MODULE_THREE_TAB_LABEL_WIDTH) // 2,
            y=(spec.MODULE_THREE_TAB_SIZE[1] - (spec.MODULE_THREE_TAB_BORDER_WIDTH * 2)) - 10,
            width=spec.MODULE_THREE_TAB_LABEL_WIDTH,
            height=8,
        )
        self.icon_label.lift()
        self.text_label.lift()
        self._loading_overlay = LoadingOverlay(
            self,
            size=spec.MODULE_THREE_TAB_ICON_SIZE,
            icon_path=loading_icon_path,
            bg_color=spec.MODULE_THREE_TAB_BG,
        )
        self._loading_overlay.resize(spec.MODULE_THREE_TAB_ICON_SIZE)
        self._loading_overlay.place_forget()

        self._hovered = False
        self._selected = False
        self._locked = False
        for widget in (self, self.icon_label, self.text_label, self.content):
            widget.bind('<Enter>', self._on_enter, add='+')
            widget.bind('<Leave>', self._on_leave, add='+')
            widget.bind('<ButtonPress-1>', self._on_press, add='+')

    def set_image(self, path: str | None) -> None:
        self._image = load_tk_photoimage_contained(path, spec.MODULE_THREE_TAB_ICON_SIZE)
        self.icon_label.configure(image=self._image if self._image is not None else '')
        self.icon_label.image = self._image

    def show_loading(self) -> None:
        fill = self._fill_color
        self._loading_overlay.set_bg_color(fill)
        self._loading_overlay.show(
            x=(spec.MODULE_THREE_TAB_SIZE[0] - spec.MODULE_THREE_TAB_ICON_SIZE[0]) // 2,
            y=int((spec.MODULE_THREE_TAB_SIZE[1] - spec.MODULE_THREE_TAB_ICON_SIZE[1]) // 2),
        )
        self._loading_overlay.lift()
        self.text_label.lift()

    def hide_loading(self) -> None:
        self._loading_overlay.hide()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_colors()

    def _apply_colors(self) -> None:
        if self._locked:
            fill = '#565258' if self._selected else spec.MODULE_THREE_TAB_BG
            border = '#9c98a0' if self._selected else spec.MODULE_THREE_TAB_BORDER_COLOR
        else:
            fill = spec.MODULE_THREE_TAB_SELECTED_BG if self._selected else spec.MODULE_THREE_TAB_HOVER_BG if self._hovered else spec.MODULE_THREE_TAB_BG
            border = spec.MODULE_THREE_TAB_BORDER_COLOR
        self.set_colors(fill_color=fill, border_color=border)
        self.icon_label.configure(bg=fill)
        self.text_label.configure(bg=fill)
        self._loading_overlay.set_bg_color(fill)

    def _on_enter(self, _event: tk.Event) -> None:
        if self._locked:
            return
        self._hovered = True
        self._apply_colors()

    def _on_leave(self, _event: tk.Event) -> None:
        if self._locked:
            return
        self._hovered = False
        self._apply_colors()

    def _on_press(self, _event: tk.Event) -> str:
        if self._locked:
            return 'break'
        self._on_selected(self.kind)
        return 'break'

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        self._hovered = False
        self._apply_colors()

class _AppearanceGridTile(_BorderSurface):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        entry: AppearanceGridEntry,
        display_mode: PreviewMode,
        on_selected: Callable[[str], None],
        on_remove_custom: Callable[[str], None],
        on_remove_generated: Callable[[str], None],
        on_hover_started: Callable[[AppearanceGridEntry, int, int], None],
        on_hover_moved: Callable[[AppearanceGridEntry, int, int], None],
        on_hover_ended: Callable[[AppearanceGridEntry], None],
    ) -> None:
        super().__init__(
            parent,
            size=spec.MODULE_THREE_GRID_TILE_SIZE,
            fill_color=spec.MODULE_THREE_GRID_TILE_BG,
            border_color=spec.MODULE_THREE_GRID_TILE_BORDER_COLOR,
            border_width=spec.MODULE_THREE_GRID_TILE_BORDER_WIDTH,
        )
        self.entry = entry
        self._on_selected = on_selected
        self._on_remove_custom = on_remove_custom
        self._on_remove_generated = on_remove_generated
        self._on_hover_started = on_hover_started
        self._on_hover_moved = on_hover_moved
        self._on_hover_ended = on_hover_ended
        self._hovered = False
        self._selected = False
        self._locked = False
        self._show_empty = False
        self._display_mode: PreviewMode = display_mode
        self._image_cache: dict[tuple[int, PreviewMode, bool], object | None] = {}
        self.icon_label = tk.Label(self, bg=spec.MODULE_THREE_GRID_TILE_BG, bd=0, highlightthickness=0)
        self.icon_label.place(
            x=(spec.MODULE_THREE_GRID_TILE_SIZE[0] - spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0]) // 2,
            y=(spec.MODULE_THREE_GRID_TILE_SIZE[1] - spec.MODULE_THREE_GRID_TILE_ICON_SIZE[1]) // 2,
            width=spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0],
            height=spec.MODULE_THREE_GRID_TILE_ICON_SIZE[1],
        )
        self._prime_image_cache()
        self.set_icon_size(spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0])
        self.delete_label = tk.Label(
            self,
            text='X',
            bg=spec.MODULE_THREE_GRID_TILE_BG,
            fg=spec.MODULE_THREE_CUSTOM_DELETE_X_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.MODULE_THREE_CUSTOM_DELETE_X_FONT_FAMILY, spec.MODULE_THREE_CUSTOM_DELETE_X_FONT_SIZE),
            anchor='center',
        )
        if entry.is_custom or entry.is_generated:
            self.delete_label.place(
                x=spec.MODULE_THREE_CUSTOM_DELETE_X_POS[0],
                y=spec.MODULE_THREE_CUSTOM_DELETE_X_POS[1],
                width=spec.MODULE_THREE_CUSTOM_DELETE_X_SIZE[0],
                height=spec.MODULE_THREE_CUSTOM_DELETE_X_SIZE[1],
            )
            self.delete_label.bind('<ButtonPress-1>', self._on_delete_press, add='+')
        for widget in (self, self.icon_label, self.content):
            widget.bind('<Enter>', self._on_enter, add='+')
            widget.bind('<Leave>', self._on_leave, add='+')
            widget.bind('<Motion>', self._on_motion, add='+')
            widget.bind('<ButtonPress-1>', self._on_press, add='+')

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_colors()

    def set_icon_size(self, size: int) -> None:
        cache_key = (size, self._display_mode, self._show_empty)
        image = self._image_cache.get(cache_key)
        if image is None:
            image = load_tk_photoimage_contained(
                self.entry.displayed_path(self._display_mode, show_empty=self._show_empty),
                (size, size),
            )
            self._image_cache[cache_key] = image
        x = (spec.MODULE_THREE_GRID_TILE_SIZE[0] - size) // 2
        y = (spec.MODULE_THREE_GRID_TILE_SIZE[1] - size) // 2
        self.icon_label.place(x=x, y=y, width=size, height=size)
        self.icon_label.configure(image=image if image is not None else '')
        self.icon_label.image = image

    def set_dual_phase(self, *, show_empty: bool) -> None:
        if not self.entry.is_dual:
            return
        if self._show_empty == show_empty:
            return
        self._show_empty = show_empty
        self.set_icon_size(spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0])

    def set_display_mode(self, mode: PreviewMode) -> None:
        if self._display_mode == mode:
            return
        self._display_mode = mode
        self.set_icon_size(spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0])

    @property
    def display_mode(self) -> PreviewMode:
        return self._display_mode

    def current_display_path(self) -> str:
        return self.entry.displayed_path(self._display_mode, show_empty=self._show_empty)

    def current_inventory_path(self) -> str:
        return self.entry.displayed_inventory_path(show_empty=self._show_empty)

    def current_world_path(self) -> str:
        return self.entry.displayed_world_path(show_empty=self._show_empty)

    def _prime_image_cache(self) -> None:
        size = spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0]
        self._image_cache[(size, 'inventory', False)] = load_tk_photoimage_contained(self.entry.inventory_path, (size, size))
        self._image_cache[(size, 'world', False)] = load_tk_photoimage_contained(self.entry.world_path, (size, size))
        if self.entry.is_dual:
            self._image_cache[(size, 'inventory', True)] = load_tk_photoimage_contained(self.entry.inventory_empty_path, (size, size))
            self._image_cache[(size, 'world', True)] = load_tk_photoimage_contained(self.entry.world_empty_path, (size, size))

    def _apply_colors(self) -> None:
        if self._locked:
            fill = spec.MODULE_THREE_GRID_TILE_LOCKED_SELECTED_BG if self._selected else spec.MODULE_THREE_GRID_TILE_BG
            border = spec.MODULE_THREE_GRID_TILE_LOCKED_SELECTED_BORDER_COLOR if self._selected else spec.MODULE_THREE_GRID_TILE_BORDER_COLOR
        elif self._selected:
            fill = spec.MODULE_THREE_GRID_TILE_SELECTED_BG
            border = spec.MODULE_THREE_GRID_TILE_SELECTED_BORDER_COLOR
        elif self._hovered:
            fill = spec.MODULE_THREE_GRID_TILE_HOVER_BG
            border = spec.MODULE_THREE_GRID_TILE_BORDER_COLOR
        else:
            fill = spec.MODULE_THREE_GRID_TILE_BG
            border = spec.MODULE_THREE_GRID_TILE_BORDER_COLOR
        self.set_colors(fill_color=fill, border_color=border)
        self.icon_label.configure(bg=fill)
        self.delete_label.configure(bg=fill)

    def _on_enter(self, event: tk.Event) -> None:
        if self._locked:
            return
        self._hovered = True
        self._apply_colors()
        self._on_hover_started(self.entry, int(event.x_root), int(event.y_root))

    def _on_leave(self, _event: tk.Event) -> None:
        if self._locked:
            return
        self._hovered = False
        self._apply_colors()
        self._on_hover_ended(self.entry)

    def _on_motion(self, event: tk.Event) -> None:
        if self._locked:
            return
        self._on_hover_moved(self.entry, int(event.x_root), int(event.y_root))

    def _on_press(self, _event: tk.Event) -> str:
        if self._locked:
            return 'break'
        self._on_selected(self.entry.key)
        return 'break'

    def _on_delete_press(self, _event: tk.Event) -> str:
        if self._locked:
            return 'break'
        if self.entry.is_generated:
            self._on_remove_generated(self.entry.key)
            return 'break'
        self._on_remove_custom(self.entry.key)
        return 'break'

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        self._hovered = False
        self._apply_colors()


class AppearanceSelector:
    def __init__(
        self,
        shell: AppearancePanelShell,
        *,
        asset_catalog: dict[str, list[AssetEntry]],
        small_check_icon_path: str | None,
        loading_icon_path: str | None,
        get_custom_assets: Callable[[AppearanceKind], list[dict[str, str]]],
        get_generated_entries: Callable[[AppearanceKind], list[AppearanceGridEntry]],
        get_staged_custom_images: Callable[[AppearanceKind], dict[str, str]],
        on_pick_custom_slot: Callable[[AppearanceKind, str], None],
        on_reset_custom: Callable[[AppearanceKind, bool], None],
        on_commit_custom: Callable[[AppearanceKind, bool], None],
        on_delete_custom: Callable[[AppearanceKind, str], None],
        on_delete_generated: Callable[[str], None],
        can_generate_from_cover: Callable[[MediaRow | None], bool],
        on_generate_from_cover: Callable[[int], None] | None,
        automatic_textures_enabled_getter: Callable[[], bool],
        on_preview_mode_selected: Callable[[int, str], None] | None,
        on_selection_changed: Callable[[int], None] | None,
        on_change: Callable[[], None],
    ) -> None:
        self.shell = shell
        self.asset_catalog = asset_catalog
        self._small_check_icon_path = small_check_icon_path
        self._loading_icon_path = loading_icon_path
        self._get_custom_assets = get_custom_assets
        self._get_generated_entries = get_generated_entries
        self._get_staged_custom_images = get_staged_custom_images
        self._on_pick_custom_slot = on_pick_custom_slot
        self._on_reset_custom = on_reset_custom
        self._on_commit_custom = on_commit_custom
        self._on_delete_custom = on_delete_custom
        self._on_delete_generated = on_delete_generated
        self._can_generate_from_cover = can_generate_from_cover
        self._on_generate_from_cover = on_generate_from_cover
        self._automatic_textures_enabled_getter = automatic_textures_enabled_getter
        self._on_preview_mode_selected = on_preview_mode_selected
        self._on_selection_changed = on_selection_changed
        self._on_change = on_change
        self._active_row: MediaRow | None = None
        self._active_kind: AppearanceKind | None = 'cassette'
        self._locked = False
        self._tab_widgets: dict[AppearanceKind, _AppearanceTab] = {}
        self._grid_tiles: dict[str, _AppearanceGridTile] = {}
        self._current_entries_by_kind: dict[AppearanceKind, list[AppearanceGridEntry]] = {}
        self._dual_phase_show_empty = False
        self._dual_phase_after_id: str | None = None
        self._grid_build_after_id: str | None = None
        self._grid_build_generation = 0
        self._tab_loading_after_id: str | None = None
        self._tooltip_hide_after_id: str | None = None
        self._cursor_tooltip = CursorTooltip(self.shell)
        self._grid_loading_overlay = LoadingOverlay(
            self.shell,
            size=spec.MODULE_THREE_GRID_LOADING_OVERLAY_SIZE,
            icon_path=self._loading_icon_path,
            bg_color=spec.MODULE_THREE_PANEL_BG,
        )
        self._dual_row_label_font = tkfont.Font(
            family=spec.MODULE_THREE_DUAL_SPRITE_LABEL_FONT_FAMILY,
            size=spec.MODULE_THREE_DUAL_SPRITE_LABEL_FONT_SIZE,
        )
        self._preview_mode_toggle: PreviewModeToggle | None = None

        self._build_tabs()
        self._build_generate_row()
        self._build_dual_sprite_row()
        self._build_footer()

    def _automatic_textures_enabled(self) -> bool:
        return bool(self._automatic_textures_enabled_getter())

    def _apply_vertical_layout(self, *, automatic_textures_enabled: bool) -> None:
        metrics = resolve_module_three_vertical_metrics(automatic_textures_enabled=automatic_textures_enabled)
        self.shell.grid_viewport.resize(
            size=metrics.grid_viewport_size,
            viewport_size=metrics.grid_mask_size,
            scrollbar_size=metrics.grid_scrollbar_size,
        )
        self.shell.grid_viewport.place_configure(
            x=0,
            y=spec.MODULE_THREE_GRID_VIEWPORT_Y,
            width=metrics.grid_viewport_size[0],
            height=metrics.grid_viewport_size[1],
        )
        self.shell.footer_pane.place_configure(x=0, y=metrics.footer_y)
        self._grid_loading_overlay.resize(metrics.loading_overlay_size)

    def _current_grid_mask_size(self) -> tuple[int, int]:
        return resolve_module_three_vertical_metrics(
            automatic_textures_enabled=self._automatic_textures_enabled(),
        ).grid_mask_size

    @property
    def active_kind(self) -> AppearanceKind | None:
        return self._active_kind

    def set_active_kind(self, kind: AppearanceKind) -> None:
        if kind not in dict(TAB_KINDS):
            return
        if kind == self._active_kind:
            return
        self._active_kind = kind
        self.refresh_from_active_row()

    def set_active_row(self, row: MediaRow | None) -> None:
        self._cancel_tooltip_hide()
        self._cursor_tooltip.hide()
        self._active_row = row
        self.refresh_from_active_row()

    def refresh_from_active_row(self) -> None:
        row = self._active_row
        if row is None:
            self._cancel_dual_phase_loop()
            self._cancel_grid_build()
            self._cancel_tooltip_hide()
            self._cursor_tooltip.hide()
            self._grid_loading_overlay.hide()
            self._cancel_tab_loading_indicator()
            self._active_kind = None
            self._apply_tab_visibility(())
            return
        row.ensure_appearances()
        visible_kinds = visible_tab_kinds_for_enabled_media(row.enabled_media)
        self._normalize_active_kind(visible_kinds)
        self._apply_tab_visibility(visible_kinds)
        for kind, _label in TAB_KINDS:
            if kind not in visible_kinds:
                continue
            self._ensure_valid_selection(row, kind)
            self._tab_widgets[kind].set_selected(kind == self._active_kind)
            self._tab_widgets[kind].set_locked(self._locked)
            entry = self._entry_for_kind(row, kind)
            self._tab_widgets[kind].set_image(entry.displayed_path(self._preview_mode(), show_empty=False) if entry else None)
        self._refresh_dual_sprite_row()
        self._refresh_generate_button_state()
        self._refresh_footer()
        self._rebuild_grid()

    def _build_tabs(self) -> None:
        for index, (kind, label) in enumerate(TAB_KINDS):
            tab = _AppearanceTab(
                self.shell.tabs_pane,
                kind=kind,
                label=label,
                on_selected=self._handle_tab_selected,
                loading_icon_path=self._loading_icon_path,
            )
            tab.place(x=index * spec.MODULE_THREE_TAB_SIZE[0], y=0)
            self._tab_widgets[kind] = tab

    def _build_dual_sprite_row(self) -> None:
        row_content = self.shell.dual_sprite_left_pane.content
        self.dual_checkbox = _SmallCheckBox(
            row_content,
            check_icon_path=self._small_check_icon_path,
            command=self._toggle_dual_sprite,
        )
        self.dual_checkbox.place(
            x=spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_POS[0],
            y=spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_POS[1],
        )
        label_x = spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_POS[0] + spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_SIZE[0] + spec.MODULE_THREE_DUAL_SPRITE_LABEL_GAP_X
        self.dual_label = tk.Label(
            row_content,
            text=spec.MODULE_THREE_DUAL_SPRITE_LABEL_TEXT,
            bg=spec.MODULE_THREE_PANEL_BG,
            fg=spec.MODULE_THREE_DUAL_SPRITE_LABEL_COLOR,
            bd=0,
            highlightthickness=0,
            font=self._dual_row_label_font,
            anchor='w',
        )
        self._place_dual_label(label_x)

    def _build_generate_row(self) -> None:
        self.generate_from_cover_button = make_builder_button(
            self.shell.generate_button_pane,
            spec.MODULE_THREE_GENERATE_BUTTON_TEXT,
            self._handle_generate_from_cover,
            size='compact',
            width=spec.MODULE_THREE_DUAL_SPRITE_ROW_SIZE[0],
        )
        self.generate_from_cover_button.configure(
            font=ctk.CTkFont(
                family=spec.MODULE_THREE_GENERATE_BUTTON_FONT_FAMILY,
                size=spec.MODULE_THREE_GENERATE_BUTTON_FONT_SIZE,
                weight='bold',
            ),
            corner_radius=0,
            height=spec.MODULE_THREE_DUAL_SPRITE_ROW_SIZE[1],
        )
        self.generate_from_cover_button.place(x=0, y=0)
        self._preview_mode_toggle = PreviewModeToggle(
            self.shell.preview_mode_pane.content,
            left_text='INVENTORY',
            right_text='WORLD',
            left_mode='inventory',
            right_mode='world',
            left_width=spec.MODULE_THREE_PREVIEW_MODE_INVENTORY_SIZE[0],
            right_width=spec.MODULE_THREE_PREVIEW_MODE_WORLD_SIZE[0],
            height=spec.MODULE_THREE_PREVIEW_MODE_ROW_SIZE[1],
            initial_mode='inventory',
            command=self._select_preview_mode,
            bg_color=spec.MODULE_THREE_PANEL_BG,
            outline_color=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE,
            outline_width=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE_WIDTH,
        )
        self._preview_mode_toggle.place(x=0, y=0)

    def _build_footer(self) -> None:
        self.single_custom_footer = AppearanceSingleCustomFooter(
            self.shell.footer_pane,
            on_pick_inventory=lambda: self._on_pick_custom_slot(self._active_kind, 'inventory_full'),
            on_pick_world=lambda: self._on_pick_custom_slot(self._active_kind, 'world_full'),
            on_commit=lambda: self._on_commit_custom(self._active_kind, False),
            on_reset=lambda: self._on_reset_custom(self._active_kind, False),
        )
        self.single_custom_footer.place(x=0, y=0)
        self.dual_custom_footer = AppearanceDualCustomFooter(
            self.shell.footer_pane,
            on_pick_inventory_full=lambda: self._on_pick_custom_slot(self._active_kind, 'inventory_full'),
            on_pick_world_full=lambda: self._on_pick_custom_slot(self._active_kind, 'world_full'),
            on_pick_inventory_empty=lambda: self._on_pick_custom_slot(self._active_kind, 'inventory_empty'),
            on_pick_world_empty=lambda: self._on_pick_custom_slot(self._active_kind, 'world_empty'),
            on_commit=lambda: self._on_commit_custom(self._active_kind, True),
            on_reset=lambda: self._on_reset_custom(self._active_kind, True),
        )
        self.dual_custom_footer.place_forget()

    def _refresh_dual_sprite_row(self) -> None:
        row = self._active_row
        if row is None:
            return
        automatic_textures_enabled = self._automatic_textures_enabled()
        self._apply_vertical_layout(automatic_textures_enabled=automatic_textures_enabled)
        self.dual_checkbox.set_enabled(True)
        if self._preview_mode_toggle is not None:
            self._preview_mode_toggle.set_mode(self._preview_mode())
            if automatic_textures_enabled and self._active_kind is not None and should_show_dual_sprite_controls(self._active_kind):
                left_width = spec.MODULE_THREE_PREVIEW_MODE_HALF_INVENTORY_SIZE[0]
                right_width = spec.MODULE_THREE_PREVIEW_MODE_HALF_WORLD_SIZE[0]
            else:
                left_width = spec.MODULE_THREE_PREVIEW_MODE_INVENTORY_SIZE[0]
                right_width = spec.MODULE_THREE_PREVIEW_MODE_WORLD_SIZE[0]
            self._preview_mode_toggle.resize(
                left_width=left_width,
                right_width=right_width,
                height=spec.MODULE_THREE_PREVIEW_MODE_ROW_SIZE[1],
            )
            self._preview_mode_toggle.place(x=0, y=0)
        if self._active_kind is None:
            self.dual_checkbox.place_forget()
            self.dual_label.place_forget()
            self.shell.preview_mode_pane.resize(spec.MODULE_THREE_PREVIEW_MODE_FULL_SIZE)
            self.shell.preview_mode_pane.place(x=0, y=spec.MODULE_THREE_PREVIEW_MODE_ROW_Y)
            self.shell.generate_button_pane.resize(spec.MODULE_THREE_DUAL_SPRITE_ROW_SIZE)
            if automatic_textures_enabled:
                self.shell.generate_button_pane.place_forget()
            else:
                self.shell.generate_button_pane.place(x=0, y=spec.MODULE_THREE_DUAL_SPRITE_ROW_Y)
            self.shell.dual_sprite_left_pane.place_forget()
            return
        visible = should_show_dual_sprite_controls(self._active_kind)
        layout = resolve_module_three_control_layout(
            automatic_textures_enabled=automatic_textures_enabled,
            dual_visible=visible,
        )
        self.shell.preview_mode_pane.resize(layout.preview_row_size)
        self.shell.preview_mode_pane.place(x=0, y=layout.preview_row_y)
        if visible:
            self.shell.generate_button_pane.resize(layout.generate_row_size)
            if layout.show_generate:
                self.shell.generate_button_pane.place(x=0, y=spec.MODULE_THREE_DUAL_SPRITE_ROW_Y)
            else:
                self.shell.generate_button_pane.place_forget()
            self.shell.dual_sprite_left_pane.resize(spec.MODULE_THREE_DUAL_SPRITE_LEFT_SIZE)
            self.shell.dual_sprite_left_pane.place(
                x=layout.dual_left_x,
                y=layout.dual_row_y,
            )
            selection = row.appearances[self._active_kind]
            self.dual_checkbox.set_checked(selection.sprite_mode == 'dual')
            self.dual_checkbox.place(
                x=spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_POS[0],
                y=spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_POS[1],
            )
            label_x = spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_POS[0] + spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_SIZE[0] + spec.MODULE_THREE_DUAL_SPRITE_LABEL_GAP_X
            self._place_dual_label(label_x)
            if layout.show_generate:
                self.generate_from_cover_button.configure(
                    font=ctk.CTkFont(
                        family=spec.MODULE_THREE_GENERATE_BUTTON_FONT_FAMILY,
                        size=spec.MODULE_THREE_GENERATE_BUTTON_HALF_FONT_SIZE,
                        weight='bold',
                    ),
                    width=spec.MODULE_THREE_GENERATE_BUTTON_ROW_SIZE[0],
                    height=spec.MODULE_THREE_DUAL_SPRITE_ROW_SIZE[1],
                )
                self.generate_from_cover_button.place_configure(x=0, y=0)
        else:
            self.shell.generate_button_pane.resize(layout.generate_row_size)
            if layout.show_generate:
                self.shell.generate_button_pane.place(x=0, y=spec.MODULE_THREE_DUAL_SPRITE_ROW_Y)
            else:
                self.shell.generate_button_pane.place_forget()
            self.shell.dual_sprite_left_pane.place_forget()
            self.dual_checkbox.place_forget()
            self.dual_label.place_forget()
            if layout.show_generate:
                self.generate_from_cover_button.configure(
                    font=ctk.CTkFont(
                        family=spec.MODULE_THREE_GENERATE_BUTTON_FONT_FAMILY,
                        size=spec.MODULE_THREE_GENERATE_BUTTON_FONT_SIZE,
                        weight='bold',
                    ),
                    width=spec.MODULE_THREE_DUAL_SPRITE_ROW_SIZE[0],
                    height=spec.MODULE_THREE_DUAL_SPRITE_ROW_SIZE[1],
                )
                self.generate_from_cover_button.place_configure(x=0, y=0)
        self._refresh_generate_button_state()

    def _refresh_footer(self) -> None:
        if self._active_kind is None:
            self.dual_custom_footer.place_forget()
            self.single_custom_footer.place_forget()
            return
        staged = self._get_staged_custom_images(self._active_kind)
        dual_mode = self._footer_uses_dual_mode()
        if dual_mode:
            self.single_custom_footer.place_forget()
            self.dual_custom_footer.place(x=0, y=0)
            self.dual_custom_footer.set_staged_images(
                inventory_full=staged.get('inventory_full', ''),
                world_full=staged.get('world_full', ''),
                inventory_empty=staged.get('inventory_empty', ''),
                world_empty=staged.get('world_empty', ''),
            )
            self.dual_custom_footer.set_commit_enabled(can_commit_dual_custom(staged))
            self.dual_custom_footer.set_enabled(not self._locked)
        else:
            self.dual_custom_footer.place_forget()
            self.single_custom_footer.place(x=0, y=0)
            self.single_custom_footer.set_staged_images(
                inventory_path=staged.get('inventory_full', ''),
                world_path=staged.get('world_full', ''),
            )
            self.single_custom_footer.set_commit_enabled(can_commit_single_custom(staged))
            self.single_custom_footer.set_enabled(not self._locked)

    def _rebuild_grid(self) -> None:
        self._cancel_dual_phase_loop()
        self._cancel_grid_build()
        self._cancel_tooltip_hide()
        self._cursor_tooltip.hide()
        for child in self.shell.grid_viewport.content_frame.winfo_children():
            child.destroy()
        self._grid_tiles.clear()
        self._dual_phase_show_empty = False
        row = self._active_row
        if row is None or self._active_kind is None:
            grid_mask_size = self._current_grid_mask_size()
            self.shell.grid_viewport.content_frame.configure(
                width=grid_mask_size[0],
                height=0,
            )
            self.shell.grid_viewport.refresh_scroll_region()
            return
        entries = self._entries_for_kind(self._active_kind)
        self._current_entries_by_kind[self._active_kind] = entries
        selected_key = row.appearances[self._active_kind].selected_asset_key
        row_count = max(1, (len(entries) + 3) // 4)
        content_height = row_count * spec.MODULE_THREE_GRID_TILE_SIZE[1]
        grid_mask_size = self._current_grid_mask_size()
        self.shell.grid_viewport.content_frame.configure(
            width=grid_mask_size[0],
            height=content_height,
        )
        self.shell.grid_viewport.refresh_scroll_region()
        self._grid_loading_overlay.show(x=0, y=spec.MODULE_THREE_GRID_VIEWPORT_Y)
        self._grid_build_generation += 1
        generation = self._grid_build_generation
        self._schedule_tab_loading_indicator(generation=generation)
        self._build_grid_entries_chunk(
            generation=generation,
            entries=entries,
            selected_key=selected_key,
            start_index=0,
        )

    def _handle_tab_selected(self, kind: AppearanceKind) -> None:
        if self._locked:
            return
        self.set_active_kind(kind)

    def _handle_grid_selected(self, key: str) -> None:
        if self._locked:
            return
        row = self._active_row
        if row is None or self._active_kind is None:
            return
        selection = row.appearances[self._active_kind]
        entry = next((item for item in self._entries_for_kind(self._active_kind) if item.key == key), None)
        if entry is None:
            return
        apply_selection_from_grid_entry(selection, entry)
        for tile_key, tile in self._grid_tiles.items():
            tile.set_selected(tile_key == key)
            if tile_key != key:
                tile.set_icon_size(spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0])
        self._update_active_tab_icon()
        self._refresh_dual_sprite_row()
        self._refresh_footer()
        if self._on_selection_changed is not None:
            self._on_selection_changed(row.row_id)
        self._on_change()

    def _handle_remove_custom(self, key: str) -> None:
        if self._locked:
            return
        if self._active_kind is None:
            return
        self._on_delete_custom(self._active_kind, key)

    def _handle_remove_generated(self, key: str) -> None:
        if self._locked:
            return
        self._on_delete_generated(key)

    def _handle_tile_hover_started(self, _entry: AppearanceGridEntry, x_root: int, y_root: int) -> None:
        if self._preview_mode() != 'world':
            self._cursor_tooltip.hide()
            return
        self._cancel_tooltip_hide()
        tile = self._grid_tiles.get(_entry.key)
        self._cursor_tooltip.set_image(tile.current_world_path() if tile is not None else _entry.displayed_world_path(show_empty=False))
        self._cursor_tooltip.show_at_cursor(x_root, y_root, direction='left')

    def _handle_tile_hover_moved(self, _entry: AppearanceGridEntry, x_root: int, y_root: int) -> None:
        if self._preview_mode() != 'world':
            self._cursor_tooltip.hide()
            return
        self._cancel_tooltip_hide()
        tile = self._grid_tiles.get(_entry.key)
        self._cursor_tooltip.set_image(tile.current_world_path() if tile is not None else _entry.displayed_world_path(show_empty=False))
        self._cursor_tooltip.move_to_cursor(x_root, y_root)

    def _handle_tile_hover_ended(self, _entry: AppearanceGridEntry) -> None:
        self._schedule_tooltip_hide()

    def _toggle_dual_sprite(self) -> None:
        row = self._active_row
        if row is None or self._active_kind is None or not should_show_dual_sprite_controls(self._active_kind):
            return
        selection = row.appearances[self._active_kind]
        selection.sprite_mode = 'single' if selection.sprite_mode == 'dual' else 'dual'
        self._refresh_dual_sprite_row()
        self._refresh_footer()
        if self._on_selection_changed is not None:
            self._on_selection_changed(row.row_id)
        self._on_change()

    def _ensure_valid_selection(self, row: MediaRow, kind: AppearanceKind) -> None:
        entries = self._entries_for_kind(kind)
        selection = row.appearances[kind]
        selection.selected_asset_key = BUILT_IN_DUAL_EMPTY_TO_FULL.get(selection.selected_asset_key, selection.selected_asset_key)
        if entries and selection.selected_asset_key not in {entry.key for entry in entries}:
            preferred_key = preferred_default_asset_key(kind, {entry.key for entry in entries})
            default_entry = next((entry for entry in entries if entry.key == preferred_key), entries[0])
            apply_selection_from_grid_entry(selection, default_entry)

    def _entry_for_kind(self, row: MediaRow, kind: AppearanceKind) -> AppearanceGridEntry | None:
        entries = self._entries_for_kind(kind)
        if not entries:
            return None
        selected_key = row.appearances[kind].selected_asset_key
        return next((entry for entry in entries if entry.key == selected_key), entries[0])

    def _entries_for_kind(self, kind: AppearanceKind) -> list[AppearanceGridEntry]:
        return merge_appearance_grid_entries(
            kind,
            self.asset_catalog.get(kind, []),
            self._get_generated_entries(kind),
            self._get_custom_assets(kind),
        )

    def _footer_uses_dual_mode(self) -> bool:
        row = self._active_row
        if row is None or self._active_kind is None or not should_show_dual_sprite_controls(self._active_kind):
            return False
        return row.appearances[self._active_kind].sprite_mode == 'dual'

    def _update_active_tab_icon(self) -> None:
        row = self._active_row
        if row is None or self._active_kind is None:
            return
        entry = self._entry_for_kind(row, self._active_kind)
        if entry is None:
            self._tab_widgets[self._active_kind].set_image(None)
            return
        selected_tile = self._grid_tiles.get(entry.key)
        if selected_tile is not None:
            self._tab_widgets[self._active_kind].set_image(selected_tile.current_display_path())
            return
        self._tab_widgets[self._active_kind].set_image(entry.displayed_path(self._preview_mode(), show_empty=self._dual_phase_show_empty))

    def _schedule_dual_phase_loop_if_needed(self) -> None:
        if any(tile.entry.is_dual for tile in self._grid_tiles.values()):
            self._dual_phase_after_id = self.shell.after(spec.MODULE_THREE_DUAL_GRID_SWAP_INTERVAL_MS, self._advance_dual_phase)

    def _cancel_dual_phase_loop(self) -> None:
        if self._dual_phase_after_id is not None:
            try:
                self.shell.after_cancel(self._dual_phase_after_id)
            except tk.TclError:
                pass
            self._dual_phase_after_id = None

    def _advance_dual_phase(self) -> None:
        self._dual_phase_after_id = None
        if not self._grid_tiles or self._grid_build_after_id is not None:
            return
        self._dual_phase_show_empty = not self._dual_phase_show_empty
        for tile in self._grid_tiles.values():
            tile.set_dual_phase(show_empty=self._dual_phase_show_empty)
        hovered_tile = next((tile for tile in self._grid_tiles.values() if tile._hovered), None)
        if hovered_tile is not None and self._preview_mode() == 'world':
            self._cursor_tooltip.set_image(hovered_tile.current_world_path())
        elif self._preview_mode() != 'world':
            self._cursor_tooltip.hide()
        self._update_active_tab_icon()
        self._schedule_dual_phase_loop_if_needed()

    def _place_dual_label(self, x: int) -> None:
        row_height = spec.MODULE_THREE_DUAL_SPRITE_ROW_SIZE[1] - (spec.MODULE_THREE_PANEL_BORDER_WIDTH * 2)
        label_height = self._dual_row_label_font.metrics('linespace') + 2
        y = max(0, (row_height - label_height) // 2)
        self.dual_label.place(x=x, y=y, width=spec.MODULE_THREE_DUAL_SPRITE_LABEL_WIDTH, height=label_height)

    def _preview_mode(self) -> PreviewMode:
        row = self._active_row
        if row is None:
            return 'inventory'
        return 'world' if row.preview_mode == 'world' else 'inventory'

    def _select_preview_mode(self, mode: str) -> None:
        row = self._active_row
        if row is None or mode not in {'inventory', 'world'}:
            return
        if self._on_preview_mode_selected is not None:
            self._on_preview_mode_selected(row.row_id, mode)

    def _handle_generate_from_cover(self) -> None:
        row = self._active_row
        if row is None or self._active_kind is None or self._locked:
            return
        if not self._can_generate_from_cover(row):
            return
        if self._on_generate_from_cover is not None:
            self._on_generate_from_cover(row.row_id)

    def _refresh_generate_button_state(self) -> None:
        enabled = (not self._locked) and self._can_generate_from_cover(self._active_row)
        button_text = generate_button_text_for_state(
            locked=self._locked,
            row=self._active_row,
            kind=self._active_kind,
            enabled=enabled,
        )
        if enabled:
            self.generate_from_cover_button.configure(
                state='normal',
                fg_color=theme.ACCENT,
                hover_color=theme.ACCENT_DARK,
                border_color=theme.ACCENT_DARK,
                text_color=theme.BUTTON_TEXT,
                text_color_disabled=theme.BUTTON_TEXT,
                text=button_text,
            )
            return
        self.generate_from_cover_button.configure(
            state='disabled',
            fg_color='#4a474c',
            hover_color='#4a474c',
            border_color='#706b73',
            text_color=theme.BUTTON_TEXT,
            text_color_disabled='#a9a5ab',
            text=button_text,
        )

    def _normalize_active_kind(self, visible_kinds: tuple[AppearanceKind, ...]) -> None:
        if not visible_kinds:
            self._active_kind = None
            return
        if self._active_kind in visible_kinds:
            return
        self._active_kind = visible_kinds[0]

    def _apply_tab_visibility(self, visible_kinds: tuple[AppearanceKind, ...]) -> None:
        visible_set = set(visible_kinds)
        visible_index = 0
        for kind, _label in TAB_KINDS:
            tab = self._tab_widgets[kind]
            if kind in visible_set:
                tab.place(x=visible_index * spec.MODULE_THREE_TAB_SIZE[0], y=0)
                visible_index += 1
            else:
                tab.place_forget()

    def _schedule_tooltip_hide(self) -> None:
        self._cancel_tooltip_hide()
        self._tooltip_hide_after_id = self.shell.after(spec.MODULE_THREE_GRID_HOVER_HIDE_DELAY_MS, self._hide_tooltip_now)

    def _cancel_tooltip_hide(self) -> None:
        if self._tooltip_hide_after_id is not None:
            try:
                self.shell.after_cancel(self._tooltip_hide_after_id)
            except tk.TclError:
                pass
            self._tooltip_hide_after_id = None

    def _hide_tooltip_now(self) -> None:
        self._tooltip_hide_after_id = None
        self._cursor_tooltip.hide()

    def _cancel_grid_build(self) -> None:
        if self._grid_build_after_id is not None:
            try:
                self.shell.after_cancel(self._grid_build_after_id)
            except tk.TclError:
                pass
            self._grid_build_after_id = None
        self._cancel_tab_loading_indicator()

    def _schedule_tab_loading_indicator(self, *, generation: int) -> None:
        self._cancel_tab_loading_indicator()
        self._tab_loading_after_id = self.shell.after(
            spec.MODULE_THREE_TAB_LOADING_DELAY_MS,
            lambda: self._show_tab_loading_indicator(generation),
        )

    def _show_tab_loading_indicator(self, generation: int) -> None:
        self._tab_loading_after_id = None
        if generation != self._grid_build_generation or self._grid_build_after_id is None:
            return
        if self._active_kind is None:
            return
        tab = self._tab_widgets.get(self._active_kind)
        if tab is not None:
            tab.show_loading()

    def _cancel_tab_loading_indicator(self) -> None:
        if self._tab_loading_after_id is not None:
            try:
                self.shell.after_cancel(self._tab_loading_after_id)
            except tk.TclError:
                pass
            self._tab_loading_after_id = None
        for tab in self._tab_widgets.values():
            tab.hide_loading()

    def _build_grid_entries_chunk(
        self,
        *,
        generation: int,
        entries: list[AppearanceGridEntry],
        selected_key: str,
        start_index: int,
    ) -> None:
        if generation != self._grid_build_generation:
            return
        end_index = min(start_index + spec.MODULE_THREE_GRID_LOADING_BATCH_SIZE, len(entries))
        for index in range(start_index, end_index):
            entry = entries[index]
            tile = _AppearanceGridTile(
                self.shell.grid_viewport.content_frame,
                entry=entry,
                display_mode=self._preview_mode(),
                on_selected=self._handle_grid_selected,
                on_remove_custom=self._handle_remove_custom,
                on_remove_generated=self._handle_remove_generated,
                on_hover_started=self._handle_tile_hover_started,
                on_hover_moved=self._handle_tile_hover_moved,
                on_hover_ended=self._handle_tile_hover_ended,
            )
            tile.place(
                x=(index % 4) * spec.MODULE_THREE_GRID_TILE_SIZE[0],
                y=(index // 4) * spec.MODULE_THREE_GRID_TILE_SIZE[1],
            )
            tile.set_selected(entry.key == selected_key)
            tile.set_locked(self._locked)
            self._grid_tiles[entry.key] = tile
        self.shell.grid_viewport.refresh_scroll_region()
        if end_index < len(entries):
            self._grid_build_after_id = self.shell.after(
                1,
                lambda: self._build_grid_entries_chunk(
                    generation=generation,
                    entries=entries,
                    selected_key=selected_key,
                    start_index=end_index,
                ),
            )
            return
        self._grid_build_after_id = None
        self._cancel_tab_loading_indicator()
        self._grid_loading_overlay.hide()
        self._update_active_tab_icon()
        self._scroll_tile_into_view(selected_key)
        self._schedule_dual_phase_loop_if_needed()

    def _scroll_tile_into_view(self, key: str) -> None:
        tile = self._grid_tiles.get(key)
        if tile is None:
            return
        viewport_height = self._current_grid_mask_size()[1]
        content_height = self.shell.grid_viewport.content_frame.winfo_reqheight()
        if content_height <= viewport_height:
            self.shell.grid_viewport.viewport_canvas.yview_moveto(0.0)
            return
        tile_y = tile.winfo_y()
        tile_height = spec.MODULE_THREE_GRID_TILE_SIZE[1]
        scrollable = max(0, content_height - viewport_height)
        target_top = max(0, min(scrollable, tile_y - ((viewport_height - tile_height) // 2)))
        target_fraction = (target_top / content_height) if content_height > 0 else 0.0
        self.shell.grid_viewport.viewport_canvas.yview_moveto(target_fraction)
        first, last = self.shell.grid_viewport.viewport_canvas.yview()
        self.shell.grid_viewport.scrollbar.set_view(first, last)

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        for tab in self._tab_widgets.values():
            tab.set_locked(locked)
        for tile in self._grid_tiles.values():
            tile.set_locked(locked)
        self._refresh_generate_button_state()
        self._refresh_footer()
