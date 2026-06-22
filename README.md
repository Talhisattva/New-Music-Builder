# New Music Builder

New Music Builder is the desktop authoring tool for generating Project Zomboid song packs from a structured project file.

## Platform Support

- Windows is the primary packaged release target.
- Linux and macOS are intended to run from the source release with Python 3.12+.
- The codebase tries to stay cross-platform where practical, but Windows packaging remains the main shipped binary path.

## Status

- Song pack export is working end to end.
- Covers, compression, naming, organization, Lua/bootstrap output, and texture export are in place.
- Current work is focused on cleanup, release shaping, and packaging rather than new feature churn.

## Repo Layout

- `src/new_music_builder/` contains the application code.
- `assets/` contains runtime assets that ship with the app.
- `tests/` contains automated validation coverage.
- `docs/` contains source documentation worth keeping in the repo.
- `_references/` is local reference material and is intentionally ignored from Git.
- `workspace/`, `logs/`, `build/`, `dist/`, and `release/` are runtime or packaging outputs and are intentionally ignored from Git.

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

## Packaging

Release packaging is documented in [docs/release_packaging.md](docs/release_packaging.md).
