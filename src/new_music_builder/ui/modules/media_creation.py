from __future__ import annotations

from pathlib import Path
import tkinter.filedialog as fd

import customtkinter as ctk

from new_music_builder.domain.models import MediaRow, TrackEntry
from new_music_builder.services.asset_catalog import AssetEntry
from new_music_builder.ui import theme
from new_music_builder.ui.widgets.images import load_ctk_image
from new_music_builder.ui.widgets.module_panel import ModulePanel
from new_music_builder.ui.widgets.tooltip import Tooltip


class MediaCreationModule(ModulePanel):
    def __init__(self, master, session, asset_catalog, on_change, on_select_row):
        super().__init__(master, 'PHASE 2: MEDIA CREATION')
        self.session = session
        self.asset_catalog = asset_catalog
        self.on_change = on_change
        self.on_select_row = on_select_row
        self.active_side = 'A'
        self.active_row_id = session.project.media_rows[0].row_id if session.project.media_rows else None
        self.scroll = ctk.CTkScrollableFrame(self.body, fg_color='transparent')
        self.scroll.pack(fill='both', expand=True, padx=8, pady=8)
        self.refresh()

    def set_active_row(self, row_id: int | None) -> None:
        self.active_row_id = row_id
        self.refresh()

    def add_row(self) -> None:
        row_id = self.session.add_media_row()
        self.active_row_id = row_id
        for row in self.session.project.media_rows:
            row.expanded = row.row_id == row_id
        self.on_change()
        self.on_select_row(row_id)
        self.refresh()

    def remove_active_row(self) -> None:
        if self.active_row_id is None:
            return
        self.session.remove_media_row(self.active_row_id)
        self.active_row_id = self.session.project.media_rows[0].row_id
        self.on_change()
        self.on_select_row(self.active_row_id)
        self.refresh()

    def refresh(self) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        actions = ctk.CTkFrame(self.scroll, fg_color='transparent')
        actions.pack(fill='x', pady=(0, 8))
        add_button = ctk.CTkButton(actions, text='+ Add Media Row', command=self.add_row)
        add_button.pack(side='left', expand=True, fill='x', padx=(0, 4))
        Tooltip(add_button, 'Click to add a new media row to your project.')
        remove_button = ctk.CTkButton(actions, text='X Remove Media Row', command=self.remove_active_row)
        remove_button.pack(side='left', expand=True, fill='x', padx=(4, 0))
        Tooltip(remove_button, 'Remove the current expanded active media row.')

        for row in self.session.project.media_rows:
            self._render_row(row)

    def _render_row(self, row: MediaRow) -> None:
        card = ctk.CTkFrame(self.scroll, fg_color=theme.PANEL, border_color=theme.BORDER, border_width=1, corner_radius=12)
        card.pack(fill='x', pady=(0, 8))
        top = ctk.CTkFrame(card, fg_color='transparent')
        top.pack(fill='x', padx=10, pady=10)
        number = ctk.CTkButton(top, text=str(row.row_id), width=36, command=lambda rid=row.row_id: self._toggle_row(rid))
        number.pack(side='left')
        cover = ctk.CTkLabel(top, text='Cover', width=56)
        cover.pack(side='left', padx=(8, 8))
        cover_image = load_ctk_image(row.cover_path, (48, 48))
        if cover_image is not None:
            cover.configure(text='', image=cover_image)
            cover.image = cover_image
        media_text = ' '.join([label for key, label in [('cassette', 'Cas'), ('vinyl', 'Vin'), ('cd', 'CD')] if row.enabled_media.get(key)])
        ctk.CTkLabel(top, text=media_text or 'No Media', text_color=theme.MUTED).pack(side='left', padx=(0, 12))
        summary = f"A-Side ({len(row.tracks_a)} Songs)    B-Side ({len(row.tracks_b)} Songs)"
        ctk.CTkLabel(top, text=summary, text_color=theme.TEXT, anchor='w').pack(side='left', fill='x', expand=True)

        if row.expanded:
            self._render_expanded(card, row)

    def _toggle_row(self, row_id: int) -> None:
        self.active_row_id = row_id
        for row in self.session.project.media_rows:
            if row.row_id == row_id:
                row.expanded = not row.expanded
            else:
                row.expanded = False
        self.on_select_row(row_id)
        self.on_change()
        self.refresh()

    def _render_expanded(self, master, row: MediaRow) -> None:
        body = ctk.CTkFrame(master, fg_color=theme.PANEL_ALT)
        body.pack(fill='x', padx=10, pady=(0, 10))

        left = ctk.CTkFrame(body, fg_color='transparent')
        left.pack(side='left', fill='y', padx=10, pady=10)
        cover_btn = ctk.CTkButton(left, text='Pick Cover', width=140, height=140, command=lambda rid=row.row_id: self._pick_cover(rid))
        cover_btn.pack()
        if row.cover_path:
            cover_image = load_ctk_image(row.cover_path, (132, 132))
            if cover_image is not None:
                cover_btn.configure(text='', image=cover_image)
                cover_btn.image = cover_image
        toggle_row = ctk.CTkFrame(left, fg_color='transparent')
        toggle_row.pack(fill='x', pady=(8, 0))
        for kind, label in [('cassette', 'Cas'), ('vinyl', 'Vin'), ('cd', 'CD')]:
            button = ctk.CTkButton(
                toggle_row,
                text=label,
                width=40,
                fg_color=theme.ACCENT if row.enabled_media[kind] else theme.PANEL,
                command=lambda current=kind, rid=row.row_id: self._toggle_media(rid, current),
            )
            button.pack(side='left', padx=4)

        center = ctk.CTkFrame(body, fg_color='transparent')
        center.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        name_var = ctk.StringVar(value=row.media_name)
        name_entry = ctk.CTkEntry(center, textvariable=name_var)
        name_entry.pack(fill='x')
        name_entry.bind('<FocusOut>', lambda _e, rid=row.row_id, var=name_var: self._rename_row(rid, var.get()))
        side_bar = ctk.CTkFrame(center, fg_color='transparent')
        side_bar.pack(fill='x', pady=(8, 8))
        for side in ['A', 'B']:
            button = ctk.CTkButton(side_bar, text=f'{side} - Side', fg_color=theme.ACCENT if self.active_side == side else theme.PANEL)
            button.configure(command=lambda current=side: self._switch_side(current))
            button.pack(side='left', padx=(0, 8))
        self._render_track_list(center, row)

        right = ctk.CTkFrame(body, fg_color='transparent', width=240)
        right.pack(side='left', fill='y', padx=10, pady=10)
        ctk.CTkLabel(right, text='LIVE PREVIEW', text_color=theme.TEXT).pack(anchor='w')
        preview_box = ctk.CTkFrame(right, fg_color=theme.PANEL, width=220, height=180)
        preview_box.pack(fill='both', expand=True, pady=(8, 0))
        preview_box.pack_propagate(False)
        for item in self._preview_assets_for_row(row):
            image = load_ctk_image(item.inventory_path, (48, 48))
            label = ctk.CTkLabel(preview_box, text=item.label, image=image, compound='top')
            label.image = image
            label.pack(side='left', padx=6, pady=12)

    def _render_track_list(self, master, row: MediaRow) -> None:
        tracks = row.tracks_a if self.active_side == 'A' else row.tracks_b
        box = ctk.CTkScrollableFrame(master, height=180)
        box.pack(fill='both', expand=True)
        for index, track in enumerate(tracks, start=1):
            line = ctk.CTkFrame(box, fg_color=theme.PANEL)
            line.pack(fill='x', pady=(0, 4))
            ctk.CTkLabel(line, text=f'{index:02d}', width=28).pack(side='left', padx=4)
            ctk.CTkLabel(line, text=track.display_label or Path(track.source_path).name or 'Empty Track', anchor='w').pack(side='left', fill='x', expand=True)
            ctk.CTkLabel(line, text=track.duration or '--:--').pack(side='left', padx=4)
        controls = ctk.CTkFrame(master, fg_color='transparent')
        controls.pack(fill='x', pady=(8, 0))
        ctk.CTkButton(controls, text='+ Add Songs', command=lambda rid=row.row_id: self._add_songs(rid)).pack(side='left', padx=(0, 6))
        ctk.CTkButton(controls, text='- Clear Side', command=lambda rid=row.row_id: self._clear_side(rid)).pack(side='left')

    def _switch_side(self, side: str) -> None:
        self.active_side = side
        self.refresh()

    def _rename_row(self, row_id: int, value: str) -> None:
        for row in self.session.project.media_rows:
            if row.row_id == row_id:
                row.media_name = value.strip() or f'Media Row {row_id}'
                break
        self.on_change()

    def _toggle_media(self, row_id: int, kind: str) -> None:
        for row in self.session.project.media_rows:
            if row.row_id == row_id:
                row.enabled_media[kind] = not row.enabled_media[kind]
        self.on_change()
        self.refresh()

    def _pick_cover(self, row_id: int) -> None:
        selected = fd.askopenfilename(filetypes=[('Images', '*.png;*.jpg;*.jpeg;*.webp')])
        if not selected:
            return
        for row in self.session.project.media_rows:
            if row.row_id == row_id:
                row.cover_path = selected
        self.on_change()
        self.refresh()

    def _add_songs(self, row_id: int) -> None:
        selected = fd.askopenfilenames(filetypes=[('Audio', '*.ogg;*.flac;*.wav;*.mp3')])
        if not selected:
            return
        for row in self.session.project.media_rows:
            if row.row_id == row_id:
                target = row.tracks_a if self.active_side == 'A' else row.tracks_b
                for path in selected:
                    target.append(TrackEntry(source_path=path, display_label=Path(path).stem, conversion_status='linked'))
        self.on_change()
        self.refresh()

    def _clear_side(self, row_id: int) -> None:
        for row in self.session.project.media_rows:
            if row.row_id == row_id:
                if self.active_side == 'A':
                    row.tracks_a = []
                else:
                    row.tracks_b = []
        self.on_change()
        self.refresh()

    def _preview_assets_for_row(self, row: MediaRow) -> list[AssetEntry]:
        assets: list[AssetEntry] = []
        for kind, appearance_key in [('cassette', 'cassette'), ('vinyl', 'vinyl'), ('cd', 'cd')]:
            if not row.enabled_media.get(kind):
                continue
            chosen = row.appearances[appearance_key].selected_asset_key
            matches = [entry for entry in self.asset_catalog.get(appearance_key, []) if entry.key == chosen]
            if not matches and self.asset_catalog.get(appearance_key):
                matches = [self.asset_catalog[appearance_key][0]]
            if matches:
                assets.append(matches[0])
        return assets[:3]
