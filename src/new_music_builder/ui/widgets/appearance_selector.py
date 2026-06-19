from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import tkinter as tk
import tkinter.font as tkfont

from new_music_builder.domain.models import AppearanceKind, AppearanceSelection, MediaRow
from new_music_builder.services.asset_catalog import AssetEntry
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.appearance_custom_footer import AppearanceDualCustomFooter, AppearanceSingleCustomFooter
from new_music_builder.ui.widgets.appearance_panel_shell import AppearancePanelShell
from new_music_builder.ui.widgets.images import load_tk_photoimage_contained


TAB_KINDS: tuple[tuple[AppearanceKind, str], ...] = (
    ('cassette', 'Cassette'),
    ('vinyl', 'Vinyl'),
    ('cd', 'CD'),
    ('case', 'Case'),
    ('jacket', 'Jacket'),
    ('cd_cover', 'CD Case'),
)

DUAL_SPRITE_KINDS: frozenset[AppearanceKind] = frozenset({'case', 'jacket', 'cd_cover'})
BUILT_IN_DUAL_PAIRS: dict[str, str] = {
    'jacket:18': 'jacket:18_empty',
    'jacket:19': 'jacket:19_empty',
    'jacket:20': 'jacket:20_empty',
    'jacket:21': 'jacket:21_empty',
    'jacket:_Zomboid': 'jacket:_Zomboid_Empty',
    'cd_cover:_Blank': 'cd_cover:_Empty',
}
BUILT_IN_DUAL_EMPTY_TO_FULL: dict[str, str] = {empty_key: full_key for full_key, empty_key in BUILT_IN_DUAL_PAIRS.items()}


@dataclass(slots=True)
class AppearanceGridEntry:
    key: str
    label: str
    inventory_path: str
    world_path: str
    sprite_mode: str
    kind: AppearanceKind
    is_custom: bool = False
    is_dual: bool = False
    inventory_empty_path: str = ''
    world_empty_path: str = ''

    def displayed_inventory_path(self, *, show_empty: bool) -> str:
        if self.is_dual and show_empty and self.inventory_empty_path:
            return self.inventory_empty_path
        return self.inventory_path


def appearance_tab_order() -> tuple[tuple[AppearanceKind, str], ...]:
    return TAB_KINDS


def should_show_dual_sprite_controls(kind: AppearanceKind) -> bool:
    return kind in DUAL_SPRITE_KINDS


def can_commit_single_custom(staged: dict[str, str]) -> bool:
    return bool(staged.get('inventory_full') and staged.get('world_full'))


def can_commit_dual_custom(staged: dict[str, str]) -> bool:
    return bool(
        staged.get('inventory_full')
        and staged.get('world_full')
        and staged.get('inventory_empty')
        and staged.get('world_empty')
    )


def merge_appearance_grid_entries(
    kind: AppearanceKind,
    defaults: list[AssetEntry],
    custom_assets: list[dict[str, str]],
) -> list[AppearanceGridEntry]:
    merged: list[AppearanceGridEntry] = []
    defaults_by_key = {entry.key: entry for entry in defaults}
    consumed_default_keys: set[str] = set()
    for entry in defaults:
        if entry.key in consumed_default_keys:
            continue
        empty_pair_key = BUILT_IN_DUAL_PAIRS.get(entry.key)
        if empty_pair_key and empty_pair_key in defaults_by_key:
            empty_entry = defaults_by_key[empty_pair_key]
            merged.append(
                AppearanceGridEntry(
                    key=entry.key,
                    label=entry.label,
                    inventory_path=entry.inventory_path,
                    world_path=entry.world_path,
                    sprite_mode='dual',
                    kind=kind,
                    is_custom=False,
                    is_dual=True,
                    inventory_empty_path=empty_entry.inventory_path,
                    world_empty_path=empty_entry.world_path,
                )
            )
            consumed_default_keys.add(entry.key)
            consumed_default_keys.add(empty_pair_key)
            continue
        if entry.key in BUILT_IN_DUAL_EMPTY_TO_FULL:
            consumed_default_keys.add(entry.key)
            continue
        merged.append(
            AppearanceGridEntry(
                key=entry.key,
                label=entry.label,
                inventory_path=entry.inventory_path,
                world_path=entry.world_path,
                sprite_mode=entry.sprite_mode,
                kind=kind,
                is_custom=False,
            )
        )
    for index, asset in enumerate(custom_assets):
        inventory_path = asset.get('inventory_full', '')
        world_path = asset.get('world_full', '')
        key = asset.get('key', f'custom:{kind}:{index + 1}')
        label = asset.get('label') or inventory_path.rsplit('/', 1)[-1].rsplit('\\', 1)[-1] or f'Custom {index + 1}'
        sprite_mode = asset.get('sprite_mode', 'single') or 'single'
        is_dual = sprite_mode == 'dual' and bool(asset.get('inventory_empty') and asset.get('world_empty'))
        merged.append(
            AppearanceGridEntry(
                key=key,
                label=label,
                inventory_path=inventory_path,
                world_path=world_path,
                sprite_mode=sprite_mode,
                kind=kind,
                is_custom=True,
                is_dual=is_dual,
                inventory_empty_path=asset.get('inventory_empty', ''),
                world_empty_path=asset.get('world_empty', ''),
            )
        )
    return merged


def fallback_selected_asset_key_after_delete(
    entries: list[AppearanceGridEntry],
    *,
    deleted_key: str,
    selected_key: str,
) -> str:
    if selected_key != deleted_key:
        return selected_key
    return entries[0].key if entries else ''


def apply_selection_from_grid_entry(selection: AppearanceSelection, entry: AppearanceGridEntry) -> None:
    selection.selected_asset_key = entry.key
    selection.sprite_mode = entry.sprite_mode if should_show_dual_sprite_controls(entry.kind) else 'single'
    if entry.is_custom:
        selection.source = 'custom'
        selection.inventory_full = entry.inventory_path
        selection.world_full = entry.world_path
        selection.inventory_empty = entry.inventory_empty_path if entry.is_dual else ''
        selection.world_empty = entry.world_empty_path if entry.is_dual else ''
    else:
        selection.source = 'default'
        selection.inventory_full = ''
        selection.world_full = ''
        selection.inventory_empty = ''
        selection.world_empty = ''


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
        self._command()
        return 'break'


class _AppearanceTab(_BorderSurface):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        kind: AppearanceKind,
        label: str,
        on_selected: Callable[[AppearanceKind], None],
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
            self,
            text=label,
            bg=spec.MODULE_THREE_TAB_BG,
            fg=spec.MODULE_THREE_TAB_LABEL_COLOR,
            bd=0,
            highlightthickness=0,
            font=label_font,
            anchor='s',
        )
        self.text_label.place(
            x=(spec.MODULE_THREE_TAB_SIZE[0] - spec.MODULE_THREE_TAB_LABEL_WIDTH) // 2,
            y=spec.MODULE_THREE_TAB_SIZE[1] - 12,
            width=spec.MODULE_THREE_TAB_LABEL_WIDTH,
            height=9,
        )
        self.icon_label.lift()
        self.text_label.lift()

        self._hovered = False
        self._selected = False
        for widget in (self, self.icon_label, self.text_label, self.content):
            widget.bind('<Enter>', self._on_enter, add='+')
            widget.bind('<Leave>', self._on_leave, add='+')
            widget.bind('<ButtonPress-1>', self._on_press, add='+')

    def set_image(self, path: str | None) -> None:
        self._image = load_tk_photoimage_contained(path, spec.MODULE_THREE_TAB_ICON_SIZE)
        self.icon_label.configure(image=self._image if self._image is not None else '')
        self.icon_label.image = self._image

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_colors()

    def _apply_colors(self) -> None:
        fill = spec.MODULE_THREE_TAB_SELECTED_BG if self._selected else spec.MODULE_THREE_TAB_HOVER_BG if self._hovered else spec.MODULE_THREE_TAB_BG
        self.set_colors(fill_color=fill, border_color=spec.MODULE_THREE_TAB_BORDER_COLOR)
        self.icon_label.configure(bg=fill)
        self.text_label.configure(bg=fill)

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._apply_colors()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._apply_colors()

    def _on_press(self, _event: tk.Event) -> str:
        self._on_selected(self.kind)
        return 'break'

class _AppearanceGridTile(_BorderSurface):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        entry: AppearanceGridEntry,
        on_selected: Callable[[str], None],
        on_remove_custom: Callable[[str], None],
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
        self._hovered = False
        self._selected = False
        self._show_empty = False
        self._image_cache: dict[tuple[int, bool], object | None] = {}
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
        if entry.is_custom:
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
            widget.bind('<ButtonPress-1>', self._on_press, add='+')

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_colors()

    def set_icon_size(self, size: int) -> None:
        cache_key = (size, self._show_empty)
        image = self._image_cache.get(cache_key)
        if image is None:
            image = load_tk_photoimage_contained(self.entry.displayed_inventory_path(show_empty=self._show_empty), (size, size))
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

    def current_inventory_path(self) -> str:
        return self.entry.displayed_inventory_path(show_empty=self._show_empty)

    def _prime_image_cache(self) -> None:
        sizes = set(spec.MODULE_THREE_GRID_ANIMATION_SIZES + (spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0],))
        for size in sizes:
            self._image_cache[(size, False)] = load_tk_photoimage_contained(self.entry.inventory_path, (size, size))
            if self.entry.is_dual:
                self._image_cache[(size, True)] = load_tk_photoimage_contained(self.entry.inventory_empty_path, (size, size))

    def _apply_colors(self) -> None:
        if self._selected:
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

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._apply_colors()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._apply_colors()

    def _on_press(self, _event: tk.Event) -> str:
        self._on_selected(self.entry.key)
        return 'break'

    def _on_delete_press(self, _event: tk.Event) -> str:
        self._on_remove_custom(self.entry.key)
        return 'break'


class AppearanceSelector:
    def __init__(
        self,
        shell: AppearancePanelShell,
        *,
        asset_catalog: dict[str, list[AssetEntry]],
        small_check_icon_path: str | None,
        get_custom_assets: Callable[[AppearanceKind], list[dict[str, str]]],
        get_staged_custom_images: Callable[[AppearanceKind], dict[str, str]],
        on_pick_custom_slot: Callable[[AppearanceKind, str], None],
        on_reset_custom: Callable[[AppearanceKind, bool], None],
        on_commit_custom: Callable[[AppearanceKind, bool], None],
        on_delete_custom: Callable[[AppearanceKind, str], None],
        on_change: Callable[[], None],
    ) -> None:
        self.shell = shell
        self.asset_catalog = asset_catalog
        self._small_check_icon_path = small_check_icon_path
        self._get_custom_assets = get_custom_assets
        self._get_staged_custom_images = get_staged_custom_images
        self._on_pick_custom_slot = on_pick_custom_slot
        self._on_reset_custom = on_reset_custom
        self._on_commit_custom = on_commit_custom
        self._on_delete_custom = on_delete_custom
        self._on_change = on_change
        self._active_row: MediaRow | None = None
        self._active_kind: AppearanceKind = 'cassette'
        self._tab_widgets: dict[AppearanceKind, _AppearanceTab] = {}
        self._grid_tiles: dict[str, _AppearanceGridTile] = {}
        self._current_entries_by_kind: dict[AppearanceKind, list[AppearanceGridEntry]] = {}
        self._dual_phase_show_empty = False
        self._dual_phase_after_id: str | None = None
        self._dual_row_label_font = tkfont.Font(
            family=spec.MODULE_THREE_DUAL_SPRITE_LABEL_FONT_FAMILY,
            size=spec.MODULE_THREE_DUAL_SPRITE_LABEL_FONT_SIZE,
        )

        self._build_tabs()
        self._build_dual_sprite_row()
        self._build_footer()

    @property
    def active_kind(self) -> AppearanceKind:
        return self._active_kind

    def set_active_kind(self, kind: AppearanceKind) -> None:
        if kind not in dict(TAB_KINDS):
            return
        if kind == self._active_kind:
            return
        self._active_kind = kind
        self.refresh_from_active_row()

    def set_active_row(self, row: MediaRow | None) -> None:
        self._active_row = row
        self.refresh_from_active_row()

    def refresh_from_active_row(self) -> None:
        row = self._active_row
        if row is None:
            self._cancel_dual_phase_loop()
            return
        row.ensure_appearances()
        for kind, _label in TAB_KINDS:
            self._ensure_valid_selection(row, kind)
            self._tab_widgets[kind].set_selected(kind == self._active_kind)
            entry = self._entry_for_kind(row, kind)
            self._tab_widgets[kind].set_image(entry.displayed_inventory_path(show_empty=False) if entry else None)
        self._refresh_dual_sprite_row()
        self._refresh_footer()
        self._rebuild_grid()

    def _build_tabs(self) -> None:
        for index, (kind, label) in enumerate(TAB_KINDS):
            tab = _AppearanceTab(self.shell.tabs_pane, kind=kind, label=label, on_selected=self._handle_tab_selected)
            tab.place(x=index * spec.MODULE_THREE_TAB_SIZE[0], y=0)
            self._tab_widgets[kind] = tab

    def _build_dual_sprite_row(self) -> None:
        row_content = self.shell.dual_sprite_row.content
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
        self.dual_label.place(x=label_x, y=0, width=160, height=spec.MODULE_THREE_DUAL_SPRITE_ROW_SIZE[1] - (spec.MODULE_THREE_PANEL_BORDER_WIDTH * 2))

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
        visible = should_show_dual_sprite_controls(self._active_kind)
        if visible:
            selection = row.appearances[self._active_kind]
            self.dual_checkbox.set_checked(selection.sprite_mode == 'dual')
            self.dual_checkbox.place(
                x=spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_POS[0],
                y=spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_POS[1],
            )
            label_x = spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_POS[0] + spec.MODULE_THREE_DUAL_SPRITE_CHECKBOX_SIZE[0] + spec.MODULE_THREE_DUAL_SPRITE_LABEL_GAP_X
            self.dual_label.place(
                x=label_x,
                y=0,
                width=160,
                height=spec.MODULE_THREE_DUAL_SPRITE_ROW_SIZE[1] - (spec.MODULE_THREE_PANEL_BORDER_WIDTH * 2),
            )
        else:
            self.dual_checkbox.place_forget()
            self.dual_label.place_forget()

    def _refresh_footer(self) -> None:
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
        else:
            self.dual_custom_footer.place_forget()
            self.single_custom_footer.place(x=0, y=0)
            self.single_custom_footer.set_staged_images(
                inventory_path=staged.get('inventory_full', ''),
                world_path=staged.get('world_full', ''),
            )
            self.single_custom_footer.set_commit_enabled(can_commit_single_custom(staged))

    def _rebuild_grid(self) -> None:
        self._cancel_dual_phase_loop()
        for child in self.shell.grid_viewport.content_frame.winfo_children():
            child.destroy()
        self._grid_tiles.clear()
        self._dual_phase_show_empty = False
        row = self._active_row
        if row is None:
            return
        entries = self._entries_for_kind(self._active_kind)
        self._current_entries_by_kind[self._active_kind] = entries
        selected_key = row.appearances[self._active_kind].selected_asset_key
        row_count = max(1, (len(entries) + 3) // 4)
        content_height = row_count * spec.MODULE_THREE_GRID_TILE_SIZE[1]
        self.shell.grid_viewport.content_frame.configure(
            width=spec.MODULE_THREE_GRID_MASK_SIZE[0],
            height=content_height,
        )
        for index, entry in enumerate(entries):
            tile = _AppearanceGridTile(
                self.shell.grid_viewport.content_frame,
                entry=entry,
                on_selected=self._handle_grid_selected,
                on_remove_custom=self._handle_remove_custom,
            )
            tile.place(
                x=(index % 4) * spec.MODULE_THREE_GRID_TILE_SIZE[0],
                y=(index // 4) * spec.MODULE_THREE_GRID_TILE_SIZE[1],
            )
            tile.set_selected(entry.key == selected_key)
            self._grid_tiles[entry.key] = tile
        self.shell.grid_viewport.refresh_scroll_region()
        self._update_active_tab_icon()
        self._schedule_dual_phase_loop_if_needed()

    def _handle_tab_selected(self, kind: AppearanceKind) -> None:
        self.set_active_kind(kind)

    def _handle_grid_selected(self, key: str) -> None:
        row = self._active_row
        if row is None:
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
        self._on_change()

    def _handle_remove_custom(self, key: str) -> None:
        self._on_delete_custom(self._active_kind, key)

    def _toggle_dual_sprite(self) -> None:
        row = self._active_row
        if row is None or not should_show_dual_sprite_controls(self._active_kind):
            return
        selection = row.appearances[self._active_kind]
        selection.sprite_mode = 'single' if selection.sprite_mode == 'dual' else 'dual'
        self._refresh_dual_sprite_row()
        self._refresh_footer()
        self._on_change()

    def _ensure_valid_selection(self, row: MediaRow, kind: AppearanceKind) -> None:
        entries = self._entries_for_kind(kind)
        selection = row.appearances[kind]
        selection.selected_asset_key = BUILT_IN_DUAL_EMPTY_TO_FULL.get(selection.selected_asset_key, selection.selected_asset_key)
        if entries and selection.selected_asset_key not in {entry.key for entry in entries}:
            apply_selection_from_grid_entry(selection, entries[0])

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
            self._get_custom_assets(kind),
        )

    def _footer_uses_dual_mode(self) -> bool:
        row = self._active_row
        if row is None or not should_show_dual_sprite_controls(self._active_kind):
            return False
        return row.appearances[self._active_kind].sprite_mode == 'dual'

    def _update_active_tab_icon(self) -> None:
        row = self._active_row
        if row is None:
            return
        entry = self._entry_for_kind(row, self._active_kind)
        if entry is None:
            self._tab_widgets[self._active_kind].set_image(None)
            return
        selected_tile = self._grid_tiles.get(entry.key)
        if selected_tile is not None:
            self._tab_widgets[self._active_kind].set_image(selected_tile.current_inventory_path())
            return
        self._tab_widgets[self._active_kind].set_image(entry.displayed_inventory_path(show_empty=self._dual_phase_show_empty))

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
        if not self._grid_tiles:
            return
        self._dual_phase_show_empty = not self._dual_phase_show_empty
        for tile in self._grid_tiles.values():
            tile.set_dual_phase(show_empty=self._dual_phase_show_empty)
        self._update_active_tab_icon()
        self._schedule_dual_phase_loop_if_needed()
