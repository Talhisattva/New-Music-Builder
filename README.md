# New Music Builder

New Music Builder is a ground-up Python desktop rewrite of the old Simple Moozic Builder.

## Intent

- Keep the old builder's reliable cross-platform mechanics
- Target the current New Music Example Pack authoring model
- Stay decomposed and maintainable
- Use the Figma / Illustrator output as reference only, not production code

## Reference Material

- `_references/figma_export/` contains the exported Figma React code and assets
- `NewMusicBuilder.png` and `NewMusicBuilder.ai` are visual references
- `Builder Test.zip` is preserved as the original export artifact

## Runtime Stack

- Python 3.12+
- customtkinter + tkinter/ttk
- Pillow
- miniaudio preview backend
- soundfile / numpy audio backend
- ffmpeg fallback

## Current Status

This repo now contains the functional shell, project persistence, split-pane desktop layout, base texture catalog scanner, and the first runnable UI modules. Export/build generation will be layered in on top of this foundation.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```