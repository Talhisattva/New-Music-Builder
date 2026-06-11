from __future__ import annotations

import customtkinter as ctk

from new_music_builder.ui import theme
from new_music_builder.ui.widgets.fields import make_builder_label
from new_music_builder.ui.widgets.module_panel import ModulePanel


class BuildSummaryModule(ModulePanel):
    def __init__(self, master, session):
        super().__init__(master, 'BUILD SUMMARY')
        self.session = session
        self.rows = {}
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.stats = ctk.CTkFrame(self.body, fg_color='transparent')
        self.stats.pack(fill='both', expand=True, padx=8, pady=8)
        for label in ['Media Rows', 'Total Sides', 'Total Songs', 'Converted', 'Queued', 'Errors']:
            row = ctk.CTkFrame(self.stats, fg_color=theme.PANEL)
            row.pack(fill='x', pady=(0, 3))
            make_builder_label(row, label, text_color=theme.TEXT, size=11, weight='bold').pack(side='left', padx=8, pady=5)
            value = make_builder_label(row, '0', text_color=theme.TEXT, size=11, weight='bold')
            value.pack(side='right', padx=8)
            self.rows[label] = value

    def refresh(self) -> None:
        media_rows = len(self.session.project.media_rows)
        total_sides = media_rows * 2
        total_songs = sum(len(row.tracks_a) + len(row.tracks_b) for row in self.session.project.media_rows)
        values = {
            'Media Rows': media_rows,
            'Total Sides': total_sides,
            'Total Songs': total_songs,
            'Converted': 0,
            'Queued': total_songs,
            'Errors': 0,
        }
        for key, value in values.items():
            self.rows[key].configure(text=str(value), text_color=theme.ERROR if key == 'Errors' and value else theme.TEXT)
