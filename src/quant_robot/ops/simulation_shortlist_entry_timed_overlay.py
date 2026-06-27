from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_robot.ops.shortlist_official_template_cash_filter import _read_frame
from quant_robot.ops.shortlist_return_block_audit import summarize_return_blocks
from quant_robot.ops.turnover_low_overlay_walk_forward import (
    OverlayPolicy,
    apply_overlay_policy_to_period_events,
)


STAGE = "simulation_shortlist_entry_timed_overlay"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"


def build_simulation_shortlist_entry_timed_overlay(
    period_events: str | Path | pd.DataFrame,
    *,
    candidate_name: str,
    return_column: str = "period_return",
    date_column: str = "date",
    decision_date_column: str = "entry_date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    target_annual_vol: float = 0.06,
    lookback_events: int = 84,
    min_exposure: float = 0.25,
    max_exposure: float = 1.0,
    self_risk_window: int = 21,
    self_risk_threshold: float = 0.0,
    self_risk_exposure: float = 0.5,
) -> dict[str, Any]:
    raw = _load_period_events(
        period_events,
        return_column=return_column,
        date_column=date_column,
        decision_date_column=decision_date_column,
    )
    vol_policy = OverlayPolicy(
        name="entry_timed_vol_target",
        kind="vol_target",
        target_annual_volatility=float(target_annual_vol),
        lookback_periods=int(lookback_events),
        min_exposure=float(min_exposure),
        max_exposure=float(max_exposure),
    )
    vol = apply_overlay_policy_to_period_events(
        raw[["date", "decision_date", "period_return", "raw_period_return"]],
        vol_policy,
        periods_per_year=periods_per_year,
    )
    vol = vol.rename(columns={"exposure": "vol_target_exposure", "period_return": "vol_target_period_return"})
    vol = vol.merge(raw[["date", "decision_date", "raw_period_return"]], on=["date", "decision_date"], how="left")
    overlay = _apply_entry_timed_self_risk(
        vol,
        candidate_name=candidate_name,
        self_risk_window=self_risk_window,
        self_risk_threshold=self_risk_threshold,
        self_risk_exposure=self_risk_exposure,
    )
    metric_returns = (
        overlay.groupby("date", as_index=False)["period_return"]
        .sum()
        .sort_values("date")
        .reset_index(drop=True)
    )
    metrics = summarize_return_blocks(
        metric_returns,
        candidate_name=candidate_name,
        return_column="period_return",
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    blockers = []
    if overlay["date"].isna().any() or overlay["decision_date"].isna().any():
        blockers.append("missing_event_or_decision_date")
    if (overlay["decision_date"] > overlay["date"]).any():
        blockers.append("decision_after_event_date")
    return _sanitize(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "summary": {
                "candidate_name": candidate_name,
                "event_count": int(len(overlay)),
                "average_vol_target_exposure": _number(overlay["vol_target_exposure"].mean()),
                "average_self_risk_exposure": _number(overlay["self_risk_exposure"].mean()),
                "average_final_exposure": _number(overlay["final_exposure"].mean()),
                "self_risk_guard_event_share": _number((overlay["self_risk_exposure"] < 0.999999).mean()),
            },
            "parameters": {
                "return_column": return_column,
                "date_column": date_column,
                "decision_date_column": decision_date_column,
                "periods_per_year": float(periods_per_year),
                "holding_period": int(holding_period),
                "target_annual_vol": float(target_annual_vol),
                "lookback_events": int(lookback_events),
                "min_exposure": float(min_exposure),
                "max_exposure": float(max_exposure),
                "self_risk_window": int(self_risk_window),
                "self_risk_threshold": float(self_risk_threshold),
                "self_risk_exposure": float(self_risk_exposure),
            },
            "paper_readiness": {
                "paper_ready": not blockers,
                "blockers": blockers,
                "interpretation": (
                    "Exposure is computed by decision date using only returns closed before that decision."
                    if not blockers
                    else "Entry-timed overlay has structural blockers."
                ),
            },
            "metrics": metrics,
            "event_rows": overlay.to_dict(orient="records"),
        }
    )


def write_simulation_shortlist_entry_timed_overlay(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "simulation_shortlist_entry_timed_overlay.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("event_rows", [])).to_csv(
        output / "simulation_shortlist_entry_timed_events.csv",
        index=False,
    )


def _load_period_events(
    source: str | Path | pd.DataFrame,
    *,
    return_column: str,
    date_column: str,
    decision_date_column: str,
) -> pd.DataFrame:
    frame = source.copy() if isinstance(source, pd.DataFrame) else _read_frame(Path(source))
    missing = [column for column in (date_column, decision_date_column, return_column) if column not in frame]
    if missing:
        raise ValueError(f"period events missing columns: {', '.join(missing)}")
    output = frame.copy()
    output["date"] = pd.to_datetime(output[date_column], errors="coerce")
    output["decision_date"] = pd.to_datetime(output[decision_date_column], errors="coerce")
    output["raw_period_return"] = pd.to_numeric(output[return_column], errors="coerce").fillna(0.0)
    output["period_return"] = output["raw_period_return"]
    output = output.dropna(subset=["date", "decision_date"]).sort_values(["decision_date", "date"])
    return output[["date", "decision_date", "period_return", "raw_period_return"]].reset_index(drop=True)


def _apply_entry_timed_self_risk(
    vol_events: pd.DataFrame,
    *,
    candidate_name: str,
    self_risk_window: int,
    self_risk_threshold: float,
    self_risk_exposure: float,
) -> pd.DataFrame:
    working = vol_events.sort_values(["decision_date", "date"]).copy()
    pending: list[tuple[pd.Timestamp, int, float]] = []
    closed_source_returns: list[float] = []
    exposures = pd.Series(1.0, index=working.index, dtype=float)
    prior_roll = pd.Series(0.0, index=working.index, dtype=float)
    adjusted = pd.Series(0.0, index=working.index, dtype=float)

    for decision_date, group in working.groupby("decision_date", sort=True):
        pending.sort(key=lambda item: (item[0], item[1]))
        still_pending: list[tuple[pd.Timestamp, int, float]] = []
        for exit_date, row_index, source_return in pending:
            if exit_date <= decision_date:
                closed_source_returns.append(float(source_return))
            else:
                still_pending.append((exit_date, row_index, source_return))
        pending = still_pending
        recent = closed_source_returns[-int(self_risk_window) :]
        roll_sum = float(sum(recent)) if recent else 0.0
        exposure = float(self_risk_exposure) if roll_sum < float(self_risk_threshold) else 1.0
        for row_index, row in group.iterrows():
            source_return = float(row["vol_target_period_return"])
            exposures.loc[row_index] = exposure
            prior_roll.loc[row_index] = roll_sum
            adjusted.loc[row_index] = source_return * exposure
            pending.append((pd.Timestamp(row["date"]), int(row_index), source_return))

    output = working.copy()
    output["candidate"] = candidate_name
    output["source_period_return"] = output["vol_target_period_return"].astype(float)
    output["prior_roll21_sum"] = prior_roll
    output["self_risk_exposure"] = exposures.clip(lower=0.0, upper=1.0)
    output["final_exposure"] = output["vol_target_exposure"].astype(float) * output["self_risk_exposure"]
    output["period_return"] = adjusted
    output = output.sort_values(["date", "decision_date"]).reset_index(drop=True)
    output["equity"] = (1.0 + output["period_return"]).cumprod()
    peak = output["equity"].cummax().replace(0.0, np.nan)
    output["drawdown"] = (output["equity"] / peak - 1.0).fillna(0.0)
    return output[
        [
            "date",
            "decision_date",
            "candidate",
            "raw_period_return",
            "vol_target_exposure",
            "vol_target_period_return",
            "source_period_return",
            "prior_roll21_sum",
            "self_risk_exposure",
            "final_exposure",
            "period_return",
            "equity",
            "drawdown",
        ]
    ]


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, np.generic):
        return _sanitize(value.item())
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
