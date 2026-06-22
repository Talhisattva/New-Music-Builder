# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


PROJECT_ROOT = Path(SPECPATH)
ASSETS_DIR = PROJECT_ROOT / "assets"
ICON_PATH = ASSETS_DIR / "new_music_builder.ico"


def _safe_collect_data(package: str):
    try:
        return collect_data_files(package, include_py_files=False)
    except Exception:
        return []


def _safe_collect_bins(package: str):
    try:
        return collect_dynamic_libs(package)
    except Exception:
        return []


datas = [
    (str(ASSETS_DIR), "assets"),
]
datas += _safe_collect_data("customtkinter")
datas += _safe_collect_data("soundfile")
datas += _safe_collect_data("tkinterdnd2")

binaries = []
binaries += _safe_collect_bins("soundfile")
binaries += _safe_collect_bins("miniaudio")

hiddenimports = [
    "miniaudio",
    "numpy",
    "soundfile",
    "tkinterdnd2",
]


a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT), str(PROJECT_ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NewMusicBuilder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ICON_PATH)],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="NewMusicBuilder",
)
