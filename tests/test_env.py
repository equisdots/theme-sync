from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from themesync import core


class EnvStateTests(unittest.TestCase):
    def make_env(self, palette: dict, **kwargs) -> core.Env:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        return core.Env(
            home=root,
            palettes_dir=root / "palettes",
            settings_path=root / "settings.json",
            slug="x",
            palettes=[],
            palette=palette,
            **kwargs,
        )

    def test_light_palette_and_scheme_int(self) -> None:
        env = self.make_env({"background": "#ffffff", "foreground": "#000000"})
        self.assertTrue(env.light)
        self.assertEqual(env.scheme_int, 1)

    def test_dark_palette_and_scheme_int(self) -> None:
        env = self.make_env({"background": "#000000", "foreground": "#ffffff"})
        self.assertFalse(env.light)
        self.assertEqual(env.scheme_int, 2)

    def test_mid_gray_is_dark(self) -> None:
        env = self.make_env({"background": "#808080"})
        self.assertFalse(env.light)

    def test_light_uses_base16_fallback(self) -> None:
        env = self.make_env({"base16": {"color0": "#f0f0f0"}})
        self.assertTrue(env.light)

    def test_note_appends_in_order(self) -> None:
        env = self.make_env({})
        env.note("first")
        env.note("second")
        self.assertEqual(env.log, ["first", "second"])


class EnvFileTests(unittest.TestCase):
    def make_env(self, root: Path, **kwargs) -> core.Env:
        return core.Env(
            home=root,
            palettes_dir=root / "palettes",
            settings_path=root / "settings.json",
            slug="x",
            palettes=[],
            palette={},
            **kwargs,
        )

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_write_creates_the_file(self) -> None:
        env = self.make_env(self.root)
        path = self.root / "nested" / "out.txt"
        env.write(path, "content")
        self.assertEqual(path.read_text(encoding="utf-8"), "content")

    def test_write_honors_dry_run(self) -> None:
        env = self.make_env(self.root, dry_run=True)
        path = self.root / "out.txt"
        env.write(path, "content")
        self.assertFalse(path.exists())
        self.assertEqual(env.log, ["[dry-run] would write %s (7 bytes)" % path])

    def test_mkdir_creates_and_respects_dry_run(self) -> None:
        env = self.make_env(self.root)
        env.mkdir(self.root / "a" / "b")
        self.assertTrue((self.root / "a" / "b").is_dir())

        dry = self.make_env(self.root, dry_run=True)
        dry.mkdir(self.root / "c")
        self.assertFalse((self.root / "c").exists())

    def test_unlink_removes_and_respects_dry_run(self) -> None:
        path = self.root / "file.txt"
        path.write_text("x", encoding="utf-8")

        dry = self.make_env(self.root, dry_run=True)
        dry.unlink(path)
        self.assertTrue(path.exists())

        env = self.make_env(self.root)
        env.unlink(path)
        self.assertFalse(path.exists())
        env.unlink(path)  # missing is not an error

    def test_copytree_once_copies_only_once(self) -> None:
        src = self.root / "src"
        src.mkdir()
        (src / "file.txt").write_text("first", encoding="utf-8")
        dst = self.root / "dst"

        env = self.make_env(self.root)
        env.copytree_once(src, dst)
        self.assertEqual((dst / "file.txt").read_text(encoding="utf-8"), "first")

        (src / "file.txt").write_text("second", encoding="utf-8")
        env.copytree_once(src, dst)
        self.assertEqual((dst / "file.txt").read_text(encoding="utf-8"), "first")

    def test_copytree_once_respects_dry_run(self) -> None:
        src = self.root / "src"
        src.mkdir()
        (src / "file.txt").write_text("x", encoding="utf-8")
        dst = self.root / "dst"

        env = self.make_env(self.root, dry_run=True)
        env.copytree_once(src, dst)
        self.assertFalse(dst.exists())

    def test_copytree_once_swallows_missing_source(self) -> None:
        dst = self.root / "dst"
        env = self.make_env(self.root)
        env.copytree_once(self.root / "missing", dst)
        self.assertFalse(dst.exists())


class EnvProcessTests(unittest.TestCase):
    def make_env(self, root: Path, **kwargs) -> core.Env:
        return core.Env(
            home=root,
            palettes_dir=root / "palettes",
            settings_path=root / "settings.json",
            slug="x",
            palettes=[],
            palette={},
            **kwargs,
        )

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_binary_uses_home_fallback(self) -> None:
        local_bin = self.root / ".local" / "bin"
        local_bin.mkdir(parents=True)
        tool = local_bin / "tool"
        tool.write_text("#!/bin/sh\n", encoding="utf-8")
        tool.chmod(0o755)

        env = self.make_env(self.root)
        with mock.patch.object(core.shutil, "which", return_value=None):
            self.assertEqual(env.binary("tool"), str(tool))

    def test_pgrep_true_false_and_failure(self) -> None:
        env = self.make_env(self.root)
        with mock.patch("themesync.core.subprocess.run",
                        return_value=mock.Mock(returncode=0)):
            self.assertTrue(env.pgrep("firefox"))
        with mock.patch("themesync.core.subprocess.run",
                        return_value=mock.Mock(returncode=1)):
            self.assertFalse(env.pgrep("firefox"))
        with mock.patch("themesync.core.subprocess.run",
                        side_effect=OSError("no pgrep")):
            self.assertFalse(env.pgrep("firefox"))

    def test_run_dry_run_logs_and_skips_subprocess(self) -> None:
        env = self.make_env(self.root, dry_run=True)
        with mock.patch("themesync.core.subprocess.run") as run:
            self.assertTrue(env.run(["echo", "hi"]))
        run.assert_not_called()
        self.assertEqual(env.log, ["[dry-run] would run: echo hi"])

    def test_run_reports_success_and_failure(self) -> None:
        env = self.make_env(self.root)
        with mock.patch("themesync.core.subprocess.run",
                        return_value=mock.Mock(returncode=0)):
            self.assertTrue(env.run(["true"]))
        with mock.patch("themesync.core.subprocess.run",
                        return_value=mock.Mock(returncode=3)):
            self.assertFalse(env.run(["false"]))
        with mock.patch("themesync.core.subprocess.run",
                        side_effect=OSError("missing")):
            self.assertFalse(env.run(["missing"]))

    def test_capture_returns_stdout(self) -> None:
        env = self.make_env(self.root)
        with mock.patch("themesync.core.subprocess.run",
                        return_value=mock.Mock(stdout="hello\n")):
            self.assertEqual(env.capture(["cmd"]), "hello\n")

    def test_capture_handles_empty_stdout_and_failure(self) -> None:
        env = self.make_env(self.root)
        with mock.patch("themesync.core.subprocess.run",
                        return_value=mock.Mock(stdout=None)):
            self.assertEqual(env.capture(["cmd"]), "")
        with mock.patch("themesync.core.subprocess.run",
                        side_effect=OSError("missing")):
            self.assertEqual(env.capture(["cmd"]), "")


if __name__ == "__main__":
    unittest.main()
