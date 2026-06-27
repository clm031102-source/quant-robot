from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_robot.ops.shortlist_official_template_cash_filter import (
    _flag_trades as _flag_dragon_trades,
    _load_dragon_tiger,
    _load_trades,
    _resolve_spec as _resolve_dragon_spec,
)
from quant_robot.ops.shortlist_public_factor_entry_filter import (
    PublicFactorEntryFilterSpec,
    _attach_public_factor,
    _flag_by_factor_quantile,
    _load_public_factor_values,
)
from quant_robot.ops.simulation_shortlist_entry_timed_overlay import (
    SAFETY,
    build_simulation_shortlist_entry_timed_overlay,
)


STAGE = "simulation_shortlist_cohort_entry_timed"


def build_simulation_shortlist_cohort_entry_timed(
    *,
    trades_source: str | Path | pd.DataFrame,
    dragon_tiger_source: str | Path | pd.DataFrame,
    public_factor_source: str | Path | pd.DataFrame,
    public_factor_name: str,
    public_factor_side: str,
    candidate_name: str,
    dragon_candidate: str = "dragon_hot_chase_20d",
    public_factor_quantile: float = 0.10,
    public_factor_exposure_multiplier: float = 1.50,
    trade_return_column: str = "entry_cash_proxy_weighted_return",
    trade_signal_date_column: str = "signal_date",
    trade_entry_date_column: str = "entry_date",
    trade_exit_date_column: str = "exit_date",
    weight_column: str = "target_weight",
    lookback_anchor_column: str = "available_date",
    target_annual_vol: float = 0.08,
    lookback_events: int = 84,
    min_exposure: float = 0.25,
    max_exposure: float = 1.0,
    self_risk_window: int = 21,
    self_risk_threshold: float = 0.0,
    self_risk_exposure: float = 0.8,
) -> dict[str, Any]:
    trades = _load_trades(
        trades_source,
        return_column=trade_return_column,
        entry_date_column=trade_entry_date_column,
        exit_date_column=trade_exit_date_column,
    )
    for column in (trade_signal_date_column, weight_column):
        if column not in trades:
            raise ValueError(f"trades source missing column: {column}")
    trades[trade_signal_date_column] = pd.to_datetime(trades[trade_signal_date_column], errors="coerce")
    trades[weight_column] = pd.to_numeric(trades[weight_column], errors="coerce").fillna(0.0)
    trades[trade_return_column] = pd.to_numeric(trades[trade_return_column], errors="coerce").fillna(0.0)
    trades = trades.dropna(subset=[trade_signal_date_column]).reset_index(drop=True)
    trades["trade_id"] = np.arange(len(trades), dtype=int)

    dragon = _load_dragon_tiger(dragon_tiger_source)
    dragon_flagged = _flag_dragon_trades(
        trades,
        dragon,
        spec=_resolve_dragon_spec(dragon_candidate),
        entry_date_column=trade_entry_date_column,
        lookback_anchor_column=lookback_anchor_column,
    )
    dragon_trade_ids = set(int(value) for value in dragon_flagged["trade_id"].dropna().astype(int))

    factor_spec = PublicFactorEntryFilterSpec(
        name=public_factor_name,
        public_factor_name=public_factor_name,
        side=public_factor_side,
        quantile=float(public_factor_quantile),
    )
    candidate_universe = trades[~trades["trade_id"].isin(dragon_trade_ids)].copy()
    factors = _load_public_factor_values(public_factor_source)
    trade_factors, factor_summary = _attach_public_factor(
        candidate_universe,
        factors,
        spec=factor_spec,
        trade_signal_date_column=trade_signal_date_column,
    )
    public_flagged = _flag_by_factor_quantile(
        trade_factors,
        spec=factor_spec,
        trade_signal_date_column=trade_signal_date_column,
    )
    public_trade_ids = set(int(value) for value in public_flagged["trade_id"].dropna().astype(int))

    working = trades.copy()
    working["dragon_cash_filter"] = working["trade_id"].isin(dragon_trade_ids)
    working["public_factor_tilt"] = working["trade_id"].isin(public_trade_ids)
    working["entry_tilt_multiplier"] = np.select(
        [working["dragon_cash_filter"], working["public_factor_tilt"]],
        [0.0, float(public_factor_exposure_multiplier)],
        default=1.0,
    )
    working["pre_overlay_return_contribution"] = (
        working[trade_return_column].astype(float) * working["entry_tilt_multiplier"]
    )
    working["pre_overlay_target_weight"] = working[weight_column].astype(float) * working["entry_tilt_multiplier"]

    cohort = (
        working.groupby([trade_exit_date_column, trade_entry_date_column], as_index=False)
        .agg(
            period_return=("pre_overlay_return_contribution", "sum"),
            gross_weight=("pre_overlay_target_weight", lambda values: float(pd.Series(values).abs().sum())),
            trade_count=("trade_id", "count"),
            signal_date_count=(trade_signal_date_column, "nunique"),
        )
        .rename(columns={trade_exit_date_column: "date", trade_entry_date_column: "entry_date"})
    )
    cohort["date"] = pd.to_datetime(cohort["date"], errors="coerce")
    cohort["entry_date"] = pd.to_datetime(cohort["entry_date"], errors="coerce")
    cohort = cohort.dropna(subset=["date", "entry_date"]).sort_values(["entry_date", "date"])

    overlay = build_simulation_shortlist_entry_timed_overlay(
        cohort,
        candidate_name=candidate_name,
        date_column="date",
        decision_date_column="entry_date",
        return_column="period_return",
        target_annual_vol=target_annual_vol,
        lookback_events=lookback_events,
        min_exposure=min_exposure,
        max_exposure=max_exposure,
        self_risk_window=self_risk_window,
        self_risk_threshold=self_risk_threshold,
        self_risk_exposure=self_risk_exposure,
    )
    return _sanitize(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "candidate_name": candidate_name,
            "parameters": {
                "dragon_candidate": dragon_candidate,
                "public_factor_name": public_factor_name,
                "public_factor_side": public_factor_side,
                "public_factor_quantile": float(public_factor_quantile),
                "public_factor_exposure_multiplier": float(public_factor_exposure_multiplier),
                "trade_return_column": trade_return_column,
                "target_annual_vol": float(target_annual_vol),
                "lookback_events": int(lookback_events),
                "min_exposure": float(min_exposure),
                "max_exposure": float(max_exposure),
                "self_risk_window": int(self_risk_window),
                "self_risk_threshold": float(self_risk_threshold),
                "self_risk_exposure": float(self_risk_exposure),
            },
            "summary": {
                "trade_count": int(len(trades)),
                "cohort_count": int(len(cohort)),
                "unique_exit_date_count": int(cohort["date"].nunique()),
                "duplicate_exit_date_row_count": int(cohort.duplicated("date").sum()),
                "dragon_cash_trade_count": int(len(dragon_trade_ids)),
                "public_tilt_trade_count": int(len(public_trade_ids)),
                "factor_summary": factor_summary,
                **overlay["summary"],
            },
            "paper_readiness": overlay["paper_readiness"],
            "metrics": overlay["metrics"],
            "cohort_rows": cohort.to_dict(orient="records"),
            "event_rows": overlay["event_rows"],
        }
    )


def write_simulation_shortlist_cohort_entry_timed(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    summary = {key: value for key, value in result.items() if key not in {"cohort_rows", "event_rows"}}
    (output / "simulation_shortlist_cohort_entry_timed.json").write_text(
        json.dumps(_sanitize(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("cohort_rows", [])).to_csv(output / "cohort_source_period_returns.csv", index=False)
    pd.DataFrame(result.get("event_rows", [])).to_csv(output / "simulation_shortlist_entry_timed_events.csv", index=False)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, np.generic):
        return _sanitize(value.item())
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
