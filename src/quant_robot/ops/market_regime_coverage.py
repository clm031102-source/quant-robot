from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_6_0_market_regime_coverage"


def build_market_regime_coverage_pack(
    regime_rows: list[dict[str, Any]] | pd.DataFrame,
    *,
    min_regimes: int = 2,
    min_rows_per_regime: int = 5,
    positive_threshold: float = 0.02,
    negative_threshold: float = -0.02,
) -> dict[str, Any]:
    frame = _frame(regime_rows)
    classified = _classified_rows(frame, positive_threshold, negative_threshold)
    eligible = classified[classified["regime_label"] != "unknown"] if not classified.empty else classified
    counts = {str(key): int(value) for key, value in eligible["regime_label"].value_counts().sort_index().items()} if not eligible.empty else {}
    regimes = sorted(regime for regime, count in counts.items() if count >= min_rows_per_regime)
    blockers: list[str] = []
    if classified.empty:
        blockers.append("market_regime_rows_missing")
    if len(regimes) < min_regimes:
        blockers.append("market_regimes_below_minimum")
    status = "sufficient" if not blockers else "insufficient"
    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "summary": {
            "rows": int(len(classified)),
            "covered_regimes": len(regimes),
            "min_regimes": int(min_regimes),
            "min_rows_per_regime": int(min_rows_per_regime),
            "regimes": regimes,
            "regime_counts": counts,
            "observation_start": _date_value(classified["date"].min()) if "date" in classified else None,
            "observation_end": _date_value(classified["date"].max()) if "date" in classified else None,
        },
        "decision": {
            "market_regime_coverage_cleared": not blockers,
            "blockers": blockers,
        },
        "live_boundary_allowed": False,
        "safety": _safety(),
        "regime_ledger": _records(classified),
    }
    pack["markdown"] = render_market_regime_coverage_markdown(pack)
    return pack


def write_market_regime_coverage_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "market_regime_coverage_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "market_regime_coverage_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("regime_ledger", [])).to_csv(output_path / "market_regime_coverage_ledger.csv", index=False)


def render_market_regime_coverage_markdown(pack: dict[str, Any]) -> str:
    summary = _dict(pack.get("summary"))
    decision = _dict(pack.get("decision"))
    lines = [
        "# Market Regime Coverage",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Status: {pack.get('status', 'unknown')}",
        f"- Rows: {summary.get('rows', 0)}",
        f"- Covered regimes: {summary.get('covered_regimes', 0)}",
        f"- Minimum regimes: {summary.get('min_regimes', 0)}",
        f"- Regimes: {', '.join(_as_list(summary.get('regimes')))}",
        f"- Cleared: {decision.get('market_regime_coverage_cleared', False)}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', _safety())}",
        "",
        "## Blockers",
        "",
    ]
    blockers = _as_list(decision.get("blockers"))
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _classified_rows(frame: pd.DataFrame, positive_threshold: float, negative_threshold: float) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["date", "regime_momentum", "regime_label"])
    rows = frame.copy()
    if "regime_momentum" not in rows.columns:
        rows["regime_momentum"] = None
    rows["regime_momentum"] = pd.to_numeric(rows["regime_momentum"], errors="coerce")
    rows["regime_label"] = rows["regime_momentum"].apply(lambda value: _regime_label(value, positive_threshold, negative_threshold))
    columns = [column for column in ("date", "regime_momentum", "regime_allowed", "regime_label") if column in rows.columns]
    return rows[columns].reset_index(drop=True)


def _regime_label(value: Any, positive_threshold: float, negative_threshold: float) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "unknown"
    numeric = float(value)
    if numeric > positive_threshold:
        return "bull"
    if numeric < negative_threshold:
        return "bear"
    return "sideways"


def _frame(rows: list[dict[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame(rows)


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return [_sanitize(row) for row in frame.to_dict(orient="records")]


def _sanitize(row: dict[str, Any]) -> dict[str, Any]:
    clean = {}
    for key, value in row.items():
        if isinstance(value, float) and math.isnan(value):
            clean[str(key)] = None
        else:
            clean[str(key)] = value
    return clean


def _date_value(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return str(value)[:10]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _safety() -> str:
    return "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
