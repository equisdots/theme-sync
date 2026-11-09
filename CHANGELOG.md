# Changelog

All notable changes to the equisdots theme-sync engine are documented here.
Dates use YYYY-MM-DD.

## [2026-11-09]

### Fixed
- **opencode**: the target required `~/.config/opencode/themes/` to already
  exist and only updated `tui.json` when it was there, so a fresh profile
  skipped the target entirely and never got an active theme. It now checks the
  opencode config dir, creates `themes/` and creates `tui.json` (with
  `$schema`) or preserves its existing keys. When opencode v2's `cli.json`
  already exists, its `theme` object is kept in sync too.
- **xtop**: same availability bug — it required `themes/` to exist and skipped
  fresh installs. It now checks `~/.config/xtop` and creates `themes/`.
- Added unit tests for both targets (fresh profile, key preservation, v2
  `cli.json` sync, activation guard).

## [2026-11-01]

### Added
- **Local unit tests**: a stdlib `unittest` suite under `tests/` (104 tests) covering the colour maths, palette loading/selection, atomic writes, block stripping, binary lookup, the `Env` helpers and the runner's availability, selection, failure isolation and listing contracts. `scripts/check.sh` runs it before the CLI/VS Code smoke checks; no CI and no new dependencies.

### Documentation
- **Testing section**: the README documents `scripts/check.sh`, the 104 unittest cases, the CLI smoke test and the VS Code mapping/fresh-profile checks.

## [2026-10-25]

### Fixed
- VS Code target: process an installed Code / Code - Insiders variant even when
  its `User/settings.json` does not exist yet (fresh profile). The file is
  created with the generated theme instead of the target silently doing
  nothing. This was why VSCode stayed unthemed on a fresh niri profile while
  working where the file already existed.
- `scripts/check.sh`: temp-home fixture that asserts the missing settings file
  is created and contains the managed theme block.

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
