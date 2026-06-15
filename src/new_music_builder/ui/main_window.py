from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import time
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

from new_music_builder import __version__
from new_music_builder.domain.models import MediaKind, default_media_row
from new_music_builder.platform.paths import app_root
from new_music_builder.services.asset_catalog import AssetCatalog
from new_music_builder.services.audio_workspace import AudioWorkspaceService
from new_music_builder.services.index_selection import apply_index_selection
from new_music_builder.services.project_session import ProjectSession
from new_music_builder.services.project_store import ProjectStore
from new_music_builder.services.recent_projects import RecentProjectsStore
from new_music_builder.services.session_store import SessionStore
from new_music_builder.services.track_import import filter_supported_audio_paths
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.app_header import AppHeader
from new_music_builder.ui.widgets.cover_picker import CoverPicker
from new_music_builder.ui.widgets.labeled_checkbox import LabeledCheckbox
from new_music_builder.ui.widgets.labeled_text_field import LabeledTextField
from new_music_builder.ui.widgets.main_button import MainButton
from new_music_builder.ui.widgets.media_creation_header import MediaCreationHeader
from new_music_builder.ui.widgets.media_row_list import MediaRowList, RowSelectionModifiers
from new_music_builder.ui.widgets.media_songlist_table import TrackSelectionModifiers
from new_music_builder.ui.widgets.menu_strip import MenuStrip
from new_music_builder.ui.widgets.module_header import ModuleHeader
from new_music_builder.ui.widgets.module_shell import ModuleShell
from new_music_builder.ui.widgets.output_folder_field import OutputFolderField
from new_music_builder.ui.widgets.scroll_area import ScrollViewport

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore[import-not-found]
except ImportError:
    DND_FILES = None

    class _DnDCompat:
        pass
else:
    class _DnDCompat(TkinterDnD.DnDWrapper):
        pass


class MainWindow(_DnDCompat, ctk.CTk):

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        self.title(f'New Music Builder v{__version__}')
        self.geometry(f'{spec.APP_WIDTH}x{spec.APP_HEIGHT}')
        self.minsize(spec.APP_MIN_WIDTH, spec.APP_MIN_HEIGHT)
        self.configure(fg_color=spec.APP_BG)
        self._initialize_drag_and_drop()

        self.project_store = ProjectStore()
        self.recent_store = RecentProjectsStore()
        self.session_store = SessionStore()
        self.audio_workspace = AudioWorkspaceService()
        self.session, saved_path = self.session_store.load()
        self.session = ProjectSession(project=self.session, current_path=saved_path)
        self.module_two_selected_row_ids: set[int] = set()
        self.module_two_selection_anchor_row_id: int | None = None
        self.module_two_song_selected_indices: dict[tuple[int, str], set[int]] = {}
        self.module_two_song_selection_anchor_indices: dict[tuple[int, str], int | None] = {}
        self._module_two_song_drag_session: dict[str, object] | None = None
        self._module_two_selection_suppressed_until = 0.0
        self._module_two_consume_next_plain_selection = False
        self._restore_unsaved_phase_two_default()
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
        self.bind('<Delete>', self._on_delete_selected_songs, add='+')
        self.refresh_all()
        self.protocol('WM_DELETE_WINDOW', self.on_close)

    def _initialize_drag_and_drop(self) -> None:
        if DND_FILES is None:
            return
        try:
            TkinterDnD._require(self)
        except (RuntimeError, tk.TclError):
            pass

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

    def _cassette_item_icon_path(self) -> Path:
        return app_root() / 'assets' / 'Inventory' / 'Cassette' / 'Item_NM_Cassette4.png'

    def _vinyl_item_icon_path(self) -> Path:
        return app_root() / 'assets' / 'Inventory' / 'Vinyl' / 'Item_NM_Vinyl7.png'

    def _cd_item_icon_path(self) -> Path:
        return app_root() / 'assets' / 'Inventory' / 'CD' / 'Item_NM_CD.png'

    def _edit_icon_path(self) -> Path:
        return app_root() / 'assets' / 'EditIcon.png'

    def _ear_icon_path(self) -> Path:
        return app_root() / 'assets' / 'EarIcon.png'

    def _grab_icon_path(self) -> Path:
        return app_root() / 'assets' / 'GrabIcon.png'

    def _table_check_icon_path(self) -> Path:
        return app_root() / 'assets' / 'TableCheckIcon.png'

    def _preview_audio_icon_path(self) -> Path:
        return app_root() / 'assets' / 'PreviewAudioIcon.png'

    def _module_two_live_preview_paths(self) -> dict[str, dict[str, str]]:
        inventory_root = app_root() / 'assets' / 'Inventory'
        world_root = app_root() / 'assets' / 'World'
        return {
            'inventory': {
                'cassette': str(inventory_root / 'Cassette' / 'Item_NM_Cassette4.png'),
                'cassette_case': str(inventory_root / 'CassetteCase' / 'Item_NM_Case9.png'),
                'vinyl': str(inventory_root / 'Vinyl' / 'Item_NM_Vinyl7.png'),
                'vinyl_jacket': str(inventory_root / 'VinylJacket' / 'Item_NM_Jacket9.png'),
                'cd': str(inventory_root / 'CD' / 'Item_NM_CD.png'),
                'cd_cover': str(inventory_root / 'CDCover' / 'Item_NM_CDCover9.png'),
            },
            'world': {
                'cassette': str(world_root / 'Cassette' / 'World_NM_Cassette04.png'),
                'cassette_case': str(world_root / 'CassetteCase' / 'World_NM_CassetteCover9.png'),
                'vinyl': str(world_root / 'Vinyl' / 'World_NM_Vinyl8.png'),
                'vinyl_jacket': str(world_root / 'VinylJacket' / 'World_NM_Cover9.png'),
                'cd': str(world_root / 'CD' / 'World_NM_CD.png'),
                'cd_cover': str(world_root / 'CDCover' / 'World_NM_CDCover9.png'),
            },
        }

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

    def _restore_unsaved_phase_two_default(self) -> None:
        if self.session.current_path:
            return
        first_row = default_media_row(1)
        second_row = default_media_row(2)
        second_row.expanded = False
        third_row = default_media_row(3)
        third_row.expanded = False
        self.session.project.media_rows = [first_row, second_row, third_row]

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

        self.module_two_top_header = MediaCreationHeader(
            self.module_two_midground_border,
            add_command=self._add_module_two_media_row,
            remove_command=self._remove_module_two_media_rows,
        )
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
        self._build_module_two_row_list()

        self.module_one_cover_picker = CoverPicker(
            self.module_one_midground,
            folder_icon_path=self._folder_button_icon_path(),
            command=self._select_workshop_poster_image,
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

    def _build_module_two_row_list(self) -> None:
        current_row_ids = {row.row_id for row in self.session.project.media_rows}
        self.module_two_selected_row_ids &= current_row_ids
        if self.module_two_selection_anchor_row_id not in current_row_ids:
            self.module_two_selection_anchor_row_id = None
        if hasattr(self, 'module_two_row_list'):
            self.module_two_row_list.destroy()
        self.module_two_row_list = MediaRowList(
            self.module_two_content_surface,
            rows=self.session.project.media_rows,
            folder_icon_path=str(self._folder_button_icon_path()),
            cassette_icon_path=str(self._cassette_item_icon_path()),
            vinyl_icon_path=str(self._vinyl_item_icon_path()),
            cd_icon_path=str(self._cd_item_icon_path()),
            check_icon_path=str(self._check_icon_path()),
            edit_icon_path=str(self._edit_icon_path()),
            ear_icon_path=str(self._ear_icon_path()),
            grab_icon_path=str(self._grab_icon_path()),
            table_check_icon_path=str(self._table_check_icon_path()),
            preview_audio_icon_path=str(self._preview_audio_icon_path()),
            live_preview_paths=self._module_two_live_preview_paths(),
            bg_color=spec.MODULE_MIDGROUND_BG,
            on_row_selected=self._expand_module_two_media_row,
            selected_row_ids=self.module_two_selected_row_ids,
            on_background_selected=self._select_module_two_media_row,
            on_enabled_media_changed=self._set_module_two_media_enabled,
            on_name_committed=self._commit_module_two_media_name,
            on_side_selected=self._set_module_two_media_side,
            on_preview_mode_selected=self._set_module_two_preview_mode,
            on_cover_selected=self._select_module_two_media_cover,
            on_add_song=self._add_module_two_songs,
            on_remove_song=self._remove_module_two_selected_songs,
            selected_song_indices_by_key=self.module_two_song_selected_indices,
            on_song_selected=self._select_module_two_song,
            on_song_remove_requested=self._remove_module_two_song_via_row_click,
            on_song_drag_started=self._begin_module_two_song_drag,
            on_song_drag_moved=self._update_module_two_song_drag,
            on_song_drag_finished=self._finish_module_two_song_drag,
            dnd_type=DND_FILES,
            can_accept_song_drop=self._can_accept_song_drop,
            on_song_drop=self._on_module_two_song_drop,
        )
        self.module_two_row_list.pack(anchor='nw')
        self.module_two_scroll_area.refresh_scroll_region()

    def _image_filetypes(self) -> list[tuple[str, str]]:
        return [
            ('Image Files', '*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff'),
            ('PNG Files', '*.png'),
            ('JPEG Files', '*.jpg *.jpeg'),
            ('All Files', '*.*'),
        ]

    def _audio_filetypes(self) -> list[tuple[str, str]]:
        return [
            ('Audio Files', '*.ogg *.mp3 *.wav *.flac *.m4a *.aac *.wma'),
            ('All Files', '*.*'),
        ]

    def _initial_image_dir(self, current_path: str | None) -> str:
        if current_path:
            resolved = Path(current_path)
            if resolved.exists():
                return str(resolved.parent if resolved.is_file() else resolved)
        return str(Path.home())

    def _initial_audio_dir(self, row_id: int | None = None) -> str:
        if row_id is not None:
            target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
            if target_row is not None:
                active_tracks = target_row.tracks_a if target_row.selected_side == 'A' else target_row.tracks_b
                if active_tracks:
                    first_path = Path(active_tracks[-1].source_path)
                    if first_path.exists():
                        return str(first_path.parent)
        return str(Path.home())

    def _expanded_row_widget(self, row_id: int) -> object | None:
        if not hasattr(self, 'module_two_row_list'):
            return None
        return next(
            (
                widget
                for widget in self.module_two_row_list.row_widgets
                if getattr(widget, '_row_expanded', False) and getattr(widget, '_row_id', None) == row_id
            ),
            None,
        )

    def _cancel_module_two_song_drag(self) -> None:
        if self._module_two_song_drag_session is None:
            return
        row_id = int(self._module_two_song_drag_session.get('row_id', -1))
        expanded_widget = self._expanded_row_widget(row_id)
        if expanded_widget is not None:
            expanded_widget.cancel_song_drag()
        self._module_two_song_drag_session = None

    def _module_two_song_selection_key(self, row_id: int, side: str | None = None) -> tuple[int, str] | None:
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return None
        resolved_side = side if side in {'A', 'B'} else target_row.selected_side
        return (row_id, resolved_side)

    def _module_two_song_selection_for_row(self, row_id: int, side: str | None = None) -> set[int]:
        key = self._module_two_song_selection_key(row_id, side)
        if key is None:
            return set()
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return set()
        tracks = target_row.tracks_a if key[1] == 'A' else target_row.tracks_b
        selected = self.module_two_song_selected_indices.get(key, set())
        filtered = {index for index in selected if 0 <= index < len(tracks)}
        self.module_two_song_selected_indices[key] = filtered
        anchor = self.module_two_song_selection_anchor_indices.get(key)
        if anchor is not None and not (0 <= anchor < len(tracks)):
            self.module_two_song_selection_anchor_indices[key] = None
        return filtered

    def _select_workshop_poster_image(self) -> None:
        selected = fd.askopenfilename(
            title='Select Workshop Poster Image',
            filetypes=self._image_filetypes(),
            initialdir=self._initial_image_dir(self.session.project.workshop_poster_path),
            parent=self,
        )
        if not selected:
            return
        self.session.project.workshop_poster_path = selected
        self.module_one_cover_picker.set_cover_path(selected)
        self.on_project_change()

    def _select_module_two_media_cover(self, row_id: int) -> None:
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return
        selected = fd.askopenfilename(
            title=f'Select Cover Image For Media Row {row_id}',
            filetypes=self._image_filetypes(),
            initialdir=self._initial_image_dir(target_row.cover_path),
            parent=self,
        )
        if not selected:
            return
        target_row.cover_path = selected
        expanded_widget = next(
            (
                widget
                for widget in self.module_two_row_list.row_widgets
                if getattr(widget, '_row_expanded', False) and getattr(widget, '_row_id', None) == row_id
            ),
            None,
        )
        if expanded_widget is not None:
            expanded_widget.refresh_cover(selected)
        self.on_project_change()

    def _can_accept_song_drop(self, paths: list[str]) -> bool:
        return bool(filter_supported_audio_paths(paths))

    def _add_module_two_songs(self, row_id: int) -> None:
        selected = fd.askopenfilenames(
            title='Add Song(s)',
            filetypes=self._audio_filetypes(),
            initialdir=self._initial_audio_dir(row_id),
            parent=self,
        )
        if not selected:
            return
        self._add_module_two_songs_from_paths(row_id, list(selected))

    def _on_module_two_song_drop(self, row_id: int, paths: list[str]) -> None:
        self._add_module_two_songs_from_paths(row_id, paths)

    def _add_module_two_songs_from_paths(self, row_id: int, paths: list[str]) -> None:
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return
        inserted = self.session.add_tracks_to_media_row(row_id, target_row.selected_side, paths)
        if not inserted:
            return
        expanded_widget = self._expanded_row_widget(row_id)
        if expanded_widget is not None:
            expanded_widget.refresh_song_table()
            expanded_widget.set_song_selection_state(self._module_two_song_selection_for_row(row_id))
        self.on_project_change()

    def _on_delete_selected_songs(self, _event: tk.Event | None = None) -> str:
        focused_widget = self.focus_get()
        if isinstance(focused_widget, tk.Entry):
            return ''
        expanded_row = next((row for row in self.session.project.media_rows if row.expanded), None)
        if expanded_row is None:
            return 'break'
        self._remove_module_two_selected_songs(expanded_row.row_id)
        return 'break'

    def _remove_module_two_selected_songs(self, row_id: int) -> None:
        self._cancel_module_two_song_drag()
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return
        key = (row_id, target_row.selected_side)
        selected_indices = self._module_two_song_selection_for_row(row_id, target_row.selected_side)
        if not selected_indices:
            return
        removed = self.session.remove_tracks_from_media_row(row_id, target_row.selected_side, selected_indices)
        if not removed:
            return
        self.module_two_song_selected_indices[key] = set()
        self.module_two_song_selection_anchor_indices[key] = None
        expanded_widget = self._expanded_row_widget(row_id)
        if expanded_widget is not None:
            expanded_widget.refresh_song_table()
            expanded_widget.set_song_selection_state(set())
        self.on_project_change()

    def _remove_module_two_song_via_row_click(self, row_id: int, track_index: int) -> None:
        self._cancel_module_two_song_drag()
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return
        key = (row_id, target_row.selected_side)
        current_selected = self._module_two_song_selection_for_row(row_id, target_row.selected_side)
        if len(current_selected) > 1:
            removal_indices = set(current_selected)
            removal_indices.add(track_index)
        else:
            removal_indices = {track_index}
        removed = self.session.remove_tracks_from_media_row(row_id, target_row.selected_side, removal_indices)
        if not removed:
            return
        self.module_two_song_selected_indices[key] = set()
        self.module_two_song_selection_anchor_indices[key] = None
        expanded_widget = self._expanded_row_widget(row_id)
        if expanded_widget is not None:
            expanded_widget.refresh_song_table()
            expanded_widget.set_song_selection_state(set())
        self.on_project_change()

    def _add_module_two_media_row(self) -> None:
        self._cancel_module_two_song_drag()
        for row in self.session.project.media_rows:
            row.expanded = False

        new_row_id = self.session.add_media_row()
        for row in self.session.project.media_rows:
            row.expanded = row.row_id == new_row_id

        self._build_module_two_row_list()
        self.module_two_content_viewport.yview_moveto(1.0)
        self.module_two_scroll_area.refresh_scroll_region()
        self.module_two_content_viewport.yview_moveto(1.0)
        self.on_project_change()

    def _remove_module_two_media_rows(self) -> None:
        self._cancel_module_two_song_drag()
        if self.module_two_selected_row_ids:
            row_ids_to_remove = set(self.module_two_selected_row_ids)
        elif self.session.project.media_rows:
            row_ids_to_remove = {self.session.project.media_rows[-1].row_id}
        else:
            return

        current_view = self.module_two_content_viewport.yview()
        self.session.remove_media_rows(row_ids_to_remove)
        self.module_two_selected_row_ids.clear()
        self.module_two_selection_anchor_row_id = None
        self.module_two_song_selected_indices = {
            key: value
            for key, value in self.module_two_song_selected_indices.items()
            if key[0] not in row_ids_to_remove
        }
        self.module_two_song_selection_anchor_indices = {
            key: value
            for key, value in self.module_two_song_selection_anchor_indices.items()
            if key[0] not in row_ids_to_remove
        }
        self._build_module_two_row_list()
        self.module_two_content_viewport.yview_moveto(current_view[0])
        self.on_project_change()

    def _set_module_two_media_enabled(self, row_id: int, kind: MediaKind, enabled: bool) -> None:
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return
        if target_row.enabled_media[kind] == enabled:
            return
        target_row.enabled_media[kind] = enabled
        if (
            hasattr(self, 'module_two_row_list')
            and self.module_two_row_list.row_widgets
        ):
            expanded_widget = self._expanded_row_widget(row_id)
            if expanded_widget is not None:
                expanded_widget.refresh_live_preview()
        self.on_project_change()

    def _commit_module_two_media_name(self, row_id: int, value: str) -> None:
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return
        self._module_two_selection_suppressed_until = (
            time.monotonic() + (spec.MEDIA_ROW_SELECTION_SUPPRESS_AFTER_TOGGLE_MS / 1000.0)
        )
        self._module_two_consume_next_plain_selection = True
        target_row.media_name = value
        self.on_project_change()

    def _set_module_two_media_side(self, row_id: int, side: str) -> None:
        self._cancel_module_two_song_drag()
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None or side not in {'A', 'B'}:
            return
        if target_row.selected_side == side:
            return

        target_row.selected_side = side
        expanded_widget = self._expanded_row_widget(row_id)
        if expanded_widget is not None:
            expanded_widget.refresh_song_table()
            expanded_widget.set_song_selection_state(self._module_two_song_selection_for_row(row_id, side))
        self.on_project_change()

    def _set_module_two_preview_mode(self, row_id: int, mode: str) -> None:
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None or mode not in {'inventory', 'world'}:
            return
        if target_row.preview_mode == mode:
            return
        target_row.preview_mode = mode
        self.on_project_change()

    def _expand_module_two_media_row(self, row_id: int) -> None:
        self._cancel_module_two_song_drag()
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return

        current_view = self.module_two_content_viewport.yview()
        self.module_two_selected_row_ids.clear()
        self.module_two_selection_anchor_row_id = None
        if target_row.expanded:
            target_row.expanded = False
        else:
            for row in self.session.project.media_rows:
                row.expanded = row.row_id == row_id

        self._build_module_two_row_list()
        self.module_two_content_viewport.yview_moveto(current_view[0])
        self.on_project_change()

    def _select_module_two_media_row(self, row_id: int, modifiers: RowSelectionModifiers) -> None:
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return
        suppressed = time.monotonic() < self._module_two_selection_suppressed_until
        if (
            self._module_two_consume_next_plain_selection
            and not modifiers.shift
            and not modifiers.additive
        ):
            if suppressed:
                self._module_two_consume_next_plain_selection = False
                return
            self._module_two_consume_next_plain_selection = False
        if suppressed:
            return
        self._module_two_consume_next_plain_selection = False

        if (
            not modifiers.shift
            and not modifiers.additive
            and target_row.expanded
            and self.module_two_selected_row_ids == {row_id}
        ):
            return

        if modifiers.shift:
            self._select_module_two_row_range(row_id)
        elif modifiers.additive:
            if row_id in self.module_two_selected_row_ids:
                self.module_two_selected_row_ids.remove(row_id)
            else:
                self.module_two_selected_row_ids.add(row_id)
            self.module_two_selection_anchor_row_id = row_id
        else:
            self.module_two_selected_row_ids = {row_id}
            self.module_two_selection_anchor_row_id = row_id
        self.module_two_row_list.set_selection_state(self.module_two_selected_row_ids)

    def _select_module_two_row_range(self, row_id: int) -> None:
        if self.module_two_selection_anchor_row_id is None:
            self.module_two_selected_row_ids = {row_id}
            self.module_two_selection_anchor_row_id = row_id
            return

        row_ids = [row.row_id for row in self.session.project.media_rows]
        try:
            anchor_index = row_ids.index(self.module_two_selection_anchor_row_id)
            target_index = row_ids.index(row_id)
        except ValueError:
            self.module_two_selected_row_ids = {row_id}
            self.module_two_selection_anchor_row_id = row_id
            return

        start = min(anchor_index, target_index)
        end = max(anchor_index, target_index)
        self.module_two_selected_row_ids = set(row_ids[start:end + 1])

    def _select_module_two_song(self, row_id: int, track_index: int, modifiers: TrackSelectionModifiers) -> None:
        self._cancel_module_two_song_drag()
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return
        key = (row_id, target_row.selected_side)
        tracks = target_row.tracks_a if target_row.selected_side == 'A' else target_row.tracks_b
        current_selected = self._module_two_song_selection_for_row(row_id, target_row.selected_side)
        current_anchor = self.module_two_song_selection_anchor_indices.get(key)
        next_selected, next_anchor = apply_index_selection(
            current_selected,
            current_anchor,
            track_index,
            len(tracks),
            shift=modifiers.shift,
            additive=modifiers.additive,
        )
        if next_selected == current_selected and next_anchor == current_anchor:
            return
        self.module_two_song_selected_indices[key] = next_selected
        self.module_two_song_selection_anchor_indices[key] = next_anchor
        expanded_widget = self._expanded_row_widget(row_id)
        if expanded_widget is not None:
            expanded_widget.set_song_selection_state(next_selected)

    def _begin_module_two_song_drag(self, row_id: int, track_index: int, x_root: int, y_root: int) -> None:
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return
        expanded_widget = self._expanded_row_widget(row_id)
        if expanded_widget is None:
            return
        side = target_row.selected_side
        key = (row_id, side)
        current_selected = self._module_two_song_selection_for_row(row_id, side)
        if track_index in current_selected and len(current_selected) > 1:
            dragged_indices = set(current_selected)
        else:
            dragged_indices = {track_index}
            self.module_two_song_selected_indices[key] = dragged_indices
            self.module_two_song_selection_anchor_indices[key] = track_index
            expanded_widget.set_song_selection_state(dragged_indices)
        self._module_two_song_drag_session = {
            'row_id': row_id,
            'side': side,
            'dragged_indices': dragged_indices,
        }
        expanded_widget.begin_song_drag(dragged_indices, x_root, y_root)

    def _update_module_two_song_drag(self, row_id: int, x_root: int, y_root: int) -> None:
        if self._module_two_song_drag_session is None:
            return
        if int(self._module_two_song_drag_session.get('row_id', -1)) != row_id:
            return
        expanded_widget = self._expanded_row_widget(row_id)
        if expanded_widget is not None:
            expanded_widget.update_song_drag(x_root, y_root)

    def _finish_module_two_song_drag(self, row_id: int, x_root: int, y_root: int) -> None:
        if self._module_two_song_drag_session is None:
            return
        if int(self._module_two_song_drag_session.get('row_id', -1)) != row_id:
            return
        expanded_widget = self._expanded_row_widget(row_id)
        if expanded_widget is None:
            self._module_two_song_drag_session = None
            return
        insertion_index = expanded_widget.finish_song_drag(x_root, y_root)
        drag_session = self._module_two_song_drag_session
        self._module_two_song_drag_session = None
        if insertion_index is None:
            return
        side = str(drag_session.get('side', ''))
        dragged_indices = set(drag_session.get('dragged_indices', set()))
        moved_indices = self.session.move_tracks_within_media_row(row_id, side, dragged_indices, insertion_index)
        if not moved_indices:
            return
        key = (row_id, side)
        moved_selection = set(moved_indices)
        self.module_two_song_selected_indices[key] = moved_selection
        self.module_two_song_selection_anchor_indices[key] = moved_indices[0] if moved_indices else None
        expanded_widget.refresh_song_table()
        expanded_widget.set_song_selection_state(moved_selection)
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
        if hasattr(self, 'module_one_cover_picker'):
            self.module_one_cover_picker.set_cover_path(self.session.project.workshop_poster_path)
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
        self._cancel_module_two_song_drag()
        self.session.reset()
        self._restore_unsaved_phase_two_default()
        self.module_two_selected_row_ids.clear()
        self.module_two_selection_anchor_row_id = None
        self.module_two_song_selected_indices.clear()
        self.module_two_song_selection_anchor_indices.clear()
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
        self._cancel_module_two_song_drag()
        self.session.project = self.project_store.load(path)
        self.session.current_path = str(path)
        self.recent_store.push(path)
        self.module_two_selected_row_ids.clear()
        self.module_two_selection_anchor_row_id = None
        self.module_two_song_selected_indices.clear()
        self.module_two_song_selection_anchor_indices.clear()
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
