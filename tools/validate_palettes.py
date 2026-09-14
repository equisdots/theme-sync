#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════
# validate_palettes — validates palettes/ without external dependencies.
#
#   - Every palettes/<slug>.json matches the contract (name/slug/base16 + hex).
#   - palettes/index.json lists exactly the existing slugs (the desktop panel
#     uses index.json as its card model).
#
# Exits non-zero on errors. Used by CI.
# ═══════════════════════════════════════════════════════════════════════════
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PALETTES = ROOT / "palettes"
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")

errors = []
warnings = []


def check_palette(path: pathlib.Path) -> str | None:
    """Validate one palette file; return its slug or None if invalid."""
    try:
        pal = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append("%s: invalid JSON (%s)" % (path.name, exc))
        return None

    slug = pal.get("slug") or path.stem
    if not isinstance(pal.get("name"), str) or not pal["name"].strip():
        errors.append("%s: missing 'name'" % path.name)
    if not isinstance(pal.get("slug"), str) or not SLUG.match(pal["slug"]):
        errors.append("%s: invalid 'slug' (must match %s)" % (path.name, SLUG.pattern))
    if slug != path.stem:
        errors.append("%s: slug '%s' != file name" % (path.name, slug))

    b16 = pal.get("base16")
    if not isinstance(b16, dict):
        errors.append("%s: missing 'base16'" % path.name)
    else:
        for i in range(16):
            key = "color%d" % i
            val = b16.get(key)
            if not isinstance(val, str) or not HEX.match(val):
                errors.append("%s: invalid base16.%s (%r)" % (path.name, key, val))

    for key in ("background", "foreground"):
        if key in pal and not (isinstance(pal[key], str) and HEX.match(pal[key])):
            errors.append("%s: invalid '%s' (%r)" % (path.name, key, pal[key]))

    roles = pal.get("roles")
    if roles is not None:
        if not isinstance(roles, dict):
            errors.append("%s: 'roles' must be an object" % path.name)
        else:
            for role, val in roles.items():
                if not (isinstance(val, str) and HEX.match(val)):
                    errors.append("%s: invalid roles.%s (%r)" % (path.name, role, val))
    return slug


def check_index(slugs: set) -> None:
    idx_path = PALETTES / "index.json"
    if not idx_path.is_file():
        errors.append("index.json: missing")
        return
    try:
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append("index.json: invalid JSON (%s)" % exc)
        return
    if not isinstance(idx, list):
        errors.append("index.json: must be a list")
        return
    listed = set()
    for i, entry in enumerate(idx):
        if not isinstance(entry, dict):
            errors.append("index.json[%d]: must be an object" % i)
            continue
        slug = entry.get("slug")
        if not isinstance(slug, str) or not SLUG.match(slug):
            errors.append("index.json[%d]: invalid slug (%r)" % (i, slug))
            continue
        if slug in listed:
            errors.append("index.json: duplicate slug '%s'" % slug)
        listed.add(slug)
        if not isinstance(entry.get("name"), str) or not entry["name"].strip():
            errors.append("index.json[%d] (%s): missing 'name'" % (i, slug))
        colors = entry.get("colors")
        if not (isinstance(colors, list) and len(colors) == 8
                and all(isinstance(c, str) and HEX.match(c) for c in colors)):
            errors.append("index.json[%d] (%s): 'colors' must be a list of 8 hex"
                          % (i, slug))
        if slug not in slugs:
            errors.append("index.json: '%s' has no palette file" % slug)
    for slug in sorted(slugs - listed):
        errors.append("palettes/%s.json is not in index.json" % slug)


def main() -> int:
    slugs = set()
    for path in sorted(PALETTES.glob("*.json")):
        if path.name in ("index.json", "schema.json"):
            continue
        slug = check_palette(path)
        if slug:
            slugs.add(slug)
    check_index(slugs)

    for w in warnings:
        print("WARN  %s" % w)
    for e in errors:
        print("ERROR %s" % e)
    if errors:
        print("\n%d error(s), %d warning(s)" % (len(errors), len(warnings)))
        return 1
    print("OK: %d valid palettes (index.json consistent)" % len(slugs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
