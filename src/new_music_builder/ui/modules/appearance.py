from __future__ import annotations

import tkinter.filedialog as fd

import customtkinter as ctk

from new_music_builder.ui import theme
from new_music_builder.ui.widgets.buttons import apply_builder_button_style, make_builder_button
from new_music_builder.ui.widgets.checkboxes import make_builder_checkbox
from new_music_builder.ui.widgets.images import load_ctk_image
from new_music_builder.ui.widgets.module_panel import ModulePanel
from new_music_builder.ui.widgets.tooltip import Tooltip


class AppearanceModule(ModulePanel):
    PREFERRED_WIDTH = 408

    def __init__(self, master, session, asset_catalog, on_change):
        super().__init__(master, 'CUSTOMIZE APPEARANCE')
        self.session = session
        self.asset_catalog = asset_catalog
        self.on_change = on_change
        self.active_kind = 'cassette'
        self.active_row_id = session.project.media_rows[0].row_id if session.project.media_rows else None
        self.asset_grid = ctk.CTkScrollableFrame(self.body, fg_color='transparent')
        self.kind_buttons: dict[str, ctk.CTkButton] = {}
        self._asset_columns = 0
        self._layout_refresh_after: str | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.tabs = ctk.CTkFrame(self.body, fg_color='transparent')
        self.tabs.pack(fill='x', padx=10, pady=(10, 4))
        kinds = [('cassette', 'Cassette'), ('vinyl', 'Vinyl'), ('cd', 'CD'), ('case', 'Case'), ('jacket', 'Jacket'), ('cd_cover', 'CD Cover')]
        for column in range(3):
            self.tabs.grid_columnconfigure(column, weight=1)
        for index, (kind, label) in enumerate(kinds):
            button = make_builder_button(
                self.tabs,
                label,
                lambda current=kind: self._switch_kind(current),
                variant='subtle',
                size='compact',
            )
            button.grid(row=index // 3, column=index % 3, padx=3, pady=3, sticky='ew')
            self.kind_buttons[kind] = button
        self.dual_var = ctk.BooleanVar(value=False)
        self.dual_check = make_builder_checkbox(self.body, 'Dual Sprite Full/Empty', self.dual_var)
        self.dual_check.pack(anchor='w', padx=12, pady=(0, 4))
        self.asset_grid.configure(scrollbar_button_color=theme.ACCENT, scrollbar_button_hover_color=theme.ACCENT_DARK)
        self.asset_grid.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        self.body.bind('<Configure>', self._schedule_layout_refresh)
        self.custom = ctk.CTkFrame(self.body, fg_color=theme.PANEL)
        self.custom.pack(fill='x', padx=10, pady=(0, 10))
        self.custom_label = ctk.CTkLabel(
            self.custom,
            text='Add Custom Asset Pair',
            text_color=theme.TEXT,
            font=ctk.CTkFont(family='Orbitron', size=13, weight='bold'),
        )
        self.custom_label.pack(anchor='w', padx=10, pady=(10, 6))
        self.custom_buttons = ctk.CTkFrame(self.custom, fg_color='transparent')
        self.custom_buttons.pack(fill='x', padx=10, pady=(0, 10))
        make_builder_button(self.custom_buttons, 'Pick Inventory', lambda: self._pick_custom('inventory')).pack(side='left', padx=(0, 6))
        make_builder_button(self.custom_buttons, 'Pick World', lambda: self._pick_custom('world'), variant='secondary').pack(side='left')
        self.custom_status = ctk.CTkLabel(self.custom, text='', text_color=theme.MUTED)
        self.custom_status.pack(anchor='w', padx=10, pady=(0, 10))
        self._custom_pending: dict[str, str] = {}

    def set_active_row(self, row_id: int | None) -> None:
        self.active_row_id = row_id
        self.refresh()

    def _switch_kind(self, kind: str) -> None:
        self.active_kind = kind
        self.refresh()

    def _schedule_layout_refresh(self, _event=None) -> None:
        if self._layout_refresh_after is not None:
            self.after_cancel(self._layout_refresh_after)
        self._layout_refresh_after = self.after(80, self._refresh_layout_if_needed)

    def _refresh_layout_if_needed(self) -> None:
        self._layout_refresh_after = None
        columns = self._calculate_asset_columns()
        if columns != self._asset_columns:
            self.refresh()

    def _calculate_asset_columns(self) -> int:
        available_width = max(self.asset_grid.winfo_width(), self.body.winfo_width() - 24, 240)
        return max(2, min(3, available_width // 104))

    def refresh(self) -> None:
        row = self._active_row()
        if row is None:
            return
        for kind, button in self.kind_buttons.items():
            apply_builder_button_style(
                button,
                variant='selected' if self.active_kind == kind else 'subtle',
                size='compact',
            )
        selection = row.appearances[self.active_kind]
        self.dual_check.pack_forget()
        if self.active_kind in {'case', 'jacket', 'cd_cover'}:
            self.dual_var.set(selection.sprite_mode == 'dual')
            self.dual_check.pack(anchor='w', padx=12, pady=(0, 4))
        for child in self.asset_grid.winfo_children():
            child.destroy()
        entries = self.asset_catalog.get(self.active_kind, [])
        if entries and not selection.selected_asset_key:
            selection.selected_asset_key = entries[0].key
        row.appearances[self.active_kind] = selection
        columns = self._calculate_asset_columns()
        self._asset_columns = columns
        for column in range(columns):
            self.asset_grid.grid_columnconfigure(column, weight=1)
        for idx, entry in enumerate(entries):
            tile = make_builder_button(
                self.asset_grid,
                '',
                lambda key=entry.key: self._select_asset(key),
                width=84,
                variant='selected' if selection.selected_asset_key == entry.key else 'subtle',
                size='compact',
                image=load_ctk_image(entry.inventory_path, (56, 56)),
                height=84,
            )
            tile.configure(anchor='center', border_width=2)
            Tooltip(tile, entry.label)
            tile.grid(row=idx // columns, column=idx % columns, padx=3, pady=3, sticky='n')

    def _select_asset(self, key: str) -> None:
        row = self._active_row()
        if row is None:
            return
        selected = row.appearances[self.active_kind]
        selected.selected_asset_key = key
        entries = [entry for entry in self.asset_catalog.get(self.active_kind, []) if entry.key == key]
        if entries:
            selected.sprite_mode = entries[0].sprite_mode
        self.on_change()
        self.refresh()

    def _pick_custom(self, which: str) -> None:
        selected = fd.askopenfilename(filetypes=[('Images', '*.png;*.jpg;*.jpeg;*.webp')])
        if not selected:
            return
        self._custom_pending[which] = selected
        self.custom_status.configure(text=f"{which.title()} selected: {selected}")
        if {'inventory', 'world'}.issubset(self._custom_pending):
            self._commit_custom_pair()

    def _commit_custom_pair(self) -> None:
        row = self._active_row()
        if row is None:
            return
        selection = row.appearances[self.active_kind]
        selection.source = 'custom'
        selection.inventory_full = self._custom_pending.get('inventory', '')
        selection.world_full = self._custom_pending.get('world', '')
        selection.sprite_mode = 'dual' if self.dual_var.get() else 'single'
        self.session.project.custom_assets.setdefault(self.active_kind, []).append({
            'inventory_full': selection.inventory_full,
            'world_full': selection.world_full,
            'sprite_mode': selection.sprite_mode,
        })
        self._custom_pending = {}
        self.custom_status.configure(text='Custom asset pair added to project state.')
        self.on_change()

    def _active_row(self):
        for row in self.session.project.media_rows:
            if row.row_id == self.active_row_id:
                return row
        return self.session.project.media_rows[0] if self.session.project.media_rows else None
