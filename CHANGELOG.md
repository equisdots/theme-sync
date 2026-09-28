# Changelog

All notable changes to the equisdots theme-sync engine are documented here.
Dates use YYYY-MM-DD.

## [2026-09-28]

### Fixed
- Palette loading recurses into subfolders (`rglob`) and the active palette fallback also looks under `community/`, so the community palettes shipped by the `equisdots/palettes` repo generate themes exactly like the flat ones.
