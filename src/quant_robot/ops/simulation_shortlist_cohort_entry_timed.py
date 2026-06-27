from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.shortlist_official_template_cash_filter import (
    _flag_trades as _flag_dragon_trades,
    _load_dragon_tiger,
    _load_trades,
    _resolve_spec as _resolve_dragon_spec,
)
from quant_robot.ops.shortlist_trade_attribute_cash_filter import (
    AttributeFilterSpec,
    _flag_trades as _flag_attribute_trades,
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
    public_factor_tilt_risk_cap_column: str | None = None,
    public_factor_tilt_risk_cap_operator: str = "gt",
    public_factor_tilt_risk_cap_value: float | None = None,
    public_factor_tilt_risk_cap_multiplier: float = 1.0,
    trade_return_column: str = "entry_cash_proxy_weighted_return",
    trade_signal_date_column: str = "signal_date",
    trade_entry_date_column: str = "entry_date",
    trade_exit_date_column: str = "exit_date",
    weight_column: str = "target_weight",
    lookback_anchor_column: str = "available_date",
    apply_dragon_cash_filter: bool = True,
    entry_attribute_cash_rules: Sequence[AttributeFilterSpec] = (),
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

    if apply_dragon_cash_filter:
        dragon = _load_dragon_tiger(dragon_tiger_source)
        dragon_flagged = _flag_dragon_trades(
            trades,
            dragon,
            spec=_resolve_dragon_spec(dragon_candidate),
            entry_date_column=trade_entry_date_column,
            lookback_anchor_column=lookback_anchor_column,
        )
        dragon_trade_ids = set(int(value) for value in dragon_flagged["trade_id"].dropna().astype(int))
    else:
        dragon_trade_ids = set()

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
    working["public_factor_tilt_risk_cap"] = False
    entry_attribute_cash_rule_counts: dict[str, int] = {}
    entry_attribute_trade_ids: set[int] = set()
    for spec in entry_attribute_cash_rules:
        flagged = _flag_attribute_trades(working, spec)
        rule_trade_ids = set(int(value) for value in flagged["trade_id"].dropna().astype(int))
        entry_attribute_cash_rule_counts[spec.name] = int(len(rule_trade_ids))
        entry_attribute_trade_ids.update(rule_trade_ids)
    working["entry_attribute_cash_filter"] = working["trade_id"].isin(entry_attribute_trade_ids)
    if public_factor_tilt_risk_cap_column:
        if public_factor_tilt_risk_cap_value is None:
            raise ValueError("public_factor_tilt_risk_cap_value is required when risk cap column is set")
        if public_factor_tilt_risk_cap_column not in working:
            raise ValueError(f"trades source missing risk cap column: {public_factor_tilt_risk_cap_column}")
        risk_condition = _numeric_risk_cap_condition(
            working[public_factor_tilt_risk_cap_column],
            operator=public_factor_tilt_risk_cap_operator,
            value=float(public_factor_tilt_risk_cap_value),
        )
        working["public_factor_tilt_risk_cap"] = working["public_factor_tilt"] & risk_condition
    working["entry_tilt_multiplier"] = np.select(
        [
            working["dragon_cash_filter"],
            working["entry_attribute_cash_filter"],
            working["public_factor_tilt_risk_cap"],
            working["public_factor_tilt"],
        ],
        [
            0.0,
            0.0,
            float(public_factor_tilt_risk_cap_multiplier),
            float(public_factor_exposure_multiplier),
        ],
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
    trade_rows = _build_trade_rows(
        working,
        overlay.get("event_rows", []),
        trade_entry_date_column=trade_entry_date_column,
        trade_exit_date_column=trade_exit_date_column,
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
                "public_factor_tilt_risk_cap_column": public_factor_tilt_risk_cap_column,
                "public_factor_tilt_risk_cap_operator": public_factor_tilt_risk_cap_operator,
                "public_factor_tilt_risk_cap_value": public_factor_tilt_risk_cap_value,
                "public_factor_tilt_risk_cap_multiplier": float(public_factor_tilt_risk_cap_multiplier),
                "trade_return_column": trade_return_column,
                "weight_column": weight_column,
                "apply_dragon_cash_filter": bool(apply_dragon_cash_filter),
                "entry_attribute_cash_rules": [
                    _attribute_rule_to_dict(spec) for spec in entry_attribute_cash_rules
                ],
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
                "public_tilt_risk_capped_trade_count": int(working["public_factor_tilt_risk_cap"].sum()),
                "entry_attribute_cash_trade_count": int(len(entry_attribute_trade_ids)),
                "entry_attribute_cash_rule_counts": entry_attribute_cash_rule_counts,
                "factor_summary": factor_summary,
                **overlay["summary"],
            },
            "paper_readiness": overlay["paper_readiness"],
            "metrics": overlay["metrics"],
            "trade_rows": trade_rows.to_dict(orient="records"),
            "cohort_rows": cohort.to_dict(orient="records"),
            "event_rows": overlay["event_rows"],
        }
    )


def write_simulation_shortlist_cohort_entry_timed(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    summary = {key: value for key, value in result.items() if key not in {"trade_rows", "cohort_rows", "event_rows"}}
    (output / "simulation_shortlist_cohort_entry_timed.json").write_text(
        json.dumps(_sanitize(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("trade_rows", [])).to_csv(output / "cohort_trade_rows.csv", index=False)
    pd.DataFrame(result.get("cohort_rows", [])).to_csv(output / "cohort_source_period_returns.csv", index=False)
    pd.DataFrame(result.get("event_rows", [])).to_csv(output / "simulation_shortlist_entry_timed_events.csv", index=False)


def _build_trade_rows(
    working: pd.DataFrame,
    event_rows: list[dict[str, Any]],
    *,
    trade_entry_date_column: str,
    trade_exit_date_column: str,
) -> pd.DataFrame:
    working = working.drop(
        columns=["final_exposure", "final_target_weight", "final_return_contribution"],
        errors="ignore",
    )
    exposure = pd.DataFrame(event_rows)
    if exposure.empty:
        output = working.copy()
        output["final_exposure"] = 0.0
    else:
        required = {"date", "decision_date", "final_exposure"}
        missing = sorted(required - set(exposure.columns))
        if missing:
            raise ValueError(f"overlay event rows missing columns: {', '.join(missing)}")
        exposure = exposure[["date", "decision_date", "final_exposure"]].copy()
        exposure["date"] = pd.to_datetime(exposure["date"], errors="coerce")
        exposure["decision_date"] = pd.to_datetime(exposure["decision_date"], errors="coerce")
        exposure["final_exposure"] = pd.to_numeric(exposure["final_exposure"], errors="coerce").fillna(0.0)
        output = working.merge(
            exposure,
            left_on=[trade_exit_date_column, trade_entry_date_column],
            right_on=["date", "decision_date"],
            how="left",
            validate="many_to_one",
        )
        output = output.drop(columns=["date", "decision_date"], errors="ignore")
        output["final_exposure"] = pd.to_numeric(output["final_exposure"], errors="coerce").fillna(0.0)
    output["final_target_weight"] = output["pre_overlay_target_weight"].astype(float) * output["final_exposure"].astype(float)
    output["final_return_contribution"] = (
        output["pre_overlay_return_contribution"].astype(float) * output["final_exposure"].astype(float)
    )
    return output.sort_values([trade_entry_date_column, trade_exit_date_column, "trade_id"]).reset_index(drop=True)


def _numeric_risk_cap_condition(series: pd.Series, *, operator: str, value: float) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if operator == "gt":
        return values > value
    if operator == "ge":
        return values >= value
    if operator == "lt":
        return values < value
    if operator == "le":
        return values <= value
    raise ValueError(f"unsupported public factor tilt risk cap operator: {operator}")


def _attribute_rule_to_dict(spec: AttributeFilterSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "column": spec.column,
        "operator": spec.operator,
        "values": list(spec.values),
    }


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
