from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as messagebox
from uuid import uuid4

import customtkinter as ctk
from PIL import Image, ImageTk

from new_music_builder import __version__
from new_music_builder.domain.models import (
    AudioRunEvent,
    AudioRunResult,
    AppearanceKind,
    BuildSummaryStats,
    ConversionSideGroup,
    ConversionSongProgress,
    ExportLogLine,
    ExportTargetPaths,
    GeneratedPreviewRow,
    MediaKind,
    ScaffoldResult,
    SongSortColumn,
    default_media_row,
)
from new_music_builder.platform.paths import app_root, assets_root
from new_music_builder.platform.paths import detect_workshop_dir, open_folder
from new_music_builder.services.asset_catalog import AssetCatalog
from new_music_builder.services.build_event_pump import BuildEventPump
from new_music_builder.services.export_build_runner import run_staged_export
from new_music_builder.services.export_planning import build_export_plan, build_preview_scenario
from new_music_builder.services.export_scaffold import (
    build_scaffold_stats,
    build_validation_log_lines,
    render_square_image,
    resolve_export_target,
    validate_export_request,
)
from new_music_builder.services.index_selection import apply_index_selection
from new_music_builder.services.project_session import ProjectSession
from new_music_builder.services.project_store import ProjectStore
from new_music_builder.services.recent_projects import RecentProjectsStore
from new_music_builder.services.session_store import SessionStore
from new_music_builder.services.track_import import filter_supported_audio_paths
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.app_header import AppHeader
from new_music_builder.ui.widgets.audio_settings_dialog import AudioSettingsDialog
from new_music_builder.ui.widgets.appearance_entries import entry_for_selected_key
from new_music_builder.ui.widgets.appearance_panel_shell import AppearancePanelShell
from new_music_builder.ui.widgets.appearance_selector import (
    AppearanceSelector,
    AppearanceGridEntry,
    apply_selection_from_grid_entry,
    can_commit_dual_custom,
    can_commit_single_custom,
    fallback_selected_asset_key_after_delete,
    merge_appearance_grid_entries,
)
from new_music_builder.ui.widgets.border_pane import BorderPane
from new_music_builder.ui.widgets.cover_picker import CoverPicker
from new_music_builder.ui.widgets.confirmation_dialog import ConfirmDialog
from new_music_builder.ui.widgets.labeled_checkbox import LabeledCheckbox
from new_music_builder.ui.widgets.labeled_text_field import LabeledTextField
from new_music_builder.ui.widgets.main_button import MainButton
from new_music_builder.ui.widgets.media_creation_header import MediaCreationHeader
from new_music_builder.ui.widgets.media_row_list import MediaRowList, RowSelectionModifiers
from new_music_builder.ui.widgets.media_songlist_table import TrackSelectionModifiers
from new_music_builder.ui.widgets.menu_strip import MenuAction, MenuStrip
from new_music_builder.ui.widgets.module_four_panel import ModuleFourPanel
from new_music_builder.ui.widgets.module_five_panel import ModuleFivePanel
from new_music_builder.ui.widgets.module_six_panel import ModuleSixPanel
from new_music_builder.ui.widgets.module_six_stats_table import ModuleSixStatsTable
from new_music_builder.ui.widgets.module_action_header import ModuleActionHeader
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


LOGGER = logging.getLogger('new_music_builder')


@dataclass(frozen=True, slots=True)
class ShortcutMenuSpec:
    menu_name: str
    label: str
    handler_name: str
    shortcut_label: str = ""
    shortcut_sequences: tuple[str, ...] = ()
    disabled_during_build: bool = False


MENU_SHORTCUT_SPECS: tuple[ShortcutMenuSpec, ...] = (
    ShortcutMenuSpec(
        menu_name='FILE',
        label='New',
        handler_name='new_project',
        shortcut_label='(Ctrl + N)',
        shortcut_sequences=('<Control-KeyPress-n>', '<Control-KeyPress-N>'),
        disabled_during_build=True,
    ),
    ShortcutMenuSpec(
        menu_name='FILE',
        label='Open',
        handler_name='load_project',
        shortcut_label='(Ctrl + O)',
        shortcut_sequences=('<Control-KeyPress-o>', '<Control-KeyPress-O>'),
        disabled_during_build=True,
    ),
    ShortcutMenuSpec(
        menu_name='FILE',
        label='Save',
        handler_name='save_project',
        shortcut_label='(Ctrl + S)',
        shortcut_sequences=('<Control-KeyPress-s>',),
        disabled_during_build=True,
    ),
    ShortcutMenuSpec(
        menu_name='FILE',
        label='Save As...',
        handler_name='save_project_as',
        shortcut_label='(Ctrl + Shift + S)',
        shortcut_sequences=('<Control-KeyPress-S>', '<Control-Shift-KeyPress-S>'),
        disabled_during_build=True,
    ),
    ShortcutMenuSpec(
        menu_name='FILE',
        label='Exit',
        handler_name='on_close',
        shortcut_label='(Ctrl + Q)',
        shortcut_sequences=('<Control-KeyPress-q>', '<Control-KeyPress-Q>'),
        disabled_during_build=True,
    ),
    ShortcutMenuSpec(
        menu_name='PREFERENCES',
        label='Audio Settings',
        handler_name='_show_audio_settings_dialog',
        shortcut_label='(Ctrl + P)',
        shortcut_sequences=('<Control-KeyPress-p>', '<Control-KeyPress-P>'),
        disabled_during_build=True,
    ),
    ShortcutMenuSpec(
        menu_name='HELP',
        label='Tutorial',
        handler_name='_show_tutorial_placeholder',
        shortcut_label='(Ctrl + H)',
        shortcut_sequences=('<Control-KeyPress-h>', '<Control-KeyPress-H>'),
    ),
)


def build_menu_action_map(window: object) -> dict[str, list[MenuAction]]:
    menu_actions: dict[str, list[MenuAction]] = {}
    for spec in MENU_SHORTCUT_SPECS:
        menu_actions.setdefault(spec.menu_name, []).append(
            MenuAction(
                label=spec.label,
                command=getattr(window, spec.handler_name),
                shortcut_label=spec.shortcut_label,
            )
        )
    return menu_actions


def build_project_mutation_actions() -> tuple[tuple[str, str], ...]:
    return tuple(
        (spec.menu_name, spec.label)
        for spec in MENU_SHORTCUT_SPECS
        if spec.disabled_during_build
    )


def resolve_song_removal_indices(
    selected_indices: set[int],
    *,
    track_count: int,
    fallback_to_last: bool,
) -> set[int]:
    if selected_indices:
        return set(selected_indices)
    if fallback_to_last and track_count > 0:
        return {track_count - 1}
    return set()


def build_project_saved_log_line(project_path: str) -> ExportLogLine:
    return ExportLogLine(
        timestamp=datetime.now().strftime("%H:%M:%S"),
        prefix_text="Project saved:",
        subject_text=project_path,
        color_role="done",
    )


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
        self.session, saved_path = self.session_store.load()
        self.session = ProjectSession(project=self.session, current_path=saved_path)
        self.module_two_selected_row_ids: set[int] = set()
        self.module_two_selection_anchor_row_id: int | None = None
        self.module_two_song_selected_indices: dict[tuple[int, str], set[int]] = {}
        self.module_two_song_selection_anchor_indices: dict[tuple[int, str], int | None] = {}
        self._module_two_song_drag_session: dict[str, object] | None = None
        self._module_two_row_drag_session: dict[str, object] | None = None
        self._module_two_selection_suppressed_until = 0.0
        self._module_two_consume_next_plain_selection = False
        self._restore_unsaved_phase_two_default()
        self.mod_name_var = tk.StringVar(value=self.session.project.mod_name)
        self.mod_id_var = tk.StringVar(value=self.session.project.mod_id)
        self.parent_mod_id_var = tk.StringVar(value=self.session.project.parent_mod_id)
        self.author_var = tk.StringVar(value=self.session.project.author)
        self.ogg_output_folder_var = tk.StringVar(value=self.session.project.ogg_output_folder)
        self.workshop_output_folder_var = tk.StringVar(value=self.session.project.workshop_output_folder)
        self._phase_one_sync_after_id: str | None = None
        self._phase_one_sync_suspended = False
        self._window_icon_image = None
        self._last_export_output_path: str = ""
        self._build_event_queue: queue.Queue[object] | None = None
        self._build_poll_after_id: str | None = None
        self._active_build_thread: threading.Thread | None = None
        self._build_event_pump = BuildEventPump()
        self._build_locked = False
        self._build_abort_requested = False
        self._build_abort_event: threading.Event | None = None
        self._active_build_run_id: str | None = None
        self._locked_module_two_browse_row_id: int | None = None
        self._active_build_final_targets: ExportTargetPaths | None = None
        self._active_preview_rows_by_side: dict[tuple[int, str], GeneratedPreviewRow] = {}
        self._active_successful_sides: list[tuple[int, str]] = []
        self._active_successful_sides_by_row: dict[int, set[str]] = {}
        self._active_emitted_preview_rows: set[tuple[int, str]] = set()

        self.asset_catalog_service = AssetCatalog(assets_root())
        self.asset_catalog = self.asset_catalog_service.scan()
        self.module_three_staged_custom_images: dict[str, dict[str, str]] = {}
        self.build_log: list[str] = []
        self.preview_entries: list[str] = []
        self._responsive_content_width = 0
        self._responsive_layout_after_id: str | None = None
        self._responsive_finalize_after_id: str | None = None
        self._responsive_last_widths: dict[str, int] = {}
        self._live_resize_active = False

        self._apply_window_icon()
        self._build_menu()
        self._build_header()
        self._build_menu_strip()
        self._build_layout()
        self._register_phase_one_field_traces()
        self._sync_phase_one_ui_from_project()
        self.content_frame.bind('<Configure>', self._on_content_frame_configure, add='+')
        self.bind('<Delete>', self._on_delete_selected_songs, add='+')
        self.refresh_all()
        self._schedule_responsive_layout()
        self._bind_app_shortcuts()
        self.protocol('WM_DELETE_WINDOW', self.on_close)

    def _initialize_drag_and_drop(self) -> None:
        if DND_FILES is None:
            return
        try:
            TkinterDnD._require(self)
        except (RuntimeError, tk.TclError):
            pass

    def _main_icon_path(self) -> Path:
        return assets_root() / 'AppIcon' / 'NMB-Ico256.png'

    def _header_logo_path(self) -> Path:
        return self._main_icon_path()

    def _native_icon_path(self) -> Path:
        return assets_root() / 'new_music_builder.ico'

    def _folder_button_icon_path(self) -> Path:
        return assets_root() / 'NMB_Folder2.png'

    def _phase_one_icon_path(self) -> Path:
        return assets_root() / 'PhaseOneIcon.png'

    def _phase_two_icon_path(self) -> Path:
        return assets_root() / 'PhaseTwoIcon.png'

    def _phase_three_icon_path(self) -> Path:
        return assets_root() / 'PhaseThreeIcon.png'

    def _phase_four_icon_path(self) -> Path:
        return assets_root() / 'PhaseFourIcon.png'

    def _phase_one_disabled_icon_path(self) -> Path:
        return assets_root() / 'PhaseOneIconDisabled.png'

    def _phase_two_disabled_icon_path(self) -> Path:
        return assets_root() / 'PhaseTwoIconDisabled.png'

    def _phase_three_disabled_icon_path(self) -> Path:
        return assets_root() / 'PhaseThreeIconDisabled.png'

    def _phase_five_icon_path(self) -> Path:
        return assets_root() / 'PhaseFiveIcon.png'

    def _check_icon_path(self) -> Path:
        return assets_root() / 'Check.png'

    def _small_check_icon_path(self) -> Path:
        return assets_root() / 'SmallCheck.png'

    def _loading_icon_path(self) -> Path:
        root = assets_root()
        preferred = root / 'LoadingIcon.png'
        if preferred.exists():
            return preferred
        return root / 'LoadingImage.png'

    def _cassette_item_icon_path(self) -> Path:
        return assets_root() / 'Inventory' / 'Cassette' / 'Item_NM_Cassette4.png'

    def _vinyl_item_icon_path(self) -> Path:
        return assets_root() / 'Inventory' / 'Vinyl' / 'Item_NM_Vinyl7.png'

    def _cd_item_icon_path(self) -> Path:
        return assets_root() / 'Inventory' / 'CD' / 'Item_NM_CD.png'

    def _edit_icon_path(self) -> Path:
        return assets_root() / 'EditIcon.png'

    def _ear_icon_path(self) -> Path:
        return assets_root() / 'EarIcon.png'

    def _grab_icon_path(self) -> Path:
        return assets_root() / 'GrabIcon.png'

    def _table_check_icon_path(self) -> Path:
        return assets_root() / 'TableCheckIcon.png'

    def _preview_audio_icon_path(self) -> Path:
        return assets_root() / 'PreviewAudioIcon.png'

    def _status_check_icon_path(self) -> Path:
        return assets_root() / 'StatusCheckIcon.png'

    def _status_converting_icon_path(self) -> Path:
        return assets_root() / 'StatusConvertingIcon.png'

    def _status_queued_icon_path(self) -> Path:
        return assets_root() / 'StatusQueuedIcon.png'

    def _build_complete_check_icon_path(self) -> Path:
        return assets_root() / 'BuildCompleteCheckIcon.png'

    def _open_folder_check_icon_path(self) -> Path:
        return assets_root() / 'OpenFolderCheckIcon.png'

    def _reset_icon_path(self) -> Path:
        return assets_root() / 'ResetIcon.png'

    def _project_mutation_actions(self) -> tuple[tuple[str, str], ...]:
        return build_project_mutation_actions()

    def _is_build_locked(self) -> bool:
        return self._build_locked

    def _set_build_locked(self, locked: bool) -> None:
        started = time.perf_counter()
        LOGGER.info(
            "[run=%s] build-lock start locked=%s thread=%s",
            self._active_build_run_id or "-",
            locked,
            threading.current_thread().name,
        )
        self._build_locked = locked
        if locked:
            self._locked_module_two_browse_row_id = self._current_expanded_row_id()
        else:
            self._locked_module_two_browse_row_id = None
        self.phase_three_combo_header.set_right_text('CLICK TO ABORT EXPORT' if locked else 'CLICK TO EXPORT')
        self.module_one_header.set_icon_path(self._phase_one_disabled_icon_path() if locked else self._phase_one_icon_path())
        self.module_two_header.set_icon_path(self._phase_two_disabled_icon_path() if locked else self._phase_two_icon_path())
        self.module_three_header.set_icon_path(self._phase_three_disabled_icon_path() if locked else self._phase_three_icon_path())
        header_text_color = spec.MODULE_HEADER_DISABLED_TEXT_COLOR if locked else spec.MODULE_HEADER_TEXT_COLOR
        self.module_one_header.set_text_color(header_text_color)
        self.module_two_header.set_text_color(header_text_color)
        self.module_three_header.set_text_color(header_text_color)

        self.module_one_cover_picker.set_enabled(not locked)
        self.poster_name_checkbox.set_enabled(not locked)
        self.module_one_mod_name_field.set_enabled(not locked)
        self.module_one_mod_id_field.set_enabled(not locked)
        self.module_one_parent_id_field.set_enabled(not locked)
        self.module_one_author_field.set_enabled(not locked)
        self.module_one_ogg_output_folder.set_enabled(not locked)
        self.module_one_workshop_output_folder.set_enabled(not locked)
        self.module_one_save_button.set_enabled(not locked)
        self.module_one_load_button.set_enabled(not locked)

        self.module_two_top_header.set_enabled(not locked)
        self.module_two_row_list.set_locked(locked)
        if not locked:
            self.module_two_row_list.set_browse_expanded_row(None)

        self.module_three_appearance_selector.set_locked(locked)

        for menu_name, item_label in self._project_mutation_actions():
            self.menu_strip.set_action_enabled(menu_name, item_label, not locked)
        LOGGER.info(
            "[run=%s] build-lock end locked=%s duration_ms=%.1f thread=%s",
            self._active_build_run_id or "-",
            locked,
            (time.perf_counter() - started) * 1000.0,
            threading.current_thread().name,
        )

    def _request_abort_export(self) -> None:
        if not self._build_locked:
            return
        LOGGER.info(
            "[run=%s] abort requested thread=%s",
            self._active_build_run_id or "-",
            threading.current_thread().name,
        )
        self._build_abort_requested = True
        if self._build_abort_event is not None:
            self._build_abort_event.set()
        if hasattr(self, 'module_four_panel'):
            self.module_four_panel.append_log_line(
                ExportLogLine(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    prefix_text="Abort requested.",
                    trailing_text="Stopping export at the next safe checkpoint.",
                    color_role="error",
                )
            )

    def _build_abort_pending(self) -> bool:
        return bool(self._build_abort_event is not None and self._build_abort_event.is_set())

    def _module_two_preview_entry(self, row, kind: AppearanceKind) -> AppearanceGridEntry | None:
        row.ensure_appearances()
        entries = self._module_three_entries_for_kind(kind)
        return entry_for_selected_key(entries, row.appearances[kind].selected_asset_key)

    def _module_two_preview_path_for_row(self, row, kind: AppearanceKind, mode: str, show_empty: bool = False) -> str | None:
        entry = self._module_two_preview_entry(row, kind)
        if entry is None:
            return None
        return entry.displayed_path('world' if mode == 'world' else 'inventory', show_empty=show_empty)

    def _module_two_media_strip_path_for_row(self, row, kind: MediaKind, mode: str) -> str | None:
        return self._module_two_preview_path_for_row(row, kind, 'inventory')

    def _apply_window_icon(self) -> None:
        native_icon = self._native_icon_path()
        applied_native = False
        if native_icon.exists() and sys.platform.startswith('win'):
            try:
                self.iconbitmap(default=str(native_icon))
                applied_native = True
            except tk.TclError:
                pass

        icons = self._window_icon_photo_paths()
        if icons:
            try:
                photos = []
                for path in icons:
                    image = Image.open(path)
                    photos.append(ImageTk.PhotoImage(image))
                self._window_icon_images = photos
                self.iconphoto(True, *photos)
                return
            except Exception:
                if applied_native:
                    return

        icon = self._main_icon_path()
        if icon.exists() and not applied_native:
            try:
                image = Image.open(icon)
                self._window_icon_image = ImageTk.PhotoImage(image)
                self.iconphoto(True, self._window_icon_image)
            except Exception:
                pass

    def _window_icon_photo_paths(self) -> list[Path]:
        icon_dir = assets_root() / 'AppIcon'
        sizes = (16, 24, 32, 48, 64, 128, 256)
        return [path for size in sizes if (path := icon_dir / f'NMB-Ico{size}.png').exists()]

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
        self.menu_strip = MenuStrip(self, menu_actions=build_menu_action_map(self))
        self.menu_strip.pack(fill='x')

    def _bind_app_shortcuts(self) -> None:
        for spec in MENU_SHORTCUT_SPECS:
            callback = getattr(self, spec.handler_name)
            for sequence in spec.shortcut_sequences:
                self.bind_all(
                    sequence,
                    lambda _event, action=callback: self._handle_app_shortcut(action),
                    add='+',
                )

    def _handle_app_shortcut(self, action: Callable[[], None]) -> str:
        action()
        return 'break'

    def _show_tutorial_placeholder(self) -> None:
        messagebox.showinfo('Tutorial', 'Tutorial coming soon.')

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
        self.content_frame.grid_columnconfigure(2, weight=0)
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

        self.module_three_shell = ModuleShell(
            self.content_frame,
            size=spec.MODULE_THREE_SIZE,
            midground_size=spec.MODULE_THREE_MIDGROUND_SIZE,
        )
        self.module_three_shell.grid(row=0, column=2, sticky='nw', padx=(spec.MODULE_GAP_X, 0))
        self.module_three_shell.grid_propagate(False)
        self.module_three_background = self.module_three_shell.background_surface
        self.module_three_midground_border = self.module_three_shell.midground_border
        self.module_three_midground = self.module_three_shell.midground_surface

        self.phase_three_combo_shell = ModuleShell(
            self.content_frame,
            size=spec.PHASE_THREE_COMBO_SIZE,
            midground_size=spec.PHASE_THREE_COMBO_MIDGROUND_SIZE,
            midground_offset=spec.PHASE_THREE_COMBO_MIDGROUND_OFFSET,
        )
        self.phase_three_combo_shell.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky='nw',
            pady=(spec.PHASE_THREE_COMBO_TOP_GAP, 0),
        )
        self.phase_three_combo_shell.grid_propagate(False)
        self.phase_three_combo_background = self.phase_three_combo_shell.background_surface
        self.phase_three_combo_midground_border = self.phase_three_combo_shell.midground_border
        self.phase_three_combo_midground = self.phase_three_combo_shell.midground_surface

        self.module_six_shell = ModuleShell(
            self.content_frame,
            size=spec.MODULE_SIX_SIZE,
            midground_size=spec.MODULE_SIX_MIDGROUND_SIZE,
            midground_offset=spec.MODULE_SIX_MIDGROUND_OFFSET,
        )
        self.module_six_shell.grid(
            row=1,
            column=2,
            sticky='nw',
            padx=(spec.MODULE_GAP_X, 0),
            pady=(spec.MODULE_SIX_TOP_GAP, 0),
        )
        self.module_six_shell.grid_propagate(False)
        self.module_six_background = self.module_six_shell.background_surface
        self.module_six_midground_border = self.module_six_shell.midground_border
        self.module_six_midground = self.module_six_shell.midground_surface

        self.module_two_header = ModuleHeader(
            self.module_two_background,
            text='PHASE 2 : MEDIA CREATION',
            icon_path=self._phase_two_icon_path(),
            bg_color=spec.MODULE_BACKGROUND_BG,
            text_color=spec.MODULE_HEADER_TEXT_COLOR,
        )
        self.module_two_phase_icon = self.module_two_header.icon_label
        self.module_two_phase_label = self.module_two_header.text_label

        self.module_three_header = ModuleHeader(
            self.module_three_background,
            text='PHASE 2 : APPERANCE',
            icon_path=self._phase_three_icon_path(),
            bg_color=spec.MODULE_BACKGROUND_BG,
            text_color=spec.MODULE_HEADER_TEXT_COLOR,
        )
        self.module_three_phase_icon = self.module_three_header.icon_label
        self.module_three_phase_label = self.module_three_header.text_label

        self.phase_three_combo_header = ModuleActionHeader(
            self.phase_three_combo_midground_border,
            width=spec.PHASE_THREE_COMBO_MIDGROUND_SIZE[0],
            text='PHASE 3 : BUILD & EXPORT',
            icon_path=self._phase_four_icon_path(),
            right_text='CLICK TO EXPORT',
            command=self.run_build_preview,
        )
        self.phase_three_combo_header.place(x=0, y=0)
        self.phase_three_combo_phase_icon = self.phase_three_combo_header.icon_label
        self.phase_three_combo_phase_label = self.phase_three_combo_header.text_label

        self.module_six_header = ModuleHeader(
            self.module_six_background,
            text='BUILD SUMMARY',
            icon_path=self._phase_five_icon_path(),
            bg_color=spec.MODULE_BACKGROUND_BG,
            text_color=spec.MODULE_HEADER_TEXT_COLOR,
            x=spec.MODULE_SIX_HEADER_X,
            y=spec.MODULE_SIX_HEADER_Y,
        )
        self.module_six_phase_icon = self.module_six_header.icon_label
        self.module_six_phase_label = self.module_six_header.text_label
        self.module_six_panel = ModuleSixPanel(
            self.module_six_midground,
            build_complete_icon_path=str(self._build_complete_check_icon_path()),
            open_folder_icon_path=str(self._open_folder_check_icon_path()),
            reset_icon_path=str(self._reset_icon_path()),
            on_open_output_folder=self._open_output_folder,
            on_reset=self.reset_project_to_defaults,
        )
        self.module_six_panel.place(x=0, y=0)

        self.phase_three_combo_content_area = tk.Frame(
            self.phase_three_combo_midground,
            bg=spec.MODULE_MIDGROUND_BG,
            bd=0,
            highlightthickness=0,
            width=spec.PHASE_THREE_COMBO_CONTENT_AREA_SIZE[0],
            height=spec.PHASE_THREE_COMBO_CONTENT_AREA_SIZE[1],
        )
        self.phase_three_combo_content_area.place(x=0, y=spec.PHASE_THREE_COMBO_CONTENT_AREA_Y)
        self.phase_three_combo_content_area.pack_propagate(False)

        self.phase_three_module_four_foreground = BorderPane(
            self.phase_three_combo_content_area,
            size=spec.PHASE_THREE_MODULE_FOUR_SIZE,
            fill_color=spec.PHASE_THREE_FOREGROUND_BG,
            border_color=spec.PHASE_THREE_FOREGROUND_BORDER_COLOR,
            border_width=spec.PHASE_THREE_FOREGROUND_BORDER_WIDTH,
        )
        self.phase_three_module_four_foreground.place(
            x=spec.PHASE_THREE_MODULE_FOUR_POS[0],
            y=spec.PHASE_THREE_MODULE_FOUR_POS[1],
        )
        self.module_four_panel = ModuleFourPanel(
            self.phase_three_module_four_foreground,
            status_check_icon_path=str(self._status_check_icon_path()),
            status_converting_icon_path=str(self._status_converting_icon_path()),
            status_queued_icon_path=str(self._status_queued_icon_path()),
        )
        self.module_four_panel.place(x=0, y=0)

        module_five_x = (
            spec.PHASE_THREE_MODULE_FOUR_POS[0]
            + spec.PHASE_THREE_MODULE_FOUR_SIZE[0]
            + spec.PHASE_THREE_MODULE_FIVE_GAP_X
        )
        self.phase_three_module_five_foreground = BorderPane(
            self.phase_three_combo_content_area,
            size=spec.PHASE_THREE_MODULE_FIVE_SIZE,
            fill_color=spec.PHASE_THREE_FOREGROUND_BG,
            border_color=spec.PHASE_THREE_FOREGROUND_BORDER_COLOR,
            border_width=spec.PHASE_THREE_FOREGROUND_BORDER_WIDTH,
        )
        self.phase_three_module_five_foreground.place(
            x=module_five_x,
            y=spec.PHASE_THREE_MODULE_FOUR_POS[1],
        )
        self.module_five_panel = ModuleFivePanel(self.phase_three_module_five_foreground)
        self.module_five_panel.place(x=0, y=0)

        self.module_three_appearance_shell = AppearancePanelShell(
            self.module_three_midground,
            bg_color=spec.MODULE_MIDGROUND_BG,
            show_expanded_footer_overlay=False,
        )
        self.module_three_appearance_shell.place(
            x=spec.MODULE_THREE_CONTENT_POS[0],
            y=spec.MODULE_THREE_CONTENT_POS[1],
        )
        self.module_three_tabs_pane = self.module_three_appearance_shell.tabs_pane
        self.module_three_dual_sprite_row = self.module_three_appearance_shell.dual_sprite_row
        self.module_three_grid_viewport = self.module_three_appearance_shell.grid_viewport
        self.module_three_footer_pane = self.module_three_appearance_shell.footer_pane
        self.module_three_expanded_footer_overlay = self.module_three_appearance_shell.expanded_footer_overlay
        self.module_three_appearance_selector = AppearanceSelector(
            self.module_three_appearance_shell,
            asset_catalog=self.asset_catalog,
            small_check_icon_path=str(self._small_check_icon_path()),
            loading_icon_path=str(self._loading_icon_path()),
            get_custom_assets=self._module_three_custom_assets_for_kind,
            get_staged_custom_images=self._module_three_staged_custom_for_kind,
            on_pick_custom_slot=self._pick_module_three_custom_slot,
            on_reset_custom=self._reset_module_three_custom_staged,
            on_commit_custom=self._commit_module_three_custom,
            on_delete_custom=self._delete_module_three_custom_asset,
            on_preview_mode_selected=self._set_module_two_preview_mode,
            on_selection_changed=self._refresh_module_two_live_preview_for_row,
            on_change=self.on_project_change,
        )

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
        self._refresh_module_three_appearance_selector()

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
            checked=bool(self.session.project.write_mod_name_on_poster),
            command=lambda _checked: self._schedule_phase_one_project_sync(),
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
            command=self._pick_ogg_output_folder,
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
            command=self._pick_workshop_output_folder,
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
            command=self.save_project,
        )
        self.module_one_save_button.place(x=action_button_x, y=action_button_y)

        load_button_x = action_button_x + spec.MAIN_BUTTON_SIZE[0] + spec.PHASE_ONE_ACTION_BUTTON_GAP_X
        self.module_one_load_button = MainButton(
            self.module_one_midground_border,
            text='OPEN',
            command=self.load_project,
        )
        self.module_one_load_button.place(x=load_button_x, y=action_button_y)

    def _show_audio_settings_dialog(self) -> None:
        if self._is_build_locked():
            return
        popup = AudioSettingsDialog(
            self,
            icon_path=self._native_icon_path(),
            initial_sample_rate=self.session.project.sample_rate,
            initial_compression_quality=self.session.project.compression_quality,
            initial_reencode_existing_ogg=self.session.project.reencode_existing_ogg,
            check_icon_path=self._check_icon_path(),
        )
        result = popup.show()
        if result is None:
            return
        sample_rate, compression_quality, reencode_existing_ogg = result
        self.session.project.sample_rate = int(sample_rate)
        self.session.project.compression_quality = float(compression_quality)
        self.session.project.reencode_existing_ogg = bool(reencode_existing_ogg)
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
            check_icon_path=str(self._check_icon_path()),
            edit_icon_path=str(self._edit_icon_path()),
            ear_icon_path=str(self._ear_icon_path()),
            grab_icon_path=str(self._grab_icon_path()),
            table_check_icon_path=str(self._table_check_icon_path()),
            preview_audio_icon_path=str(self._preview_audio_icon_path()),
            resolve_live_preview_path=self._module_two_preview_path_for_row,
            resolve_media_strip_path=self._module_two_media_strip_path_for_row,
            bg_color=spec.MODULE_MIDGROUND_BG,
            on_row_selected=self._expand_module_two_media_row,
            selected_row_ids=self.module_two_selected_row_ids,
            on_background_selected=self._select_module_two_media_row,
            on_enabled_media_changed=self._set_module_two_media_enabled,
            on_name_committed=self._commit_module_two_media_name,
            on_side_selected=self._set_module_two_media_side,
            on_preview_mode_selected=self._set_module_two_preview_mode,
            on_cover_selected=self._select_module_two_media_cover,
            on_remove_row=self._remove_module_two_media_row,
            on_add_song=self._add_module_two_songs,
            on_remove_song=self._remove_module_two_selected_songs_or_last,
            selected_song_indices_by_key=self.module_two_song_selected_indices,
            on_song_selected=self._select_module_two_song,
            on_song_remove_requested=self._remove_module_two_song_via_row_click,
            on_song_sort_requested=self._sort_module_two_songs,
            on_song_drag_started=self._begin_module_two_song_drag,
            on_song_drag_moved=self._update_module_two_song_drag,
            on_song_drag_finished=self._finish_module_two_song_drag,
            on_row_drag_started=self._begin_module_two_row_drag,
            on_row_drag_moved=self._update_module_two_row_drag,
            on_row_drag_finished=self._finish_module_two_row_drag,
            dnd_type=DND_FILES,
            can_accept_song_drop=self._can_accept_song_drop,
            on_song_drop=self._on_module_two_song_drop,
        )
        self.module_two_row_list.pack(anchor='nw')
        self.module_two_scroll_area.refresh_scroll_region()
        self._schedule_responsive_layout()

    def _on_content_frame_configure(self, _event: tk.Event) -> None:
        self._schedule_responsive_layout()

    def _schedule_responsive_layout(self) -> None:
        if self._responsive_layout_after_id is not None:
            if self._responsive_finalize_after_id is not None:
                self.after_cancel(self._responsive_finalize_after_id)
            self._responsive_finalize_after_id = self.after(140, self._finalize_responsive_layout)
            return
        self._responsive_layout_after_id = self.after_idle(self._apply_live_responsive_layout)
        if self._responsive_finalize_after_id is not None:
            self.after_cancel(self._responsive_finalize_after_id)
        self._responsive_finalize_after_id = self.after(140, self._finalize_responsive_layout)

    def _apply_live_responsive_layout(self) -> None:
        self._set_live_resize_active(True)
        self._apply_responsive_layout(include_heavy=False)

    def _finalize_responsive_layout(self) -> None:
        self._responsive_finalize_after_id = None
        self._set_live_resize_active(False)
        self._apply_responsive_layout(include_heavy=True, force=True)

    def _set_live_resize_active(self, active: bool) -> None:
        if self._live_resize_active == active:
            return
        self._live_resize_active = active
        if active:
            if hasattr(self, 'module_two_row_list'):
                self.module_two_row_list.pack_forget()
            if hasattr(self, 'module_four_panel'):
                self.module_four_panel.place_forget()
            if hasattr(self, 'module_five_panel'):
                self.module_five_panel.place_forget()
            return
        if hasattr(self, 'module_two_row_list'):
            self.module_two_row_list.pack(anchor='nw')
        if hasattr(self, 'module_four_panel'):
            self.module_four_panel.place(x=0, y=0)
        if hasattr(self, 'module_five_panel'):
            self.module_five_panel.place(x=0, y=0)

    def _apply_responsive_layout(self, *, include_heavy: bool = True, force: bool = False) -> None:
        self._responsive_layout_after_id = None
        if not hasattr(self, 'content_frame'):
            return
        available_width = self.content_frame.winfo_width()
        if available_width <= 1:
            return
        if not force and available_width == self._responsive_content_width:
            return
        self._responsive_content_width = available_width

        base_top_width = (
            spec.MODULE_ONE_SIZE[0]
            + spec.MODULE_GAP_X
            + spec.MODULE_TWO_SIZE[0]
            + spec.MODULE_GAP_X
            + spec.MODULE_THREE_SIZE[0]
        )
        extra_width = max(0, available_width - base_top_width)

        module_two_width = spec.MODULE_TWO_SIZE[0] + extra_width
        module_two_midground_width = spec.MODULE_TWO_MIDGROUND_SIZE[0] + extra_width
        module_two_top_header_width = spec.MODULE_TWO_TOP_HEADER_SIZE[0] + extra_width
        module_two_scroll_area_width = spec.MODULE_TWO_SCROLL_AREA_SIZE[0] + extra_width
        module_two_scroll_viewport_width = spec.MODULE_TWO_SCROLL_VIEWPORT_SIZE[0] + extra_width
        media_row_list_width = spec.MEDIA_ROW_LIST_WIDTH + extra_width

        if self._responsive_last_widths.get('module_two_shell') != module_two_width:
            self.module_two_shell.resize(
                size=(module_two_width, spec.MODULE_TWO_SIZE[1]),
                midground_size=(module_two_midground_width, spec.MODULE_TWO_MIDGROUND_SIZE[1]),
            )
            self._responsive_last_widths['module_two_shell'] = module_two_width
        if self._responsive_last_widths.get('module_two_header') != module_two_top_header_width:
            self.module_two_top_header.resize(module_two_top_header_width)
            self.module_two_top_header.place_configure(width=module_two_top_header_width, height=spec.MODULE_TWO_TOP_HEADER_SIZE[1])
            self._responsive_last_widths['module_two_header'] = module_two_top_header_width
        if self._responsive_last_widths.get('module_two_scroll') != module_two_scroll_area_width:
            self.module_two_scroll_area.resize(
                size=(module_two_scroll_area_width, spec.MODULE_TWO_SCROLL_AREA_SIZE[1]),
                viewport_size=(module_two_scroll_viewport_width, spec.MODULE_TWO_SCROLL_VIEWPORT_SIZE[1]),
                scrollbar_size=spec.SCROLLBAR_TRACK_SIZE,
            )
            self.module_two_scroll_area.place_configure(
                x=0,
                y=spec.MODULE_TWO_TOP_HEADER_SIZE[1],
                width=module_two_scroll_area_width,
                height=spec.MODULE_TWO_SCROLL_AREA_SIZE[1],
            )
            self._responsive_last_widths['module_two_scroll'] = module_two_scroll_area_width
        if include_heavy and hasattr(self, 'module_two_row_list'):
            if self._responsive_last_widths.get('module_two_rows') != media_row_list_width:
                self.module_two_row_list.resize(media_row_list_width)
                self._responsive_last_widths['module_two_rows'] = media_row_list_width

        phase_three_width = spec.PHASE_THREE_COMBO_SIZE[0] + extra_width
        phase_three_midground_width = spec.PHASE_THREE_COMBO_MIDGROUND_SIZE[0] + extra_width
        phase_three_content_width = spec.PHASE_THREE_COMBO_CONTENT_AREA_SIZE[0] + extra_width
        module_four_width = spec.PHASE_THREE_MODULE_FOUR_SIZE[0] + extra_width
        module_five_x = (
            spec.PHASE_THREE_MODULE_FOUR_POS[0]
            + module_four_width
            + spec.PHASE_THREE_MODULE_FIVE_GAP_X
        )

        if self._responsive_last_widths.get('phase_three_shell') != phase_three_width:
            self.phase_three_combo_shell.resize(
                size=(phase_three_width, spec.PHASE_THREE_COMBO_SIZE[1]),
                midground_size=(phase_three_midground_width, spec.PHASE_THREE_COMBO_MIDGROUND_SIZE[1]),
                midground_offset=spec.PHASE_THREE_COMBO_MIDGROUND_OFFSET,
            )
            self._responsive_last_widths['phase_three_shell'] = phase_three_width
        if self._responsive_last_widths.get('phase_three_header') != phase_three_midground_width:
            self.phase_three_combo_header.resize(phase_three_midground_width)
            self.phase_three_combo_header.place_configure(x=0, y=0, width=phase_three_midground_width, height=spec.MODULE_ACTION_HEADER_HEIGHT)
            self._responsive_last_widths['phase_three_header'] = phase_three_midground_width
        if self._responsive_last_widths.get('phase_three_content') != phase_three_content_width:
            self.phase_three_combo_content_area.configure(width=phase_three_content_width, height=spec.PHASE_THREE_COMBO_CONTENT_AREA_SIZE[1])
            self.phase_three_combo_content_area.place_configure(
                x=0,
                y=spec.PHASE_THREE_COMBO_CONTENT_AREA_Y,
                width=phase_three_content_width,
                height=spec.PHASE_THREE_COMBO_CONTENT_AREA_SIZE[1],
            )
            self._responsive_last_widths['phase_three_content'] = phase_three_content_width
        if self._responsive_last_widths.get('module_four_width') != module_four_width:
            self.phase_three_module_four_foreground.resize((module_four_width, spec.PHASE_THREE_MODULE_FOUR_SIZE[1]))
            self.phase_three_module_four_foreground.place_configure(
                x=spec.PHASE_THREE_MODULE_FOUR_POS[0],
                y=spec.PHASE_THREE_MODULE_FOUR_POS[1],
                width=module_four_width,
                height=spec.PHASE_THREE_MODULE_FOUR_SIZE[1],
            )
            if include_heavy:
                self.module_four_panel.resize(module_four_width)
                self.module_four_panel.place_configure(x=0, y=0, width=module_four_width, height=spec.PHASE_THREE_MODULE_FOUR_SIZE[1])
            self.phase_three_module_five_foreground.place_configure(
                x=module_five_x,
                y=spec.PHASE_THREE_MODULE_FOUR_POS[1],
                width=spec.PHASE_THREE_MODULE_FIVE_SIZE[0],
                height=spec.PHASE_THREE_MODULE_FIVE_SIZE[1],
            )
            self._responsive_last_widths['module_four_width'] = module_four_width
        elif include_heavy and hasattr(self, 'module_four_panel'):
            self.module_four_panel.resize(module_four_width)
            self.module_four_panel.place_configure(x=0, y=0, width=module_four_width, height=spec.PHASE_THREE_MODULE_FOUR_SIZE[1])

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

    def _module_three_staged_custom_for_kind(self, kind: AppearanceKind) -> dict[str, str]:
        return self.module_three_staged_custom_images.setdefault(kind, {})

    def _module_three_custom_assets_for_kind(self, kind: AppearanceKind) -> list[dict[str, str]]:
        assets = self.session.project.custom_assets.setdefault(kind, [])
        changed = False
        for index, asset in enumerate(assets):
            if not asset.get('key'):
                asset['key'] = f'custom:{kind}:{uuid4().hex}'
                changed = True
            if not asset.get('label'):
                inventory_path = asset.get('inventory_full', '')
                label = Path(inventory_path).stem if inventory_path else f'Custom {index + 1}'
                asset['label'] = label
                changed = True
        if changed:
            self.on_project_change()
        return assets

    def _module_three_entries_for_kind(self, kind: AppearanceKind) -> list[AppearanceGridEntry]:
        return merge_appearance_grid_entries(
            kind,
            self.asset_catalog.get(kind, []),
            self._module_three_custom_assets_for_kind(kind),
        )

    def _pick_module_three_custom_image(self, kind: AppearanceKind, slot: str) -> None:
        staged = self._module_three_staged_custom_for_kind(kind)
        target_row = self._active_module_three_row()
        initial_path = staged.get(slot, '')
        if not initial_path and target_row is not None:
            selection = target_row.appearances[kind]
            if slot == 'inventory_full':
                initial_path = selection.inventory_full
            elif slot == 'world_full':
                initial_path = selection.world_full
            elif slot == 'inventory_empty':
                initial_path = selection.inventory_empty
            else:
                initial_path = selection.world_empty
        selected = fd.askopenfilename(
            title=f"Select {slot.replace('_', ' ').title()} Texture",
            filetypes=self._image_filetypes(),
            initialdir=self._initial_image_dir(initial_path),
            parent=self,
        )
        if not selected:
            return
        staged[slot] = selected
        self._refresh_module_three_appearance_selector()

    def _pick_module_three_custom_slot(self, kind: AppearanceKind, slot: str) -> None:
        if self._is_build_locked():
            return
        self._pick_module_three_custom_image(kind, slot)

    def _reset_module_three_custom_staged(self, kind: AppearanceKind, dual_mode: bool) -> None:
        if self._is_build_locked():
            return
        staged = self._module_three_staged_custom_for_kind(kind)
        if dual_mode:
            for key in ('inventory_full', 'world_full', 'inventory_empty', 'world_empty'):
                staged.pop(key, None)
        else:
            for key in ('inventory_full', 'world_full'):
                staged.pop(key, None)
        self._refresh_module_three_appearance_selector()

    def _commit_module_three_custom(self, kind: AppearanceKind, dual_mode: bool) -> None:
        if self._is_build_locked():
            return
        staged = self._module_three_staged_custom_for_kind(kind)
        if dual_mode:
            if not can_commit_dual_custom(staged):
                return
        elif not can_commit_single_custom(staged):
            return
        target_row = self._active_module_three_row()
        if target_row is None:
            return
        target_row.ensure_appearances()
        selection = target_row.appearances[kind]
        sprite_mode = 'dual' if dual_mode else 'single'
        custom_key = f'custom:{kind}:{uuid4().hex}'
        custom_record = {
            'key': custom_key,
            'label': Path(staged['inventory_full']).stem or 'Custom',
            'inventory_full': staged['inventory_full'],
            'world_full': staged['world_full'],
            'sprite_mode': sprite_mode,
        }
        if dual_mode:
            custom_record['inventory_empty'] = staged['inventory_empty']
            custom_record['world_empty'] = staged['world_empty']
        self.session.project.custom_assets.setdefault(kind, []).append(custom_record)
        apply_selection_from_grid_entry(
            selection,
            AppearanceGridEntry(
                key=custom_record['key'],
                label=custom_record['label'],
                inventory_path=custom_record['inventory_full'],
                world_path=custom_record['world_full'],
                sprite_mode=custom_record['sprite_mode'],
                kind=kind,
                is_custom=True,
                is_dual=dual_mode,
                inventory_empty_path=custom_record.get('inventory_empty', ''),
                world_empty_path=custom_record.get('world_empty', ''),
            ),
        )
        self._refresh_module_two_live_preview_for_row(target_row.row_id)
        self._reset_module_three_custom_staged(kind, dual_mode)
        self._refresh_module_three_appearance_selector()
        self.on_project_change()

    def _delete_module_three_custom_asset(self, kind: AppearanceKind, key: str) -> None:
        if self._is_build_locked():
            return
        assets = self._module_three_custom_assets_for_kind(kind)
        next_assets = [asset for asset in assets if asset.get('key') != key]
        if len(next_assets) == len(assets):
            return
        self.session.project.custom_assets[kind] = next_assets
        remaining_entries = self._module_three_entries_for_kind(kind)
        for row in self.session.project.media_rows:
            row.ensure_appearances()
            selection = row.appearances[kind]
            next_key = fallback_selected_asset_key_after_delete(
                remaining_entries,
                deleted_key=key,
                selected_key=selection.selected_asset_key,
            )
            if next_key == selection.selected_asset_key:
                continue
            if not next_key:
                selection.selected_asset_key = ''
                selection.source = 'default'
                selection.inventory_full = ''
                selection.world_full = ''
                selection.inventory_empty = ''
                selection.world_empty = ''
                selection.sprite_mode = 'single'
                continue
            next_entry = next((entry for entry in remaining_entries if entry.key == next_key), None)
            if next_entry is not None:
                apply_selection_from_grid_entry(selection, next_entry)
                self._refresh_module_two_live_preview_for_row(row.row_id)
        self._refresh_module_three_appearance_selector()
        self.on_project_change()

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
                if getattr(widget, '_row_id', None) == row_id and getattr(widget, '_row_expanded', False)
            ),
            None,
        )

    def _current_expanded_row_id(self) -> int | None:
        if self._build_locked and self._locked_module_two_browse_row_id is not None:
            return self._locked_module_two_browse_row_id
        expanded = next((row.row_id for row in self.session.project.media_rows if row.expanded), None)
        return expanded

    def _active_module_three_row(self):
        expanded = next((row for row in self.session.project.media_rows if row.expanded), None)
        if expanded is not None:
            return expanded
        return self.session.project.media_rows[0] if self.session.project.media_rows else None

    def _refresh_module_three_appearance_selector(self) -> None:
        if not hasattr(self, 'module_three_appearance_selector'):
            return
        self.module_three_appearance_selector.set_active_row(self._active_module_three_row())

    def _refresh_module_two_live_preview_for_row(self, row_id: int) -> None:
        expanded_widget = self._expanded_row_widget(row_id)
        if expanded_widget is not None:
            expanded_widget.refresh_live_preview()
        if hasattr(self, 'module_two_row_list'):
            self.module_two_row_list.refresh_media_type_strips_for_row(row_id)

    def _cancel_module_two_song_drag(self) -> None:
        if self._module_two_song_drag_session is None:
            return
        row_id = int(self._module_two_song_drag_session.get('row_id', -1))
        expanded_widget = self._expanded_row_widget(row_id)
        if expanded_widget is not None:
            expanded_widget.cancel_song_drag()
        self._module_two_song_drag_session = None

    def _cancel_module_two_row_drag(self) -> None:
        if self._module_two_row_drag_session is None:
            return
        if hasattr(self, 'module_two_row_list'):
            self.module_two_row_list.cancel_row_drag()
        self._module_two_row_drag_session = None

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
        if self._is_build_locked():
            return
        selected = fd.askopenfilename(
            title='Select Workshop Poster Image',
            filetypes=self._image_filetypes(),
            initialdir=self._initial_image_dir(self.session.project.workshop_poster_path),
            parent=self,
        )
        if not selected:
            return
        self.session.project.workshop_poster_path = selected
        self._refresh_module_one_poster_preview()
        self.on_project_change()

    def _select_module_two_media_cover(self, row_id: int) -> None:
        if self._is_build_locked():
            return
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
        if self._is_build_locked():
            return
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
        if self._is_build_locked():
            return
        self._add_module_two_songs_from_paths(row_id, paths)

    def _add_module_two_songs_from_paths(self, row_id: int, paths: list[str]) -> None:
        if self._is_build_locked():
            return
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
        self._remove_module_two_songs(row_id, fallback_to_last=False)

    def _remove_module_two_selected_songs_or_last(self, row_id: int) -> None:
        self._remove_module_two_songs(row_id, fallback_to_last=True)

    def _remove_module_two_songs(self, row_id: int, *, fallback_to_last: bool) -> None:
        if self._is_build_locked():
            return
        self._cancel_module_two_song_drag()
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return
        key = (row_id, target_row.selected_side)
        selected_indices = self._module_two_song_selection_for_row(row_id, target_row.selected_side)
        tracks = target_row.tracks_a if target_row.selected_side == 'A' else target_row.tracks_b
        removal_indices = resolve_song_removal_indices(
            selected_indices,
            track_count=len(tracks),
            fallback_to_last=fallback_to_last,
        )
        if not removal_indices:
            return
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

    def _remove_module_two_song_via_row_click(self, row_id: int, track_index: int) -> None:
        if self._is_build_locked():
            return
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
        if self._is_build_locked():
            return
        self._cancel_module_two_song_drag()
        self._cancel_module_two_row_drag()
        for row in self.session.project.media_rows:
            row.expanded = False

        new_row_id = self.session.add_media_row()
        for row in self.session.project.media_rows:
            row.expanded = row.row_id == new_row_id

        self._build_module_two_row_list()
        self.module_two_content_viewport.yview_moveto(1.0)
        self.module_two_scroll_area.refresh_scroll_region()
        self.module_two_content_viewport.yview_moveto(1.0)
        self._refresh_module_three_appearance_selector()
        self.on_project_change()

    def _remove_module_two_media_rows(self) -> None:
        if self._is_build_locked():
            return
        self._remove_module_two_media_row_set(
            set(self.module_two_selected_row_ids) if self.module_two_selected_row_ids else None
        )

    def _remove_module_two_media_row(self, row_id: int) -> None:
        if self._is_build_locked():
            return
        self._remove_module_two_media_row_set({row_id})

    def _remove_module_two_media_row_set(self, row_ids_to_remove: set[int] | None) -> None:
        if self._is_build_locked():
            return
        self._cancel_module_two_song_drag()
        self._cancel_module_two_row_drag()
        if row_ids_to_remove:
            target_row_ids = set(row_ids_to_remove)
        elif self.session.project.media_rows:
            target_row_ids = {self.session.project.media_rows[-1].row_id}
        else:
            return

        current_view = self.module_two_content_viewport.yview()
        self.session.remove_media_rows(target_row_ids)
        self.module_two_selected_row_ids = {
            row_id for row_id in self.module_two_selected_row_ids if row_id not in target_row_ids
        }
        self.module_two_selection_anchor_row_id = None
        self.module_two_song_selected_indices = {
            key: value
            for key, value in self.module_two_song_selected_indices.items()
            if key[0] not in target_row_ids
        }
        self.module_two_song_selection_anchor_indices = {
            key: value
            for key, value in self.module_two_song_selection_anchor_indices.items()
            if key[0] not in target_row_ids
        }
        self._build_module_two_row_list()
        self.module_two_content_viewport.yview_moveto(current_view[0])
        self._refresh_module_three_appearance_selector()
        self.on_project_change()

    def _set_module_two_media_enabled(self, row_id: int, kind: MediaKind, enabled: bool) -> None:
        if self._is_build_locked():
            return
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
            self.module_two_row_list.refresh_media_type_strips_for_row(row_id)
        self._refresh_module_three_appearance_selector()
        self.on_project_change()

    def _commit_module_two_media_name(self, row_id: int, value: str) -> None:
        if self._is_build_locked():
            return
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
        locked = self._is_build_locked()
        self._cancel_module_two_song_drag()
        self._cancel_module_two_row_drag()
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
        if not locked:
            self.on_project_change()

    def _sort_module_two_songs(self, row_id: int, column: SongSortColumn) -> None:
        if self._is_build_locked():
            return
        self._cancel_module_two_song_drag()
        self._cancel_module_two_row_drag()
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return
        side = target_row.selected_side
        sort_state = self.session.sort_tracks_in_media_row(row_id, side, column)
        if sort_state is None:
            return
        key = (row_id, side)
        self.module_two_song_selected_indices[key] = set()
        self.module_two_song_selection_anchor_indices[key] = None
        expanded_widget = self._expanded_row_widget(row_id)
        if expanded_widget is not None:
            expanded_widget.refresh_song_table()
            expanded_widget.set_song_selection_state(set())
        self.on_project_change()

    def _set_module_two_preview_mode(self, row_id: int, mode: str) -> None:
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None or mode not in {'inventory', 'world'}:
            return
        if target_row.preview_mode == mode:
            return
        target_row.preview_mode = mode
        self._refresh_module_two_live_preview_for_row(row_id)
        self._refresh_module_three_appearance_selector()
        self.on_project_change()

    def _expand_module_two_media_row(self, row_id: int) -> None:
        if self._is_build_locked():
            self._browse_locked_module_two_media_row(row_id)
            return
        self._cancel_module_two_song_drag()
        self._cancel_module_two_row_drag()
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return

        current_view = self.module_two_content_viewport.yview()
        self.module_two_selected_row_ids.clear()
        self.module_two_selection_anchor_row_id = None
        if target_row.expanded:
            expanded_row_id: int | None = None
            target_row.expanded = False
        else:
            for row in self.session.project.media_rows:
                row.expanded = row.row_id == row_id
            expanded_row_id = row_id

        self.module_two_row_list.set_expanded_row(expanded_row_id)
        self.module_two_scroll_area.refresh_scroll_region()
        self.module_two_content_viewport.yview_moveto(current_view[0])
        self._refresh_module_three_appearance_selector()
        self.on_project_change()

    def _browse_locked_module_two_media_row(self, row_id: int) -> None:
        if not hasattr(self, 'module_two_row_list'):
            return
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return
        current_view = self.module_two_content_viewport.yview()
        next_row_id = None if self._locked_module_two_browse_row_id == row_id else row_id
        self._locked_module_two_browse_row_id = next_row_id
        self.module_two_row_list.set_browse_expanded_row(next_row_id)
        self.module_two_scroll_area.refresh_scroll_region()
        self.module_two_content_viewport.yview_moveto(current_view[0])

    def _select_module_two_media_row(self, row_id: int, modifiers: RowSelectionModifiers) -> None:
        if self._is_build_locked():
            return
        self._cancel_module_two_row_drag()
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

    def _begin_module_two_row_drag(self, row_id: int, x_root: int, y_root: int) -> None:
        if self._is_build_locked():
            return
        if self._module_two_row_drag_session is not None or not hasattr(self, 'module_two_row_list'):
            return
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None or target_row.expanded:
            return
        if row_id in self.module_two_selected_row_ids and len(self.module_two_selected_row_ids) > 1:
            dragged_row_ids = set(self.module_two_selected_row_ids)
        else:
            dragged_row_ids = {row_id}
            self.module_two_selected_row_ids = set(dragged_row_ids)
            self.module_two_selection_anchor_row_id = row_id
            self.module_two_row_list.set_selection_state(self.module_two_selected_row_ids)
        self._module_two_row_drag_session = {
            'anchor_row_id': row_id,
            'dragged_row_ids': dragged_row_ids,
        }
        self.module_two_row_list.begin_row_drag(dragged_row_ids, row_id, x_root, y_root)

    def _update_module_two_row_drag(self, row_id: int, x_root: int, y_root: int) -> None:
        if self._is_build_locked():
            return
        if self._module_two_row_drag_session is None or not hasattr(self, 'module_two_row_list'):
            return
        if int(self._module_two_row_drag_session.get('anchor_row_id', -1)) != row_id:
            return
        self.module_two_row_list.update_row_drag(x_root, y_root)

    def _finish_module_two_row_drag(self, row_id: int, x_root: int, y_root: int) -> None:
        if self._is_build_locked():
            return
        if self._module_two_row_drag_session is None or not hasattr(self, 'module_two_row_list'):
            return
        if int(self._module_two_row_drag_session.get('anchor_row_id', -1)) != row_id:
            return
        current_view = self.module_two_content_viewport.yview()
        insertion_index = self.module_two_row_list.finish_row_drag(x_root, y_root)
        drag_session = self._module_two_row_drag_session
        self._module_two_row_drag_session = None
        if insertion_index is None:
            return
        dragged_row_ids = set(drag_session.get('dragged_row_ids', set()))
        moved_row_ids = self.session.move_media_rows(dragged_row_ids, insertion_index)
        if not moved_row_ids:
            return
        self.module_two_selected_row_ids = set(moved_row_ids)
        self.module_two_selection_anchor_row_id = moved_row_ids[0] if moved_row_ids else None
        self.module_two_row_list.reorder_rows(self.session.project.media_rows)
        self.module_two_row_list.set_selection_state(self.module_two_selected_row_ids)
        self.module_two_scroll_area.refresh_scroll_region()
        self.module_two_content_viewport.yview_moveto(current_view[0])
        self._refresh_module_three_appearance_selector()
        self.on_project_change()

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
        if self._is_build_locked():
            return
        self._cancel_module_two_song_drag()
        self._cancel_module_two_row_drag()
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
        if self._is_build_locked():
            return
        self._cancel_module_two_row_drag()
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
        if self._is_build_locked():
            return
        if self._module_two_song_drag_session is None:
            return
        if int(self._module_two_song_drag_session.get('row_id', -1)) != row_id:
            return
        expanded_widget = self._expanded_row_widget(row_id)
        if expanded_widget is not None:
            expanded_widget.update_song_drag(x_root, y_root)

    def _finish_module_two_song_drag(self, row_id: int, x_root: int, y_root: int) -> None:
        if self._is_build_locked():
            return
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
        target_row = next((row for row in self.session.project.media_rows if row.row_id == row_id), None)
        if target_row is None:
            return
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
        self._commit_phase_one_project_state()
        self._refresh_module_one_poster_preview()
        if hasattr(self, 'module_two_row_list'):
            self.module_two_row_list.refresh_collapsed_details()
        if hasattr(self, 'build_summary'):
            self.build_summary.refresh()
        self.session_store.save(self.session.project, self.session.current_path)

    def refresh_all(self) -> None:
        self._apply_default_asset_selections()
        self._refresh_module_one_poster_preview()
        self._refresh_module_three_appearance_selector()
        if hasattr(self, 'mod_setup'):
            self.mod_setup.refresh()
        if hasattr(self, 'media_creation'):
            self.media_creation.refresh()
        if hasattr(self, 'appearance'):
            self.appearance.refresh()
        if hasattr(self, 'build_export'):
            self.build_export.refresh(self.build_log, self.preview_entries)
        if hasattr(self, 'module_two_row_list'):
            self.module_two_row_list.refresh_media_type_strips()
            self.module_two_row_list.refresh_collapsed_details()
        if hasattr(self, 'module_four_panel'):
            self.module_four_panel.queue_scroll.refresh_scroll_region()
            self.module_four_panel.log_scroll.refresh_scroll_region()
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
        if self._is_build_locked():
            return
        if not self._confirm_reset_to_defaults('Start New Project', 'YES'):
            return
        self._reset_project_to_defaults()

    def reset_project_to_defaults(self) -> None:
        if self._is_build_locked():
            return
        if not self._confirm_reset_to_defaults('Reset Project', 'RESET'):
            return
        self._reset_project_to_defaults()

    def _reset_project_to_defaults(self) -> None:
        self._cancel_module_two_song_drag()
        self._cancel_module_two_row_drag()
        self.session.reset()
        self._restore_unsaved_phase_two_default()
        self._sync_phase_one_ui_from_project()
        self.module_three_staged_custom_images.clear()
        self.module_two_selected_row_ids.clear()
        self.module_two_selection_anchor_row_id = None
        self.module_two_song_selected_indices.clear()
        self.module_two_song_selection_anchor_indices.clear()
        self._last_export_output_path = ''
        self.build_log = []
        self.preview_entries = []
        if hasattr(self, 'module_four_panel'):
            self.module_four_panel.reset_current_run()
        if hasattr(self, 'module_five_panel'):
            self.module_five_panel.reset_preview_rows()
        if hasattr(self, 'module_six_panel'):
            self.module_six_panel.reset()
        if hasattr(self, 'module_two_row_list'):
            self._build_module_two_row_list()
        self._refresh_module_three_appearance_selector()
        self.refresh_all()
        self.on_project_change()

    def _confirm_reset_to_defaults(self, title: str, accept_text: str) -> bool:
        dialog = ConfirmDialog(
            self,
            icon_path=self._native_icon_path(),
            title=title,
            label_text='Are you sure you want to reset to default? Any unsaved changes will be lost.',
            accept_text=accept_text,
            cancel_text='CANCEL',
        )
        return dialog.show()

    def reset_phase_one_fields(self) -> None:
        if hasattr(self, 'mod_setup'):
            self.mod_setup.reset_fields()

    def save_project(self) -> None:
        if self._is_build_locked():
            return
        self._commit_phase_one_project_state()
        if self.session.current_path:
            self.project_store.save(self.session.project, Path(self.session.current_path))
            self.recent_store.push(Path(self.session.current_path))
            self.session_store.save(self.session.project, self.session.current_path)
            self._append_project_saved_log(self.session.current_path)
            return
        self.save_project_as()

    def save_project_as(self) -> None:
        if self._is_build_locked():
            return
        selected = fd.asksaveasfilename(defaultextension='.nmbproj.json', filetypes=[('New Music Builder Project', '*.nmbproj.json')])
        if not selected:
            return
        self.session.current_path = selected
        self.save_project()

    def _append_project_saved_log(self, project_path: str) -> None:
        if not project_path or not hasattr(self, 'module_four_panel'):
            return
        self.module_four_panel.append_log_line(build_project_saved_log_line(project_path))

    def load_project(self) -> None:
        if self._is_build_locked():
            return
        selected = fd.askopenfilename(filetypes=[('New Music Builder Project', '*.nmbproj.json'), ('JSON', '*.json')])
        if selected:
            self._load_path(Path(selected))

    def _load_path(self, path: Path) -> None:
        self._cancel_module_two_song_drag()
        self._cancel_module_two_row_drag()
        try:
            project = self.project_store.load(path)
        except Exception as exc:
            LOGGER.exception("Failed to load project from %s: %s", path, exc)
            messagebox.showerror('Load Project Failed', f'Could not load project.\n\n{path}\n\n{exc}')
            return
        self.session.project = project
        self.session.current_path = str(path)
        self._sync_phase_one_ui_from_project()
        self.recent_store.push(path)
        self.module_three_staged_custom_images.clear()
        self.module_two_selected_row_ids.clear()
        self.module_two_selection_anchor_row_id = None
        self.module_two_song_selected_indices.clear()
        self.module_two_song_selection_anchor_indices.clear()
        self._last_export_output_path = ''
        if hasattr(self, 'module_four_panel'):
            self.module_four_panel.reset_current_run()
        if hasattr(self, 'module_five_panel'):
            self.module_five_panel.reset_preview_rows()
        if hasattr(self, 'module_six_panel'):
            self.module_six_panel.reset()
        self._build_module_two_row_list()
        self._refresh_module_three_appearance_selector()
        self.refresh_all()
        self.session_store.save(self.session.project, self.session.current_path)

    def run_build_preview(self) -> None:
        overall_started = time.perf_counter()
        LOGGER.info(
            "[run=%s] run_build_preview start thread=%s",
            self._active_build_run_id or "-",
            threading.current_thread().name,
        )
        if self._is_build_locked():
            LOGGER.info("[run=%s] run_build_preview redirected to abort", self._active_build_run_id or "-")
            self._request_abort_export()
            return
        run_id = uuid4().hex[:8]
        self._active_build_run_id = run_id
        step_started = time.perf_counter()
        self._sync_phase_one_project_state()
        LOGGER.info("[run=%s] phase-one sync complete duration_ms=%.1f", run_id, (time.perf_counter() - step_started) * 1000.0)
        step_started = time.perf_counter()
        project_snapshot = deepcopy(self.session.project)
        LOGGER.info("[run=%s] project snapshot complete duration_ms=%.1f", run_id, (time.perf_counter() - step_started) * 1000.0)
        step_started = time.perf_counter()
        plan = build_export_plan(project_snapshot, self.asset_catalog)
        LOGGER.info("[run=%s] build_export_plan complete duration_ms=%.1f", run_id, (time.perf_counter() - step_started) * 1000.0)
        step_started = time.perf_counter()
        validation_errors = validate_export_request(project_snapshot, plan)
        LOGGER.info(
            "[run=%s] validate_export_request complete errors=%s duration_ms=%.1f",
            run_id,
            len(validation_errors),
            (time.perf_counter() - step_started) * 1000.0,
        )
        self._active_preview_rows_by_side = {}
        self._active_successful_sides = []
        scenario_output_path = ''
        if not validation_errors:
            step_started = time.perf_counter()
            targets = resolve_export_target(
                plan,
                project_snapshot.workshop_output_folder,
                mod_name=project_snapshot.mod_name,
                mod_id=project_snapshot.mod_id,
            )
            LOGGER.info(
                "[run=%s] resolve_export_target complete root=%s duration_ms=%.1f",
                run_id,
                targets.root,
                (time.perf_counter() - step_started) * 1000.0,
            )
            scenario_output_path = targets.root
        step_started = time.perf_counter()
        scenario = build_preview_scenario(plan, scenario_output_path)
        LOGGER.info(
            "[run=%s] build_preview_scenario complete rows=%s duration_ms=%.1f",
            run_id,
            len(scenario.preview_rows),
            (time.perf_counter() - step_started) * 1000.0,
        )
        self._active_preview_rows_by_side = {
            (row.row_id, row.side): row
            for row in scenario.preview_rows
        }
        self._active_successful_sides_by_row = {}
        self._active_emitted_preview_rows.clear()

        LOGGER.info("[run=%s] resetting module four/five current run state", run_id)
        if hasattr(self, 'module_four_panel'):
            self.module_four_panel.archive_current_run()
            self.module_four_panel.reset_current_run()
        if hasattr(self, 'module_five_panel'):
            self.module_five_panel.reset_preview_rows()

        if validation_errors:
            LOGGER.info("[run=%s] validation blocked export", run_id)
            stats = build_scaffold_stats(
                plan,
                ScaffoldResult(mod_size_text='0 KB', errors=validation_errors),
            )
            log_lines = build_validation_log_lines(validation_errors)
            self._last_export_output_path = ''
            if hasattr(self, 'module_four_panel'):
                self.module_four_panel.set_output_path('')
                self.module_four_panel.set_log_lines(log_lines)
            if hasattr(self, 'module_six_panel'):
                self.module_six_panel.set_stats(stats)
            self.build_log = [self._module_four_log_line_text(line) for line in log_lines]
            self.preview_entries = []
            if hasattr(self, 'build_summary'):
                self.build_summary.refresh()
            self._active_build_run_id = None
            return

        output_root = Path(targets.root)
        LOGGER.info("[run=%s] export output_root=%s exists=%s", run_id, output_root, output_root.exists())
        if output_root.exists() and not self._confirm_overwrite_export_root(output_root):
            LOGGER.info("[run=%s] overwrite cancelled output_root=%s", run_id, output_root)
            cancelled_line = ExportLogLine(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                prefix_text="Build cancelled.",
                trailing_text="Existing export was not overwritten.",
                color_role="error",
            )
            cancelled_stats = BuildSummaryStats(
                media_rows=0,
                exported_media_rows=0,
                total_sides=0,
                total_songs=0,
                built_songs=0,
                planned_media_rows=plan.stats.planned_media_rows,
                planned_total_sides=plan.stats.planned_total_sides,
                planned_total_songs=plan.stats.planned_total_songs,
                converted=0,
                mod_size_text="0 KB",
                errors=1,
            )
            self._last_export_output_path = ''
            if hasattr(self, 'module_four_panel'):
                self.module_four_panel.set_output_path(str(output_root))
                self.module_four_panel.set_log_lines([cancelled_line])
            if hasattr(self, 'module_six_panel'):
                self.module_six_panel.set_stats(cancelled_stats)
            self.build_log = [self._module_four_log_line_text(cancelled_line)]
            self.preview_entries = []
            if hasattr(self, 'build_summary'):
                self.build_summary.refresh()
            self._active_build_run_id = None
            return

        self._build_abort_requested = False
        self._build_abort_event = threading.Event()
        self._active_build_final_targets = targets
        LOGGER.info("[run=%s] setting initial module four state", run_id)
        if hasattr(self, 'module_four_panel'):
            self.module_four_panel.set_output_path(targets.root)
            self.module_four_panel.set_log_lines(
                [
                    ExportLogLine(
                        timestamp=datetime.now().strftime("%H:%M:%S"),
                        prefix_text="Preparing export...",
                        subject_text=str(output_root),
                        color_role="queued",
                    ),
                ]
            )
        self.update_idletasks()
        LOGGER.info("[run=%s] initial module four state rendered", run_id)
        self._set_build_locked(True)
        self.build_log = []
        self.preview_entries = []

        LOGGER.info("[run=%s] starting worker-backed export run", run_id)
        self._start_audio_build_run(
            plan=plan,
            project_snapshot=project_snapshot,
            final_targets=targets,
            run_id=run_id,
        )
        LOGGER.info(
            "[run=%s] run_build_preview end duration_ms=%.1f thread=%s",
            run_id,
            (time.perf_counter() - overall_started) * 1000.0,
            threading.current_thread().name,
        )

    def reset_transient_state(self) -> None:
        self._last_export_output_path = ''
        self.build_log = []
        self.preview_entries = []
        if hasattr(self, 'module_four_panel'):
            self.module_four_panel.reset_current_run()
        if hasattr(self, 'module_five_panel'):
            self.module_five_panel.reset_preview_rows()
        if hasattr(self, 'module_six_panel'):
            self.module_six_panel.reset()
        if hasattr(self, 'build_export'):
            self.build_export.refresh(self.build_log, self.preview_entries)

    def _confirm_overwrite_export_root(self, output_root: Path) -> bool:
        dialog = ConfirmDialog(
            self,
            icon_path=self._native_icon_path(),
            title='Overwrite Existing Mod',
            label_text='This build will overwrite an existing mod. Proceed?',
            accept_text='YES',
            cancel_text='CANCEL',
        )
        return dialog.show()

    def _start_audio_build_run(
        self,
        *,
        plan,
        project_snapshot,
        final_targets: ExportTargetPaths,
        run_id: str,
    ) -> None:
        LOGGER.info("[run=%s] start_audio_build_run root=%s", run_id, final_targets.root)
        self._build_event_queue = queue.Queue()
        self._active_build_thread = threading.Thread(
            target=self._run_audio_build_worker,
            kwargs={
                "project_snapshot": project_snapshot,
                "plan": plan,
                "final_targets": final_targets,
                "run_id": run_id,
            },
            daemon=True,
            name='nmb-build-worker',
        )
        self._active_build_thread.start()
        LOGGER.info("[run=%s] build worker started ident=%s", run_id, self._active_build_thread.ident)
        self._schedule_build_event_poll(plan, run_id)

    def _run_audio_build_worker(
        self,
        *,
        project_snapshot,
        plan,
        final_targets: ExportTargetPaths,
        run_id: str,
    ) -> None:
        assert self._build_event_queue is not None
        LOGGER.info("[run=%s] build worker entry root=%s thread=%s", run_id, final_targets.root, threading.current_thread().name)
        try:
            result = run_staged_export(
                project_snapshot,
                plan,
                final_targets,
                asset_catalog=self.asset_catalog,
                cache_root=project_snapshot.ogg_output_folder,
                emit=lambda event: self._build_event_queue.put(("event", event)),
                cancel_requested=self._build_abort_pending,
                run_id=run_id,
            )
            LOGGER.info(
                "[run=%s] build worker result aborted=%s fatal_error=%s errors=%s built_songs=%s",
                run_id,
                result.aborted,
                bool(result.fatal_error),
                len(result.errors),
                result.built_song_count,
            )
            self._build_event_queue.put(("result", result))
        except Exception as exc:
            LOGGER.exception("[run=%s] build worker fatal exception: %s", run_id, exc)
            self._build_event_queue.put(("fatal", (final_targets.root, str(exc))))

    def _schedule_build_event_poll(self, plan, run_id: str) -> None:
        if self._build_poll_after_id is not None:
            self.after_cancel(self._build_poll_after_id)
        self._build_poll_after_id = self.after(16, lambda: self._poll_build_events(plan, run_id))

    def _poll_build_events(self, plan, run_id: str) -> None:
        if self._build_event_queue is None:
            self._build_poll_after_id = None
            return
        batch = self._build_event_pump.drain(self._build_event_queue)
        keep_polling = True
        for kind, payload in batch.items:
            if kind == "event":
                self._handle_audio_run_event(payload)
            elif kind == "result":
                self._finalize_audio_run(plan, payload)
                keep_polling = False
            elif kind == "fatal":
                output_root, error_message = payload
                self._finalize_audio_run_failure(plan, str(output_root), str(error_message))
                keep_polling = False
        if keep_polling:
            self._build_poll_after_id = self.after(16, lambda: self._poll_build_events(plan, run_id))
        else:
            self._build_poll_after_id = None
            self._build_event_queue = None
            self._active_build_thread = None

    def _handle_audio_run_event(self, event: AudioRunEvent) -> None:
        if not hasattr(self, 'module_four_panel'):
            return
        if event.kind == "run_preparing":
            line = ExportLogLine(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                prefix_text="Preparing export...",
                trailing_text=event.message,
                color_role="queued",
            )
            if self.module_four_panel.state.current_run_log_lines:
                self.module_four_panel.update_active_log_line(line)
            else:
                self.module_four_panel.append_log_line(line)
            return
        if event.kind == "scaffold_started":
            self.module_four_panel.append_log_line(
                ExportLogLine(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    prefix_text="Starting scaffold:",
                    trailing_text=event.message,
                    color_role="queued",
                )
            )
            return
        if event.kind == "scaffold_completed":
            self.module_four_panel.append_log_line(
                ExportLogLine(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    prefix_text="Export scaffold complete.",
                    trailing_text=event.message,
                    size_text=event.size_text,
                    color_role="done",
                )
            )
            return
        if event.kind == "run_aborted":
            abort_detail = "" if event.message.strip() == "Build aborted by user." else event.message
            self.module_four_panel.append_log_line(
                ExportLogLine(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    prefix_text="Build aborted by user.",
                    trailing_text=abort_detail,
                    color_role="error",
                )
            )
            return
        if event.kind == "run_failed":
            self.module_four_panel.append_log_line(
                ExportLogLine(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    prefix_text="Build failed.",
                    trailing_text=event.message,
                    color_role="error",
                )
            )
            return
        key = (event.row_id, event.side)
        if event.kind == "side_started":
            label = self._active_preview_rows_by_side.get(key)
            display_label = label.inventory_cell.label_text.replace(f" ({event.side}-Side)", f"\n{event.side}-SIDE") if label is not None else f"Row {event.row_id}\n{event.side}-SIDE"
            self.module_four_panel.append_queue_group(
                ConversionSideGroup(row_id=event.row_id, side=event.side, display_label=display_label, songs=[])
            )
        elif event.kind == "song_started":
            self.module_four_panel.append_song_to_group(
                event.row_id,
                event.side,
                ConversionSongProgress(
                    song_label=event.display_label,
                    queue_index=event.track_number or ((event.song_index or 0) + 1),
                    percent=0,
                    status="converting",
                    size_label="",
                ),
            )
        elif event.kind in {"song_progress", "song_succeeded", "song_failed"} and event.song_index is not None:
            status = "converting"
            if event.kind == "song_succeeded":
                status = "done"
            elif event.kind == "song_failed":
                status = "failed"
            self.module_four_panel.update_song_progress(
                event.row_id,
                event.side,
                event.song_index,
                event.percent,
                status,
                event.size_text,
            )

        if event.kind == "song_started":
            self.module_four_panel.append_log_line(
                ExportLogLine(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    prefix_text="Starting song:",
                    subject_text=event.display_label,
                    color_role="queued",
                )
            )
        elif event.kind == "song_progress":
            self.module_four_panel.update_active_log_line(
                ExportLogLine(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    prefix_text="Converting:",
                    subject_text=event.display_label,
                    trailing_text=f"{event.percent}%",
                    color_role="converting",
                )
            )
        elif event.kind == "song_succeeded":
            self._active_successful_sides_by_row.setdefault(event.row_id, set()).add(event.side)
            self._sync_converted_song_ogg_link(event)
            self.module_four_panel.finalize_active_log_line(
                ExportLogLine(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    prefix_text="Exported:",
                    subject_text=event.display_label,
                    size_text=event.size_text,
                    color_role="done",
                )
            )
        elif event.kind == "song_failed":
            self.module_four_panel.finalize_active_log_line(
                ExportLogLine(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    prefix_text="Failed:",
                    subject_text=event.display_label,
                    trailing_text=event.message,
                    color_role="error",
                )
            )
        elif event.kind == "side_completed":
            self._mark_preview_row_ready(event.row_id, event.side)

    def _sync_converted_song_ogg_link(self, event: AudioRunEvent) -> None:
        if event.song_index is None or not event.cached_ogg_path.strip():
            return
        target_row = next((row for row in self.session.project.media_rows if row.row_id == event.row_id), None)
        if target_row is None:
            return
        tracks = target_row.tracks_a if event.side == "A" else target_row.tracks_b
        if event.song_index < 0 or event.song_index >= len(tracks):
            return
        track = tracks[event.song_index]
        track.cached_ogg_path = event.cached_ogg_path
        if track.conversion_status != "source_ogg":
            track.conversion_status = "cached_ogg"
        expanded_widget = self._expanded_row_widget(event.row_id)
        if expanded_widget is None or target_row.selected_side != event.side:
            return
        expanded_widget.refresh_song_table()
        expanded_widget.set_song_selection_state(self._module_two_song_selection_for_row(event.row_id, event.side))

    def _mark_preview_row_ready(self, row_id: int, side: str) -> None:
        preview_key = (row_id, side)
        if preview_key in self._active_emitted_preview_rows:
            return
        successful_sides = self._active_successful_sides_by_row.get(row_id, set())
        if side not in successful_sides or not hasattr(self, 'module_five_panel'):
            return
        preview_row = self._active_preview_rows_by_side.get(preview_key)
        if preview_row is None:
            return
        self.module_five_panel.append_preview_row(preview_row)
        self._active_emitted_preview_rows.add(preview_key)

    def _finalize_audio_run(self, plan, result: AudioRunResult) -> None:
        LOGGER.info(
            "[run=%s] finalize_audio_run aborted=%s fatal_error=%s errors=%s built_songs=%s",
            self._active_build_run_id or "-",
            result.aborted,
            bool(result.fatal_error),
            len(result.errors),
            result.built_song_count,
        )
        final_targets = self._active_build_final_targets
        if result.aborted:
            output_path = Path(final_targets.root) if final_targets is not None else Path(result.output_path)
            self._last_export_output_path = str(output_path) if output_path.exists() else ''
            stats = BuildSummaryStats(
                media_rows=0,
                exported_media_rows=0,
                total_sides=0,
                total_songs=0,
                built_songs=0,
                planned_media_rows=plan.stats.planned_media_rows,
                planned_total_sides=plan.stats.planned_total_sides,
                planned_total_songs=plan.stats.planned_total_songs,
                converted=result.converted_count,
                mod_size_text=self._directory_size_text(output_path),
                errors=max(1, len(result.errors) + 1),
            )
            if hasattr(self, 'module_six_panel'):
                self.module_six_panel.set_stats(stats)
            self._snapshot_current_build_log()
            self.preview_entries = []
            self._refresh_build_summary()
            self._clear_active_build_run_state()
            return
        if result.fatal_error:
            output_path = Path(final_targets.root) if final_targets is not None else Path(result.output_path)
            self._last_export_output_path = str(output_path) if output_path.exists() else ''
            stats = BuildSummaryStats(
                media_rows=0,
                exported_media_rows=0,
                total_sides=0,
                total_songs=0,
                built_songs=0,
                planned_media_rows=plan.stats.planned_media_rows,
                planned_total_sides=plan.stats.planned_total_sides,
                planned_total_songs=plan.stats.planned_total_songs,
                converted=result.converted_count,
                mod_size_text=result.mod_size_text or self._directory_size_text(output_path),
                errors=max(1, len(result.errors) or 1),
            )
            if hasattr(self, 'module_six_panel'):
                self.module_six_panel.set_stats(stats)
            self._snapshot_current_build_log()
            self.preview_entries = []
            self._refresh_build_summary()
            self._clear_active_build_run_state()
            return

        output_path = Path(final_targets.root) if final_targets is not None else Path(result.output_path)
        result.output_path = str(output_path)
        self._last_export_output_path = str(output_path) if output_path.exists() else ''
        successful_rows = {row_id for row_id, _side in result.successful_sides}
        preview_rows = [
            self._active_preview_rows_by_side[key]
            for key in result.successful_sides
            if key in self._active_preview_rows_by_side
        ]
        if hasattr(self, 'module_five_panel'):
            self.module_five_panel.set_preview_rows(preview_rows)
        if hasattr(self, 'module_four_panel'):
            self.module_four_panel.append_log_line(
                ExportLogLine(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    prefix_text="Build finished:",
                    subject_text=str(Path(result.output_path)),
                    trailing_text=result.mod_size_text,
                    color_role="done" if not result.errors else "error",
                )
            )
        stats = BuildSummaryStats(
            media_rows=len(successful_rows),
            exported_media_rows=len(successful_rows),
            total_sides=len(result.successful_sides),
            total_songs=result.built_song_count,
            built_songs=result.built_song_count,
            planned_media_rows=plan.stats.planned_media_rows,
            planned_total_sides=plan.stats.planned_total_sides,
            planned_total_songs=plan.stats.planned_total_songs,
            converted=result.converted_count,
            mod_size_text=result.mod_size_text,
            errors=len(result.errors),
        )
        if hasattr(self, 'module_six_panel'):
            self.module_six_panel.set_stats(stats)
        self._snapshot_current_build_log()
        self.preview_entries = [f"{row.inventory_cell.label_text}" for row in preview_rows]
        self._refresh_build_summary()
        self._clear_active_build_run_state()

    def _finalize_audio_run_failure(self, plan, output_root: str, error_message: str) -> None:
        LOGGER.error("[run=%s] finalize_audio_run_failure root=%s error=%s", self._active_build_run_id or "-", output_root, error_message)
        final_targets = self._active_build_final_targets
        output_path = Path(final_targets.root) if final_targets is not None else Path(output_root)
        self._last_export_output_path = str(output_path) if output_path.exists() else ''
        if hasattr(self, 'module_four_panel'):
            self.module_four_panel.append_log_line(
                ExportLogLine(
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    prefix_text="Build failed.",
                    trailing_text=error_message,
                    color_role="error",
                )
            )
        stats = BuildSummaryStats(
            media_rows=0,
            exported_media_rows=0,
            total_sides=0,
            total_songs=0,
            built_songs=0,
            planned_media_rows=plan.stats.planned_media_rows,
            planned_total_sides=plan.stats.planned_total_sides,
            planned_total_songs=plan.stats.planned_total_songs,
            converted=0,
            mod_size_text=self._directory_size_text(output_path),
            errors=1,
        )
        if hasattr(self, 'module_six_panel'):
            self.module_six_panel.set_stats(stats)
        self._snapshot_current_build_log()
        self.preview_entries = []
        self._refresh_build_summary()
        self._clear_active_build_run_state()

    def _directory_size_text(self, root: Path) -> str:
        if not root.exists():
            return "0 KB"
        total = 0
        for path in root.rglob('*'):
            if not path.is_file():
                continue
            try:
                total += path.stat().st_size
            except OSError:
                continue
        if total >= 1024 * 1024 * 1024:
            return f"{total / (1024 * 1024 * 1024):.1f} GB"
        if total >= 1024 * 1024:
            return f"{total / (1024 * 1024):.1f} MB"
        if total >= 1024:
            return f"{total / 1024:.1f} KB"
        return f"{total} B"

    def _module_four_log_line_text(self, line: ExportLogLine) -> str:
        parts: list[str] = []
        if line.timestamp:
            parts.append(f'[{line.timestamp}]')
        if line.prefix_text:
            parts.append(line.prefix_text)
        if line.subject_text:
            parts.append(line.subject_text)
        if line.trailing_text:
            parts.append(line.trailing_text)
        if line.size_text:
            parts.append(line.size_text)
        return ' '.join(parts)

    def _snapshot_current_build_log(self) -> None:
        if not hasattr(self, 'module_four_panel'):
            self.build_log = []
            return
        self.build_log = [
            self._module_four_log_line_text(line)
            for line in self.module_four_panel.state.current_run_log_lines
        ]

    def _refresh_build_summary(self) -> None:
        if hasattr(self, 'build_summary'):
            self.build_summary.refresh()

    def _clear_active_build_run_state(self) -> None:
        self._set_build_locked(False)
        self._build_abort_event = None
        self._active_build_final_targets = None
        self._active_build_run_id = None

    def _module_five_preview_rows(self) -> list[GeneratedPreviewRow]:
        return self._build_preview_scenario('').preview_rows

    def _build_preview_scenario(self, output_path: str):
        plan = build_export_plan(self.session.project, self.asset_catalog)
        return build_preview_scenario(plan, output_path)

    def _open_output_folder(self) -> None:
        preferred = self._last_export_output_path or self.session.project.workshop_output_folder or str(app_root())
        output_path = Path(preferred)
        if output_path.exists():
            open_folder(output_path)
            return
        messagebox.showinfo('Output Folder', str(output_path))

    def _pick_ogg_output_folder(self) -> None:
        if self._is_build_locked():
            return
        initial_dir = self.session.project.ogg_output_folder or str(Path.home())
        selected = fd.askdirectory(
            title='Select .ogg Output Folder',
            initialdir=initial_dir,
            parent=self,
        )
        if not selected:
            return
        self.ogg_output_folder_var.set(selected)
        self.session.project.ogg_output_folder = selected
        self.on_project_change()

    def _pick_workshop_output_folder(self) -> None:
        if self._is_build_locked():
            return
        detected = detect_workshop_dir()
        initial_dir = self.session.project.workshop_output_folder or (str(detected) if detected else str(Path.home()))
        selected = fd.askdirectory(
            title='Select Zomboid Workshop Folder',
            initialdir=initial_dir,
            parent=self,
        )
        if not selected:
            return
        self.workshop_output_folder_var.set(selected)
        self.session.project.workshop_output_folder = selected
        self.on_project_change()

    def _sync_phase_one_project_state(self) -> None:
        self.session.project.mod_name = self.mod_name_var.get().strip()
        self.session.project.mod_id = self.mod_id_var.get().strip()
        self.session.project.parent_mod_id = self.parent_mod_id_var.get().strip()
        self.session.project.author = self.author_var.get().strip()
        self.session.project.ogg_output_folder = self.ogg_output_folder_var.get().strip()
        self.session.project.workshop_output_folder = self.workshop_output_folder_var.get().strip()
        if hasattr(self, 'poster_name_checkbox'):
            self.session.project.write_mod_name_on_poster = self.poster_name_checkbox.is_checked()

    def _register_phase_one_field_traces(self) -> None:
        for var in (
            self.mod_name_var,
            self.mod_id_var,
            self.parent_mod_id_var,
            self.author_var,
            self.ogg_output_folder_var,
            self.workshop_output_folder_var,
        ):
            var.trace_add('write', self._schedule_phase_one_project_sync)

    def _schedule_phase_one_project_sync(self, *_args) -> None:
        if self._phase_one_sync_suspended:
            return
        if self._phase_one_sync_after_id is not None:
            self.after_cancel(self._phase_one_sync_after_id)
        self._phase_one_sync_after_id = self.after(200, self._flush_phase_one_project_sync)

    def _flush_phase_one_project_sync(self) -> None:
        self._phase_one_sync_after_id = None
        self._commit_phase_one_project_state()
        self._refresh_module_one_poster_preview()
        self.session_store.save(self.session.project, self.session.current_path)
        if hasattr(self, 'build_summary'):
            self.build_summary.refresh()

    def _commit_phase_one_project_state(self) -> None:
        if self._phase_one_sync_after_id is not None:
            self.after_cancel(self._phase_one_sync_after_id)
            self._phase_one_sync_after_id = None
        self._sync_phase_one_project_state()

    def _sync_phase_one_ui_from_project(self) -> None:
        self._phase_one_sync_suspended = True
        try:
            if not self.session.project.workshop_output_folder:
                detected = detect_workshop_dir()
                if detected is not None:
                    self.session.project.workshop_output_folder = str(detected)
            self.mod_name_var.set(self.session.project.mod_name)
            self.mod_id_var.set(self.session.project.mod_id)
            self.parent_mod_id_var.set(self.session.project.parent_mod_id)
            self.author_var.set(self.session.project.author)
            self.ogg_output_folder_var.set(self.session.project.ogg_output_folder)
            self.workshop_output_folder_var.set(self.session.project.workshop_output_folder)
            if hasattr(self, 'poster_name_checkbox'):
                self.poster_name_checkbox.set_checked(bool(self.session.project.write_mod_name_on_poster))
            self._refresh_module_one_poster_preview()
        finally:
            self._phase_one_sync_suspended = False

    def _refresh_module_one_poster_preview(self) -> None:
        if not hasattr(self, 'module_one_cover_picker'):
            return
        poster_path = (self.session.project.workshop_poster_path or '').strip()
        if not poster_path:
            self.module_one_cover_picker.set_cover_image(None)
            return
        source = Path(poster_path)
        if not source.exists() or not source.is_file():
            self.module_one_cover_picker.set_cover_image(None)
            return
        rendered = render_square_image(
            source,
            spec.COVER_SIZE[0] - 2,
            (self.session.project.mod_name or '').strip(),
            add_name_overlay=bool(self.session.project.write_mod_name_on_poster),
        )
        self.module_one_cover_picker.set_cover_image(rendered)

    def on_close(self) -> None:
        if self._is_build_locked():
            return
        self._commit_phase_one_project_state()
        self.session_store.save(self.session.project, self.session.current_path)
        self.destroy()

    def report_callback_exception(self, exc, val, tb) -> None:
        from new_music_builder.platform.logging_support import write_runtime_fatal_log

        crash_path = write_runtime_fatal_log(
            "Unhandled Tk callback exception",
            exc,
            val,
            tb,
            thread_name=threading.current_thread().name,
        )
        LOGGER.exception("Unhandled Tk callback exception. See %s", crash_path, exc_info=(exc, val, tb))
        messagebox.showerror(
            'New Music Builder Error',
            'An unexpected error occurred.\n\n'
            f'See: {crash_path}',
        )
