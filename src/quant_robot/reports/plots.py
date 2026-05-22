from __future__ import annotations

import math
from html import escape
from pathlib import Path

import pandas as pd


def write_line_svg(frame: pd.DataFrame, x_column: str, y_column: str, path: str | Path, title: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    points = _clean_points(frame, x_column, y_column)
    svg = _render_svg(points, title)
    path.write_text(svg, encoding="utf-8")
    return path


def _clean_points(frame: pd.DataFrame, x_column: str, y_column: str) -> list[tuple[str, float]]:
    if frame.empty or x_column not in frame.columns or y_column not in frame.columns:
        return []
    points = []
    for row in frame[[x_column, y_column]].dropna().itertuples(index=False):
        value = float(row[1])
        if math.isfinite(value):
            points.append((str(row[0]), value))
    return points


def _render_svg(points: list[tuple[str, float]], title: str) -> str:
    width = 720
    height = 360
    left = 56
    right = 24
    top = 40
    bottom = 44
    inner_width = width - left - right
    inner_height = height - top - bottom
    if not points:
        polyline = ""
        y_min = 0.0
        y_max = 1.0
    else:
        values = [value for _, value in points]
        y_min = min(values)
        y_max = max(values)
        if y_min == y_max:
            y_min -= 0.5
            y_max += 0.5
        coords = []
        for index, (_, value) in enumerate(points):
            x = left + (inner_width * index / max(len(points) - 1, 1))
            y = top + inner_height - ((value - y_min) / (y_max - y_min) * inner_height)
            coords.append(f"{x:.2f},{y:.2f}")
        polyline = " ".join(coords)
    first_label = escape(points[0][0]) if points else ""
    last_label = escape(points[-1][0]) if points else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="{left}" y="24" font-family="Arial, sans-serif" font-size="16" font-weight="700">{escape(title)}</text>
  <line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="#222" stroke-width="1"/>
  <line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="#222" stroke-width="1"/>
  <text x="8" y="{top + 4}" font-family="Arial, sans-serif" font-size="11" fill="#555">{y_max:.4f}</text>
  <text x="8" y="{height - bottom}" font-family="Arial, sans-serif" font-size="11" fill="#555">{y_min:.4f}</text>
  <text x="{left}" y="{height - 14}" font-family="Arial, sans-serif" font-size="11" fill="#555">{first_label}</text>
  <text x="{width - right - 96}" y="{height - 14}" font-family="Arial, sans-serif" font-size="11" fill="#555">{last_label}</text>
  <polyline fill="none" stroke="#1f77b4" stroke-width="2.5" points="{polyline}"/>
</svg>
"""
