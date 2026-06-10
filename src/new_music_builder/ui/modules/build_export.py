from __future__ import annotations

import customtkinter as ctk

from new_music_builder.ui import theme
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
        self._build()

    def _build(self) -> None:
        top = ctk.CTkFrame(self.body, fg_color='transparent')
        top.pack(fill='both', expand=True, padx=10, pady=(10, 6))
        left = ctk.CTkFrame(top, fg_color='transparent')
        left.pack(side='left', fill='both', expand=True, padx=(0, 6))
        right = ctk.CTkFrame(top, fg_color='transparent')
        right.pack(side='left', fill='both', expand=True, padx=(6, 0))

        ctk.CTkLabel(left, text='QUEUE / PROGRESS', text_color=theme.TEXT).pack(anchor='w')
        self.queue_frame.pack(in_=left, fill='both', expand=True, pady=(6, 0))

        ctk.CTkLabel(right, text='GENERATED ITEM PREVIEW', text_color=theme.TEXT).pack(anchor='w')
        self.preview_frame.pack(in_=right, fill='both', expand=True, pady=(6, 0))

        ctk.CTkLabel(self.body, text='BUILD LOG', text_color=theme.TEXT).pack(anchor='w', padx=10)
        self.log_box.pack(fill='x', padx=10, pady=(6, 6))

        actions = ctk.CTkFrame(self.body, fg_color='transparent')
        actions.pack(fill='x', padx=10, pady=(0, 10))
        ctk.CTkButton(actions, text='OPEN OUTPUT FOLDER', command=lambda: None).pack(side='left', padx=(0, 6))
        ctk.CTkButton(actions, text='CANCEL / RESET', fg_color=theme.PANEL, command=self.on_reset).pack(side='left')
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
                ctk.CTkLabel(outer, text=f'{row.media_name} (Side {side_name})').pack(anchor='w', padx=8, pady=(6, 2))
                ctk.CTkProgressBar(outer).pack(fill='x', padx=8, pady=(0, 4))
                ctk.CTkLabel(outer, text=f'{len(tracks)} songs queued').pack(anchor='w', padx=8, pady=(0, 6))
        for entry in preview_entries:
            tile = ctk.CTkFrame(self.preview_frame, fg_color=theme.PANEL_ALT)
            tile.pack(fill='x', pady=(0, 4))
            ctk.CTkLabel(tile, text=entry).pack(anchor='w', padx=8, pady=8)
        self.log_box.delete('1.0', 'end')
        self.log_box.insert('end', '\n'.join(build_log) if build_log else 'Build has not started yet.')