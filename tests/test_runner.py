from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from themesync import runner
from themesync.core import Env


class FakeTarget:
    """Test double for a target module (NAME/DESCRIPTION/available/apply)."""

    def __init__(
        self,
        name: str,
        *,
        description: str = "target description",
        available: bool = True,
        available_error: Exception | None = None,
        apply_error: Exception | None = None,
        output=(),
        notes=(),
    ) -> None:
        self.NAME = name
        self.DESCRIPTION = description
        self._available = available
        self._available_error = available_error
        self._apply_error = apply_error
        self._output = list(output)
        self._notes = list(notes)
        self.available_calls = 0
        self.apply_calls = 0

    def available(self, env) -> bool:
        self.available_calls += 1
        if self._available_error is not None:
            raise self._available_error
        return self._available

    def apply(self, env) -> list:
        self.apply_calls += 1
        for note in self._notes:
            env.note(note)
        if self._apply_error is not None:
            raise self._apply_error
        return list(self._output)


class RunnerTestCase(unittest.TestCase):
    def make_env(self) -> Env:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        return Env(
            home=root,
            palettes_dir=root / "palettes",
            settings_path=root / "settings.json",
            slug="x",
            palettes=[],
            palette={},
        )

    def install_targets(self, targets) -> list:
        """Replace the registry with fakes, keeping TARGETS and BY_NAME in sync."""
        targets = list(targets)
        patchers = (
            mock.patch.object(runner, "TARGETS", targets),
            mock.patch.object(runner, "BY_NAME", {t.NAME: t for t in targets}),
        )
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        return targets

    def run_captured(self, env: Env, only: list | None = None) -> tuple[int, list]:
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = runner.run(env, only=only)
        return code, stream.getvalue().splitlines()


class RunAvailabilityTests(RunnerTestCase):
    def test_runs_available_targets_and_reports_skipped_ones(self) -> None:
        first = FakeTarget("alpha", output=["alpha applied"])
        skipped = FakeTarget("beta", available=False)
        third = FakeTarget("gamma", output=["gamma applied"])
        self.install_targets([first, skipped, third])
        env = self.make_env()

        code, lines = self.run_captured(env)

        self.assertEqual(code, 0)
        self.assertEqual(lines, [
            "alpha applied",
            "beta: not available; skipped",
            "gamma applied",
        ])
        self.assertEqual(first.apply_calls, 1)
        self.assertEqual(skipped.apply_calls, 0)
        self.assertEqual(third.apply_calls, 1)
        self.assertEqual(
            [first.available_calls, skipped.available_calls, third.available_calls],
            [1, 1, 1],
        )

    def test_all_targets_unavailable_is_still_success(self) -> None:
        first = FakeTarget("alpha", available=False)
        second = FakeTarget("beta", available=False)
        self.install_targets([first, second])
        env = self.make_env()

        code, lines = self.run_captured(env)

        self.assertEqual(code, 0)
        self.assertEqual(lines, [
            "alpha: not available; skipped",
            "beta: not available; skipped",
        ])
        self.assertEqual(first.apply_calls, 0)
        self.assertEqual(second.apply_calls, 0)

    def test_notes_from_a_successful_target_follow_its_output(self) -> None:
        target = FakeTarget(
            "alpha",
            output=["alpha applied"],
            notes=["note one", "note two"],
        )
        self.install_targets([target])
        env = self.make_env()

        code, lines = self.run_captured(env)

        self.assertEqual(code, 0)
        self.assertEqual(lines, ["alpha applied", "note one", "note two"])


class RunSelectionTests(RunnerTestCase):
    def test_only_runs_selected_targets_in_requested_order(self) -> None:
        alpha = FakeTarget("alpha", output=["alpha applied"])
        beta = FakeTarget("beta", output=["beta applied"])
        gamma = FakeTarget("gamma", output=["gamma applied"])
        delta = FakeTarget("delta", output=["delta applied"])
        self.install_targets([alpha, beta, gamma, delta])
        env = self.make_env()

        code, lines = self.run_captured(env, only=["gamma", "alpha"])

        self.assertEqual(code, 0)
        self.assertEqual(lines, ["gamma applied", "alpha applied"])
        self.assertEqual([alpha.apply_calls, gamma.apply_calls], [1, 1])
        # Unselected targets are never even probed.
        self.assertEqual([beta.available_calls, delta.available_calls], [0, 0])
        self.assertEqual([beta.apply_calls, delta.apply_calls], [0, 0])

    def test_only_skips_selected_unavailable_targets_without_failing(self) -> None:
        alpha = FakeTarget("alpha", output=["alpha applied"])
        beta = FakeTarget("beta", available=False)
        self.install_targets([alpha, beta])
        env = self.make_env()

        code, lines = self.run_captured(env, only=["beta", "alpha"])

        self.assertEqual(code, 0)
        self.assertEqual(lines, [
            "beta: not available; skipped",
            "alpha applied",
        ])
        self.assertEqual(beta.apply_calls, 0)
        self.assertEqual(alpha.apply_calls, 1)

    def test_unknown_names_are_reported_and_make_run_fail(self) -> None:
        alpha = FakeTarget("alpha", output=["alpha applied"])
        self.install_targets([alpha])
        env = self.make_env()

        code, lines = self.run_captured(
            env, only=["alpha", "missing", "also-missing"]
        )

        self.assertEqual(code, 1)
        self.assertEqual(lines, [
            "unknown target: missing",
            "unknown target: also-missing",
            "alpha applied",
        ])
        self.assertEqual(alpha.apply_calls, 1)

    def test_only_unknown_names_runs_nothing(self) -> None:
        alpha = FakeTarget("alpha", output=["alpha applied"])
        self.install_targets([alpha])
        env = self.make_env()

        code, lines = self.run_captured(env, only=["missing"])

        self.assertEqual(code, 1)
        self.assertEqual(lines, ["unknown target: missing"])
        self.assertEqual(alpha.available_calls, 0)
        self.assertEqual(alpha.apply_calls, 0)

    def test_empty_only_list_behaves_like_no_filter(self) -> None:
        alpha = FakeTarget("alpha", output=["alpha applied"])
        beta = FakeTarget("beta", output=["beta applied"])
        self.install_targets([alpha, beta])
        env = self.make_env()

        code, lines = self.run_captured(env, only=[])

        self.assertEqual(code, 0)
        self.assertEqual(lines, ["alpha applied", "beta applied"])
        self.assertEqual(alpha.apply_calls, 1)
        self.assertEqual(beta.apply_calls, 1)


class RunFailureTests(RunnerTestCase):
    def test_failing_target_does_not_abort_remaining_targets(self) -> None:
        boom = FakeTarget("boom", apply_error=RuntimeError("kaboom"))
        after = FakeTarget("after", output=["after applied"])
        self.install_targets([boom, after])
        env = self.make_env()

        code, lines = self.run_captured(env)

        self.assertEqual(code, 1)
        self.assertEqual(lines, [
            "boom: ERROR: kaboom",
            "after applied",
        ])
        self.assertEqual(boom.apply_calls, 1)
        self.assertEqual(after.apply_calls, 1)

    def test_failure_notes_are_flushed_before_continuing(self) -> None:
        boom = FakeTarget(
            "boom",
            notes=["boom note"],
            apply_error=RuntimeError("kaboom"),
        )
        after = FakeTarget("after", output=["after applied"])
        self.install_targets([boom, after])
        env = self.make_env()

        code, lines = self.run_captured(env)

        self.assertEqual(code, 1)
        self.assertEqual(lines, [
            "boom: ERROR: kaboom",
            "boom note",
            "after applied",
        ])

    def test_available_failure_is_recorded_and_does_not_stop_others(self) -> None:
        broken = FakeTarget("broken", available_error=RuntimeError("probe failed"))
        after = FakeTarget("after", output=["after applied"])
        self.install_targets([broken, after])
        env = self.make_env()

        code, lines = self.run_captured(env)

        self.assertEqual(code, 1)
        self.assertEqual(lines, [
            "broken: ERROR: probe failed",
            "after applied",
        ])
        self.assertEqual(broken.apply_calls, 0)
        self.assertEqual(after.apply_calls, 1)

    def test_multiple_failures_run_every_target_and_return_failure(self) -> None:
        first = FakeTarget("first", apply_error=RuntimeError("first failed"))
        middle = FakeTarget("middle", output=["middle applied"])
        last = FakeTarget("last", available_error=RuntimeError("last failed"))
        self.install_targets([first, middle, last])
        env = self.make_env()

        code, lines = self.run_captured(env)

        self.assertEqual(code, 1)
        self.assertEqual(lines, [
            "first: ERROR: first failed",
            "middle applied",
            "last: ERROR: last failed",
        ])
        self.assertEqual(first.apply_calls, 1)
        self.assertEqual(middle.apply_calls, 1)
        self.assertEqual(last.apply_calls, 0)


class ListingTests(RunnerTestCase):
    def test_lists_names_availability_and_descriptions_in_order(self) -> None:
        kitty = FakeTarget("kitty", description="Kitty target", available=True)
        gtk = FakeTarget("gtk", description="GTK target", available=False)
        long_name = FakeTarget(
            "verylongname", description="Long description", available=True
        )
        self.install_targets([kitty, gtk, long_name])
        env = self.make_env()

        lines = runner.listing(env)

        self.assertEqual(lines, [
            "kitty     yes  Kitty target",
            "gtk       --  GTK target",
            "verylongname yes  Long description",
        ])

    def test_available_errors_are_listed_as_unavailable(self) -> None:
        alpha = FakeTarget("alpha", description="A target", available=True)
        broken = FakeTarget(
            "broken",
            description="B target",
            available_error=RuntimeError("probe failed"),
        )
        gamma = FakeTarget("gamma", description="C target", available=True)
        self.install_targets([alpha, broken, gamma])
        env = self.make_env()

        lines = runner.listing(env)

        self.assertEqual(lines, [
            "alpha     yes  A target",
            "broken    --  B target",
            "gamma     yes  C target",
        ])

    def test_listing_never_applies_a_target(self) -> None:
        target = FakeTarget("alpha", output=["applied"])
        self.install_targets([target])
        env = self.make_env()

        runner.listing(env)

        self.assertEqual(target.available_calls, 1)
        self.assertEqual(target.apply_calls, 0)

    def test_empty_registry_returns_no_lines(self) -> None:
        self.install_targets([])
        env = self.make_env()

        self.assertEqual(runner.listing(env), [])


if __name__ == "__main__":
    unittest.main()
