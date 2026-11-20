"""Clean Markdown and dual-series SVG report generators for backtest comparisons."""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.backtest.simulator import BacktestReport


def render_comparison_markdown(reports: list[BacktestReport], title: str = "Quant Robot Backtest Comparison") -> str:
    lines = [
        f"# {title}",
        "",
        "> 仅研究与模拟盘评估（含真实最低佣金、滑点、整手约束与 T+1 因果执行），不构成实盘盈利承诺。",
        "",
        "| 策略 | 市场 | 区间 | 初始资金 | 期末净值 | 总收益 | 年化(CAGR) | 夏普 | 最大回撤 | 交易次数 | 费用合计 | 跑赢买入持有 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rep in reports:
        m = rep.metrics
        fees = m.get("total_commission", 0.0) + m.get("total_slippage", 0.0)
        ex = m.get("excess_total_return", 0.0)
        lines.append(
            f"| {rep.name} | {rep.market} | {rep.start_date} ~ {rep.end_date} | "
            f"{m['initial_cash']:,.0f} {rep.currency} | {m['final_nav']:,.2f} | "
            f"{m['total_return']:+.2%} | {m['cagr']:+.2%} | {m['sharpe']:.2f} | "
            f"{m['max_drawdown']:.2%} | {int(m['trade_count'])} | {fees:,.2f} | {ex:+.2%} |"
        )
    lines.append("")
    for rep in reports:
        lines.append(f"## {rep.name} — 年度明细")
        lines.append("")
        lines.append("| 年份 | 策略收益 | 等权买入持有 | 最大回撤 | 成交笔数 |")
        lines.append("| ---: | ---: | ---: | ---: | ---: |")
        for yr in rep.yearly_returns:
            b = f"{yr['benchmark_return']:+.2%}" if "benchmark_return" in yr else "-"
            lines.append(
                f"| {yr['year']} | {yr['strategy_return']:+.2%} | {b} | {yr['max_drawdown']:.2%} | {yr['trades']} |"
            )
        lines.append("")
    return "\n".join(lines)


def write_comparison_svg(eq_df: pd.DataFrame, path: str | Path, title: str) -> Path:
    """Write a clean dark-friendly SVG chart comparing strategy NAV vs benchmark NAV."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    svg = render_equity_svg(eq_df, title)
    out.write_text(svg, encoding="utf-8")
    return out


def render_equity_svg(eq_df: pd.DataFrame, title: str) -> str:
    width, height = 760, 320
    left, right, top, bottom = 64, 24, 38, 36
    iw, ih = width - left - right, height - top - bottom
    if eq_df.empty or "nav" not in eq_df.columns:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"></svg>'

    dates = list(eq_df["date"].astype(str))
    navs = [float(v) for v in eq_df["nav"]]
    has_bench = "benchmark_nav" in eq_df.columns and eq_df["benchmark_nav"].notna().any()
    bench = [float(v) for v in eq_df["benchmark_nav"]] if has_bench else []

    all_vals = navs + bench
    y_min, y_max = min(all_vals), max(all_vals)
    if y_max <= y_min:
        y_min -= 1.0
        y_max += 1.0
    pad = (y_max - y_min) * 0.06
    y_min -= pad
    y_max += pad

    def to_points(vals: list[float]) -> str:
        n = max(len(vals) - 1, 1)
        pts = []
        for i, v in enumerate(vals):
            x = left + iw * i / n
            y = top + ih - ((v - y_min) / (y_max - y_min) * ih)
            pts.append(f"{x:.1f},{y:.1f}")
        return " ".join(pts)

    strat_pts = to_points(navs)
    bench_svg = (
        f'<polyline fill="none" stroke="#94a3b8" stroke-width="1.6" stroke-dasharray="5,4" points="{to_points(bench)}"/>'
        if has_bench
        else ""
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" rx="8" fill="#0f172a"/>'
        f'<text x="{left}" y="24" fill="#f8fafc" font-family="Segoe UI,sans-serif" font-size="14" font-weight="600">{escape(title)}</text>'
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#334155" stroke-width="1"/>'
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#334155" stroke-width="1"/>'
        f'<text x="8" y="{top+10}" fill="#94a3b8" font-family="Segoe UI,sans-serif" font-size="11">{y_max:,.1f}</text>'
        f'<text x="8" y="{height-bottom}" fill="#94a3b8" font-family="Segoe UI,sans-serif" font-size="11">{y_min:,.1f}</text>'
        f'<text x="{left}" y="{height-12}" fill="#94a3b8" font-family="Segoe UI,sans-serif" font-size="11">{escape(dates[0])}</text>'
        f'<text x="{width-right-76}" y="{height-12}" fill="#94a3b8" font-family="Segoe UI,sans-serif" font-size="11">{escape(dates[-1])}</text>'
        f"{bench_svg}"
        f'<polyline fill="none" stroke="#38bdf8" stroke-width="2.4" points="{strat_pts}"/>'
        f"</svg>"
    )
