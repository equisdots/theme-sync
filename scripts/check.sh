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
else
    echo "note: no palette source found, CLI smoke test skipped" >&2
fi

if [ "$fail" -eq 0 ]; then
    echo "theme-sync: checks OK"
fi
exit "$fail"
