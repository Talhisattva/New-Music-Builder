# Release Packaging

## Release Shape

Use two release artifacts:

- `NewMusicBuilder-v<version>-win64.zip`
  Windows packaged app built with PyInstaller.
- `NewMusicBuilder-v<version>-source.zip`
  Source release for Windows, Linux, and macOS users running the app with Python 3.12+.

This keeps the release model honest:

- Windows gets the convenient packaged build.
- Linux and macOS get the portable source release instead of a fake universal binary.

## Source Repo Rules

- Keep `src/`, `assets/`, `tests/`, `docs/`, and `tools/` in Git.
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
- builds the PyInstaller Windows app from `NewMusicBuilder.spec`
- creates `release/NewMusicBuilder-v<version>-win64.zip`
- creates `release/NewMusicBuilder-v<version>-source.zip`

## Source Release Notes

The source release should include repo files needed to run and validate the app:

- `src/`
- `assets/`
- `tests/`
- `docs/`
- `tools/`
- top-level run and requirements files

It should not include generated runtime or packaging output:

- `_references/`
- `workspace/`
- `logs/`
- `build/`
- `dist/`
- `release/`

## Linux and macOS Run Expectations

Users running the source release should be able to:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Pre-Push Check

Before pushing to GitHub:

```powershell
git status --short
python -m compileall src
pytest -q
```
