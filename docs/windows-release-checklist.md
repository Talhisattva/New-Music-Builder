# Windows Release Checklist

Use this checklist before publishing a packaged Windows release of `New Music Builder`.

## Build

1. Start from a clean repo state.
2. Run:

```powershell
python -m compileall src
pytest -q
powershell -ExecutionPolicy Bypass -File .\tools\package_release.ps1
```

3. Confirm the release zip exists under `release/`.

## Inspect The Packaged Layout

Open the release zip and confirm the packaged app folder contains only the shipped application runtime:

- `NewMusicBuilder.exe`
- `_internal/`

The packaged app folder should **not** include pre-seeded runtime state such as:

- `workspace/`
- `logs/`
- `Generated Textures/`

## First-Run Verification

Launch the packaged app on a clean Windows user profile or clean test machine.

Confirm that first run creates runtime state under:

`%LOCALAPPDATA%\NewMusicBuilder`

Verify these folders/files appear there after launch or normal use:

- `workspace\last_session.json`
- `workspace\recent.json`
- `logs\new_music_builder.log`
- `logs\startup_fatal.log`
- `logs\runtime_fatal.log`
- `Generated Textures\`

## Functional Smoke Test

In the packaged build, verify:

- app launches normally
- file picker import works
- drag-and-drop import works
- audio conversion/export works
- texture generation works
- recent project state saves and reloads

## AV And Reputation Follow-Up

Scan the packaged release with:

- Windows Defender
- VirusTotal

If the build is still flagged, submit false-positive reports with the exact release zip or executable:

- Microsoft Defender Security Intelligence:
  `https://www.microsoft.com/wdsi/filesubmission`
- Bkav false-positive / sample submission:
  `https://www.bkav.com.vn/ho-tro-khach-hang/gui-mau-phan-tich`

Record which engines flagged the build and whether the detection changed from the prior release.

## Public Release Notes

For the public mod/release description:

- explain that the tool is an unsigned packaged Python desktop app
- note that heuristic AV warnings can happen with this type of bundle
- mention that the release layout was cleaned to reduce false positives
- provide the source/manual-run fallback path for cautious users
- do not instruct users to disable Defender or their firewall globally
