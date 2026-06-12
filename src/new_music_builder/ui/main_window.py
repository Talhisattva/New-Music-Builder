from __future__ import annotations

from collections.abc import Callable
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
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.app_header import AppHeader
from new_music_builder.ui.widgets.menu_strip import MenuStrip
from new_music_builder.ui.widgets.module_header import ModuleHeader
class MainWindow(ctk.CTk):
    MODULE_BG = '#1d1c1e'
    MODULE_BORDER = '#000000'
    MODULE_ONE_SIZE = (370, 450)
    MODULE_BORDER_WIDTH = 1
    MODULE_MIDGROUND_BG = '#222123'
    MODULE_MIDGROUND_BORDER = '#141216'
    MODULE_MIDGROUND_SIZE = (350, 410)
    MODULE_MIDGROUND_OFFSET = (10, 30)
    MODULE_TITLE_COLOR = '#8253a2'
    COVER_BG = '#101010'
    COVER_BORDER = '#575151'
    COVER_SIZE = (100, 100)
    COVER_INSET_BUTTON_CENTER = (5, 5)
    FOLDER_BUTTON_BG = '#8a57a3'
    FOLDER_BUTTON_STROKE = '#382b47'
    FOLDER_BUTTON_SIZE = (30, 30)
    FOLDER_BUTTON_STROKE_WIDTH = 2

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        self.title(f'New Music Builder v{__version__}')
        self.geometry(f'{spec.APP_WIDTH}x{spec.APP_HEIGHT}')
        self.minsize(spec.APP_MIN_WIDTH, spec.APP_MIN_HEIGHT)
        self.configure(fg_color=spec.APP_BG)

        self.project_store = ProjectStore()
        self.recent_store = RecentProjectsStore()
        self.session_store = SessionStore()
        self.audio_workspace = AudioWorkspaceService()
        self.session, saved_path = self.session_store.load()
        self.session = ProjectSession(project=self.session, current_path=saved_path)
        self._window_icon_image = None
        self._folder_button_image = None

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

    def _folder_button_icon_path(self) -> Path:
        return app_root() / 'assets' / 'NMB_Folder2.png'

    def _phase_one_icon_path(self) -> Path:
        return app_root() / 'assets' / 'PhaseOneIcon.png'

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
        self.header = AppHeader(self, logo_path=self._header_logo_path())
        self.header.pack(fill='x')

    def _build_menu_strip(self) -> None:
        self.menu_strip = MenuStrip(self)
        self.menu_strip.pack(fill='x')

    def _build_layout(self) -> None:
        self.stage = ctk.CTkFrame(self, fg_color=spec.APP_BG, corner_radius=0)
        self.stage.pack(fill='both', expand=True)

        self.content_frame = ctk.CTkFrame(self.stage, fg_color='transparent', corner_radius=0)
        self.content_frame.pack(
            fill='both',
            expand=True,
            padx=spec.CONTENT_PADDING,
            pady=spec.CONTENT_PADDING,
        )

        self.content_frame.grid_columnconfigure(0, weight=0)
        self.content_frame.grid_columnconfigure(1, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=0)
        self.content_frame.grid_rowconfigure(1, weight=1)

        self.module_one_border = tk.Canvas(
            self.content_frame,
            bg=self.MODULE_BORDER,
            width=self.MODULE_ONE_SIZE[0],
            height=self.MODULE_ONE_SIZE[1],
            bd=0,
            highlightthickness=0,
        )
        self.module_one_border.grid(row=0, column=0, sticky='nw')
        self.module_one_border.grid_propagate(False)
        self.module_one_border.configure(width=self.MODULE_ONE_SIZE[0], height=self.MODULE_ONE_SIZE[1])
        self.module_one_border.create_rectangle(
            0,
            0,
            self.MODULE_ONE_SIZE[0],
            self.MODULE_ONE_SIZE[1],
            outline='',
            fill=self.MODULE_BORDER,
        )

        self.module_one_background = tk.Frame(
            self.module_one_border,
            bg=self.MODULE_BG,
            bd=0,
            highlightthickness=0,
            width=self.MODULE_ONE_SIZE[0] - (self.MODULE_BORDER_WIDTH * 2),
            height=self.MODULE_ONE_SIZE[1] - (self.MODULE_BORDER_WIDTH * 2),
        )
        self.module_one_border.create_window(
            self.MODULE_BORDER_WIDTH,
            self.MODULE_BORDER_WIDTH,
            anchor='nw',
            window=self.module_one_background,
            width=self.MODULE_ONE_SIZE[0] - (self.MODULE_BORDER_WIDTH * 2),
            height=self.MODULE_ONE_SIZE[1] - (self.MODULE_BORDER_WIDTH * 2),
        )

        self.module_one_midground_border = tk.Frame(
            self.module_one_border,
            bg=self.MODULE_MIDGROUND_BORDER,
            bd=0,
            highlightthickness=0,
            width=self.MODULE_MIDGROUND_SIZE[0],
            height=self.MODULE_MIDGROUND_SIZE[1],
        )
        self.module_one_border.create_window(
            self.MODULE_MIDGROUND_OFFSET[0],
            self.MODULE_MIDGROUND_OFFSET[1],
            anchor='nw',
            window=self.module_one_midground_border,
            width=self.MODULE_MIDGROUND_SIZE[0],
            height=self.MODULE_MIDGROUND_SIZE[1],
        )
        self.module_one_midground = tk.Frame(
            self.module_one_midground_border,
            bg=self.MODULE_MIDGROUND_BG,
            bd=0,
            highlightthickness=0,
            width=self.MODULE_MIDGROUND_SIZE[0] - 2,
            height=self.MODULE_MIDGROUND_SIZE[1] - 2,
        )
        self.module_one_midground.place(x=1, y=1)

        self.module_one_header = ModuleHeader(
            self.module_one_background,
            text='PHASE 1 : MOD SETUP',
            icon_path=self._phase_one_icon_path(),
            bg_color=self.MODULE_BG,
            text_color=self.MODULE_TITLE_COLOR,
        )
        self.module_one_phase_icon = self.module_one_header.icon_label
        self.module_one_phase_label = self.module_one_header.text_label

        self.module_one_cover_border = tk.Frame(
            self.module_one_midground,
            bg=self.COVER_BORDER,
            bd=0,
            highlightthickness=0,
            width=self.COVER_SIZE[0],
            height=self.COVER_SIZE[1],
        )
        self.module_one_cover_border.place(x=15, y=15)

        self.module_one_cover_surface = tk.Frame(
            self.module_one_cover_border,
            bg=self.COVER_BG,
            bd=0,
            highlightthickness=0,
            width=self.COVER_SIZE[0] - 2,
            height=self.COVER_SIZE[1] - 2,
        )
        self.module_one_cover_surface.place(x=1, y=1)

        cover_button_x = (
            15
            + self.COVER_SIZE[0]
            - self.COVER_INSET_BUTTON_CENTER[0]
            - (self.FOLDER_BUTTON_SIZE[0] // 2)
        )
        cover_button_y = (
            5
        )
        self.module_one_cover_button = self._create_folder_icon_button(self.module_one_midground)
        self.module_one_cover_button.place(x=cover_button_x, y=cover_button_y)

    def _create_folder_icon_button(
        self,
        parent: tk.Misc,
        *,
        command: Callable[[], None] | None = None,
    ) -> tk.Canvas:
        shell = tk.Canvas(
            parent,
            bg=self.FOLDER_BUTTON_BG,
            width=self.FOLDER_BUTTON_SIZE[0],
            height=self.FOLDER_BUTTON_SIZE[1],
            bd=0,
            highlightthickness=0,
        )

        icon_path = self._folder_button_icon_path()
        if icon_path.exists():
            image = Image.open(icon_path).resize(self.FOLDER_BUTTON_SIZE, Image.Resampling.LANCZOS)
            self._folder_button_image = ImageTk.PhotoImage(image)
        else:
            self._folder_button_image = None

        inset = self.FOLDER_BUTTON_STROKE_WIDTH
        shell.create_rectangle(
            0,
            0,
            self.FOLDER_BUTTON_SIZE[0],
            self.FOLDER_BUTTON_SIZE[1],
            outline='',
            fill=self.FOLDER_BUTTON_STROKE,
        )
        shell.create_rectangle(
            inset,
            inset,
            self.FOLDER_BUTTON_SIZE[0] - inset,
            self.FOLDER_BUTTON_SIZE[1] - inset,
            outline='',
            fill=self.FOLDER_BUTTON_BG,
        )
        if self._folder_button_image is not None:
            shell.create_image(
                self.FOLDER_BUTTON_SIZE[0] // 2,
                self.FOLDER_BUTTON_SIZE[1] // 2,
                image=self._folder_button_image,
            )

        def _run_command(_event: tk.Event | None = None) -> None:
            if command is not None:
                command()

        shell.bind('<Button-1>', _run_command)
        return shell

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
