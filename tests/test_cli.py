import unittest
from datetime import date
from subprocess import CompletedProcess
from unittest.mock import patch

from github_contribution_charts.cli import Point, aggregate, fetch, nice_ceiling, one_year_before, render_svg


class ChartTests(unittest.TestCase):
    def test_monthly_aggregation(self):
        points = [
            Point("2026-01-01", 2),
            Point("2026-01-31", 3),
            Point("2026-02-01", 7),
        ]
        self.assertEqual(
            aggregate(points, "month"),
            [Point("2026-01", 5), Point("2026-02", 7)],
        )

    def test_weekly_aggregation_starts_on_monday(self):
        points = [Point("2026-01-04", 2), Point("2026-01-05", 3)]
        self.assertEqual(
            aggregate(points, "week"),
            [Point("2025-12-29", 2), Point("2026-01-05", 3)],
        )

    def test_svg_escapes_title(self):
        svg = render_svg([Point("2026-01", 4)], chart_type="bar", title="A & B")
        self.assertIn("A &amp; B", svg)
        self.assertIn("<rect", svg)

    def test_nice_ceiling(self):
        self.assertEqual(nice_ceiling(0), 5)
        self.assertEqual(nice_ceiling(47), 50)
        self.assertEqual(nice_ceiling(101), 200)

    def test_one_year_before_handles_leap_day(self):
        self.assertEqual(one_year_before(date(2024, 2, 29)), date(2023, 2, 28))

    @patch("github_contribution_charts.cli.subprocess.run")
    def test_fetch_can_target_public_user(self, run):
        run.return_value = CompletedProcess(
            args=[],
            returncode=0,
            stdout='{"data":{"user":{"login":"legendhimself"}}}',
            stderr="",
        )
        user = fetch(date(2026, 1, 1), date(2026, 2, 1), "legendhimself")
        self.assertEqual(user["login"], "legendhimself")
        command = run.call_args.args[0]
        self.assertIn("login=legendhimself", command)
        self.assertTrue(any("user(login: $login)" in argument for argument in command))


if __name__ == "__main__":
    unittest.main()
