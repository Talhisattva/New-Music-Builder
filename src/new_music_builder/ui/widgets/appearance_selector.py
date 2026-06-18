from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import tkinter as tk
import tkinter.font as tkfont

from new_music_builder.domain.models import AppearanceKind, MediaRow
from new_music_builder.services.asset_catalog import AssetEntry
from new_music_builder.ui import spec
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


def appearance_tab_order() -> tuple[tuple[AppearanceKind, str], ...]:
    return TAB_KINDS


def should_show_dual_sprite_controls(kind: AppearanceKind) -> bool:
    return kind in DUAL_SPRITE_KINDS


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
        self.text_label.place(x=0, y=0, width=spec.MODULE_THREE_TAB_SIZE[0], height=spec.MODULE_THREE_TAB_SIZE[1] - spec.MODULE_THREE_TAB_LABEL_BOTTOM_INSET)

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


@dataclass(slots=True)
class _TileAnimationState:
    kind: AppearanceKind
    key: str
    step: int = 0
    after_id: str | None = None


class _AppearanceGridTile(_BorderSurface):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        entry: AssetEntry,
        on_selected: Callable[[str], None],
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
        self._hovered = False
        self._selected = False
        self._image_cache: dict[int, object | None] = {}
        self.icon_label = tk.Label(self, bg=spec.MODULE_THREE_GRID_TILE_BG, bd=0, highlightthickness=0)
        self.icon_label.place(
            x=(spec.MODULE_THREE_GRID_TILE_SIZE[0] - spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0]) // 2,
            y=(spec.MODULE_THREE_GRID_TILE_SIZE[1] - spec.MODULE_THREE_GRID_TILE_ICON_SIZE[1]) // 2,
            width=spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0],
            height=spec.MODULE_THREE_GRID_TILE_ICON_SIZE[1],
        )
        for size in set(spec.MODULE_THREE_GRID_ANIMATION_SIZES + (spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0],)):
            self._image_cache[size] = load_tk_photoimage_contained(entry.inventory_path, (size, size))
        self.set_icon_size(spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0])
        for widget in (self, self.icon_label, self.content):
            widget.bind('<Enter>', self._on_enter, add='+')
            widget.bind('<Leave>', self._on_leave, add='+')
            widget.bind('<ButtonPress-1>', self._on_press, add='+')

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_colors()

    def set_icon_size(self, size: int) -> None:
        image = self._image_cache.get(size)
        if image is None:
            image = load_tk_photoimage_contained(self.entry.inventory_path, (size, size))
            self._image_cache[size] = image
        x = (spec.MODULE_THREE_GRID_TILE_SIZE[0] - size) // 2
        y = (spec.MODULE_THREE_GRID_TILE_SIZE[1] - size) // 2
        self.icon_label.place(x=x, y=y, width=size, height=size)
        self.icon_label.configure(image=image if image is not None else '')
        self.icon_label.image = image

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

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._apply_colors()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._apply_colors()

    def _on_press(self, _event: tk.Event) -> str:
        self._on_selected(self.entry.key)
        return 'break'


class AppearanceSelector:
    def __init__(
        self,
        shell: AppearancePanelShell,
        *,
        asset_catalog: dict[str, list[AssetEntry]],
        small_check_icon_path: str | None,
        on_change: Callable[[], None],
    ) -> None:
        self.shell = shell
        self.asset_catalog = asset_catalog
        self._small_check_icon_path = small_check_icon_path
        self._on_change = on_change
        self._active_row: MediaRow | None = None
        self._active_kind: AppearanceKind = 'cassette'
        self._tab_widgets: dict[AppearanceKind, _AppearanceTab] = {}
        self._grid_tiles: dict[str, _AppearanceGridTile] = {}
        self._grid_animation: _TileAnimationState | None = None
        self._dual_row_label_font = tkfont.Font(
            family=spec.MODULE_THREE_DUAL_SPRITE_LABEL_FONT_FAMILY,
            size=spec.MODULE_THREE_DUAL_SPRITE_LABEL_FONT_SIZE,
        )

        self._build_tabs()
        self._build_dual_sprite_row()

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
            return
        row.ensure_appearances()
        for kind, _label in TAB_KINDS:
            self._ensure_default_selection(row, kind)
            self._tab_widgets[kind].set_selected(kind == self._active_kind)
            self._tab_widgets[kind].set_image(self._entry_for_kind(row, kind).inventory_path if self._entry_for_kind(row, kind) else None)
        self._refresh_dual_sprite_row()
        self._rebuild_grid()

    def _build_tabs(self) -> None:
        for index, (kind, label) in enumerate(TAB_KINDS):
            tab = _AppearanceTab(self.shell.tabs_pane.content, kind=kind, label=label, on_selected=self._handle_tab_selected)
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

    def _rebuild_grid(self) -> None:
        if self._grid_animation is not None and self._grid_animation.after_id is not None:
            self.shell.grid_viewport.after_cancel(self._grid_animation.after_id)
        self._grid_animation = None
        for child in self.shell.grid_viewport.content_frame.winfo_children():
            child.destroy()
        self._grid_tiles.clear()
        row = self._active_row
        if row is None:
            return
        entries = self.asset_catalog.get(self._active_kind, [])
        selected_key = row.appearances[self._active_kind].selected_asset_key
        for index, entry in enumerate(entries):
            tile = _AppearanceGridTile(
                self.shell.grid_viewport.content_frame,
                entry=entry,
                on_selected=self._handle_grid_selected,
            )
            tile.place(
                x=(index % 4) * spec.MODULE_THREE_GRID_TILE_SIZE[0],
                y=(index // 4) * spec.MODULE_THREE_GRID_TILE_SIZE[1],
            )
            tile.set_selected(entry.key == selected_key)
            self._grid_tiles[entry.key] = tile
        self.shell.grid_viewport.refresh_scroll_region()

    def _handle_tab_selected(self, kind: AppearanceKind) -> None:
        self.set_active_kind(kind)

    def _handle_grid_selected(self, key: str) -> None:
        row = self._active_row
        if row is None:
            return
        selection = row.appearances[self._active_kind]
        selection.selected_asset_key = key
        entry = next((item for item in self.asset_catalog.get(self._active_kind, []) if item.key == key), None)
        if entry is not None:
            selection.sprite_mode = entry.sprite_mode if should_show_dual_sprite_controls(self._active_kind) else 'single'
        for tile_key, tile in self._grid_tiles.items():
            tile.set_selected(tile_key == key)
            if tile_key != key:
                tile.set_icon_size(spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0])
        self._tab_widgets[self._active_kind].set_image(entry.inventory_path if entry is not None else None)
        self._refresh_dual_sprite_row()
        self._start_tile_animation(key)
        self._on_change()

    def _start_tile_animation(self, key: str) -> None:
        tile = self._grid_tiles.get(key)
        if tile is None:
            return
        if self._grid_animation is not None and self._grid_animation.after_id is not None:
            previous = self._grid_tiles.get(self._grid_animation.key)
            if previous is not None:
                previous.set_icon_size(spec.MODULE_THREE_GRID_TILE_ICON_SIZE[0])
            self.shell.grid_viewport.after_cancel(self._grid_animation.after_id)
        self._grid_animation = _TileAnimationState(kind=self._active_kind, key=key)

        def advance(step: int) -> None:
            current = self._grid_tiles.get(key)
            if (
                current is None
                or self._grid_animation is None
                or self._grid_animation.key != key
                or self._grid_animation.kind != self._active_kind
            ):
                return
            size = spec.MODULE_THREE_GRID_ANIMATION_SIZES[step]
            current.set_icon_size(size)
            if step + 1 >= len(spec.MODULE_THREE_GRID_ANIMATION_SIZES):
                if self._grid_animation is not None:
                    self._grid_animation.after_id = None
                return
            delay = spec.MODULE_THREE_GRID_ANIMATION_DELAYS_MS[step]
            after_id = self.shell.grid_viewport.after(delay, lambda: advance(step + 1))
            if self._grid_animation is not None:
                self._grid_animation.after_id = after_id

        advance(0)

    def _toggle_dual_sprite(self) -> None:
        row = self._active_row
        if row is None or not should_show_dual_sprite_controls(self._active_kind):
            return
        selection = row.appearances[self._active_kind]
        selection.sprite_mode = 'single' if selection.sprite_mode == 'dual' else 'dual'
        self._refresh_dual_sprite_row()
        self._on_change()

    def _ensure_default_selection(self, row: MediaRow, kind: AppearanceKind) -> None:
        entries = self.asset_catalog.get(kind, [])
        selection = row.appearances[kind]
        if entries and not selection.selected_asset_key:
            selection.selected_asset_key = entries[0].key
            selection.sprite_mode = entries[0].sprite_mode if should_show_dual_sprite_controls(kind) else 'single'

    def _entry_for_kind(self, row: MediaRow, kind: AppearanceKind) -> AssetEntry | None:
        entries = self.asset_catalog.get(kind, [])
        if not entries:
            return None
        selected_key = row.appearances[kind].selected_asset_key
        return next((entry for entry in entries if entry.key == selected_key), entries[0])
