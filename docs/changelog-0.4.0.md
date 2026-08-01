# New Music Builder 0.4.0

## Highlights

- Streamlined and optimized Module 2, Module 4, and Module 5 for 1000+ song packs.
- Optimized export throughput with bounded simultaneous conversion, calmer live conversion logging, and preserved large-pack responsiveness.
- Improved `.ogg` passthrough behavior so existing `.ogg` sources move through export much faster.
- Preserved and tightened abort responsiveness during heavy export runs.
- Moved `Legacy Mode` from a global preference into a per-row `Mixtape` / `Singles` switch.
- Added proper mixed-pack support so `Mixtape` rows and `Singles` rows can coexist in the same project and export cleanly together.

## UI / Authoring

- Added a row-level `Mixtape` / `Singles` pill switch under the live preview.
- Scoped legacy-style authoring behavior to `Singles` rows instead of the whole project.
- Kept `Mixtape` rows on the default modern row behavior.
- Updated Module 3 behavior so Singles-specific appearance editing and `Generate from Cover` flow apply only where appropriate.

## Export / Runtime

- Unified mixed export planning so single-track items and multi-track playlist items can ship in one pack.
- Restored and cleaned up Module 4 queue identity, ordering, and active-row tracking.
- Kept Module 5 on the stabilized latest-two live preview flow with full virtualized post-run browsing.
- Reduced Singles Lua/runtime fan-out by collapsing per-song Lua files into shared per-source-row Singles group files while keeping each single as its own distinct exported item.

## Notes

- This release is centered on stability, scale, and mixed-mode authoring rather than cosmetic-only polish.
