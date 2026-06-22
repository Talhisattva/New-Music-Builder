# Release Packaging

## Release Shape

Use GitHub as the source distribution and ship one packaged Windows release artifact:

- GitHub repository
  Source distribution for Windows, Linux, and macOS users running the app with Python 3.12+.
- `NewMusicBuilder-v<version>-win64.zip`
  Windows packaged app built with PyInstaller.

This keeps the release model simple and honest:

- Windows users get the convenient packaged build.
- Linux and macOS users pull the source from GitHub and run it directly.

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

## GitHub Release Guidance

- Push the source repo to GitHub.
- Create a GitHub release for the version tag you want to publish.
- Attach only `release/NewMusicBuilder-v<version>-win64.zip` as the manual release asset.
- Let GitHub’s normal source browsing and auto-generated source archives serve Linux and macOS users.

## Linux and macOS Run Expectations

Users running from source should be able to:

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
