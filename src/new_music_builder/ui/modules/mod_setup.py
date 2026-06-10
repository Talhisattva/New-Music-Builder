from __future__ import annotations

from pathlib import Path
import tkinter.filedialog as fd

import customtkinter as ctk

from new_music_builder.platform.paths import detect_workshop_dir
from new_music_builder.ui import theme
from new_music_builder.ui.widgets.fields import LabeledEntry
from new_music_builder.ui.widgets.images import load_ctk_image
from new_music_builder.ui.widgets.module_panel import ModulePanel
from new_music_builder.ui.widgets.tooltip import Tooltip


class ModSetupModule(ModulePanel):
    def __init__(self, master, session, on_change, save_callback, load_callback):
        super().__init__(master, 'PHASE 1: MOD SETUP')
        self.session = session
        self.on_change = on_change
        self.save_callback = save_callback
        self.load_callback = load_callback
        self.poster_label: ctk.CTkLabel | None = None
        self.detected_label: ctk.CTkLabel | None = None
        self._vars = {
            'mod_name': ctk.StringVar(value=session.project.mod_name),
            'mod_id': ctk.StringVar(value=session.project.mod_id),
            'parent_mod_id': ctk.StringVar(value=session.project.parent_mod_id),
            'author': ctk.StringVar(value=session.project.author),
            'ogg_output_folder': ctk.StringVar(value=session.project.ogg_output_folder),
            'workshop_output_folder': ctk.StringVar(value=session.project.workshop_output_folder),
            'poster': ctk.StringVar(value=session.project.workshop_poster_path),
            'write_name': ctk.BooleanVar(value=session.project.write_mod_name_on_poster),
        }
        self._build()
        self.refresh()

    def _build(self) -> None:
        form = ctk.CTkFrame(self.body, fg_color='transparent')
        form.pack(fill='x', padx=12, pady=12)
        for key, label in [
            ('mod_name', 'Mod Name'),
            ('mod_id', 'Mod ID'),
            ('parent_mod_id', 'Parent Mod ID'),
            ('author', 'Author'),
        ]:
            row = LabeledEntry(form, label, self._vars[key])
            row.pack(fill='x', pady=(0, 8))
            row.entry.bind('<FocusOut>', self._commit_text)

        preview_row = ctk.CTkFrame(self.body, fg_color='transparent')
        preview_row.pack(fill='x', padx=12, pady=(0, 12))
        poster_frame = ctk.CTkFrame(preview_row, width=180, height=180, fg_color=theme.PANEL, border_color=theme.BORDER, border_width=1)
        poster_frame.pack(side='left')
        poster_frame.pack_propagate(False)
        self.poster_label = ctk.CTkLabel(poster_frame, text='Poster Preview')
        self.poster_label.pack(expand=True)
        pick_button = ctk.CTkButton(preview_row, text='Pick Poster', width=110, command=self.pick_poster)
        pick_button.pack(anchor='nw', padx=(12, 0))
        Tooltip(pick_button, 'Choose the Workshop preview/poster image for this project.')
        eye_button = ctk.CTkButton(preview_row, text='Inspect Poster', width=110, command=self.show_poster)
        eye_button.pack(anchor='nw', padx=(12, 0), pady=(8, 0))
        Tooltip(eye_button, 'Open a larger poster preview in a popup window.')
        write_name = ctk.CTkCheckBox(preview_row, text='Write Mod Name On Poster', variable=self._vars['write_name'], command=self._commit_boolean)
        write_name.pack(anchor='nw', padx=(12, 0), pady=(16, 0))

        folder_block = ctk.CTkFrame(self.body, fg_color='transparent')
        folder_block.pack(fill='x', padx=12, pady=(0, 12))
        self._folder_row(folder_block, 'OGG Output Folder', 'ogg_output_folder', self.pick_ogg_folder)
        self._folder_row(folder_block, 'Zomboid Workshop Folder', 'workshop_output_folder', self.pick_workshop_folder, detected=True)

        buttons = ctk.CTkFrame(self.body, fg_color='transparent')
        buttons.pack(fill='x', padx=12, pady=(0, 12))
        ctk.CTkButton(buttons, text='SAVE', command=self.save_callback).pack(side='left', expand=True, fill='x', padx=(0, 6))
        ctk.CTkButton(buttons, text='LOAD', command=self.load_callback).pack(side='left', expand=True, fill='x', padx=(6, 0))

    def _folder_row(self, master, label_text: str, key: str, command, detected: bool = False) -> None:
        row = ctk.CTkFrame(master, fg_color='transparent')
        row.pack(fill='x', pady=(0, 8))
        ctk.CTkLabel(row, text=label_text, text_color=theme.TEXT, anchor='w').pack(fill='x')
        inner = ctk.CTkFrame(row, fg_color='transparent')
        inner.pack(fill='x', pady=(4, 0))
        entry = ctk.CTkEntry(inner, textvariable=self._vars[key])
        entry.pack(side='left', expand=True, fill='x')
        entry.bind('<FocusOut>', self._commit_text)
        ctk.CTkButton(inner, text='Browse', width=90, command=command).pack(side='left', padx=(8, 0))
        if detected:
            self.detected_label = ctk.CTkLabel(inner, text='', text_color=theme.SUCCESS)
            self.detected_label.pack(side='left', padx=(8, 0))

    def _commit_text(self, _event=None) -> None:
        self.session.project.mod_name = self._vars['mod_name'].get().strip()
        self.session.project.mod_id = self._vars['mod_id'].get().strip()
        self.session.project.parent_mod_id = self._vars['parent_mod_id'].get().strip() or 'NewMusic'
        self.session.project.author = self._vars['author'].get().strip()
        self.session.project.ogg_output_folder = self._vars['ogg_output_folder'].get().strip()
        self.session.project.workshop_output_folder = self._vars['workshop_output_folder'].get().strip()
        self.session.project.workshop_poster_path = self._vars['poster'].get().strip()
        self.on_change()

    def _commit_boolean(self) -> None:
        self.session.project.write_mod_name_on_poster = bool(self._vars['write_name'].get())
        self.on_change()

    def pick_poster(self) -> None:
        selected = fd.askopenfilename(filetypes=[('Images', '*.png;*.jpg;*.jpeg;*.webp')])
        if selected:
            self._vars['poster'].set(selected)
            self._commit_text()
            self.refresh()

    def pick_ogg_folder(self) -> None:
        selected = fd.askdirectory()
        if selected:
            self._vars['ogg_output_folder'].set(selected)
            self._commit_text()

    def pick_workshop_folder(self) -> None:
        selected = fd.askdirectory()
        if selected:
            self._vars['workshop_output_folder'].set(selected)
            self._commit_text()
            self.refresh()

    def show_poster(self) -> None:
        poster = self._vars['poster'].get().strip()
        if not poster:
            return
        image = load_ctk_image(poster, (420, 420))
        if image is None:
            return
        popup = ctk.CTkToplevel(self)
        popup.title('Poster Preview')
        label = ctk.CTkLabel(popup, image=image, text='')
        label.image = image
        label.pack(padx=12, pady=12)

    def refresh(self) -> None:
        detected = detect_workshop_dir()
        if not self._vars['workshop_output_folder'].get() and detected:
            self._vars['workshop_output_folder'].set(str(detected))
            self.session.project.workshop_output_folder = str(detected)
        if self.detected_label is not None:
            self.detected_label.configure(text='✓ DETECTED' if detected else '')
        image = load_ctk_image(self._vars['poster'].get().strip(), (160, 160))
        if self.poster_label is not None:
            if image is None:
                self.poster_label.configure(text='Poster Preview', image=None)
                self.poster_label.image = None
            else:
                self.poster_label.configure(text='', image=image)
                self.poster_label.image = image