#!/usr/bin/env bash
# Local checks for the theme-sync engine (no CI):
#   - Byte-compile the package.
#   - CLI smoke test (list + dry-run) against a local palette checkout.
#
# Palette source resolution: sibling ../palettes checkout first, then the
# installed shell copy. With no palette source the smoke test is skipped.
#
# Usage: scripts/check.sh
set -u
cd "$(dirname "$0")/.." || exit 1

fail=0

if ! python3 -m compileall -q themesync; then
    echo "compileall FAIL"
    fail=1
else
    echo "compileall: OK"
fi

PALETTES=""
for c in "$PWD/../palettes" "$HOME/.config/hypr/scripts/quickshell/dock/palettes"; do
    if [ -d "$c" ]; then
        PALETTES="$c"
        break
    fi
done

if [ -n "$PALETTES" ]; then
    tmp="$(mktemp)"
    printf '{"bar":{"palette":"x"}}\n' > "$tmp"
    if ! ./theme-sync.sh --list --palettes "$PALETTES" --settings "$tmp" >/dev/null; then
        echo "CLI list FAIL"
        fail=1
    fi
    if ! ./theme-sync.sh --dry-run --palettes "$PALETTES" --settings "$tmp" >/dev/null; then
        echo "CLI dry-run FAIL"
        fail=1
    fi
    rm -f "$tmp"
    echo "CLI smoke test: OK ($PALETTES)"

    # vscode mapping: every palette must produce valid colors and readable
    # foreground/background contrast (the dynamic tint path).
    if ! PYTHONPATH="$PWD" python3 - "$PALETTES" <<'PY'
import re, sys
from pathlib import Path
from themesync import vscode_theme
from themesync.core import contrast, load_palettes, palette_bg_fg

HEX = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")
pals = load_palettes(Path(sys.argv[1]))
if len(pals) < 2:
    print("vscode mapping: too few palettes (%d)" % len(pals))
    sys.exit(1)
for pal in pals:
    out = vscode_theme.build(pal)
    wb = out["workbench"]
    for key, value in wb.items():
        if not HEX.match(value):
            print("vscode mapping: bad color %s %s=%s" % (pal.get("slug"), key, value))
            sys.exit(1)
    bg, _ = palette_bg_fg(pal)
    if contrast(bg, wb["foreground"]) < 4.5:
        print("vscode mapping: low contrast on %s" % pal.get("slug"))
        sys.exit(1)
    if len(out["tokenRules"]) < 20 or len(out["semantic"]["rules"]) < 10:
        print("vscode mapping: thin token map on %s" % pal.get("slug"))
        sys.exit(1)
print("vscode mapping: OK (%d palettes)" % len(pals))
PY
    then
        echo "vscode mapping FAIL"
        fail=1
    fi
else
    echo "note: no palette source found, CLI smoke test skipped" >&2
fi

if [ "$fail" -eq 0 ]; then
    echo "theme-sync: checks OK"
fi
exit "$fail"
