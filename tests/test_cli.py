import unittest

from datetime import date

from github_contribution_charts.cli import Point, aggregate, nice_ceiling, one_year_before, render_svg


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


if __name__ == "__main__":
    unittest.main()
