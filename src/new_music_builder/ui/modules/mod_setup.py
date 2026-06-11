from __future__ import annotations

from pathlib import Path
import tkinter.filedialog as fd

import customtkinter as ctk

from new_music_builder.platform.paths import detect_workshop_dir
from new_music_builder.ui import theme
from new_music_builder.ui.widgets.buttons import make_builder_button
from new_music_builder.ui.widgets.checkboxes import make_builder_checkbox
from new_music_builder.ui.widgets.fields import LabeledEntry, apply_builder_entry_style, make_builder_label
from new_music_builder.ui.widgets.images import load_ctk_image
from new_music_builder.ui.widgets.module_panel import ModulePanel
from new_music_builder.ui.widgets.tooltip import Tooltip


class ModSetupModule(ModulePanel):
    def __init__(self, master, session, on_change, save_callback, load_callback, reset_callback):
        super().__init__(master, 'PHASE 1: MOD SETUP')
        self.session = session
        self.on_change = on_change
        self.save_callback = save_callback
        self.load_callback = load_callback
        self.reset_callback = reset_callback
        self.poster_label: ctk.CTkLabel | None = None
        self.poster_frame: ctk.CTkFrame | None = None
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
        top = ctk.CTkFrame(self.body, fg_color='transparent')
        top.pack(fill='both', expand=True, padx=8, pady=8)
        top.grid_columnconfigure(0, weight=1)

        poster_stack = ctk.CTkFrame(top, fg_color='transparent')
        poster_stack.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        poster_stack.grid_columnconfigure(0, weight=1)
        make_builder_label(poster_stack, 'WORKSHOP POSTER', text_color=theme.ACCENT_LIGHT, size=11, weight='bold').pack(anchor='center', pady=(0, 4))
        self.poster_frame = ctk.CTkFrame(poster_stack, width=156, height=156, fg_color=theme.PANEL, border_color=theme.BORDER, border_width=1, corner_radius=12)
        self.poster_frame.pack(anchor='center')
        self.poster_frame.pack_propagate(False)
        self.poster_label = make_builder_label(self.poster_frame, 'Click To Pick Poster', size=11, weight='bold', justify='center', wraplength=120)
        self.poster_label.pack(expand=True, padx=10, pady=10)
        self.poster_frame.bind('<Button-1>', lambda _event: self.pick_poster())
        self.poster_label.bind('<Button-1>', lambda _event: self.pick_poster())
        Tooltip(self.poster_frame, 'Click to choose the Workshop preview/poster image for this project.')
        write_name = make_builder_checkbox(
            poster_stack,
            'Write Mod Name On Poster',
            self._vars['write_name'],
            command=self._commit_boolean,
        )
        write_name.pack(anchor='center', pady=(8, 0))

        form = ctk.CTkFrame(top, fg_color='transparent')
        form.grid(row=1, column=0, sticky='nsew')
        form.grid_columnconfigure(0, weight=1)

        field_specs = [
            ('mod_name', 'Mod Name'),
            ('mod_id', 'Mod ID'),
            ('parent_mod_id', 'Parent Mod ID'),
            ('author', 'Author'),
        ]
        for index, (key, label) in enumerate(field_specs):
            row = LabeledEntry(form, label, self._vars[key], label_size=11, entry_font_size=11, entry_height=28)
            row.grid(row=index, column=0, sticky='ew', padx=0, pady=(0, 5))
            row.entry.bind('<FocusOut>', self._commit_text)

        ogg_row = ctk.CTkFrame(form, fg_color='transparent')
        ogg_row.grid(row=4, column=0, sticky='ew', padx=0, pady=(0, 5))
        self._folder_row(ogg_row, 'OGG Output Folder', 'ogg_output_folder', self.pick_ogg_folder)

        workshop_row = ctk.CTkFrame(form, fg_color='transparent')
        workshop_row.grid(row=5, column=0, sticky='ew', padx=0, pady=(0, 5))
        self._folder_row(workshop_row, 'Zomboid Workshop Folder', 'workshop_output_folder', self.pick_workshop_folder, detected=True)

        action_row = ctk.CTkFrame(form, fg_color='transparent')
        action_row.grid(row=6, column=0, sticky='ew', padx=0, pady=(6, 0))
        action_row.grid_columnconfigure(0, weight=1)
        action_row.grid_columnconfigure(1, weight=1)
        action_row.grid_columnconfigure(2, weight=1)
        make_builder_button(action_row, 'SAVE', self.save_callback, size='compact').grid(row=0, column=0, sticky='ew', padx=(0, 3))
        make_builder_button(action_row, 'LOAD', self.load_callback, size='compact').grid(row=0, column=1, sticky='ew', padx=3)
        make_builder_button(action_row, 'RESET', self.reset_callback, variant='secondary', size='compact').grid(row=0, column=2, sticky='ew', padx=(3, 0))

    def _folder_row(self, master, label_text: str, key: str, command, detected: bool = False) -> None:
        row = ctk.CTkFrame(master, fg_color='transparent')
        row.pack(fill='x')
        make_builder_label(row, label_text, text_color=theme.TEXT, anchor='w', size=11, weight='bold').pack(fill='x')
        inner = ctk.CTkFrame(row, fg_color='transparent')
        inner.pack(fill='x', pady=(2, 0))
        entry = ctk.CTkEntry(inner, textvariable=self._vars[key])
        apply_builder_entry_style(entry, font_size=11, height=28, corner_radius=8)
        entry.pack(side='left', expand=True, fill='x')
        entry.bind('<FocusOut>', self._commit_text)
        make_builder_button(inner, 'Browse', command, width=76, size='compact').pack(side='left', padx=(5, 0))
        if detected:
            self.detected_label = make_builder_label(row, '', text_color=theme.SUCCESS, anchor='e', size=11, weight='bold')
            self.detected_label.pack(fill='x', pady=(2, 0))

    def _commit_text(self, _event=None) -> None:
        self.session.project.mod_name = self._vars['mod_name'].get().strip()
        self.session.project.mod_id = self._vars['mod_id'].get().strip()
        self.session.project.parent_mod_id = self._vars['parent_mod_id'].get().strip()
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

    def reset_fields(self) -> None:
        self._vars['mod_name'].set('')
        self._vars['mod_id'].set('')
        self._vars['parent_mod_id'].set('')
        self._vars['author'].set('')
        self._vars['ogg_output_folder'].set('')
        self._vars['workshop_output_folder'].set('')
        self._vars['poster'].set('')
        self._vars['write_name'].set(False)
        self.session.project.mod_name = ''
        self.session.project.mod_id = ''
        self.session.project.parent_mod_id = ''
        self.session.project.author = ''
        self.session.project.ogg_output_folder = ''
        self.session.project.workshop_output_folder = ''
        self.session.project.workshop_poster_path = ''
        self.session.project.write_mod_name_on_poster = False
        self.on_change()
        self.refresh(auto_detect_workshop=False)

    def refresh(self, auto_detect_workshop: bool = True) -> None:
        detected = detect_workshop_dir()
        if auto_detect_workshop and not self._vars['workshop_output_folder'].get() and detected:
            self._vars['workshop_output_folder'].set(str(detected))
            self.session.project.workshop_output_folder = str(detected)
        if self.detected_label is not None:
            self.detected_label.configure(text='✓ DETECTED' if detected else '')
        image = load_ctk_image(self._vars['poster'].get().strip(), (144, 144))
        if self.poster_label is not None:
            if image is None:
                self.poster_label.configure(text='Click To Pick Poster', image=None)
                self.poster_label.image = None
            else:
                self.poster_label.configure(text='', image=image)
                self.poster_label.image = image
