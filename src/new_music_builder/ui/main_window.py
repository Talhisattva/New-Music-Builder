from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as messagebox
from tkinter import ttk

import customtkinter as ctk
from PIL import Image, ImageTk

from new_music_builder import __version__
from new_music_builder.platform.paths import app_root
from new_music_builder.services.asset_catalog import AssetCatalog
from new_music_builder.services.audio_workspace import AudioWorkspaceService
from new_music_builder.services.project_session import ProjectSession
from new_music_builder.services.project_store import ProjectStore
from new_music_builder.services.recent_projects import RecentProjectsStore
from new_music_builder.services.session_store import SessionStore
from new_music_builder.ui import theme
from new_music_builder.ui.modules.appearance import AppearanceModule
from new_music_builder.ui.modules.build_export import BuildExportModule
from new_music_builder.ui.modules.build_summary import BuildSummaryModule
from new_music_builder.ui.modules.media_creation import MediaCreationModule
from new_music_builder.ui.modules.mod_setup import ModSetupModule


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        self.title(f'New Music Builder v{__version__}')
        self.geometry('1680x980')
        self.minsize(1320, 820)
        self.configure(fg_color=theme.BG)

        self.project_store = ProjectStore()
        self.recent_store = RecentProjectsStore()
        self.session_store = SessionStore()
        self.audio_workspace = AudioWorkspaceService()
        self.session, saved_path = self.session_store.load()
        self.session = ProjectSession(project=self.session, current_path=saved_path)
        self._window_icon_image = None
        self._header_icon_image = None

        sibling_root = app_root().parent
        base_mod_root = sibling_root / 'Talis New Music'
        self.asset_catalog_service = AssetCatalog(base_mod_root)
        self.asset_catalog = self.asset_catalog_service.scan()
        self.build_log: list[str] = []
        self.preview_entries: list[str] = []

        self._configure_ttk_styles()
        self._apply_window_icon()
        self._build_menu()
        self._build_header()
        self._build_layout()
        self.refresh_all()
        self.protocol('WM_DELETE_WINDOW', self.on_close)

    def _main_icon_path(self) -> Path:
        return app_root().parent / 'Talis New Music' / 'Contents' / 'mods' / 'Talis New Music' / 'common' / 'media' / 'textures' / 'Item_NM_Cassette4.png'

    def _native_icon_path(self) -> Path:
        return app_root() / 'assets' / 'new_music_builder.ico'

    def _apply_window_icon(self) -> None:
        native_icon = self._native_icon_path()
        if native_icon.exists() and sys.platform.startswith('win'):
            try:
                self.iconbitmap(default=str(native_icon))
                return
            except tk.TclError:
                pass

        icon = self._main_icon_path()
        if icon.exists():
            try:
                image = Image.open(icon)
                self._window_icon_image = ImageTk.PhotoImage(image)
                self.iconphoto(True, self._window_icon_image)
            except Exception:
                pass

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label='New', command=self.new_project)
        file_menu.add_command(label='Save', command=self.save_project)
        file_menu.add_command(label='Save As', command=self.save_project_as)
        file_menu.add_command(label='Load', command=self.load_project)
        recent = tk.Menu(file_menu, tearoff=False)
        for path in self.recent_store.load():
            recent.add_command(label=path, command=lambda current=path: self._load_path(Path(current)))
        file_menu.add_cascade(label='Recent', menu=recent)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.on_close)
        menu.add_cascade(label='File', menu=file_menu)

        pref_menu = tk.Menu(menu, tearoff=False)
        pref_menu.add_command(label='Sample Rate: 44100 Hz', command=self._show_sample_rate_dialog)
        menu.add_cascade(label='Preferences', menu=pref_menu)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label='About', command=lambda: messagebox.showinfo('About', 'New Music Builder functional shell'))
        menu.add_cascade(label='Help', menu=help_menu)
        self.configure(menu=menu)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color='#101213', corner_radius=0, height=56)
        header.pack(fill='x')
        header.pack_propagate(False)
        icon_path = self._main_icon_path()
        title_pad = (16, 8)
        if icon_path.exists():
            self._header_icon_image = ctk.CTkImage(light_image=Image.open(icon_path), dark_image=Image.open(icon_path), size=(28, 28))
            ctk.CTkLabel(header, text='', image=self._header_icon_image).pack(side='left', padx=(16, 8), pady=12)
            title_pad = (0, 8)
        ctk.CTkLabel(header, text='NEW MUSIC BUILDER', text_color='#c7c6c6', font=ctk.CTkFont(family='Orbitron', size=22, weight='bold')).pack(side='left', padx=title_pad, pady=12)
        ctk.CTkLabel(header, text=f'v{__version__}', text_color='#c7c6c6', font=ctk.CTkFont(family='Orbitron', size=14)).pack(side='left', pady=16)

    def _configure_ttk_styles(self) -> None:
        style = ttk.Style(self)
        style.configure(
            'Dark.TPanedwindow',
            background='#000000',
            sashwidth=8,
            sashrelief='flat',
            borderwidth=0,
        )

    def _build_layout(self) -> None:
        outer = ttk.Panedwindow(self, orient='vertical', style='Dark.TPanedwindow')
        outer.pack(fill='both', expand=True)
        top = ttk.Panedwindow(outer, orient='horizontal', style='Dark.TPanedwindow')
        bottom = ttk.Panedwindow(outer, orient='horizontal', style='Dark.TPanedwindow')
        outer.add(top, weight=3)
        outer.add(bottom, weight=2)

        top_left = ctk.CTkFrame(top, fg_color='transparent')
        top_mid = ctk.CTkFrame(top, fg_color='transparent')
        top_right = ctk.CTkFrame(top, fg_color='transparent')
        top.add(top_left, weight=1)
        top.add(top_mid, weight=2)
        top.add(top_right, weight=1)

        bottom_left = ctk.CTkFrame(bottom, fg_color='transparent')
        bottom_right = ctk.CTkFrame(bottom, fg_color='transparent')
        bottom.add(bottom_left, weight=2)
        bottom.add(bottom_right, weight=1)

        self.mod_setup = ModSetupModule(top_left, self.session, self.on_project_change, self.save_project, self.load_project)
        self.mod_setup.pack(fill='both', expand=True, padx=8, pady=8)
        self.media_creation = MediaCreationModule(top_mid, self.session, self.asset_catalog, self.on_project_change, self.on_select_row)
        self.media_creation.pack(fill='both', expand=True, padx=8, pady=8)
        self.appearance = AppearanceModule(top_right, self.session, self.asset_catalog, self.on_project_change)
        self.appearance.pack(fill='both', expand=True, padx=8, pady=8)
        self.build_export = BuildExportModule(bottom_left, self.session, self.run_build_preview, self.reset_transient_state)
        self.build_export.pack(fill='both', expand=True, padx=8, pady=8)
        self.build_summary = BuildSummaryModule(bottom_right, self.session)
        self.build_summary.pack(fill='both', expand=True, padx=8, pady=8)

    def _show_sample_rate_dialog(self) -> None:
        popup = ctk.CTkInputDialog(text='Enter project sample rate', title='Sample Rate')
        value = popup.get_input()
        if not value:
            return
        try:
            self.session.project.sample_rate = int(value)
        except ValueError:
            messagebox.showerror('Invalid sample rate', 'Sample rate must be a number.')
            return
        self.on_project_change()

    def on_select_row(self, row_id: int | None) -> None:
        if row_id is None:
            return
        self.media_creation.set_active_row(row_id)
        self.appearance.set_active_row(row_id)

    def on_project_change(self) -> None:
        self.build_summary.refresh()
        self.session_store.save(self.session.project, self.session.current_path)

    def refresh_all(self) -> None:
        self._apply_default_asset_selections()
        if self.session.project.media_rows and not any(row.expanded for row in self.session.project.media_rows):
            self.session.project.media_rows[0].expanded = True
        self.mod_setup.refresh()
        self.media_creation.refresh()
        self.appearance.refresh()
        self.build_export.refresh(self.build_log, self.preview_entries)
        self.build_summary.refresh()

    def _apply_default_asset_selections(self) -> None:
        for row in self.session.project.media_rows:
            row.ensure_appearances()
            for kind, entries in self.asset_catalog.items():
                if entries and not row.appearances[kind].selected_asset_key:
                    row.appearances[kind].selected_asset_key = entries[0].key
                    row.appearances[kind].sprite_mode = entries[0].sprite_mode

    def new_project(self) -> None:
        self.session.reset()
        self.build_log = []
        self.preview_entries = []
        self.refresh_all()

    def save_project(self) -> None:
        if self.session.current_path:
            self.project_store.save(self.session.project, Path(self.session.current_path))
            self.recent_store.push(Path(self.session.current_path))
            self.session_store.save(self.session.project, self.session.current_path)
            return
        self.save_project_as()

    def save_project_as(self) -> None:
        selected = fd.asksaveasfilename(defaultextension='.nmbproj.json', filetypes=[('New Music Builder Project', '*.nmbproj.json')])
        if not selected:
            return
        self.session.current_path = selected
        self.save_project()

    def load_project(self) -> None:
        selected = fd.askopenfilename(filetypes=[('New Music Builder Project', '*.nmbproj.json'), ('JSON', '*.json')])
        if selected:
            self._load_path(Path(selected))

    def _load_path(self, path: Path) -> None:
        self.session.project = self.project_store.load(path)
        self.session.current_path = str(path)
        self.recent_store.push(path)
        self.refresh_all()

    def run_build_preview(self) -> None:
        self.build_log = [f"[{datetime.now().strftime('%H:%M:%S')}] Build started - {len(self.session.project.media_rows) * 2} sides queued."]
        self.preview_entries = []
        for row in self.session.project.media_rows:
            for side_name, tracks in [('A', row.tracks_a), ('B', row.tracks_b)]:
                self.build_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Queued: {row.media_name} (Side {side_name}) - {len(tracks)} songs")
                self.preview_entries.append(f'{row.media_name} (Side {side_name})')
        self.build_export.refresh(self.build_log, self.preview_entries)
        self.build_summary.refresh()

    def reset_transient_state(self) -> None:
        self.build_log = []
        self.preview_entries = []
        self.build_export.refresh(self.build_log, self.preview_entries)

    def on_close(self) -> None:
        self.session_store.save(self.session.project, self.session.current_path)
        self.destroy()
