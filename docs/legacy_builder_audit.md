# Legacy Builder Audit

## Keep / Reuse in the rewrite

- Cross-platform desktop Python approach (`customtkinter` + `tkinter/ttk`)
- Save/load project JSON and recent-file workflow
- Workshop folder detection and manual override
- Windows icon handling and crash logging
- Audio conversion workspace and ffmpeg fallback lookup
- Preview backend abstraction (`miniaudio` / ffplay fallback)
- Table mechanics: multiselect, inline rename, sorting, drag-reorder intent
- Generated preview tiles and build log readout pattern

## Exclude from the new builder

- Mixtape/song-stitching workflow
- Legacy TrueMoozic-specific generation assumptions
- Old monolithic UI/build split (`simple_moozic_builder_ui.py` + `simple_moozic_builder.py`)
- Legacy cover-mask workflow as the primary authoring path

## Preserve as platform robustness rules

- Keep Windows-first behavior without hard-locking paths to Windows
- Keep shell-open behavior abstracted (`os.startfile`, `open`, `xdg-open`)
- Keep ffmpeg lookup able to use bundled or system binaries
- Keep transient/cache/build data outside repo-tracked source

## New builder target

- Export packs shaped like the current `New Music Example Pack`
- One row = one album/media definition block
- Data-first pack generation aligned with `NMAlbumPackBuilder`
- Texture catalog is the source of truth for selectors and previews