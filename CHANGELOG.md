# Changelog

All notable changes to the equisdots theme-sync engine are documented here.
Dates use YYYY-MM-DD.

## [2026-09-30]

### Added
- VS Code target: palettes without a handcrafted theme in `xscriptor-themes`
  (community/, user-created, renamed) now tint Code / Code - Insiders live
  through a generated `workbench.colorCustomizations` +
  `editor.tokenColorCustomizations` + `editor.semanticTokenColorCustomizations`
  block (`themesync/vscode_theme.py`). The base theme is matched to the palette
  luminance (Default Dark/Light Modern), bundled palettes keep their native
  theme and remove the block, and user-defined customization keys are never
  overwritten. Everything (themes and icons) is discovered at runtime from the
  installed extension: no palette list is hardcoded.
- `scripts/check.sh`: validates the vscode mapping over every palette in the
  checkout (hex colors and WCAG AA contrast).

## [2026-09-28]

### Fixed
- Palette loading recurses into subfolders (`rglob`) and the active palette fallback also looks under `community/`, so the community palettes shipped by the `equisdots/palettes` repo generate themes exactly like the flat ones.
