# ═══════════════════════════════════════════════════════════════════════════
# vscode — Code / Code - Insiders theming.
#
# Two regimes, decided dynamically per editor (nothing palette-specific):
#
#   · palettes bundled by the xscriptor-themes extension ship a handcrafted
#     theme: set workbench.colorTheme/iconTheme to it and remove any generated
#     customizations (discovered by globbing the installed extension; future
#     themes are picked up without touching this file).
#
#   · any other palette (community/, user-created, renamed...) has no theme
#     file: keep a neutral base theme for the current luminance and inject an
#     intelligent `workbench.colorCustomizations` +
#     `editor.tokenColorCustomizations` + `editor.semanticTokenColorCustomizations`
#     generated from its base16 (themesync/vscode_theme.py). VS Code watches
#     settings.json, so the change applies live in every window.
#
# The generated keys live in a marker-delimited block; switching back to a
# bundled palette removes it. User-defined customization keys are never
# overwritten: if one exists outside the block, ours for that key is skipped.
# ═══════════════════════════════════════════════════════════════════════════
from __future__ import annotations

import json
import re
from pathlib import Path

from .. import vscode_theme
from ..core import load_json

NAME = "vscode"
DESCRIPTION = "colorTheme + live tint (colorCustomizations) in Code / Code - Insiders"

VARIANTS = (
    ".config/Code/User/settings.json",
    ".config/Code - Insiders/User/settings.json",
)

# vendor dir -> extensions dir (same vendor naming as VARIANTS)
EXT_DIRS = {
    "Code": ".vscode/extensions",
    "Code - Insiders": ".vscode-insiders/extensions",
}

BEGIN = "// >>> equisdots theme-sync >>>"
END = "// <<< equisdots theme-sync <<<"

_BLOCK_RE = re.compile(
    r"[ \t]*" + re.escape(BEGIN) + r".*?" + re.escape(END) + r"[ \t]*\n?",
    re.S,
)
_MANAGED_KEYS = (
    "workbench.colorCustomizations",
    "editor.tokenColorCustomizations",
    "editor.semanticTokenColorCustomizations",
)


def available(env) -> bool:
    # Always: if no variant is installed, apply() does nothing.
    return True


# ── native theme discovery (dynamic; no palette list) ─────────────────────────

def _native(env, slug: str, vendor: str):
    """Display name of the bundled theme for `slug`, or None."""
    root = Path(env.home) / EXT_DIRS.get(vendor, "")
    if not root.is_dir():
        return None
    for ext in sorted(root.glob("xscriptor.xscriptor-themes-*")):
        theme_file = ext / "themes" / ("%s.json" % slug)
        if not theme_file.is_file():
            continue
        theme = load_json(theme_file, {}) or {}
        return theme.get("name") or (slug[:1].upper() + slug[1:])
    return None


def _icon(env, slug: str, vendor: str):
    """Icon theme for `slug` (falls back to the neutral 'x-icons')."""
    root = Path(env.home) / EXT_DIRS.get(vendor, "")
    if not root.is_dir():
        return None
    for ext in sorted(root.glob("xscriptor.xscriptor-themes-*")):
        pkg = load_json(ext / "package.json", {}) or {}
        ids = [t.get("id") for t in (pkg.get("contributes", {}).get("iconThemes") or [])]
        if ("%s-icons" % slug) in ids:
            return "%s-icons" % slug
        if "x-icons" in ids:
            return "x-icons"
    return None


# ── settings.json (JSONC) helpers ─────────────────────────────────────────────

def _set_key(text: str, key: str, value: str) -> str:
    """Set a top-level JSON key (replace it in place or insert it)."""
    encoded = json.dumps(value, ensure_ascii=False)
    pat = re.compile(r'(?m)^([ \t]*)"%s"\s*:\s*[^,}\n]*' % re.escape(key))
    if pat.search(text):
        return pat.sub(lambda m: '%s"%s": %s' % (m.group(1), key, encoded), text, count=1)
    idx = text.find("{")
    if idx < 0:
        return '{\n    "%s": %s\n}\n' % (key, encoded)
    rest = text[idx + 1:]
    if rest.startswith("\n"):
        rest = rest[1:]
    comma = "" if rest.strip() in ("", "}") else ","
    return text[:idx + 1] + '\n    "%s": %s%s\n' % (key, encoded, comma) + rest


def _extract_object(text: str, key: str):
    """The top-level object value of `key`, or (None, None) if absent/invalid."""
    m = re.search(r'"%s"\s*:\s*' % re.escape(key), text)
    if not m:
        return None, None
    start = text.find("{", m.end())
    if start < 0:
        return None, None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1]), (m.start(), i + 1)
                except Exception:
                    return None, None
    return None, None


def _block(obj: dict, trailing_comma: bool) -> str:
    """Managed block: one indented `"key": value` line per key (no wrapper)."""
    parts = []
    for key, value in obj.items():
        encoded = json.dumps(value, indent=4, ensure_ascii=False)
        encoded = encoded.replace("\n", "\n    ")
        parts.append('    "%s": %s' % (key, encoded))
    body = ",\n".join(parts)
    if trailing_comma:
        body += ","
    return "%s\n%s\n%s" % (BEGIN, body, END)


def _strip_block(text: str) -> str:
    """Remove the managed block and normalize a brace-line first key."""
    text = _BLOCK_RE.sub("", text)
    m = re.match(r'\{\s*"', text)
    if m and "\n" not in m.group(0):
        text = "{\n" + text[1:].lstrip(" \t")
    return text


def _insert_block(text: str, obj: dict) -> str:
    idx = text.find("{")
    if idx < 0:
        return "{\n" + _block(obj, False) + "\n}\n"
    rest = text[idx + 1:]
    if rest.startswith("\n"):
        rest = rest[1:]
    needs_comma = rest.strip() not in ("", "}")
    return text[:idx + 1] + "\n" + _block(obj, needs_comma) + "\n" + rest


# ── apply ─────────────────────────────────────────────────────────────────────

def apply(env) -> list:
    out = []
    for rel in VARIANTS:
        path = env.home / rel
        if not path.is_file():
            continue
        vendor = Path(rel).parent.parent.name  # "Code" / "Code - Insiders"
        original = path.read_text(encoding="utf-8", errors="replace")
        text = _strip_block(original)

        display = _native(env, env.slug, vendor)
        icon = _icon(env, env.slug, vendor)
        if display:
            text = _set_key(text, "workbench.colorTheme", display)
            if icon:
                text = _set_key(text, "workbench.iconTheme", icon)
            note = "theme '%s'%s" % (display, " + '%s'" % icon if icon else "")
        else:
            generated = vscode_theme.build(env.palette)
            payload = {}
            skipped = []
            for key in _MANAGED_KEYS:
                if _extract_object(text, key)[1] is not None:
                    skipped.append(key)
                    continue
            if "workbench.colorCustomizations" not in skipped:
                payload["workbench.colorCustomizations"] = generated["workbench"]
            if "editor.tokenColorCustomizations" not in skipped:
                payload["editor.tokenColorCustomizations"] = {
                    "textMateRules": generated["tokenRules"],
                }
            if "editor.semanticTokenColorCustomizations" not in skipped:
                payload["editor.semanticTokenColorCustomizations"] = generated["semantic"]

            base = "Default Light Modern" if env.light else "Default Dark Modern"
            text = _set_key(text, "workbench.colorTheme", base)
            if icon:
                text = _set_key(text, "workbench.iconTheme", icon)
            if payload:
                text = _insert_block(text, payload)
            note = "live tint for '%s' over '%s' (%d workbench keys, %d token rules%s)" % (
                env.slug, base,
                len(generated["workbench"]), len(generated["tokenRules"]),
                "; skipped user keys: %s" % ", ".join(skipped) if skipped else "",
            )

        if text != original:
            env.write(path, text)
        out.append("vscode (%s) → %s" % (vendor, note))
    return out
