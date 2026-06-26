from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


STAGE = "trade_capacity_stress"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def summarize_capacity_stress(
    trades: pd.DataFrame,
    *,
    candidate_name: str,
    multipliers: tuple[float, ...] = (1, 5, 10, 20, 50, 100),
    max_participation_rate: float = 0.05,
) -> list[dict[str, Any]]:
    if "participation_rate" not in trades.columns:
        raise ValueError("trades must include participation_rate")

    frame = trades.copy()
    if "entry_allowed" in frame.columns:
        entry_allowed = frame["entry_allowed"].fillna(False).astype(bool)
    else:
        entry_allowed = pd.Series(True, index=frame.index)

    allowed = frame.loc[entry_allowed]
    participation = pd.to_numeric(allowed["participation_rate"], errors="coerce").fillna(0.0).clip(lower=0.0)
    total_rows = int(len(frame))
    allowed_rows = int(len(allowed))
    blocked_rows = total_rows - allowed_rows
    blocked_rate = blocked_rows / total_rows if total_rows else 0.0

    rows: list[dict[str, Any]] = []
    for multiplier in multipliers:
        scaled = participation * float(multiplier)
        breach_mask = scaled > max_participation_rate
        breach_trades = int(breach_mask.sum())
        breach_rate = breach_trades / allowed_rows if allowed_rows else 0.0
        rows.append(
            {
                "candidate_name": candidate_name,
                "aum_multiplier": _clean_number(float(multiplier)),
                "max_participation_rate_limit": max_participation_rate,
                "total_trade_rows": total_rows,
                "entry_allowed_rows": allowed_rows,
                "entry_blocked_rows": blocked_rows,
                "entry_blocked_rate": blocked_rate,
                "mean_scaled_participation_rate": _series_stat(scaled, "mean"),
                "median_scaled_participation_rate": _series_stat(scaled, "median"),
                "p95_scaled_participation_rate": _series_quantile(scaled, 0.95),
                "p99_scaled_participation_rate": _series_quantile(scaled, 0.99),
                "max_scaled_participation_rate": _series_stat(scaled, "max"),
                "capacity_breach_trades": breach_trades,
                "capacity_breach_rate": breach_rate,
                "capacity_safe": breach_trades == 0,
            }
        )
    return rows


def build_trade_capacity_stress(
    trade_sources: Mapping[str, pd.DataFrame | str | Path],
    *,
    multipliers: tuple[float, ...] = (1, 5, 10, 20, 50, 100),
    max_participation_rate: float = 0.05,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    sources: dict[str, str] = {}
    for candidate_name, source in trade_sources.items():
        if isinstance(source, pd.DataFrame):
            frame = source
            sources[candidate_name] = "<dataframe>"
        else:
            source_path = Path(source)
            frame = pd.read_parquet(source_path)
            sources[candidate_name] = str(source_path)
        rows.extend(
            summarize_capacity_stress(
                frame,
                candidate_name=candidate_name,
                multipliers=multipliers,
                max_participation_rate=max_participation_rate,
            )
        )

    safe_rows = sum(1 for row in rows if row["capacity_safe"])
    return {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "sources": sources,
        "parameters": {
            "multipliers": list(multipliers),
            "max_participation_rate": max_participation_rate,
        },
        "summary": {
            "candidate_count": len(trade_sources),
            "row_count": len(rows),
            "safe_rows": safe_rows,
            "unsafe_rows": len(rows) - safe_rows,
        },
        "rows": rows,
        "safety": SAFETY,
    }


def write_trade_capacity_stress(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    rows = pd.DataFrame(audit.get("rows", []))
    rows.to_csv(output_path / "trade_capacity_stress_rows.csv", index=False)
    (output_path / "trade_capacity_stress_summary.json").write_text(
        json.dumps(_sanitize(audit), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _series_stat(series: pd.Series, stat: str) -> float:
    if series.empty:
        return 0.0
    if stat == "mean":
        return _clean_number(float(series.mean()))
    if stat == "median":
        return _clean_number(float(series.median()))
    if stat == "max":
        return _clean_number(float(series.max()))
    raise ValueError(f"unsupported stat: {stat}")


def _series_quantile(series: pd.Series, q: float) -> float:
    if series.empty:
        return 0.0
    return _clean_number(float(series.quantile(q)))


def _clean_number(value: float) -> float | int:
    if not math.isfinite(value):
        return 0.0
    rounded = round(value, 12)
    if float(rounded).is_integer():
        return int(rounded)
    return rounded


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return str(value)
