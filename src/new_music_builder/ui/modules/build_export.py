from __future__ import annotations

import customtkinter as ctk

from new_music_builder.ui import theme
from new_music_builder.ui.widgets.buttons import make_builder_button
from new_music_builder.ui.widgets.fields import (
    apply_builder_progress_style,
    apply_builder_textbox_style,
    make_builder_label,
)
from new_music_builder.ui.widgets.module_panel import ModulePanel


class BuildExportModule(ModulePanel):
    def __init__(self, master, session, on_build, on_reset):
        super().__init__(master, 'PHASE 3 : BUILD & EXPORT', header_button=True, command=on_build)
        self.session = session
        self.on_build = on_build
        self.on_reset = on_reset
        self.queue_frame = ctk.CTkScrollableFrame(self.body, fg_color=theme.PANEL)
        self.preview_frame = ctk.CTkScrollableFrame(self.body, fg_color=theme.PANEL)
        self.log_box = ctk.CTkTextbox(self.body, height=120)
        apply_builder_textbox_style(self.log_box)
        self._build()

    def _build(self) -> None:
        top = ctk.CTkFrame(self.body, fg_color='transparent')
        top.pack(fill='both', expand=True, padx=10, pady=(10, 6))
        left = ctk.CTkFrame(top, fg_color='transparent')
        left.pack(side='left', fill='both', expand=True, padx=(0, 6))
        right = ctk.CTkFrame(top, fg_color='transparent')
        right.pack(side='left', fill='both', expand=True, padx=(6, 0))

        make_builder_label(left, 'QUEUE / PROGRESS', text_color=theme.TEXT, size=12, weight='bold').pack(anchor='w')
        self.queue_frame.pack(in_=left, fill='both', expand=True, pady=(6, 0))

        make_builder_label(right, 'GENERATED ITEM PREVIEW', text_color=theme.TEXT, size=12, weight='bold').pack(anchor='w')
        self.preview_frame.pack(in_=right, fill='both', expand=True, pady=(6, 0))

        make_builder_label(self.body, 'BUILD LOG', text_color=theme.TEXT, size=12, weight='bold').pack(anchor='w', padx=10)
        self.log_box.pack(fill='x', padx=10, pady=(6, 6))

        actions = ctk.CTkFrame(self.body, fg_color='transparent')
        actions.pack(fill='x', padx=10, pady=(0, 10))
        make_builder_button(actions, 'OPEN OUTPUT FOLDER', lambda: None).pack(side='left', padx=(0, 6))
        make_builder_button(actions, 'CANCEL / RESET', self.on_reset, variant='secondary').pack(side='left')
        self.refresh([], [])

    def refresh(self, build_log: list[str], preview_entries: list[str]) -> None:
        for child in self.queue_frame.winfo_children():
            child.destroy()
        for child in self.preview_frame.winfo_children():
            child.destroy()
        for row in self.session.project.media_rows:
            for side_name, tracks in [('A', row.tracks_a), ('B', row.tracks_b)]:
                outer = ctk.CTkFrame(self.queue_frame, fg_color=theme.PANEL_ALT)
                outer.pack(fill='x', pady=(0, 4))
                make_builder_label(outer, f'{row.media_name} (Side {side_name})', size=12, weight='bold').pack(anchor='w', padx=8, pady=(6, 2))
                progress = ctk.CTkProgressBar(outer)
                apply_builder_progress_style(progress)
                progress.set(0)
                progress.pack(fill='x', padx=8, pady=(0, 4))
                make_builder_label(outer, f'{len(tracks)} songs queued', text_color=theme.MUTED, size=11).pack(anchor='w', padx=8, pady=(0, 6))
        for entry in preview_entries:
            tile = ctk.CTkFrame(self.preview_frame, fg_color=theme.PANEL_ALT)
            tile.pack(fill='x', pady=(0, 4))
            make_builder_label(tile, entry, size=12, weight='bold').pack(anchor='w', padx=8, pady=8)
        self.log_box.delete('1.0', 'end')
        self.log_box.insert('end', '\n'.join(build_log) if build_log else 'Build has not started yet.')
