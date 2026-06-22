# Release Packaging

## Source Repo Rules

- Keep `src/`, `assets/`, `tests/`, and `docs/` in Git.
- Keep `_references/` out of Git. It is local reference material only.
- Keep `workspace/`, `logs/`, `build/`, `dist/`, and `release/` out of Git. They are generated during runtime or packaging.

## Packaging Prerequisite

```powershell
pip install -r requirements-packaging.txt
```

## Standard Release Build

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\package_release.ps1
```

That script:

- runs `python -m compileall src`
- runs `pytest -q`
- builds the PyInstaller app from `NewMusicBuilder.spec`
- creates `release/NewMusicBuilder-v<version>-win64.zip`

## Release Contents

The zipped release should contain the packaged `NewMusicBuilder/` folder created by PyInstaller and nothing from:

- `_references/`
- `tests/`
- `docs/`
- `workspace/`
- `logs/`

## Pre-Push Check

Before pushing to GitHub:

```powershell
git status --short
python -m compileall src
pytest -q
```
