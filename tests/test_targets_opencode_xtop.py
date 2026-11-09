from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from themesync.core import Env
from themesync.targets import opencode, xtop


PALETTE = {
    "name": "X",
    "slug": "x",
    "background": "#000000",
    "foreground": "#ffffff",
    "base16": {"color%d" % i: "#%02x%02x%02x" % (i * 16, i * 16, i * 16) for i in range(16)},
}


class TargetTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def make_env(self, **kwargs) -> Env:
        return Env(
            home=self.root,
            palettes_dir=self.root / "palettes",
            settings_path=self.root / "settings.json",
            slug="x",
            palettes=[PALETTE],
            palette=PALETTE,
            **kwargs,
        )


class OpencodeTargetTests(TargetTestCase):
    def test_not_available_without_config_dir(self) -> None:
        self.assertFalse(opencode.available(self.make_env()))

    def test_fresh_profile_creates_themes_and_tui_json(self) -> None:
        (self.root / ".config/opencode").mkdir(parents=True)
        env = self.make_env()
        self.assertTrue(opencode.available(env))

        lines = opencode.apply(env)

        theme = json.loads((self.root / ".config/opencode/themes/x.json").read_text())
        self.assertEqual(theme["defs"]["bg0"], "#000000")
        self.assertIn("syntaxKeyword", theme["theme"])

        tui = json.loads((self.root / ".config/opencode/tui.json").read_text())
        self.assertEqual(tui["theme"], "x")
        self.assertEqual(tui["$schema"], opencode.TUI_SCHEMA)

        manifest = json.loads(
            (self.root / opencode.STATE_REL).read_text())
        self.assertEqual(manifest, ["x"])
        self.assertIn("opencode theme → 'x' (tui.json)", lines)

    def test_tui_json_keeps_other_keys(self) -> None:
        oc = self.root / ".config/opencode"
        oc.mkdir(parents=True)
        (oc / "tui.json").write_text(json.dumps({"theme": "old", "mouse": False, "keybinds": {"x": "y"}}))

        opencode.apply(self.make_env())

        tui = json.loads((oc / "tui.json").read_text())
        self.assertEqual(tui["theme"], "x")
        self.assertFalse(tui["mouse"])
        self.assertEqual(tui["keybinds"], {"x": "y"})

    def test_cli_json_theme_object_updated_when_present(self) -> None:
        oc = self.root / ".config/opencode"
        oc.mkdir(parents=True)
        (oc / "cli.json").write_text(json.dumps({
            "theme": {"name": "old", "mode": "dark"},
            "mouse": True,
        }))

        lines = opencode.apply(self.make_env())

        cli = json.loads((oc / "cli.json").read_text())
        self.assertEqual(cli["theme"], {"name": "x", "mode": "dark"})
        self.assertTrue(cli["mouse"])
        self.assertIn("opencode theme → 'x' (cli.json)", lines)


class XtopTargetTests(TargetTestCase):
    def test_not_available_without_config_dir(self) -> None:
        self.assertFalse(xtop.available(self.make_env()))

    def test_fresh_profile_creates_themes_dir(self) -> None:
        (self.root / ".config/xtop").mkdir(parents=True)
        env = self.make_env()
        self.assertTrue(xtop.available(env))

        with mock.patch("themesync.core.find_binary", return_value=None):
            lines = xtop.apply(env)

        theme = self.root / ".config/xtop/themes/x.jsonc"
        self.assertTrue(theme.is_file())
        self.assertIn("synced from dock/palettes/", theme.read_text())
        self.assertTrue(any("xtop themes regenerated" in line for line in lines))

    def test_activation_runs_when_the_binary_exists(self) -> None:
        (self.root / ".config/xtop").mkdir(parents=True)
        env = self.make_env()

        with mock.patch("themesync.core.find_binary", return_value="/usr/bin/xtop"), \
                mock.patch("themesync.core.Env.run", return_value=True):
            lines = xtop.apply(env)

        self.assertIn("xtop theme → 'x'", lines)


if __name__ == "__main__":
    unittest.main()
