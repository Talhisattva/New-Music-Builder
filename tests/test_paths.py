from pathlib import Path
import sys

from new_music_builder.platform import paths


def test_runtime_root_uses_executable_directory_when_frozen(monkeypatch, tmp_path: Path) -> None:
    executable = tmp_path / 'release' / 'New Music Builder.exe'
    executable.parent.mkdir(parents=True)
    executable.write_text('', encoding='utf-8')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(executable))

    root = paths.runtime_root()

    assert root == executable.parent


def test_state_root_uses_localappdata_when_frozen(monkeypatch, tmp_path: Path) -> None:
    executable = tmp_path / 'release' / 'New Music Builder.exe'
    executable.parent.mkdir(parents=True)
    executable.write_text('', encoding='utf-8')
    local_appdata = tmp_path / 'LocalAppData'
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(executable))
    monkeypatch.setenv('LOCALAPPDATA', str(local_appdata))

    root = paths.state_root()

    assert root == local_appdata / 'NewMusicBuilder'


def test_state_root_falls_back_to_runtime_root_when_not_frozen(monkeypatch) -> None:
    monkeypatch.setattr(sys, 'frozen', False, raising=False)

    assert paths.state_root() == paths.runtime_root()


def test_assets_root_uses_meipass_when_present(monkeypatch, tmp_path: Path) -> None:
    bundle_root = tmp_path / 'bundle'
    bundle_root.mkdir()
    monkeypatch.setattr(sys, '_MEIPASS', str(bundle_root), raising=False)

    root = paths.assets_root()

    assert root == bundle_root / 'assets'


def test_generated_runtime_roots_use_state_root(monkeypatch, tmp_path: Path) -> None:
    state_root = tmp_path / 'StateRoot'
    monkeypatch.setattr(paths, 'state_root', lambda: state_root)

    assert paths.data_root() == state_root / 'workspace'
    assert paths.logs_root() == state_root / 'logs'
    assert paths.generated_textures_root() == state_root / 'Generated Textures'


def test_detect_workshop_dir_returns_workshop_child(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / 'home'
    workshop = home / 'Documents' / 'Zomboid' / 'Workshop'
    workshop.mkdir(parents=True)
    monkeypatch.setattr(Path, 'home', staticmethod(lambda: home))

    detected = paths.detect_workshop_dir()

    assert detected == workshop


def test_detect_workshop_dir_ignores_zomboid_without_workshop(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / 'home'
    (home / 'Documents' / 'Zomboid').mkdir(parents=True)
    monkeypatch.setattr(Path, 'home', staticmethod(lambda: home))

    detected = paths.detect_workshop_dir()

    assert detected is None
