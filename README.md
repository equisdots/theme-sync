# theme-sync

Palette-driven theming engine for the [equisdots](https://github.com/equisdots)
desktop. It reads the active palette from `settings.json` and syncs a set of
applications with it — one module per application, and a failing target never
aborts the rest.

## How it works

1. Palettes are plain JSON files: base16 (`color0`..`color15`) + `background`/
   `foreground` + optional `roles` overrides. The data and its schema live in
   [equisdots/palettes](https://github.com/equisdots/palettes).
2. The active palette slug comes from `settings.json` → `dock.palette`
   (fallback `x`).
3. Each target under `themesync/targets/` regenerates its application's config:
   per-palette artifacts (kitty, starship, xtop, nvim, opencode, Qt, xfetch) or
   active-only config (VS Code, browsers, rofi, cava, GTK).

## Usage

```bash
./theme-sync.sh --list                  # targets + availability
./theme-sync.sh --dry-run               # show what would change, write nothing
./theme-sync.sh --targets kitty,xfetch  # only these apps
./theme-sync.sh --palettes DIR --settings FILE
```

Defaults target the equisdots desktop layout:

- palettes: `~/.config/hypr/scripts/quickshell/dock/palettes`
- settings: `~/.config/hypr/settings.json`

## Targets

| Target | What it writes |
|---|---|
| `kitty` | `~/.config/kitty/themes/<slug>.conf` + include and active border in `kitty.conf` |
| `starship` | per-palette themes + fixed `~/.config/starship.toml` + `STARSHIP_CONFIG` in `.zshrc`/`.bashrc` |
| `xtop` | `~/.config/xtop/themes/<slug>.jsonc` + active theme (`xtop --ct`) |
| `vscode` | `workbench.colorTheme` / `workbench.iconTheme` in Code / Code - Insiders |
| `nvim` | `lua/themes/palettes.lua` + active-theme bootstrap |
| `browsers` | Brave/Beta prefs (`color_scheme2`, accent) + Firefox `user.js` |
| `opencode` | `~/.config/opencode/themes/<slug>.json` + active theme in `tui.json` |
| `rofi` | `colors.rasi` + `config.rasi` (dmenu included) |
| `cava` | managed `[color]` block with a palette gradient |
| `qt` | qt6ct/qt5ct color schemes + active config |
| `gtk` | `gtk-3.0`/`gtk-4.0` `gtk.css` overrides + system color-scheme |
| `xfetch` | `~/.config/xfetch/themes/<slug>.jsonc` (hex) + active theme |

## Palette format

Minimal example (see the [palettes schema](https://github.com/equisdots/palettes)
for the full contract):

```json
{
  "name": "X",
  "slug": "x",
  "author": "xscriptor",
  "base16": { "color0": "#0a0a0a", "color1": "#fc618d", "color7": "#f7f1ff", "color15": "#f7f1ff" },
  "background": "#0a0a0a",
  "foreground": "#f7f1ff",
  "roles": { "workspaceActive": "#eab308" }
}
```

`x` is special: it is the fallback palette (used when the active palette file is
missing), so it must always exist. `index.json` in the
[palettes repo](https://github.com/equisdots/palettes) is the ordered list the
desktop panel shows.

## Adding a target

Create `themesync/targets/<app>.py`:

```python
NAME = "app"
DESCRIPTION = "one line for --list"

def available(env) -> bool:
    ...

def apply(env) -> list:
    ...
```

and add it to the registry in `themesync/targets/__init__.py`.

## Development

```bash
python3 -m compileall -q themesync   # syntax check
./theme-sync.sh --dry-run            # exercise every target without writing
```

Palette validation lives with the data:
[equisdots/palettes](https://github.com/equisdots/palettes) →
`python3 tools/validate_palettes.py`.

## License

MIT — see `LICENSE`.
