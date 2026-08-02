# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import re

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)


PROJECT_ROOT = Path(SPECPATH)
ASSETS_DIR = PROJECT_ROOT / "assets"
ICON_PATH = ASSETS_DIR / "new_music_builder.ico"
PACKAGE_INIT = PROJECT_ROOT / "src" / "new_music_builder" / "__init__.py"


def _package_version() -> str:
    match = re.search(r'__version__\s*=\s*"([^"]+)"', PACKAGE_INIT.read_text(encoding="utf-8"))
    if match is None:
        raise RuntimeError(f"Unable to determine package version from {PACKAGE_INIT}")
    return match.group(1)


def _version_tuple(version: str) -> tuple[int, int, int, int]:
    parts = [int(part) for part in version.split(".") if part.strip()]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


PACKAGE_VERSION = _package_version()
PACKAGE_VERSION_TUPLE = _version_tuple(PACKAGE_VERSION)
VERSION_INFO = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=PACKAGE_VERSION_TUPLE,
        prodvers=PACKAGE_VERSION_TUPLE,
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904B0",
                    [
                        StringStruct("CompanyName", "Talismon"),
                        StringStruct("FileDescription", "New Music Builder for Tali's New Music"),
                        StringStruct("FileVersion", PACKAGE_VERSION),
                        StringStruct("InternalName", "NewMusicBuilder"),
                        StringStruct("OriginalFilename", "NewMusicBuilder.exe"),
                        StringStruct("ProductName", "New Music Builder"),
                        StringStruct("ProductVersion", PACKAGE_VERSION),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)


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
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ICON_PATH)],
    version=VERSION_INFO,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="NewMusicBuilder",
)
