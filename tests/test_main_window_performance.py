from __future__ import annotations

from dataclasses import dataclass

from new_music_builder.domain.models import ProjectConfig, default_media_row
from new_music_builder.services.project_session import ProjectSession
from new_music_builder.ui.main_window import MainWindow
from new_music_builder.ui.widgets.media_row_list import MediaRowList


@dataclass
class _FakeViewport:
    current: tuple[float, float] = (0.0, 1.0)
    moved_to: list[float] | None = None

    def yview(self) -> tuple[float, float]:
        return self.current

    def yview_moveto(self, value: float) -> None:
        if self.moved_to is None:
            self.moved_to = []
        self.moved_to.append(value)


@dataclass
class _FakeScrollArea:
    refresh_count: int = 0

    def refresh_scroll_region(self) -> None:
        self.refresh_count += 1


class _FakeRowList:
    def __init__(self) -> None:
        self.appended_row_ids: list[int] = []
        self.expanded_row_ids: list[int | None] = []
        self.removed_row_ids: list[set[int]] = []
        self.remove_rows_payloads: list[list[int]] = []
        self.selection_states: list[set[int]] = []

    def append_row(self, row) -> None:
        self.appended_row_ids.append(row.row_id)

    def set_expanded_row(self, row_id: int | None) -> None:
        self.expanded_row_ids.append(row_id)

    def remove_rows(self, row_ids: set[int], rows=None) -> None:
        self.removed_row_ids.append(set(row_ids))
        self.remove_rows_payloads.append([row.row_id for row in (rows or [])])

    def set_selection_state(self, row_ids: set[int]) -> None:
        self.selection_states.append(set(row_ids))


class _FakeRowWidget:
    def __init__(self, expanded: bool, row_id: int | None = None) -> None:
        self._expanded = expanded
        self._row_id = row_id
        self.set_expanded_calls: list[bool] = []
        self.refreshed_covers: list[str] = []

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.set_expanded_calls.append(expanded)

    def refresh_cover(self, cover_path: str) -> None:
        self.refreshed_covers.append(cover_path)


def test_add_module_two_media_row_uses_incremental_row_list() -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.module_two_row_list = _FakeRowList()
    window.module_two_scroll_area = _FakeScrollArea()
    window.module_two_content_viewport = _FakeViewport()
    window._build_module_two_row_list = lambda: (_ for _ in ()).throw(AssertionError("full rebuild should not run"))
    window._is_build_locked = lambda: False
    window._cancel_module_two_song_drag = lambda: None
    window._cancel_module_two_row_drag = lambda: None
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    MainWindow._add_module_two_media_row(window)

    assert [row.row_id for row in window.session.project.media_rows] == [1, 2]
    assert window.module_two_row_list.appended_row_ids == [2]
    assert window.module_two_row_list.expanded_row_ids == [2]
    assert window.module_two_scroll_area.refresh_count == 1
    assert window.module_two_content_viewport.moved_to == [1.0]
    assert getattr(window, "_refreshed_module_three", False) is True
    assert getattr(window, "_project_changed", False) is True


def test_remove_module_two_media_row_set_remaps_selection_and_updates_remaining_rows() -> None:
    rows = [default_media_row(1), default_media_row(2), default_media_row(3)]
    session = ProjectSession(project=ProjectConfig(media_rows=rows))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.module_two_row_list = _FakeRowList()
    window.module_two_scroll_area = _FakeScrollArea()
    window.module_two_content_viewport = _FakeViewport(current=(0.25, 0.75))
    window.module_two_selected_row_ids = {2, 3}
    window.module_two_selection_anchor_row_id = 3
    window.module_two_song_selected_indices = {(2, "A"): {0}, (3, "B"): {1}}
    window.module_two_song_selection_anchor_indices = {(2, "A"): 0, (3, "B"): 1}
    window._is_build_locked = lambda: False
    window._cancel_module_two_song_drag = lambda: None
    window._cancel_module_two_row_drag = lambda: None
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    MainWindow._remove_module_two_media_row_set(window, {1})

    assert [row.row_id for row in window.session.project.media_rows] == [1, 2]
    assert window.module_two_selected_row_ids == {1, 2}
    assert window.module_two_selection_anchor_row_id == 2
    assert window.module_two_song_selected_indices == {(1, "A"): {0}, (2, "B"): {1}}
    assert window.module_two_song_selection_anchor_indices == {(1, "A"): 0, (2, "B"): 1}
    assert window.module_two_row_list.removed_row_ids == [{1}]
    assert window.module_two_row_list.remove_rows_payloads == [[1, 2]]
    assert window.module_two_row_list.selection_states == [{1, 2}]
    assert window.module_two_content_viewport.moved_to == [0.25]
    assert getattr(window, "_refreshed_module_three", False) is True
    assert getattr(window, "_project_changed", False) is True


def test_media_row_list_set_expanded_row_only_touches_changed_widgets() -> None:
    rows = [default_media_row(1), default_media_row(2), default_media_row(3)]
    rows[0].expanded = True
    rows[1].expanded = False
    rows[2].expanded = False
    row_list = MediaRowList.__new__(MediaRowList)
    row_list.rows = rows
    row_list.row_widgets = [_FakeRowWidget(True), _FakeRowWidget(False), _FakeRowWidget(False)]
    row_list._display_expanded_row_id = None
    badge_calls: list[int] = []
    layout_calls: list[tuple[int, bool]] = []
    row_list.refresh_badge_numbers = lambda start_index=0: badge_calls.append(start_index)
    row_list.refresh_row_layouts = lambda start_index=0, refresh_badges=True: layout_calls.append((start_index, refresh_badges))

    MediaRowList.set_expanded_row(row_list, 2)

    assert rows[0].expanded is False
    assert rows[1].expanded is True
    assert rows[2].expanded is False
    assert row_list.row_widgets[0].set_expanded_calls == [False]
    assert row_list.row_widgets[1].set_expanded_calls == [True]
    assert row_list.row_widgets[2].set_expanded_calls == []
    assert badge_calls == [0]
    assert layout_calls == [(0, False)]


def test_select_module_two_media_cover_refreshes_row_cover_before_async_generation(monkeypatch, tmp_path) -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    row_widget = _FakeRowWidget(True, row_id=1)
    window = MainWindow.__new__(MainWindow)
    window.session = session
    image_dir = tmp_path / "art"
    image_dir.mkdir()
    selected_cover = image_dir / "new-cover.png"
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": str(image_dir)})()
    session_saves: list[tuple[str, str]] = []
    window._save_session_snapshot = lambda: session_saves.append(
        (window.dialog_folder_memory.song_folder, window.dialog_folder_memory.image_folder)
    )
    window.module_two_row_list = type("RowList", (), {"row_widgets": [row_widget]})()
    window._is_build_locked = lambda: False
    window._image_filetypes = lambda: [("Images", "*.png")]
    window._repair_active_generated_appearance_selections = lambda: []
    window._refresh_module_two_live_preview_for_row = lambda _row_id: None
    window._automatic_textures_enabled = lambda: True
    window._generate_module_three_from_cover = lambda row_id: setattr(window, "_generated_row_id", row_id)
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    dialog_calls: list[str] = []

    def _askopenfilename(**kwargs):
        dialog_calls.append(kwargs["initialdir"])
        return str(selected_cover)

    monkeypatch.setattr("new_music_builder.ui.main_window.fd.askopenfilename", _askopenfilename)

    MainWindow._select_module_two_media_cover(window, 1)

    assert dialog_calls == [str(image_dir)]
    assert row.cover_path == str(selected_cover)
    assert row_widget.refreshed_covers == [str(selected_cover)]
    assert session_saves == [("", str(image_dir))]
    assert window.__dict__.get("_generated_row_id") == 1
    assert window.__dict__.get("_refreshed_module_three", False) is False
    assert window.__dict__.get("_project_changed", False) is False


def test_drop_module_two_media_cover_files_triggers_automatic_textures(monkeypatch, tmp_path) -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    row_widget = _FakeRowWidget(True, row_id=1)
    image_dir = tmp_path / "art"
    image_dir.mkdir()
    selected_cover = image_dir / "drop-cover.png"
    selected_cover.write_bytes(b"png")
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": ""})()
    session_saves: list[tuple[str, str]] = []
    window._save_session_snapshot = lambda: session_saves.append(
        (window.dialog_folder_memory.song_folder, window.dialog_folder_memory.image_folder)
    )
    window.module_two_row_list = type("RowList", (), {"row_widgets": [row_widget]})()
    window._repair_active_generated_appearance_selections = lambda: []
    window._refresh_module_two_live_preview_for_row = lambda _row_id: None
    window._automatic_textures_enabled = lambda: True
    window._generate_module_three_from_cover = lambda row_id: setattr(window, "_generated_row_id", row_id)
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    MainWindow._drop_module_two_media_cover_files(window, 1, [str(selected_cover)])

    assert row.cover_path == str(selected_cover)
    assert row_widget.refreshed_covers == [str(selected_cover)]
    assert session_saves == [("", str(image_dir))]
    assert window.__dict__.get("_generated_row_id") == 1
    assert window.__dict__.get("_refreshed_module_three", False) is False
    assert window.__dict__.get("_project_changed", False) is False


def test_cover_generation_success_ignores_stale_tokens_and_applies_current_result(monkeypatch) -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window._module_three_cover_generation_tokens = {1: 7}
    window._append_generated_cover_set_logs = lambda cover_path, result: setattr(window, "_logged_cover_path", cover_path)
    window._refresh_module_two_live_preview_for_row = lambda row_id: setattr(window, "_refreshed_row_id", row_id)
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_refreshed_module_three", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)
    apply_calls: list[str] = []
    monkeypatch.setattr(
        "new_music_builder.ui.main_window.apply_generated_cover_set_result",
        lambda project, target_row, result: apply_calls.append(target_row.cover_path),
    )
    result = type("Result", (), {"outcomes": (), "source_name": "cover.png"})()

    MainWindow._finish_module_three_cover_generation_success(window, 1, 6, "C:/art/old.png", result)

    assert apply_calls == []
    assert window._module_three_cover_generation_tokens == {1: 7}

    MainWindow._finish_module_three_cover_generation_success(window, 1, 7, "C:/art/new.png", result)

    assert apply_calls == [row.cover_path]
    assert window._module_three_cover_generation_tokens == {}
    assert window.__dict__.get("_logged_cover_path") == "C:/art/new.png"
    assert window.__dict__.get("_refreshed_row_id") == 1
    assert window.__dict__.get("_refreshed_module_three", False) is True
    assert window.__dict__.get("_project_changed", False) is True


def test_cover_generation_error_clears_current_token_and_logs_failure() -> None:
    window = MainWindow.__new__(MainWindow)
    window._module_three_cover_generation_tokens = {4: 11}
    window._append_generated_asset_failure_log = lambda cover_path, reason: setattr(window, "_failure", (cover_path, reason))

    MainWindow._finish_module_three_cover_generation_error(window, 4, 11, "C:/art/fail.png", "boom")

    assert window._module_three_cover_generation_tokens == {}
    assert window.__dict__.get("_failure") == ("C:/art/fail.png", "boom")


def test_show_audio_settings_dialog_updates_project_and_persists_session(monkeypatch, tmp_path) -> None:
    project = ProjectConfig(sample_rate=44100, compression_quality=0.5, reencode_existing_ogg=True)
    session = ProjectSession(project=project)
    session.current_path = "C:/projects/test.nmbproj.json"
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window._is_build_locked = lambda: False
    window._native_icon_path = lambda: tmp_path / "icon.ico"
    window._check_icon_path = lambda: tmp_path / "check.png"

    session_saves: list[tuple[int, float, bool, str]] = []
    window.session_store = type(
        "SessionStore",
        (),
        {
            "save": lambda _self, project, current_path, dialog_folder_memory=None: session_saves.append(
                (
                    project.sample_rate,
                    project.compression_quality,
                    project.reencode_existing_ogg,
                    current_path,
                )
            )
        },
    )()
    window._commit_phase_one_project_state = lambda: None
    window._refresh_module_one_poster_preview = lambda: None
    window.on_project_change = lambda: MainWindow.on_project_change(window)
    window.module_two_row_list = type("RowList", (), {"refresh_collapsed_details": lambda _self: None})()
    window.build_summary = type("BuildSummary", (), {"refresh": lambda _self: None})()
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": ""})()

    class _FakeDialog:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def show(self):
            return (48000, 0.65, False)

    monkeypatch.setattr("new_music_builder.ui.main_window.AudioSettingsDialog", _FakeDialog)

    MainWindow._show_audio_settings_dialog(window)

    assert window.session.project.sample_rate == 48000
    assert window.session.project.compression_quality == 0.65
    assert window.session.project.reencode_existing_ogg is False
    assert session_saves == [(48000, 0.65, False, "C:/projects/test.nmbproj.json")]


def test_select_workshop_poster_image_uses_image_lane_and_remembers_selection(monkeypatch, tmp_path) -> None:
    session = ProjectSession(project=ProjectConfig())
    window = MainWindow.__new__(MainWindow)
    window.session = session
    image_dir = tmp_path / "posters"
    image_dir.mkdir()
    selected_poster = (tmp_path / "new-posters")
    selected_poster.mkdir()
    selected_path = selected_poster / "poster.png"
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": str(image_dir)})()
    window._is_build_locked = lambda: False
    window._image_filetypes = lambda: [("Images", "*.png")]
    window._refresh_module_one_poster_preview = lambda: setattr(window, "_poster_refreshed", True)
    window._save_session_snapshot = lambda: setattr(window, "_saved_session", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)

    dialog_calls: list[str] = []

    def _askopenfilename(**kwargs):
        dialog_calls.append(kwargs["initialdir"])
        return str(selected_path)

    monkeypatch.setattr("new_music_builder.ui.main_window.fd.askopenfilename", _askopenfilename)

    MainWindow._select_workshop_poster_image(window)

    assert dialog_calls == [str(image_dir)]
    assert window.session.project.workshop_poster_path == str(selected_path)
    assert window.dialog_folder_memory.image_folder == str(selected_poster)
    assert window.__dict__.get("_saved_session", False) is True
    assert window.__dict__.get("_poster_refreshed", False) is True
    assert window.__dict__.get("_project_changed", False) is True


def test_drop_workshop_poster_files_updates_project_and_image_lane(tmp_path) -> None:
    session = ProjectSession(project=ProjectConfig())
    selected_dir = tmp_path / "new-posters"
    selected_dir.mkdir()
    selected_path = selected_dir / "poster.png"
    selected_path.write_bytes(b"png")
    window = MainWindow.__new__(MainWindow)
    window.session = session
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": ""})()
    window._refresh_module_one_poster_preview = lambda: setattr(window, "_poster_refreshed", True)
    window.on_project_change = lambda: setattr(window, "_project_changed", True)
    window._save_session_snapshot = lambda: setattr(window, "_saved_session", True)

    MainWindow._drop_workshop_poster_files(window, [str(selected_path)])

    assert window.session.project.workshop_poster_path == str(selected_path)
    assert window.dialog_folder_memory.image_folder == str(selected_dir)
    assert window.__dict__.get("_saved_session", False) is True
    assert window.__dict__.get("_poster_refreshed", False) is True
    assert window.__dict__.get("_project_changed", False) is True


def test_pick_module_three_custom_image_uses_image_lane_and_remembers_selection(monkeypatch, tmp_path) -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    image_dir = tmp_path / "custom-art"
    image_dir.mkdir()
    selected_dir = tmp_path / "picked-art"
    selected_dir.mkdir()
    selected_path = selected_dir / "world.png"
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": "", "image_folder": str(image_dir)})()
    window._image_filetypes = lambda: [("Images", "*.png")]
    window._active_module_three_row = lambda: row
    window._refresh_module_three_appearance_selector = lambda: setattr(window, "_appearance_refreshed", True)
    window.module_three_staged_custom_images = {}
    window._save_session_snapshot = lambda: setattr(window, "_saved_session", True)

    dialog_calls: list[str] = []

    def _askopenfilename(**kwargs):
        dialog_calls.append(kwargs["initialdir"])
        return str(selected_path)

    monkeypatch.setattr("new_music_builder.ui.main_window.fd.askopenfilename", _askopenfilename)

    MainWindow._pick_module_three_custom_image(window, "cassette", "world_full")

    assert dialog_calls == [str(image_dir)]
    assert window.module_three_staged_custom_images["cassette"]["world_full"] == str(selected_path)
    assert window.dialog_folder_memory.image_folder == str(selected_dir)
    assert window.__dict__.get("_saved_session", False) is True
    assert window.__dict__.get("_appearance_refreshed", False) is True


def test_add_module_two_songs_uses_song_lane_and_remembers_selection(monkeypatch, tmp_path) -> None:
    row = default_media_row(1)
    session = ProjectSession(project=ProjectConfig(media_rows=[row]))
    window = MainWindow.__new__(MainWindow)
    window.session = session
    song_dir = tmp_path / "music"
    song_dir.mkdir()
    selected_dir = tmp_path / "mixes"
    selected_dir.mkdir()
    first_song = selected_dir / "a.ogg"
    second_song = selected_dir / "b.ogg"
    window.dialog_folder_memory = type("DialogFolderMemory", (), {"song_folder": str(song_dir), "image_folder": ""})()
    window._is_build_locked = lambda: False
    window._audio_filetypes = lambda: [("Audio", "*.ogg")]
    window._save_session_snapshot = lambda: setattr(window, "_saved_session", True)
    added_paths: list[tuple[int, list[str]]] = []
    window._add_module_two_songs_from_paths = lambda row_id, paths: added_paths.append((row_id, list(paths)))

    dialog_calls: list[str] = []

    def _askopenfilenames(**kwargs):
        dialog_calls.append(kwargs["initialdir"])
        return (str(first_song), str(second_song))

    monkeypatch.setattr("new_music_builder.ui.main_window.fd.askopenfilenames", _askopenfilenames)

    MainWindow._add_module_two_songs(window, 1)

    assert dialog_calls == [str(song_dir)]
    assert window.dialog_folder_memory.song_folder == str(selected_dir)
    assert window.__dict__.get("_saved_session", False) is True
    assert added_paths == [(1, [str(first_song), str(second_song)])]


def test_can_accept_image_drop_requires_supported_existing_file(tmp_path) -> None:
    image_path = tmp_path / "cover.png"
    image_path.write_bytes(b"png")
    text_path = tmp_path / "cover.txt"
    text_path.write_bytes(b"text")
    window = MainWindow.__new__(MainWindow)

    assert MainWindow._can_accept_image_drop(window, [str(image_path)]) is True
    assert MainWindow._can_accept_image_drop(window, [str(text_path)]) is False
    assert MainWindow._can_accept_image_drop(window, [str(tmp_path / "missing.png")]) is False
