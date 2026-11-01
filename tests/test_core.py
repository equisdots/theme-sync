from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from themesync import core


class RgbTests(unittest.TestCase):
    def test_parses_six_digit_hex_with_and_without_hash(self) -> None:
        self.assertEqual(core.rgb("#ff0000"), (255, 0, 0))
        self.assertEqual(core.rgb("00ff00"), (0, 255, 0))
        self.assertEqual(core.rgb("#0000FF"), (0, 0, 255))

    def test_ignores_alpha_suffix(self) -> None:
        self.assertEqual(core.rgb("#12345678"), (0x12, 0x34, 0x56))
        self.assertEqual(core.rgb("#ff000080"), (255, 0, 0))

    def test_short_hex_is_zero_padded(self) -> None:
        self.assertEqual(core.rgb("#12345"), (0x01, 0x23, 0x45))
        self.assertEqual(core.rgb("#f"), (0, 0, 15))

    def test_invalid_input_returns_black(self) -> None:
        for value in ("", "#", None, "#xyzxyz", "not-a-color"):
            with self.subTest(value=value):
                self.assertEqual(core.rgb(value), (0, 0, 0))


class HexstrTests(unittest.TestCase):
    def test_formats_lowercase_six_digits(self) -> None:
        self.assertEqual(core.hexstr(0, 0, 0), "#000000")
        self.assertEqual(core.hexstr(255, 255, 255), "#ffffff")
        self.assertEqual(core.hexstr(0xAA, 0xBB, 0xCC), "#aabbcc")

    def test_clamps_out_of_range_components(self) -> None:
        self.assertEqual(core.hexstr(-10, 300, 128), "#00ff80")
        self.assertEqual(core.hexstr(255.4, -0.4, 0), "#ff0000")

    def test_rounds_components(self) -> None:
        self.assertEqual(core.hexstr(127.6, 0.4, 1.5), "#800002")


class MixTests(unittest.TestCase):
    def test_endpoints_are_unchanged(self) -> None:
        self.assertEqual(core.mix("#112233", "#aabbcc", 0), "#112233")
        self.assertEqual(core.mix("#112233", "#aabbcc", 1), "#aabbcc")

    def test_midpoint_of_black_and_white(self) -> None:
        self.assertEqual(core.mix("#000000", "#ffffff", 0.5), "#808080")

    def test_out_of_range_t_is_clamped(self) -> None:
        self.assertEqual(core.mix("#000000", "#ffffff", 2), "#ffffff")
        self.assertEqual(core.mix("#000000", "#ffffff", -1), "#000000")

    def test_alpha_is_ignored(self) -> None:
        self.assertEqual(core.mix("#ff000080", "#00ff00", 0.5), "#808000")

    def test_invalid_color_uses_black(self) -> None:
        self.assertEqual(core.mix("#zzzzzz", "#ffffff", 0.5), "#808080")


class LuminanceTests(unittest.TestCase):
    def test_black_and_white(self) -> None:
        self.assertEqual(core.luminance("#000000"), 0.0)
        self.assertEqual(core.luminance("#ffffff"), 1.0)

    def test_primary_colors(self) -> None:
        self.assertAlmostEqual(core.luminance("#ff0000"), 0.2126, places=6)
        self.assertAlmostEqual(core.luminance("#00ff00"), 0.7152, places=6)
        self.assertAlmostEqual(core.luminance("#0000ff"), 0.0722, places=6)

    def test_mid_gray(self) -> None:
        self.assertAlmostEqual(core.luminance("#808080"), 0.2158605, places=6)

    def test_ignores_alpha_and_invalid_input(self) -> None:
        self.assertEqual(core.luminance("#ffffffff"), 1.0)
        self.assertEqual(core.luminance("garbage"), 0.0)


class ContrastTests(unittest.TestCase):
    def test_black_on_white_is_maximum(self) -> None:
        self.assertAlmostEqual(core.contrast("#000000", "#ffffff"), 21.0, places=6)

    def test_identical_colors_have_ratio_one(self) -> None:
        self.assertAlmostEqual(core.contrast("#336699", "#336699"), 1.0, places=6)

    def test_is_symmetric(self) -> None:
        self.assertAlmostEqual(core.contrast("#123456", "#fedcba"),
                               core.contrast("#fedcba", "#123456"), places=9)

    def test_red_on_black_known_value(self) -> None:
        self.assertAlmostEqual(core.contrast("#ff0000", "#000000"),
                               (0.2126 + 0.05) / 0.05, places=6)

    def test_invalid_colors_are_both_black(self) -> None:
        self.assertAlmostEqual(core.contrast("nope", "#nothex"), 1.0, places=9)


class ArgbTests(unittest.TestCase):
    def test_prepends_ff_and_lowercases(self) -> None:
        self.assertEqual(core.argb("#AABBCC"), "#ffaabbcc")
        self.assertEqual(core.argb("112233"), "#ff112233")

    def test_existing_alpha_is_left_in_place(self) -> None:
        self.assertEqual(core.argb("#80112233"), "#ff80112233")


class BestFgTests(unittest.TestCase):
    def test_picks_foreground_when_more_contrast(self) -> None:
        self.assertEqual(core.best_fg("#ffffff", "#000000", "#ffffff"), "#000000")

    def test_picks_background_when_more_contrast(self) -> None:
        self.assertEqual(core.best_fg("#000000", "#111111", "#eeeeee"), "#eeeeee")

    def test_tie_returns_foreground(self) -> None:
        self.assertEqual(core.best_fg("#ffffff", "#000000", "#000000"), "#000000")


class LoadJsonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_loads_valid_json(self) -> None:
        path = self.root / "data.json"
        path.write_text('{"a": 1, "b": [true, null]}', encoding="utf-8")
        self.assertEqual(core.load_json(path), {"a": 1, "b": [True, None]})

    def test_loads_unicode(self) -> None:
        path = self.root / "unicode.json"
        path.write_text('{"name": "caf\\u00e9"}', encoding="utf-8")
        self.assertEqual(core.load_json(path), {"name": "caf\u00e9"})

    def test_missing_file_returns_default(self) -> None:
        self.assertIsNone(core.load_json(self.root / "missing.json"))
        self.assertEqual(core.load_json(self.root / "missing.json", {"x": 1}), {"x": 1})

    def test_invalid_json_returns_default(self) -> None:
        path = self.root / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        self.assertEqual(core.load_json(path, "fallback"), "fallback")

    def test_directory_returns_default(self) -> None:
        self.assertEqual(core.load_json(self.root, "fallback"), "fallback")


class LoadPalettesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write_json(self, relative: str, payload) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_loads_sorted_and_fills_missing_slug(self) -> None:
        self.write_json("b.json", {"name": "B"})
        self.write_json("a.json", {"name": "A", "slug": "custom"})
        palettes = core.load_palettes(self.root)
        self.assertEqual([p["name"] for p in palettes], ["A", "B"])
        self.assertEqual(palettes[0]["slug"], "custom")
        self.assertEqual(palettes[1]["slug"], "b")

    def test_skips_metadata_files(self) -> None:
        self.write_json("index.json", {"cards": []})
        self.write_json("schema.json", {"type": "object"})
        self.write_json("real.json", {"name": "Real"})
        palettes = core.load_palettes(self.root)
        self.assertEqual([p["slug"] for p in palettes], ["real"])

    def test_includes_nested_palettes(self) -> None:
        self.write_json("a.json", {"name": "A"})
        self.write_json("community/z.json", {"name": "Z"})
        palettes = core.load_palettes(self.root)
        self.assertEqual([p["slug"] for p in palettes], ["a", "z"])

    def test_skips_non_dict_and_invalid_json(self) -> None:
        self.write_json("array.json", [1, 2, 3])
        self.write_json("string.json", "hello")
        self.write_json("null.json", None)
        (self.root / "broken.json").write_text("{", encoding="utf-8")
        self.assertEqual(core.load_palettes(self.root), [])

    def test_ignores_non_json_files(self) -> None:
        self.write_json("palette.json", {"name": "P"})
        (self.root / "notes.txt").write_text("ignore me", encoding="utf-8")
        self.assertEqual([p["slug"] for p in core.load_palettes(self.root)], ["palette"])

    def test_empty_and_missing_directories(self) -> None:
        self.assertEqual(core.load_palettes(self.root), [])
        self.assertEqual(core.load_palettes(self.root / "missing"), [])

    def test_existing_slug_is_not_overwritten(self) -> None:
        self.write_json("a.json", {"slug": ""})
        self.assertEqual(core.load_palettes(self.root)[0]["slug"], "")


class ActiveSlugTests(unittest.TestCase):
    def test_reads_bar_palette_and_normalizes(self) -> None:
        settings = {"bar": {"palette": "  Foo  "}}
        self.assertEqual(core.active_slug(settings), "foo")

    def test_numeric_palette_is_stringified(self) -> None:
        self.assertEqual(core.active_slug({"bar": {"palette": 7}}), "7")

    def test_missing_or_blank_falls_back_to_default(self) -> None:
        cases = [
            None,
            {},
            {"bar": None},
            {"bar": {}},
            {"bar": {"palette": None}},
            {"bar": {"palette": ""}},
            {"bar": {"palette": "   "}},
            {"bar": []},
            "not-a-dict",
        ]
        for settings in cases:
            with self.subTest(settings=settings):
                self.assertEqual(core.active_slug(settings), core.DEFAULT_SLUG)

    def test_legacy_dock_key_is_ignored(self) -> None:
        self.assertEqual(core.active_slug({"dock": {"palette": "foo"}}),
                         core.DEFAULT_SLUG)


class PaletteTests(unittest.TestCase):
    def test_bg_fg_prefers_top_level_values(self) -> None:
        pal = {
            "background": "#101010",
            "foreground": "#eeeeee",
            "base16": {"color0": "#000000", "color7": "#ffffff"},
        }
        self.assertEqual(core.palette_bg_fg(pal), ("#101010", "#eeeeee"))

    def test_bg_fg_uses_base16_fallback(self) -> None:
        pal = {"base16": {"color0": "#202020", "color7": "#d0d0d0"}}
        self.assertEqual(core.palette_bg_fg(pal), ("#202020", "#d0d0d0"))

    def test_bg_fg_defaults_when_empty(self) -> None:
        self.assertEqual(core.palette_bg_fg({}), ("#000000", "#ffffff"))
        self.assertEqual(core.palette_bg_fg({"base16": {}}), ("#000000", "#ffffff"))

    def test_empty_strings_fall_through(self) -> None:
        pal = {
            "background": "",
            "foreground": "",
            "base16": {"color0": "#111111", "color7": "#eeeeee"},
        }
        self.assertEqual(core.palette_bg_fg(pal), ("#111111", "#eeeeee"))

    def test_palette_hex_background_and_foreground(self) -> None:
        pal = {
            "background": "#101010",
            "foreground": "#f0f0f0",
            "base16": {"color0": "#000000", "color7": "#ffffff"},
        }
        self.assertEqual(core.palette_hex(pal, "background"), "#101010")
        self.assertEqual(core.palette_hex(pal, "foreground"), "#f0f0f0")

    def test_palette_hex_color_entries(self) -> None:
        pal = {"base16": {"color1": "#ff0000", "color2": "#00ff00"}}
        self.assertEqual(core.palette_hex(pal, "color1"), "#ff0000")
        self.assertEqual(core.palette_hex(pal, "color2"), "#00ff00")

    def test_palette_hex_missing_key_uses_fallback(self) -> None:
        self.assertEqual(core.palette_hex({}, "color3"), "#000000")
        self.assertEqual(core.palette_hex({}, "color3", "#abcdef"), "#abcdef")
        self.assertEqual(core.palette_hex({}, "background", "#123456"), "#123456")
        self.assertEqual(core.palette_hex({}, "foreground", "#654321"), "#654321")

    def test_palette_hex_empty_value_uses_fallback(self) -> None:
        pal = {"background": "", "foreground": "", "base16": {"color1": ""}}
        self.assertEqual(core.palette_hex(pal, "background", "#111111"), "#111111")
        self.assertEqual(core.palette_hex(pal, "foreground", "#222222"), "#222222")
        self.assertEqual(core.palette_hex(pal, "color1", "#333333"), "#333333")


class ReadTextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_reads_utf8(self) -> None:
        path = self.root / "file.txt"
        path.write_text("hello\nworld\n", encoding="utf-8")
        self.assertEqual(core.read_text(path), "hello\nworld\n")
        self.assertEqual(core.read_text(str(path)), "hello\nworld\n")

    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(core.read_text(self.root / "missing.txt"), "")

    def test_directory_returns_empty(self) -> None:
        self.assertEqual(core.read_text(self.root), "")

    def test_invalid_utf8_is_replaced(self) -> None:
        path = self.root / "binary.bin"
        path.write_bytes(b"\xff\xfeABC")
        self.assertEqual(core.read_text(path), "\ufffd\ufffdABC")


class AtomicWriteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_creates_parent_directories_and_writes_content(self) -> None:
        path = self.root / "a" / "b" / "file.txt"
        core.atomic_write(path, "payload\n")
        self.assertEqual(path.read_text(encoding="utf-8"), "payload\n")

    def test_leaves_no_temporary_file_behind(self) -> None:
        path = self.root / "file.txt"
        core.atomic_write(path, "first")
        core.atomic_write(path, "second")
        self.assertEqual(path.read_text(encoding="utf-8"), "second")
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["file.txt"])

    def test_replaces_existing_target_content(self) -> None:
        path = self.root / "file.txt"
        path.write_text("old content that is longer", encoding="utf-8")
        core.atomic_write(path, "new")
        self.assertEqual(path.read_text(encoding="utf-8"), "new")
        self.assertFalse((self.root / "file.txt.xsc.tmp").exists())

    def test_empty_text_is_written(self) -> None:
        path = self.root / "empty.txt"
        core.atomic_write(path, "")
        self.assertEqual(path.read_text(encoding="utf-8"), "")
        self.assertFalse((self.root / "empty.txt.xsc.tmp").exists())


class StripBlockTests(unittest.TestCase):
    def test_removes_block_and_reports_found(self) -> None:
        lines = ["before", "BEGIN", "managed", "END", "after"]
        kept, found = core.strip_block(lines, "BEGIN", "END")
        self.assertTrue(found)
        self.assertEqual(kept, ["before", "after"])

    def test_indentation_is_tolerated(self) -> None:
        lines = ["  BEGIN  ", "  managed", "\tEND\t", "tail"]
        kept, found = core.strip_block(lines, "BEGIN", "END")
        self.assertTrue(found)
        self.assertEqual(kept, ["tail"])

    def test_no_block_keeps_everything(self) -> None:
        lines = ["one", "two", "three"]
        kept, found = core.strip_block(lines, "BEGIN", "END")
        self.assertFalse(found)
        self.assertEqual(kept, lines)

    def test_removes_multiple_blocks(self) -> None:
        lines = ["a", "BEGIN", "x", "END", "b", "BEGIN", "y", "END", "c"]
        kept, found = core.strip_block(lines, "BEGIN", "END")
        self.assertTrue(found)
        self.assertEqual(kept, ["a", "b", "c"])

    def test_begin_without_end_drops_the_tail(self) -> None:
        lines = ["before", "BEGIN", "managed", "also managed"]
        kept, found = core.strip_block(lines, "BEGIN", "END")
        self.assertTrue(found)
        self.assertEqual(kept, ["before"])

    def test_empty_input(self) -> None:
        kept, found = core.strip_block([], "BEGIN", "END")
        self.assertFalse(found)
        self.assertEqual(kept, [])


class FindBinaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.local_bin = self.home / ".local" / "bin"
        self.local_bin.mkdir(parents=True)

    def make_executable(self, name: str, mode: int = 0o755) -> Path:
        path = self.local_bin / name
        path.write_text("#!/bin/sh\n", encoding="utf-8")
        path.chmod(mode)
        return path

    def test_path_result_wins_over_home_fallback(self) -> None:
        self.make_executable("tool")
        with mock.patch.object(core.shutil, "which", return_value="/usr/bin/tool"):
            self.assertEqual(core.find_binary("tool", self.home), "/usr/bin/tool")

    def test_falls_back_to_local_bin(self) -> None:
        path = self.make_executable("tool")
        with mock.patch.object(core.shutil, "which", return_value=None):
            self.assertEqual(core.find_binary("tool", self.home), str(path))

    def test_non_executable_fallback_is_rejected(self) -> None:
        self.make_executable("tool", mode=0o644)
        with mock.patch.object(core.shutil, "which", return_value=None), \
                mock.patch.object(core.os, "access", return_value=False):
            self.assertIsNone(core.find_binary("tool", self.home))

    def test_missing_binary_returns_none(self) -> None:
        with mock.patch.object(core.shutil, "which", return_value=None):
            self.assertIsNone(core.find_binary("missing", self.home))

    def test_no_home_means_no_fallback(self) -> None:
        self.make_executable("tool")
        with mock.patch.object(core.shutil, "which", return_value=None):
            self.assertIsNone(core.find_binary("tool"))

    def test_directory_is_not_a_binary(self) -> None:
        (self.local_bin / "tool").mkdir()
        with mock.patch.object(core.shutil, "which", return_value=None):
            self.assertIsNone(core.find_binary("tool", self.home))


if __name__ == "__main__":
    unittest.main()
