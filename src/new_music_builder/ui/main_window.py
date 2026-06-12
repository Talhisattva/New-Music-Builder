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
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.app_header import AppHeader
from new_music_builder.ui.widgets.cover_picker import CoverPicker
from new_music_builder.ui.widgets.labeled_checkbox import LabeledCheckbox
from new_music_builder.ui.widgets.labeled_text_field import LabeledTextField
from new_music_builder.ui.widgets.main_button import MainButton
from new_music_builder.ui.widgets.media_creation_header import MediaCreationHeader
from new_music_builder.ui.widgets.menu_strip import MenuStrip
from new_music_builder.ui.widgets.module_header import ModuleHeader
from new_music_builder.ui.widgets.module_shell import ModuleShell
from new_music_builder.ui.widgets.output_folder_field import OutputFolderField
from new_music_builder.ui.widgets.scroll_area import ScrollViewport


class MainWindow(ctk.CTk):

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
        self.mod_name_var = tk.StringVar(value=self.session.project.mod_name)
        self.mod_id_var = tk.StringVar(value=self.session.project.mod_id)
        self.parent_mod_id_var = tk.StringVar(value=self.session.project.parent_mod_id)
        self.author_var = tk.StringVar(value=self.session.project.author)
        self.ogg_output_folder_var = tk.StringVar(value=self.session.project.ogg_output_folder)
        self.workshop_output_folder_var = tk.StringVar(value=self.session.project.workshop_output_folder)
        self._window_icon_image = None

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

    def _phase_two_icon_path(self) -> Path:
        return app_root() / 'assets' / 'PhaseTwoIcon.png'

    def _check_icon_path(self) -> Path:
        return app_root() / 'assets' / 'Check.png'

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

        self.module_one_shell = ModuleShell(
            self.content_frame,
        )
        self.module_one_shell.grid(row=0, column=0, sticky='nw')
        self.module_one_shell.grid_propagate(False)
        self.module_one_background = self.module_one_shell.background_surface
        self.module_one_midground_border = self.module_one_shell.midground_border
        self.module_one_midground = self.module_one_shell.midground_surface

        self.module_one_header = ModuleHeader(
            self.module_one_background,
            text='PHASE 1 : MOD SETUP',
            icon_path=self._phase_one_icon_path(),
            bg_color=spec.MODULE_BACKGROUND_BG,
            text_color=spec.MODULE_HEADER_TEXT_COLOR,
        )
        self.module_one_phase_icon = self.module_one_header.icon_label
        self.module_one_phase_label = self.module_one_header.text_label

        self.module_two_shell = ModuleShell(
            self.content_frame,
            size=spec.MODULE_TWO_SIZE,
            midground_size=spec.MODULE_TWO_MIDGROUND_SIZE,
        )
        self.module_two_shell.grid(row=0, column=1, sticky='nw', padx=(spec.MODULE_GAP_X, 0))
        self.module_two_shell.grid_propagate(False)
        self.module_two_background = self.module_two_shell.background_surface
        self.module_two_midground_border = self.module_two_shell.midground_border
        self.module_two_midground = self.module_two_shell.midground_surface

        self.module_two_header = ModuleHeader(
            self.module_two_background,
            text='PHASE 2 : MEDIA CREATION',
            icon_path=self._phase_two_icon_path(),
            bg_color=spec.MODULE_BACKGROUND_BG,
            text_color=spec.MODULE_HEADER_TEXT_COLOR,
        )
        self.module_two_phase_icon = self.module_two_header.icon_label
        self.module_two_phase_label = self.module_two_header.text_label

        self.module_two_top_header = MediaCreationHeader(self.module_two_midground_border)
        self.module_two_top_header.place(x=0, y=0)
        self.module_two_add_row_button = self.module_two_top_header.add_button
        self.module_two_remove_row_button = self.module_two_top_header.remove_button

        self.module_two_scroll_area = ScrollViewport(
            self.module_two_midground_border,
            size=spec.MODULE_TWO_SCROLL_AREA_SIZE,
            viewport_size=spec.MODULE_TWO_SCROLL_VIEWPORT_SIZE,
            scrollbar_size=spec.SCROLLBAR_TRACK_SIZE,
            bg_color=spec.MODULE_MIDGROUND_BG,
        )
        self.module_two_scroll_area.place(x=0, y=spec.MODULE_TWO_TOP_HEADER_SIZE[1])
        self.module_two_content_viewport = self.module_two_scroll_area.viewport_canvas
        self.module_two_content_surface = self.module_two_scroll_area.content_frame
        self.module_two_scrollbar = self.module_two_scroll_area.scrollbar
        self._build_module_two_placeholder_content()

        self.module_one_cover_picker = CoverPicker(
            self.module_one_midground,
            folder_icon_path=self._folder_button_icon_path(),
        )
        self.module_one_cover_picker.place(x=spec.COVER_OFFSET[0], y=5)
        self.module_one_cover_border = self.module_one_cover_picker.cover_border
        self.module_one_cover_surface = self.module_one_cover_picker.cover_surface
        self.module_one_cover_button = self.module_one_cover_picker.folder_button

        checkbox_x = (
            spec.COVER_OFFSET[0]
            + spec.COVER_SIZE[0]
            - spec.FOLDER_BUTTON_CENTER_INSET[0]
            - (spec.FOLDER_BUTTON_SIZE[0] // 2)
            + spec.FOLDER_BUTTON_SIZE[0]
            + spec.POSTER_NAME_CHECKBOX_GAP
        )
        checkbox_y = 5 + spec.FOLDER_BUTTON_SIZE[1] - spec.POSTER_NAME_CHECKBOX_SIZE[1]
        self.poster_name_checkbox = LabeledCheckbox(
            self.module_one_midground,
            icon_path=self._check_icon_path(),
            bg_color=spec.MODULE_MIDGROUND_BG,
        )
        self.poster_name_checkbox.place(x=checkbox_x, y=checkbox_y)

        mod_name_row_y = 5 + 10 + spec.COVER_SIZE[1] + spec.PHASE_ONE_TEXT_ROW_GAP_BELOW_COVER
        row_step = spec.TYPEABLE_FIELD_SIZE[1] + spec.PHASE_ONE_TEXT_ROW_SPACING
        self.module_one_mod_name_field = LabeledTextField(
            self.module_one_midground_border,
            label_text='Mod Name',
            bg_color=spec.MODULE_MIDGROUND_BG,
            textvariable=self.mod_name_var,
        )
        self.module_one_mod_name_field.place(x=spec.PHASE_ONE_TEXT_ROW_X, y=mod_name_row_y)

        self.module_one_mod_id_field = LabeledTextField(
            self.module_one_midground_border,
            label_text='Mod ID',
            bg_color=spec.MODULE_MIDGROUND_BG,
            textvariable=self.mod_id_var,
        )
        self.module_one_mod_id_field.place(x=spec.PHASE_ONE_TEXT_ROW_X, y=mod_name_row_y + row_step)

        self.module_one_parent_id_field = LabeledTextField(
            self.module_one_midground_border,
            label_text='Parent ID',
            bg_color=spec.MODULE_MIDGROUND_BG,
            textvariable=self.parent_mod_id_var,
        )
        self.module_one_parent_id_field.place(x=spec.PHASE_ONE_TEXT_ROW_X, y=mod_name_row_y + (row_step * 2))

        self.module_one_author_field = LabeledTextField(
            self.module_one_midground_border,
            label_text='Author',
            bg_color=spec.MODULE_MIDGROUND_BG,
            textvariable=self.author_var,
        )
        self.module_one_author_field.place(x=spec.PHASE_ONE_TEXT_ROW_X, y=mod_name_row_y + (row_step * 3))

        output_folder_y = mod_name_row_y + (row_step * 3) + spec.TYPEABLE_FIELD_SIZE[1] + spec.PHASE_ONE_OUTPUT_FOLDER_GAP
        self.module_one_ogg_output_folder = OutputFolderField(
            self.module_one_midground_border,
            label_text='.ogg Output Folder',
            folder_icon_path=self._folder_button_icon_path(),
            textvariable=self.ogg_output_folder_var,
            bg_color=spec.MODULE_MIDGROUND_BG,
        )
        self.module_one_ogg_output_folder.place(
            x=spec.PHASE_ONE_TEXT_ROW_X + min(0, spec.OUTPUT_FOLDER_ROW_X_OFFSET),
            y=output_folder_y,
        )

        workshop_output_folder_y = (
            output_folder_y
            + self.module_one_ogg_output_folder.winfo_reqheight()
            + spec.PHASE_ONE_OUTPUT_FOLDER_STACK_GAP
        )
        self.module_one_workshop_output_folder = OutputFolderField(
            self.module_one_midground_border,
            label_text='Zomboid Workshop Folder',
            folder_icon_path=self._folder_button_icon_path(),
            textvariable=self.workshop_output_folder_var,
            bg_color=spec.MODULE_MIDGROUND_BG,
        )
        self.module_one_workshop_output_folder.place(
            x=spec.PHASE_ONE_TEXT_ROW_X + min(0, spec.OUTPUT_FOLDER_ROW_X_OFFSET),
            y=workshop_output_folder_y,
        )

        action_button_y = workshop_output_folder_y + self.module_one_workshop_output_folder.winfo_reqheight() + spec.PHASE_ONE_ACTION_BUTTON_GAP_BELOW_OUTPUT
        action_button_x = spec.PHASE_ONE_TEXT_ROW_X + min(0, spec.OUTPUT_FOLDER_ROW_X_OFFSET)
        self.module_one_save_button = MainButton(
            self.module_one_midground_border,
            text='SAVE',
        )
        self.module_one_save_button.place(x=action_button_x, y=action_button_y)

        load_button_x = action_button_x + spec.MAIN_BUTTON_SIZE[0] + spec.PHASE_ONE_ACTION_BUTTON_GAP_X
        self.module_one_load_button = MainButton(
            self.module_one_midground_border,
            text='LOAD',
        )
        self.module_one_load_button.place(x=load_button_x, y=action_button_y)

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

    def _build_module_two_placeholder_content(self) -> None:
        self.module_two_placeholder = tk.Frame(
            self.module_two_content_surface,
            bg='#2a272d',
            bd=0,
            highlightthickness=0,
            width=spec.MODULE_TWO_SCROLL_VIEWPORT_SIZE[0],
            height=640,
        )
        self.module_two_placeholder.pack(fill='x')
        self.module_two_placeholder.pack_propagate(False)
        self.module_two_scroll_area.refresh_scroll_region()

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
