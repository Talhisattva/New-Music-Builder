# New Music Builder

## Investigation Summary

This prompt is based on:

- the visual target in `NewMusicBuilder.png`
- the old Python desktop tool in `Simple-Moozic-Builder-Git`
- the current child-pack structure in `New Music Example Pack`

Important facts carried forward from the old builder:

- desktop Python app, not web app
- `customtkinter` + `tkinter/ttk` interaction style
- Windows first, but Linux/macOS supported
- file dialogs, save/load project JSON, workshop folder auto-detect and override
- ffmpeg-backed conversion with visible progress
- build converts first, then exports
- extended table selection, sorting, delete, rename, right-click actions
- live preview/build preview behavior
- custom window icon handling on Windows

Important changes for the new builder:

- no mixtape or song stitching mode
- build target is the newer child-pack structure
- the core unit is now a media row / album row, not a loose single-song row
- each row can support cassette, vinyl, CD
- each row can define A-side and B-side tracks
- each row can control item art, world art, and inherited/default assets

## Design Philosophy

- Make the app feel guided for beginners.
- Preserve power-user controls like sorting, multiselect, drag reorder, and save/load.
- Keep the screen as one readable dashboard first.
- Use strong tooltips almost everywhere.
- Keep the visuals stylish, but realistic for a Python desktop implementation.
- Prefer consistency and clarity over decorative complexity.

## Figma Prompt

Create a high-fidelity desktop application mockup for a Python-based cross-platform utility called **New Music Builder v0.1.0**. This is a dark, futuristic mod-pack builder for Project Zomboid music child packs. The app is Windows-first but should still feel plausible for macOS and Linux. The result should feel implementable in a `customtkinter` desktop app, not like a browser SaaS interface.

Use the attached PNG as the primary visual guide. Keep the layout, proportions, and visual language close to the PNG, but improve consistency, spacing, component reuse, and readability where needed. Prioritize clarity, maintainability, and realistic desktop-app implementation.

### Global Style

- dark sci-fi utility UI
- near-black background planes
- purple accent system with muted greys
- rounded modules with subtle inset borders and soft gradients
- `Orbitron` for headers, labels, and buttons
- retro pixel-style font such as `Perfect DOS VGA 437 Win` for row counters, percentages, and technical readouts
- compact but readable dense tables
- polished desktop-tool feel

### Header + Menu

At the very top:

- a dark header bar with a cassette-style icon on the far left, using the feel of `Item_NM_Cassette4`
- title text: `NEW MUSIC BUILDER` in bold Orbitron, light grey `#c7c6c6`
- version text: `v0.1.0` in smaller Orbitron medium, same color, about 5 sizes smaller
- header background `#101213`

Under that:

- a thin black divider line
- a brighter divider line around `#313233`
- then a darker menu row around `#070808`

Menu row content:

- `File`
- `Preferences`
- `Help`

Menu text:

- Orbitron bold
- muted purple-grey like `#615768`
- slightly lighter on hover and selected state

Dropdown expectations:

- File: `New`, `Save`, `Save As`, `Load`, `Recent`, `Exit`
- Preferences: `Sample Rate`
- Help: reserved for tutorials, tips, and hints

### Main Layout

Below the menu row:

- app background around `#141516`
- 5 main modules arranged on a 3-column / 2-row grid
- bottom-left build/export module spans two columns
- bottom-right build summary is its own column
- include a narrow right-side reference area like the PNG for component states and examples

### Module 1: PHASE 1: MOD SETUP

Visual style:

- rounded box around `#1d1c1e`
- darker border
- inset inner panel slightly lighter
- module title includes:
  - small rounded square icon tile
  - purple icon tile with subtle brighter gradient
  - title text `PHASE 1: MOD SETUP` in Orbitron bold and purple like `#8152a1`

Contents:

- form with four rows:
  - `Mod Name`
  - `Mod ID`
  - `Parent Mod ID`
  - `Author`
- labels:
  - Orbitron medium
  - light text like `#e2dede`
- field values:
  - retro DOS-style font
- fields:
  - no bright fill
  - subtle border only

Poster area:

- square poster preview panel
- top-right small rounded folder button with border and purple/gold folder-style icon
- next to poster preview:
  - checkbox
  - label `Write Mod Name On Poster`
- checkbox style:
  - dark purple bg
  - purple border
  - white check when active

Folder rows below:

- `.ogg Output Folder`
- `Zomboid Workshop Folder`

Each folder row should include:

- Orbitron medium label above
- bordered display field
- folder-picker button matching the poster folder button style

Workshop folder row:

- include a right-aligned green toast `✓ DETECTED` when auto-found

Bottom buttons:

- full-width pair across the module:
  - `SAVE`
  - `LOAD`
- gradient buttons
- Orbitron black or heavy text
- purple text with darker stroke

### Module 2: PHASE 2: MEDIA CREATION

Visual style:

- rounded dark module around `#1d1c1e`
- darker border
- inset panel around `#201f21`
- same purple icon tile + title style

Top actions:

- `+ Add Media Row`
- `X Remove Media Row`

Tooltips:

- `+ Add Media Row`: `Click to add a new media row to your project. Each media row can contain any of the three media types, a catalog of tracks for its A-Side and B-Side, as well as custom art for the item.`
- `X Remove Media Row`: `Remove the current expanded active media row.`

Media rows:

- each row is a slightly lighter rounded box
- top-left gradient rounded-square number chip acts as expand/collapse control
- number uses retro pixel font in light text
- chip brightens when active/expanded

#### Contracted Row State

Show:

- number chip
- small cover preview
- up to three visible media icons depending on enabled types
- a chevron-like divider
- two Orbitron medium text lines:
  - `A-Side (8 Songs) Duration: 00:01:24`
  - `B-Side (7 Songs) Duration: 00:01:24`

#### Expanded Row State

Three-column layout:

#### Column 1

- large cover preview in a rounded square with top-left notch for the number chip
- if no cover selected:
  - darker placeholder
  - subtle plus symbol in the center
  - click implies opening file explorer
- below:
  - cassette icon
  - vinyl icon
  - CD icon
- each icon has its own purple checkbox/toggle

#### Column 2

Top:

- label `Media Name`
- field underneath, bordered only
- typing into it edits the media name
- this also defines the normalized item ID behind the scenes

Below that:

- two side toggle buttons:
  - `A - Side`
  - `B - Side`
- inactive bg around `#27222d`
- selected bg shifts brighter and more purple

Main track table:

- enlarge slightly from the PNG so it feels like the primary working area
- header row with columns:
  - drag handle
  - `OGG`
  - `SONG NAME`
  - `PREVIEW`
  - `LENGTH`
  - `X`

Behavior implied in design:

- drag handle for reorder
- OGG column shows green check if already valid `.ogg` at chosen sample rate
- song name can be inline edited on double click
- preview button shows play + sound-wave motif
- length column shows duration
- X removes the row
- standard styled vertical scrollbar

Buttons under table:

- `+ Add Songs`
- `- Remove Selected`

Tooltip ideas:

- `+ Add Songs`: `Batch import or import single songs.`
- `- Remove Selected`: `Remove all selected tracks from this media item.`

#### Column 3

Live preview pane:

- title bar `LIVE PREVIEW`
- two tabs:
  - `Inventory`
  - `World`
- dark inset preview box below
- show clean previews for:
  - cassette case + cassette
  - CD cover + CD
  - vinyl jacket + vinyl record

### Module 3: CUSTOMIZE APPEARANCE

Visual style:

- same dark rounded module style
- same purple icon tile + title

Top tabs:

- `Cassette`
- `Vinyl`
- `CD`
- `Case`
- `Jacket`
- `CD Cover`

Each tab:

- dark tile
- icon + small Orbitron label
- selected state uses brighter highlight

Checkbox shown only on:

- `Case`
- `Jacket`
- `CD Cover`

Checkbox label:

- `Dual Sprite Full/Empty`

Option grid:

- scrollable grid of default selections from the base mod
- each tile shows the inventory icon
- top-right small purple eye button
- eye button implies hover preview of full-resolution world texture attached to cursor
- selected tile gets a lighter background

Custom uploader at bottom:

Single-sprite mode:

- two dashed rounded upload squares:
  - `Inventory`
  - `World`

Dual-sprite mode:

- four dashed rounded upload squares:
  - `INV. FULL`
  - `WORLD FULL`
  - `INV. EMPTY`
  - `WORLD EMPTY`

Filled state:

- plus becomes thumbnail preview
- tile bg becomes darker filled state with purple border
- small check badge top-right

Add button:

- `Add Custom`
- disabled until all required slots are filled
- turns green when valid

Preview behavior:

- dual-sprite items should imply automatic alternating preview between full and empty states in:
  - appearance grid
  - live preview
  - build preview

### Module 4: BUILD & EXPORT

This module spans the first two columns of the second row.

Header:

- the header itself acts as the main build button
- hammer icon
- Orbitron bold text `BUILD & EXPORT`

Left section:

- conversion/build table
- columns:
  - media row / side identifier
  - `SONGS`
  - `PROGRESS`
  - `STATUS`

Parent row content:

- number chip
- media side label like `Tali's Mix (Side - A)`
- tiny enabled media-type icons

Song subrows:

- nested under the parent row
- one row per song

Progress bars:

- segmented into 10 steps
- dark base
- yellow while converting
- green when done
- retro pixel percentage label beside each bar

Status states:

- `QUEUED`
- `CONVERTING`
- `DONE`
- `ERROR`

Below table:

- text log / readout pane
- timestamped status lines like:
  - `[12:45:10] Converting: Alice in Chains - Would.ogg ... DONE`
- closing success line indicating where the pack was saved

Right section of the same module:

- `GENERATED ITEM PREVIEW`
- purple header strip
- stacked preview entries appear as build progresses
- each entry includes:
  - number chip
  - side label
  - `INVENTORY` row
  - `WORLD` row
  - six generated previews as appropriate for the side
- include scrollbar

### Module 5: BUILD SUMMARY

Dark rounded module with checkmark icon tile and title `BUILD SUMMARY`.

Stats table:

- alternating row colors
- two columns: label and value
- rows:
  - `Media Rows`
  - `Total Sides`
  - `Total Songs`
  - `Converted`
  - `Queued`
  - `Errors`
- use light Orbitron text
- `Errors` value should be red

Completion card:

- green card with large checkmark
- heading `BUILD COMPLETE`
- second line with summary such as `5/5 Media - 25/25 songs`

Buttons below:

- primary blue button:
  - folder icon tile
  - `OPEN OUTPUT FOLDER`
- secondary grey button:
  - X icon
  - `CANCEL / RESET`

Disabled state:

- both button and icon tile grey out clearly when unavailable

### Right-Side Reference Rail

Include extra component examples from the PNG:

- empty custom uploader
- filled custom uploader
- dual-sprite custom uploader
- alternate live preview examples

These should look like a component playground / reference strip, not part of the main workflow.

### Behavior Notes to Encode in Annotations

This is a desktop tool, not a web app.

The design should imply these real behaviors:

- file dialogs for choosing audio, output folders, workshop folder, and images
- extended table selection with Shift/Ctrl behavior
- drag reorder within track tables
- right-click / rename / remove / batch actions
- build converts first, then exports
- output goes directly to workshop folder in the new flow
- project can be saved and loaded as a config file
- workshop folder can auto-detect but also be overridden
- extensive tooltips exist on most beginner-facing controls
- no mixtape creation, no song stitching mode

### Component States to Include

- idle / hover / selected buttons
- checked / unchecked checkboxes
- expanded / contracted media row
- empty / filled cover slot
- selected / unselected appearance tile
- single-sprite custom uploader
- dual-sprite custom uploader
- build statuses: queued, converting, done, error
- enabled / disabled open-output-folder button
- `Inventory` / `World` live-preview tab switch
- `A - Side` / `B - Side` switch

### Final Goal

Make the result feel like a polished **v0.1 desktop builder** that is visually strong, beginner-friendly, and already organized for implementation later in Python. It should look specific, grounded, and maintainable, not like a vague concept mockup.
