![New Music Builder](docs/images/NewMusicBuilder-640-transparent.png)

# New Music Builder

New Music Builder is the builder software for [Tali's New Music](https://steamcommunity.com/sharedfiles/filedetails/?id=3739256725).

It is specifically designed to create multitrack media for Project Zomboid with as little friction as possible, including authoring, cover setup, audio conversion, previewing, and export into workshop-ready song packs.

## Platform Support

- Windows is the primary packaged release target.
- Linux and macOS are intended to run from the GitHub source with Python 3.12+.
- The codebase tries to stay cross-platform where practical, but Windows packaging remains the main shipped binary path.

## Status

- Song pack export is working end to end.
- Covers, compression, naming, organization, Lua/bootstrap output, and texture export are in place.
- The current repo shape is focused on release readiness and maintainable source distribution.

## Repo Layout

- `src/new_music_builder/` contains the application code.
- `assets/` contains runtime assets that ship with the app.
- `tests/` contains automated validation coverage.
- `workspace/` contains default local app state files.
- `logs/` contains local log files that the app writes into at runtime.
- `_references/` is local reference material and is intentionally ignored from Git.
- `build/`, `dist/`, and `release/` are packaging outputs and are intentionally ignored from Git.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Validation

```powershell
python -m compileall src
pytest -q
```

## Windows Packaging

```powershell
pip install -r requirements-packaging.txt
powershell -ExecutionPolicy Bypass -File .\tools\package_release.ps1
```

That produces the Windows release zip in `release/`.
