from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from themesync.core import Env
from themesync.targets import zen


DARK = {
    "name": "X",
    "slug": "x",
    "background": "#050505",
    "foreground": "#f7f1ff",
    "base16": {
        "color0": "#0a0a0a", "color1": "#fc618d", "color2": "#7bd88f",
        "color3": "#fce566", "color4": "#fd9353", "color5": "#948ae3",
        "color6": "#5ad4e6", "color7": "#f7f1ff", "color8": "#7e7b82",
        "color9": "#fc618d", "color10": "#7bd88f", "color11": "#fce566",
        "color12": "#fd9353", "color13": "#948ae3", "color14": "#5ad4e6",
        "color15": "#f7f1ff",
    },
}

LIGHT = {
    "name": "Paper",
    "slug": "paper",
    "background": "#f5f5f5",
    "foreground": "#202020",
    "base16": {**DARK["base16"], "color1": "#aa3355", "color5": "#3355aa"},
}


class ZenTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def make_env(self, palette=None, **kwargs) -> Env:
        palette = palette or DARK
        return Env(
            home=self.root,
            palettes_dir=self.root / "palettes",
            settings_path=self.root / "settings.json",
            slug=palette["slug"],
            palettes=[palette],
            palette=palette,
            **kwargs,
        )

    def make_profile(self, root_rel=".config/zen", profile="abc.Default (release)") -> Path:
        root = self.root / root_rel
        prof = root / profile
        prof.mkdir(parents=True)
        (prof / "prefs.js").write_text('// Mozilla User Preferences\n')
        (root / "profiles.ini").write_text(
            "[General]\nVersion=2\n\n[Profile0]\n"
            "Name=Default (release)\nIsRelative=1\nPath=%s\n" % profile
        )
        return prof

    def test_not_available_without_roots_or_binary(self) -> None:
        env = self.make_env()
        with mock.patch("themesync.core.find_binary", return_value=None):
            self.assertFalse(zen.available(env))

    def test_available_with_xdg_profile_root(self) -> None:
        self.make_profile()
        self.assertTrue(zen.available(self.make_env()))

    def test_apply_writes_css_import_and_user_js(self) -> None:
        prof = self.make_profile()
        env = self.make_env()

        with mock.patch.object(Env, "pgrep", return_value=False):
            lines = zen.apply(env)

        css = (prof / "chrome/equisdots.css").read_text()
        self.assertIn("--zen-primary-color: #948ae3 !important;", css)
        self.assertIn("--zen-main-browser-background: #050505 !important;", css)
        self.assertIn("--zen-background-opacity: 1 !important;", css)
        self.assertIn("#zen-browser-background,", css)
        self.assertIn("color-scheme: dark !important;", css)

        user_chrome = (prof / "chrome/userChrome.css").read_text()
        self.assertEqual(user_chrome, "\n".join(list(zen.IMPORT_BLOCK)) + "\n")

        user_js = (prof / "user.js").read_text()
        self.assertIn(
            'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);',
            user_js)
        self.assertIn('user_pref("zen.view.window.scheme", 0);', user_js)
        self.assertIn('user_pref("zen.theme.accent-color", "#948ae3");', user_js)
        self.assertIn(
            'user_pref("layout.css.prefers-color-scheme.content-override", 0);',
            user_js)
        self.assertIn("zen palette → x", "\n".join(lines))

    def test_light_palette_uses_light_scheme(self) -> None:
        prof = self.make_profile()
        env = self.make_env(LIGHT)

        with mock.patch.object(Env, "pgrep", return_value=False):
            zen.apply(env)

        self.assertIn("color-scheme: light !important;",
                      (prof / "chrome/equisdots.css").read_text())
        user_js = (prof / "user.js").read_text()
        self.assertIn('user_pref("zen.view.window.scheme", 1);', user_js)
        self.assertIn(
            'user_pref("layout.css.prefers-color-scheme.content-override", 1);',
            user_js)

    def test_existing_user_chrome_is_preserved_and_imported_once(self) -> None:
        prof = self.make_profile()
        user_chrome = prof / "chrome/userChrome.css"
        user_chrome.parent.mkdir()
        user_chrome.write_text('@charset "UTF-8";\n\n#my-rule { color: red; }\n')
        env = self.make_env()

        with mock.patch.object(Env, "pgrep", return_value=False):
            zen.apply(env)
            zen.apply(env)

        text = user_chrome.read_text()
        self.assertTrue(text.startswith('@charset "UTF-8";\n'))
        self.assertEqual(text.count('@import url("equisdots.css");'), 1)
        self.assertIn("#my-rule { color: red; }", text)
        self.assertLess(text.index('@import url("equisdots.css");'),
                        text.index("#my-rule"))

    def test_user_js_keeps_other_prefs_and_replaces_managed_block(self) -> None:
        prof = self.make_profile()
        user_js = prof / "user.js"
        user_js.write_text(
            'user_pref("browser.startup.page", 3);\n'
            + zen.JS_BEGIN + "\n"
            'user_pref("zen.view.window.scheme", 2);\n'
            + zen.JS_END + "\n"
            'user_pref("extensions.pocket.enabled", false);\n'
        )
        env = self.make_env()

        with mock.patch.object(Env, "pgrep", return_value=False):
            zen.apply(env)

        text = user_js.read_text()
        self.assertEqual(text.count(zen.JS_BEGIN), 1)
        self.assertIn('user_pref("browser.startup.page", 3);', text)
        self.assertIn('user_pref("extensions.pocket.enabled", false);', text)
        self.assertIn('user_pref("zen.view.window.scheme", 0);', text)
        self.assertNotIn('user_pref("zen.view.window.scheme", 2);', text)

    def test_profiles_can_be_discovered_without_profiles_ini(self) -> None:
        root = self.root / ".zen"
        prof = root / "random.default"
        prof.mkdir(parents=True)
        (prof / "prefs.js").write_text("")

        env = self.make_env()
        with mock.patch.object(Env, "pgrep", return_value=False):
            zen.apply(env)

        self.assertTrue((prof / "chrome/equisdots.css").is_file())

    def test_stub_profiles_are_skipped(self) -> None:
        root = self.root / ".config/zen"
        (root / "empty.Default Profile").mkdir(parents=True)
        (root / "profiles.ini").write_text(
            "[Profile0]\nName=Empty\nIsRelative=1\nPath=empty.Default Profile\n")
        env = self.make_env()

        with mock.patch.object(Env, "pgrep", return_value=False):
            lines = zen.apply(env)

        self.assertIn("zen: no profiles found; skipped (start Zen once)", lines)

    def test_dry_run_writes_nothing(self) -> None:
        prof = self.make_profile()
        env = self.make_env(dry_run=True)

        with mock.patch.object(Env, "pgrep", return_value=False):
            zen.apply(env)

        self.assertFalse((prof / "chrome").exists())
        self.assertFalse((prof / "user.js").exists())


if __name__ == "__main__":
    unittest.main()
