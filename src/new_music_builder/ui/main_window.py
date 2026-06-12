from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as messagebox

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
class MainWindow(ctk.CTk):
    HEADER_HEIGHT = 50
    MENU_HEIGHT = 30
    APP_BG = '#131214'
    CONTENT_PADDING = 10
    MENU_BG = '#000000'
    MENU_HOVER = '#2a2030'
    HEADER_TEXT = '#c7c6c6'
    VERSION_TEXT = 'v0.1.0'
    MENU_ITEMS = ('FILE', 'PREFERENCES', 'HELP')
    MODULE_BG = '#1d1c1e'
    MODULE_BORDER = '#0e1414'
    MODULE_ONE_SIZE = (370, 450)

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        self.title(f'New Music Builder v{__version__}')
        self.geometry('1600x900')
        self.minsize(1366, 820)
        self.configure(fg_color=self.APP_BG)

        self.project_store = ProjectStore()
        self.recent_store = RecentProjectsStore()
        self.session_store = SessionStore()
        self.audio_workspace = AudioWorkspaceService()
        self.session, saved_path = self.session_store.load()
        self.session = ProjectSession(project=self.session, current_path=saved_path)
        self._window_icon_image = None
        self._header_icon_image = None
        self._menu_widgets: list[tuple[ctk.CTkFrame, ctk.CTkLabel]] = []

        sibling_root = app_root().parent
        base_mod_root = sibling_root / 'Talis New Music'
        self.asset_catalog_service = AssetCatalog(base_mod_root)
        self.asset_catalog = self.asset_catalog_service.scan()
        self.build_log: list[str] = []
        self.preview_entries: list[str] = []

        self._apply_window_icon()
        self._build_menu()
        self._build_header()
        self._build_menu_strip()
        self._build_layout()
        self.refresh_all()
        self.protocol('WM_DELETE_WINDOW', self.on_close)

    def _main_icon_path(self) -> Path:
        return app_root().parent / 'Talis New Music' / 'Contents' / 'mods' / 'Talis New Music' / 'common' / 'media' / 'textures' / 'Item_NM_Cassette4.png'

    def _header_logo_path(self) -> Path:
        return self._native_icon_path()

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
        self.configure(menu='')

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color='#101213', corner_radius=0, height=self.HEADER_HEIGHT)
        header.pack(fill='x')
        header.pack_propagate(False)
        icon_path = self._header_logo_path()
        title_pad = (15, 10)
        if icon_path.exists():
            self._header_icon_image = ctk.CTkImage(light_image=Image.open(icon_path), dark_image=Image.open(icon_path), size=(32, 32))
            ctk.CTkLabel(header, text='', image=self._header_icon_image).pack(side='left', padx=(15, 10), pady=9)
            title_pad = (0, 8)
        ctk.CTkLabel(
            header,
            text='NEW MUSIC BUILDER',
            text_color=self.HEADER_TEXT,
            font=ctk.CTkFont(family='Orbitron', size=20, weight='bold'),
        ).pack(side='left', padx=title_pad, pady=10)
        ctk.CTkLabel(
            header,
            text=self.VERSION_TEXT,
            text_color=self.HEADER_TEXT,
            font=ctk.CTkFont(family='Orbitron', size=13, weight='normal'),
        ).pack(side='left', pady=14)

    def _build_menu_strip(self) -> None:
        menu_bar = ctk.CTkFrame(self, fg_color=self.MENU_BG, corner_radius=0, height=self.MENU_HEIGHT)
        menu_bar.pack(fill='x')
        menu_bar.pack_propagate(False)
        items = ctk.CTkFrame(menu_bar, fg_color='transparent')
        items.pack(side='left', padx=(0, 0), pady=0)

        for item in self.MENU_ITEMS:
            item_frame = ctk.CTkFrame(items, fg_color=self.MENU_BG, corner_radius=0)
            item_frame.pack(side='left', padx=0, pady=0)
            label = ctk.CTkLabel(
                item_frame,
                text=item,
                text_color=self.HEADER_TEXT,
                font=ctk.CTkFont(family='Orbitron', size=12, weight='normal'),
            )
            label.pack(padx=10, pady=6)
            item_frame.bind('<Enter>', lambda _e, frame=item_frame: frame.configure(fg_color=self.MENU_HOVER))
            item_frame.bind('<Leave>', lambda _e, frame=item_frame: frame.configure(fg_color=self.MENU_BG))
            label.bind('<Enter>', lambda _e, frame=item_frame: frame.configure(fg_color=self.MENU_HOVER))
            label.bind('<Leave>', lambda _e, frame=item_frame: frame.configure(fg_color=self.MENU_BG))
            self._menu_widgets.append((item_frame, label))

    def _build_layout(self) -> None:
        self.stage = ctk.CTkFrame(self, fg_color=self.APP_BG, corner_radius=0)
        self.stage.pack(fill='both', expand=True)

        self.content_frame = ctk.CTkFrame(self.stage, fg_color='transparent', corner_radius=0)
        self.content_frame.pack(
            fill='both',
            expand=True,
            padx=self.CONTENT_PADDING,
            pady=self.CONTENT_PADDING,
        )

        self.content_frame.grid_columnconfigure(0, weight=0)
        self.content_frame.grid_columnconfigure(1, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=0)
        self.content_frame.grid_rowconfigure(1, weight=1)

        module_one = ctk.CTkFrame(
            self.content_frame,
            fg_color=self.MODULE_BORDER,
            corner_radius=0,
            width=self.MODULE_ONE_SIZE[0],
            height=self.MODULE_ONE_SIZE[1],
        )
        module_one.grid(row=0, column=0, sticky='nw')
        module_one.grid_propagate(False)
        module_one.configure(width=self.MODULE_ONE_SIZE[0], height=self.MODULE_ONE_SIZE[1])

        module_one_inner = ctk.CTkFrame(
            module_one,
            fg_color=self.MODULE_BG,
            corner_radius=0,
            width=self.MODULE_ONE_SIZE[0] - 2,
            height=self.MODULE_ONE_SIZE[1] - 2,
        )
        module_one_inner.pack(padx=1, pady=1, anchor='nw')
        module_one_inner.pack_propagate(False)
        module_one_inner.configure(
            width=self.MODULE_ONE_SIZE[0] - 2,
            height=self.MODULE_ONE_SIZE[1] - 2,
        )

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
        if row_id is None or not hasattr(self, 'media_creation') or not hasattr(self, 'appearance'):
            return
        self.media_creation.set_active_row(row_id)
        self.appearance.set_active_row(row_id)

    def on_project_change(self) -> None:
        if hasattr(self, 'build_summary'):
            self.build_summary.refresh()
        self.session_store.save(self.session.project, self.session.current_path)

    def refresh_all(self) -> None:
        self._apply_default_asset_selections()
        if self.session.project.media_rows and not any(row.expanded for row in self.session.project.media_rows):
            self.session.project.media_rows[0].expanded = True
        if hasattr(self, 'mod_setup'):
            self.mod_setup.refresh()
        if hasattr(self, 'media_creation'):
            self.media_creation.refresh()
        if hasattr(self, 'appearance'):
            self.appearance.refresh()
        if hasattr(self, 'build_export'):
            self.build_export.refresh(self.build_log, self.preview_entries)
        if hasattr(self, 'build_summary'):
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

    def reset_phase_one_fields(self) -> None:
        if hasattr(self, 'mod_setup'):
            self.mod_setup.reset_fields()

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
        if hasattr(self, 'build_export'):
            self.build_export.refresh(self.build_log, self.preview_entries)
        if hasattr(self, 'build_summary'):
            self.build_summary.refresh()

    def reset_transient_state(self) -> None:
        self.build_log = []
        self.preview_entries = []
        if hasattr(self, 'build_export'):
            self.build_export.refresh(self.build_log, self.preview_entries)

    def on_close(self) -> None:
        self.session_store.save(self.session.project, self.session.current_path)
        self.destroy()
