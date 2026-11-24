# ═══════════════════════════════════════════════════════════════════════════
# zen — Zen Browser full palette + light/dark scheme.
#
# - chrome/equisdots.css: user-origin theme built from the palette (accent,
#   browser/toolbar background, urlbar, borders, tabs). Written in full.
# - chrome/userChrome.css: managed @import of equisdots.css. @import must come
#   before other rules, so the block is inserted at the top (after a leading
#   @charset) and the rest of the file is preserved.
# - user.js: managed block with the legacy-userChrome pref (required by Zen),
#   zen.view.window.scheme (0 dark / 1 light / 2 auto), the accent color and
#   Firefox's content color-scheme override. user.js is read at startup, so it
#   is safe to write while the browser is running.
#
# Profile roots: modern Zen uses XDG (~/.config/zen); tarball/Twilight builds
# use ~/.zen; Flatpak nests its own HOME. Profiles come from profiles.ini.
# A fresh install with no profile is skipped without error.
# ═══════════════════════════════════════════════════════════════════════════
from __future__ import annotations

import configparser
import glob
import os
from pathlib import Path

from ..core import best_fg, mix, palette_bg_fg, palette_hex, strip_block

NAME = "zen"
DESCRIPTION = "Zen Browser palette + dark/light scheme (userChrome.css + user.js)"

ROOT_DIRS = (
    ".config/zen",
    ".config/zen-twilight",
    ".zen",
    ".var/app/app.zen_browser.zen/.zen",
    ".var/app/app.zen_browser.zen/zen",
)

JS_BEGIN = "// === equisdots theme-sync (managed) ==="
JS_END = "// === end equisdots ==="
JS_KEYS = (
    "toolkit.legacyUserProfileCustomizations.stylesheets",
    "zen.view.window.scheme",
    "zen.theme.accent-color",
    "zen.theme.use-system-colors",
    "layout.css.prefers-color-scheme.content-override",
)

CSS_BEGIN = "/* === equisdots theme-sync (managed) === */"
CSS_END = "/* === end equisdots === */"
CSS_REL = "chrome/equisdots.css"
IMPORT_REL = "chrome/userChrome.css"
IMPORT_BLOCK = (CSS_BEGIN, '@import url("equisdots.css");', CSS_END)

RUNNING_PATTERNS = ("/zen/zen", "zen-bin", "app.zen_browser.zen", "zen-twilight")


def available(env) -> bool:
    if _roots(env):
        return True
    return bool(env.binary("zen") or env.binary("zen-twilight"))


def apply(env) -> list:
    roots = _roots(env)
    if not roots:
        return ["zen: no profile directory; skipped (install/start Zen once)"]

    profiles = []
    for root in roots:
        profiles.extend(_profiles(root))
    profiles = _dedupe(profiles)
    if not profiles:
        return ["zen: no profiles found; skipped (start Zen once)"]

    scheme = 0 if not env.light else 1
    css = _css(env)
    accent = _accent(env.palette)

    out = []
    for prof in profiles:
        env.write(prof / CSS_REL, css)
        _ensure_import(env, prof / IMPORT_REL)
        _write_user_js(env, prof / "user.js", scheme, accent)
        out.append("zen palette → %s (%s)" % (env.slug, prof))
    if _running(env):
        out.append("zen: running; restart the browser to apply the palette")
    else:
        out.append("zen: applied on next launch")
    return out


# ── Roots and profiles ────────────────────────────────────────────────────────

def _roots(env) -> list:
    """Existing Zen profile roots (modern XDG, tarball, Flatpak), deduped."""
    seen, roots = set(), []
    for rel in ROOT_DIRS:
        root = env.home / rel
        if not root.is_dir():
            continue
        key = os.path.realpath(str(root))
        if key in seen:
            continue
        seen.add(key)
        roots.append(root)
    return roots


def _profiles(root: Path) -> list:
    """Profile directories from profiles.ini, fallback to */prefs.js scan."""
    found = []
    ini = root / "profiles.ini"
    if ini.is_file():
        cp = configparser.ConfigParser()
        try:
            cp.read(str(ini))
        except Exception:
            cp = None
        if cp is not None:
            for sec in cp.sections():
                if not sec.startswith("Profile") or not cp.has_option(sec, "Path"):
                    continue
                path = Path(cp.get(sec, "Path"))
                if cp.get(sec, "IsRelative", fallback="1") == "1":
                    path = root / path
                found.append(path)
    # A started profile always has prefs.js; stubs (Profile Groups) do not.
    found = [p for p in found if (p / "prefs.js").is_file()]
    if not found:
        found = [Path(p).parent for p in glob.glob(str(root / "*" / "prefs.js"))]
    return found


def _dedupe(profiles: list) -> list:
    seen, out = set(), []
    for prof in sorted(profiles):
        key = os.path.realpath(str(prof))
        if key in seen:
            continue
        seen.add(key)
        out.append(prof)
    return out


def _running(env) -> bool:
    return any(env.pgrep(p) for p in RUNNING_PATTERNS)


# ── userChrome.css import ─────────────────────────────────────────────────────

def _ensure_import(env, path: Path) -> None:
    lines = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    kept, _ = strip_block(lines, CSS_BEGIN, CSS_END)

    # @charset, when present, must stay the first statement of the file.
    charset = []
    if kept and kept[0].strip().lower().startswith("@charset"):
        charset = [kept.pop(0)]
    body = "\n".join(kept).strip("\n")

    block = list(charset) + list(IMPORT_BLOCK)
    if body:
        block += ["", body]
    env.write(path, "\n".join(block) + "\n")


# ── user.js ───────────────────────────────────────────────────────────────────

def _write_user_js(env, path: Path, scheme: int, accent: str) -> None:
    kept = []
    if path.is_file():
        inside = False
        for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
            t = ln.strip()
            if t == JS_BEGIN:
                inside = True
                continue
            if t == JS_END:
                inside = False
                continue
            if inside or _is_managed_pref(t):
                continue
            kept.append(ln)

    block = [
        JS_BEGIN,
        'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);',
        'user_pref("zen.view.window.scheme", %d);' % scheme,
        'user_pref("zen.theme.accent-color", "%s");' % accent,
        'user_pref("zen.theme.use-system-colors", false);',
        'user_pref("layout.css.prefers-color-scheme.content-override", %d);' % scheme,
        JS_END,
    ]
    env.write(path, "\n".join(kept + [""] + block) + "\n")


def _is_managed_pref(line: str) -> bool:
    if not line.startswith("user_pref"):
        return False
    return any(('"%s"' % key) in line for key in JS_KEYS)


# ── CSS ───────────────────────────────────────────────────────────────────────

def _accent(palette: dict) -> str:
    return palette_hex(palette, "color5", "") or palette_hex(palette, "color1")


def _css(env) -> str:
    pal = env.palette
    bg, fg = palette_bg_fg(pal)
    accent = _accent(pal)
    surface = mix(bg, fg, 0.08)
    hover = mix(bg, fg, 0.10)
    hover_strong = mix(bg, fg, 0.18)
    border = mix(bg, fg, 0.20)
    selected = mix(bg, accent, 0.24)
    on_accent = best_fg(accent, fg, bg)
    scheme = "dark" if not env.light else "light"

    decls = {
        "color-scheme": scheme,
        "--zen-primary-color": accent,
        "--zen-colors-primary": accent,
        "--zen-colors-primary-foreground": on_accent,
        "--zen-colors-secondary": surface,
        "--zen-colors-tertiary": bg,
        "--zen-colors-hover-bg": hover,
        "--zen-colors-border": border,
        "--zen-colors-border-contrast": border,
        "--zen-colors-input-bg": surface,
        "--zen-main-browser-background": bg,
        "--zen-main-browser-background-toolbar": bg,
        "--zen-themed-toolbar-bg-transparent": bg,
        "--zen-branding-bg": bg,
        "--zen-browser-content-background": bg,
        "--zen-urlbar-background": surface,
        "--zen-input-border-color": border,
        "--input-border-color": border,
        "--toolbox-textcolor": fg,
        "--toolbar-color": fg,
        "--toolbar-field-color": fg,
        "--toolbar-field-background-color": surface,
        "--toolbar-field-focus-background-color": surface,
        "--toolbar-text-color": fg,
        "--tab-selected-outline-color": accent,
        "--tab-background-color-selected": selected,
        "--tab-text-color-selected": fg,
        "--tab-background-color-hover": hover,
        "--zen-essential-tab-selected-bg": selected,
        "--zen-essential-tab-selected-bg-hover": hover,
        "--zen-toolbar-element-bg": hover,
        "--zen-toolbar-element-bg-hover": hover_strong,
        "--toolbarbutton-background-color-hover": hover,
        "--toolbarbutton-background-color-active": hover_strong,
        "--arrowpanel-background": surface,
        "--panel-separator-color": border,
        "--zen-sidebar-notification-bg": surface,
        "--zen-sidebar-themed-icon-fill": fg,
        "--zen-dialog-background": bg,
    }
    body = ["  %s: %s !important;" % (key, value) for key, value in decls.items()]
    # The workspace gradient picker writes these inline on its own elements;
    # redeclare them there so a palette beats a custom gradient.
    background = [
        "  --zen-main-browser-background: %s !important;" % bg,
        "  --zen-main-browser-background-toolbar: %s !important;" % bg,
        "  --zen-background-opacity: 1 !important;",
        "  --zen-grainy-background-opacity: 0 !important;",
    ]
    return "\n".join([
        "/* equisdots theme-sync — Zen Browser",
        " * palette: %s (%s)" % (pal.get("name") or env.slug, env.slug),
        " * generated; edits will be overwritten",
        " */",
        ":root {",
        *body,
        "}",
        "",
        "#zen-browser-background,",
        "#zen-toolbar-background {",
        *background,
        "}",
    ]) + "\n"
