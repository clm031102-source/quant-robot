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
    _read_frame,
    _resolve_spec as _resolve_dragon_spec,
)
from quant_robot.ops.shortlist_public_factor_entry_filter import (
    PublicFactorEntryFilterSpec,
    _attach_public_factor,
    _flag_by_factor_quantile,
    _load_public_factor_values,
)


STAGE = "simulation_shortlist_signal_reconstruction"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"


def build_simulation_shortlist_signal_reconstruction(
    *,
    trades_source: str | Path | pd.DataFrame,
    event_source: str | Path | pd.DataFrame,
    dragon_tiger_source: str | Path | pd.DataFrame,
    public_factor_source: str | Path | pd.DataFrame,
    public_factor_name: str,
    public_factor_side: str,
    candidate_name: str = "simulation_shortlist_candidate",
    dragon_candidate: str = "dragon_hot_chase_20d",
    public_factor_quantile: float = 0.10,
    public_factor_exposure_multiplier: float = 1.50,
    trade_return_column: str = "entry_cash_proxy_weighted_return",
    weight_column: str = "target_weight",
    trade_signal_date_column: str = "signal_date",
    trade_entry_date_column: str = "entry_date",
    trade_exit_date_column: str = "exit_date",
    event_date_column: str = "date",
    event_decision_date_column: str = "decision_date",
    event_return_column: str = "period_return",
    event_exposure_column: str = "final_exposure",
    lookback_anchor_column: str = "available_date",
    reconciliation_tolerance: float = 1e-10,
) -> dict[str, Any]:
    trades = _load_trades(
        trades_source,
        return_column=trade_return_column,
        entry_date_column=trade_entry_date_column,
        exit_date_column=trade_exit_date_column,
    )
    if trade_signal_date_column not in trades:
        raise ValueError(f"trades source missing signal date column: {trade_signal_date_column}")
    if weight_column not in trades:
        raise ValueError(f"trades source missing weight column: {weight_column}")
    trades[trade_signal_date_column] = pd.to_datetime(trades[trade_signal_date_column], errors="coerce")
    trades[weight_column] = pd.to_numeric(trades[weight_column], errors="coerce").fillna(0.0)
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

    candidate_universe = trades[~trades["trade_id"].isin(dragon_trade_ids)].copy()
    factor_spec = PublicFactorEntryFilterSpec(
        name=public_factor_name,
        public_factor_name=public_factor_name,
        side=public_factor_side,
        quantile=float(public_factor_quantile),
    )
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

    events = _load_event_source(
        event_source,
        date_column=event_date_column,
        decision_date_column=event_decision_date_column,
        return_column=event_return_column,
        exposure_column=event_exposure_column,
    )
    events_by_date = _events_by_date(events)

    working = trades.copy()
    working["dragon_cash_filter"] = working["trade_id"].isin(dragon_trade_ids)
    working["public_factor_tilt"] = working["trade_id"].isin(public_trade_ids)
    working["entry_tilt_multiplier"] = np.select(
        [working["dragon_cash_filter"], working["public_factor_tilt"]],
        [0.0, float(public_factor_exposure_multiplier)],
        default=1.0,
    )
    working["base_target_weight"] = pd.to_numeric(working[weight_column], errors="coerce").fillna(0.0)
    working["pre_overlay_target_weight"] = working["base_target_weight"] * working["entry_tilt_multiplier"]
    working["pre_overlay_return_contribution"] = (
        pd.to_numeric(working[trade_return_column], errors="coerce").fillna(0.0)
        * working["entry_tilt_multiplier"]
    )
    working = working.rename(
        columns={
            trade_entry_date_column: "decision_date",
            trade_exit_date_column: "date",
            trade_signal_date_column: "signal_date",
        }
    )
    working["date"] = pd.to_datetime(working["date"], errors="coerce")
    working["decision_date"] = pd.to_datetime(working["decision_date"], errors="coerce")
    working = working.merge(events_by_date[["date"]].assign(event_matched=True), on="date", how="left")
    unmatched_trade_dates = working[working["event_matched"].isna()][["date"]].drop_duplicates()
    working = working[working["event_matched"].fillna(False)].copy()
    working = working.merge(
        events_by_date[["date", "event_decision_date", "event_period_return", "event_final_exposure"]],
        on="date",
        how="left",
    )
    working["event_final_exposure"] = pd.to_numeric(
        working["event_final_exposure"],
        errors="coerce",
    ).fillna(1.0)
    working["target_weight"] = working["pre_overlay_target_weight"] * working["event_final_exposure"]
    working["return_contribution"] = (
        working["pre_overlay_return_contribution"] * working["event_final_exposure"]
    )

    reconstructed = (
        working.groupby("date", as_index=False)
        .agg(
            reconstructed_period_return=("return_contribution", "sum"),
            reconstructed_pre_overlay_return=("pre_overlay_return_contribution", "sum"),
            reconstructed_trade_count=("trade_id", "count"),
            trade_decision_date_count=("decision_date", "nunique"),
            reconstructed_gross_weight=("target_weight", lambda values: float(pd.Series(values).abs().sum())),
        )
    )
    reconciliation = events_by_date.merge(reconstructed, on="date", how="left")
    for column in (
        "reconstructed_period_return",
        "reconstructed_pre_overlay_return",
        "reconstructed_gross_weight",
    ):
        reconciliation[column] = pd.to_numeric(reconciliation[column], errors="coerce").fillna(0.0)
    reconciliation["reconstructed_trade_count"] = (
        pd.to_numeric(reconciliation["reconstructed_trade_count"], errors="coerce").fillna(0).astype(int)
    )
    reconciliation["trade_decision_date_count"] = (
        pd.to_numeric(reconciliation["trade_decision_date_count"], errors="coerce").fillna(0).astype(int)
    )
    reconciliation["reconciliation_diff"] = (
        reconciliation["reconstructed_period_return"] - reconciliation["event_period_return"]
    )
    max_abs_diff = _number(reconciliation["reconciliation_diff"].abs().max())
    collapsed_decision_dates = reconciliation["trade_decision_date_count"] > reconciliation[
        "event_decision_date_count"
    ]

    exposure_after_decision = reconciliation["date"] > reconciliation["event_decision_date"]
    blockers: list[str] = []
    if bool(exposure_after_decision.any()):
        blockers.append("exit_timed_exposure_requires_entry_timed_rebuild")
    if bool(collapsed_decision_dates.any()):
        blockers.append("event_decision_date_collapses_multiple_trade_decisions")
    if int(len(unmatched_trade_dates)) > 0:
        blockers.append("trade_pairs_missing_event_exposure")
    if max_abs_diff > float(reconciliation_tolerance):
        blockers.append("return_reconciliation_failed")

    signal_rows = _signal_rows(working)
    reconciliation_rows = _reconciliation_rows(reconciliation)
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
                "weight_column": weight_column,
                "event_return_column": event_return_column,
                "event_exposure_column": event_exposure_column,
                "reconciliation_tolerance": float(reconciliation_tolerance),
            },
            "summary": {
                "candidate_name": candidate_name,
                "trade_count": int(len(trades)),
                "event_matched_trade_count": int(len(working)),
                "unmatched_trade_pair_count": int(len(unmatched_trade_dates)),
                "unmatched_trade_date_count": int(len(unmatched_trade_dates)),
                "event_count": int(len(events)),
                "dragon_cash_trade_count": int(len(dragon_trade_ids)),
                "public_tilt_trade_count": int(len(public_trade_ids)),
                "factor_summary": factor_summary,
                "max_abs_return_reconciliation_diff": max_abs_diff,
                "sum_abs_return_reconciliation_diff": _number(reconciliation["reconciliation_diff"].abs().sum()),
                "max_reconstructed_gross_weight": _number(reconciliation["reconstructed_gross_weight"].max()),
                "exit_timed_exposure_row_count": int(exposure_after_decision.sum()),
                "collapsed_event_decision_date_count": int(collapsed_decision_dates.sum()),
            },
            "paper_readiness": {
                "paper_ready": not blockers,
                "blockers": blockers,
                "interpretation": (
                    "Exact event-return reconstruction is not the same as an entry-timed paper signal "
                    "when exposures are keyed by exit/event date."
                    if blockers
                    else "Asset-level signal rows reconcile and do not use exit-timed exposure."
                ),
            },
            "signal_rows": signal_rows,
            "reconciliation_rows": reconciliation_rows,
        }
    )


def write_simulation_shortlist_signal_reconstruction(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "simulation_shortlist_signal_reconstruction.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("signal_rows", [])).to_csv(
        output / "simulation_shortlist_signal_rows.csv",
        index=False,
    )
    pd.DataFrame(result.get("reconciliation_rows", [])).to_csv(
        output / "simulation_shortlist_reconciliation_rows.csv",
        index=False,
    )


def _load_event_source(
    source: str | Path | pd.DataFrame,
    *,
    date_column: str,
    decision_date_column: str,
    return_column: str,
    exposure_column: str,
) -> pd.DataFrame:
    frame = source.copy() if isinstance(source, pd.DataFrame) else _read_frame(Path(source))
    missing = [column for column in (date_column, decision_date_column, return_column) if column not in frame]
    if missing:
        raise ValueError(f"event source missing columns: {', '.join(missing)}")
    output = frame.copy()
    output["date"] = pd.to_datetime(output[date_column], errors="coerce")
    output["decision_date"] = pd.to_datetime(output[decision_date_column], errors="coerce")
    output["event_period_return"] = pd.to_numeric(output[return_column], errors="coerce").fillna(0.0)
    if exposure_column in output:
        output["event_final_exposure"] = pd.to_numeric(output[exposure_column], errors="coerce").fillna(1.0)
    else:
        output["event_final_exposure"] = 1.0
    output = output.dropna(subset=["date", "decision_date"]).sort_values(["date", "decision_date"])
    return output[["date", "decision_date", "event_period_return", "event_final_exposure"]].reset_index(drop=True)


def _events_by_date(events: pd.DataFrame) -> pd.DataFrame:
    output = (
        events.groupby("date", as_index=False)
        .agg(
            event_period_return=("event_period_return", "sum"),
            event_final_exposure=("event_final_exposure", "first"),
            event_decision_date=("decision_date", "first"),
            event_decision_date_count=("decision_date", "nunique"),
            event_row_count=("decision_date", "count"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    return output


def _signal_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    columns = [
        "signal_date",
        "decision_date",
        "event_decision_date",
        "date",
        "asset_id",
        "base_target_weight",
        "dragon_cash_filter",
        "public_factor_tilt",
        "entry_tilt_multiplier",
        "pre_overlay_target_weight",
        "event_final_exposure",
        "target_weight",
        "pre_overlay_return_contribution",
        "return_contribution",
    ]
    available = [column for column in columns if column in frame]
    return frame[available].sort_values(["decision_date", "date", "asset_id"]).to_dict(orient="records")


def _reconciliation_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    columns = [
        "date",
        "event_decision_date",
        "event_decision_date_count",
        "trade_decision_date_count",
        "event_period_return",
        "event_final_exposure",
        "reconstructed_period_return",
        "reconstructed_pre_overlay_return",
        "reconstructed_trade_count",
        "reconstructed_gross_weight",
        "reconciliation_diff",
    ]
    available = [column for column in columns if column in frame]
    return frame[available].sort_values(["date"]).to_dict(orient="records")


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
