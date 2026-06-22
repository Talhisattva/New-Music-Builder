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


def test_assets_root_uses_meipass_when_present(monkeypatch, tmp_path: Path) -> None:
    bundle_root = tmp_path / 'bundle'
    bundle_root.mkdir()
    monkeypatch.setattr(sys, '_MEIPASS', str(bundle_root), raising=False)

    root = paths.assets_root()

    assert root == bundle_root / 'assets'


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
