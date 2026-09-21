from __future__ import annotations

import argparse
import csv
import html
import json
import math
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


QUERY = """
query ContributionCalendar($from: DateTime!, $to: DateTime!) {
  viewer {
    login
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


@dataclass(frozen=True)
class Point:
    label: str
    value: int


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from error


def iso_datetime(day: date, *, end: bool = False) -> str:
    clock = "23:59:59Z" if end else "00:00:00Z"
    return f"{day.isoformat()}T{clock}"


def one_year_before(day: date) -> date:
    try:
        return day.replace(year=day.year - 1)
    except ValueError:  # February 29
        return day.replace(year=day.year - 1, day=28)


def fetch(from_day: date, to_day: date) -> dict:
    command = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={QUERY}",
        "-F",
        f"from={iso_datetime(from_day)}",
        "-F",
        f"to={iso_datetime(to_day, end=True)}",
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError("GitHub CLI (`gh`) was not found in PATH") from None
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or "GitHub API request failed"
        raise RuntimeError(message) from None

    payload = json.loads(result.stdout)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0].get("message", "GraphQL request failed"))
    return payload["data"]["viewer"]


def daily_points(viewer: dict) -> list[Point]:
    weeks = viewer["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [
        Point(day["date"], day["contributionCount"])
        for week in weeks
        for day in week["contributionDays"]
    ]


def aggregate(points: Iterable[Point], group: str) -> list[Point]:
    if group == "day":
        return list(points)

    totals: dict[str, int] = defaultdict(int)
    for point in points:
        day = date.fromisoformat(point.label)
        if group == "week":
            monday = day - timedelta(days=day.weekday())
            key = monday.isoformat()
        else:
            key = day.strftime("%Y-%m")
        totals[key] += point.value
    return [Point(key, totals[key]) for key in sorted(totals)]


def nice_ceiling(value: int) -> int:
    if value <= 5:
        return max(5, value)
    magnitude = 10 ** math.floor(math.log10(value))
    normalized = value / magnitude
    step = 1 if normalized <= 1 else 2 if normalized <= 2 else 5 if normalized <= 5 else 10
    return step * magnitude


def render_svg(points: list[Point], *, chart_type: str, title: str) -> str:
    width, height = 1200, 620
    left, right, top, bottom = 84, 32, 72, 82
    plot_width = width - left - right
    plot_height = height - top - bottom
    maximum = nice_ceiling(max((point.value for point in points), default=0))
    green = "#2da44e"
    grid = "#d0d7de"
    ink = "#24292f"
    muted = "#57606a"

    def x(index: int) -> float:
        if len(points) <= 1:
            return left + plot_width / 2
        return left + (index / (len(points) - 1)) * plot_width

    def y(value: int) -> float:
        return top + plot_height - (value / maximum) * plot_height

    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="14" fill="#ffffff"/>',
        f'<text x="{left}" y="38" font-family="system-ui,sans-serif" font-size="24" font-weight="650" fill="{ink}">{html.escape(title)}</text>',
    ]

    for tick in range(6):
        value = round(maximum * tick / 5)
        yy = y(value)
        pieces.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="{grid}" stroke-width="1"/>')
        pieces.append(f'<text x="{left-12}" y="{yy+5:.1f}" text-anchor="end" font-family="system-ui,sans-serif" font-size="13" fill="{muted}">{value}</text>')

    if chart_type == "line" and points:
        coordinates = " ".join(f"{x(i):.1f},{y(point.value):.1f}" for i, point in enumerate(points))
        area = f"{left},{top+plot_height} {coordinates} {width-right},{top+plot_height}"
        pieces.append(f'<polygon points="{area}" fill="{green}" opacity="0.12"/>')
        pieces.append(f'<polyline points="{coordinates}" fill="none" stroke="{green}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
    elif points:
        slot = plot_width / len(points)
        bar_width = max(1.5, slot * 0.76)
        for i, point in enumerate(points):
            xx = left + i * slot + (slot - bar_width) / 2
            yy = y(point.value)
            pieces.append(f'<rect x="{xx:.1f}" y="{yy:.1f}" width="{bar_width:.1f}" height="{top+plot_height-yy:.1f}" rx="2" fill="{green}"/>')

    label_count = min(12, len(points))
    if label_count:
        indexes = sorted({round(i * (len(points) - 1) / max(1, label_count - 1)) for i in range(label_count)})
        for index in indexes:
            xx = (
                left + (index + 0.5) * (plot_width / len(points))
                if chart_type == "bar"
                else x(index)
            )
            label = html.escape(points[index].label)
            pieces.append(f'<text x="{xx:.1f}" y="{height-42}" text-anchor="middle" font-family="system-ui,sans-serif" font-size="12" fill="{muted}">{label}</text>')

    pieces.append(f'<text x="20" y="{top+plot_height/2}" transform="rotate(-90 20 {top+plot_height/2})" text-anchor="middle" font-family="system-ui,sans-serif" font-size="14" fill="{muted}">Contributions</text>')
    pieces.append("</svg>")
    return "\n".join(pieces)


def write_csv(path: Path, points: list[Point]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["period", "contributions"])
        writer.writerows((point.label, point.value) for point in points)


def parser() -> argparse.ArgumentParser:
    today = datetime.now(timezone.utc).date()
    result = argparse.ArgumentParser(
        prog="gh-contrib-chart",
        description="Generate an SVG chart from your GitHub contribution calendar.",
    )
    result.add_argument("--type", choices=("line", "bar"), default="line")
    result.add_argument("--group", choices=("day", "week", "month"), default="day")
    result.add_argument("--from", dest="from_day", type=parse_date, default=one_year_before(today))
    result.add_argument("--to", dest="to_day", type=parse_date, default=today)
    result.add_argument("--output", type=Path, default=Path("github-contributions.svg"))
    result.add_argument("--csv", type=Path, help="also export the aggregated data as CSV")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.from_day > args.to_day:
        print("error: --from must not be later than --to", file=sys.stderr)
        return 2
    if (args.to_day - args.from_day).days > 366:
        print("error: GitHub contribution windows cannot exceed one year", file=sys.stderr)
        return 2

    try:
        viewer = fetch(args.from_day, args.to_day)
        points = aggregate(daily_points(viewer), args.group)
    except (RuntimeError, KeyError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    calendar = viewer["contributionsCollection"]["contributionCalendar"]
    period_name = {"day": "daily", "week": "weekly", "month": "monthly"}[args.group]
    title = (
        f"@{viewer['login']} · {calendar['totalContributions']:,} GitHub contributions"
        f" · {period_name}"
    )
    args.output.write_text(render_svg(points, chart_type=args.type, title=title), encoding="utf-8")
    if args.csv:
        write_csv(args.csv, points)

    print(f"Created {args.output}")
    if args.csv:
        print(f"Created {args.csv}")
    return 0
