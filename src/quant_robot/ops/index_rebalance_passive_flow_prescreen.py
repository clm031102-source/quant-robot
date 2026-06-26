from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.event_factor_pit_ic_prescreen import summarize_event_factor_pit_ic_prescreen
from quant_robot.ops.event_factor_preregistration import EventFactorCandidateSpec, SAFETY
from quant_robot.research.labels import make_forward_returns


STAGE = "index_rebalance_passive_flow_prescreen"
NEXT_DIRECTION_WITH_LEADS = "round232_index_rebalance_passive_flow_reference_dedup_or_walk_forward_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round232_rotate_after_index_rebalance_passive_flow_failure"

INDEX_REBALANCE_PASSIVE_FLOW_FACTOR_NAMES = (
    "index_rebalance_add_pressure_1d",
    "index_rebalance_remove_pressure_1d",
    "index_rebalance_weight_up_pressure_1d",
    "index_rebalance_weight_down_pressure_1d",
    "index_rebalance_abs_flow_pressure_1d",
)

RESULT_COLUMNS = [
    "factor_name",
    "horizon",
    "ic_observations",
    "mean_spearman_ic",
    "icir",
    "ic_t_stat",
    "ic_p_value",
    "fdr_significant",
    "ic_positive_rate",
    "quantile_spread",
    "quantile_monotonicity",
    "industry_neutral_observations",
    "mean_industry_neutral_rank_ic",
    "industry_neutral_rank_ic_t_stat",
    "size_neutral_observations",
    "mean_size_neutral_rank_ic",
    "size_neutral_rank_ic_t_stat",
    "research_lead",
    "promotion_allowed",
    "blockers",
]


def build_index_rebalance_passive_flow_factor_frame(index_events: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    events = _normalise_events(index_events)
    if events.empty:
        return _empty_factor_frame()
    factor_rows: list[dict[str, Any]] = []
    for row in events.itertuples(index=False):
        values = _factor_values(row)
        for factor_name, factor_value in values.items():
            factor_rows.append(
                {
                    "date": row.date,
                    "asset_id": row.asset_id,
                    "market": "CN",
                    "factor_name": factor_name,
                    "factor_value": factor_value,
                    "source_event_count": 1,
                }
            )
    frame = pd.DataFrame(factor_rows)
    if frame.empty:
        return _empty_factor_frame()
    grouped = (
        frame.groupby(["date", "asset_id", "market", "factor_name"], as_index=False)
        .agg(
            factor_value=("factor_value", "sum"),
            source_event_count=("source_event_count", "sum"),
        )
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )
    return _attach_bar_context(grouped, bars)


def build_index_rebalance_passive_flow_prescreen(
    *,
    index_events: pd.DataFrame,
    bars: pd.DataFrame,
    stock_basic: pd.DataFrame,
    horizons: tuple[int, ...] = (5, 20),
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.50,
) -> dict[str, Any]:
    clean_bars = _normalise_bars(bars)
    raw_factor_frame = build_index_rebalance_passive_flow_factor_frame(index_events, clean_bars)
    factor_frame, constant_filter = _drop_constant_factor_dates(raw_factor_frame)
    labels = make_forward_returns(
        clean_bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    result = summarize_event_factor_pit_ic_prescreen(
        factor_frame,
        labels,
        stock_basic,
        expected_candidate_count=len(INDEX_REBALANCE_PASSIVE_FLOW_FACTOR_NAMES),
        candidate_specs=default_index_rebalance_passive_flow_specs(),
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
    )
    research_leads = int(result.get("summary", {}).get("research_lead_count", 0))
    result["stage"] = STAGE
    result["summary"]["next_direction"] = NEXT_DIRECTION_WITH_LEADS if research_leads else NEXT_DIRECTION_WITHOUT_LEADS
    result["summary"]["constant_factor_date_rows_dropped"] = constant_filter["rows_dropped"]
    result["summary"]["constant_factor_date_groups_dropped"] = constant_filter["groups_dropped"]
    result["data_window"] = _data_window(clean_bars, factor_frame, labels, index_events)
    result["pit_policy"] = {
        "event_date_source": "index_rebalance_event_available_date",
        "same_day_event_trading_allowed": False,
        "execution_lag": int(execution_lag),
        "signal_date_rule": "use_first_trade_date_after_index_weight_snapshot_from_index_rebalance_audit",
    }
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": "reference_dedup_or_walk_forward_preflight_only_if_neutral_research_lead_survives",
        "reason": "Index rebalance passive-flow event IC is not a portfolio result and cannot be promoted without later de-dup, cost, capacity, regime, and holdout gates.",
    }
    result["factor_rows"] = _rows(factor_frame)
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_index_rebalance_passive_flow_prescreen_markdown(result)
    return result


def write_index_rebalance_passive_flow_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "index_rebalance_passive_flow_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "index_rebalance_passive_flow_prescreen.md").write_text(
        render_index_rebalance_passive_flow_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "index_rebalance_passive_flow_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "index_rebalance_passive_flow_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )
    _write_csv(
        output_path / "index_rebalance_passive_flow_neutral_observations.csv",
        result.get("neutral_observations", []),
        [
            "factor_name",
            "horizon",
            "date",
            "industry_neutral_rank_ic",
            "size_neutral_rank_ic",
            "cross_section",
            "industry_count",
        ],
    )
    factor_frame = pd.DataFrame(result.get("factor_rows", []))
    factor_frame.to_csv(output_path / "index_rebalance_passive_flow_factor_rows.csv", index=False)


def render_index_rebalance_passive_flow_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    lines = [
        "# Index Rebalance Passive Flow Prescreen Round231",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Neutral-gate pass tests: {summary.get('neutral_gate_pass_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: {summary.get('next_direction', NEXT_DIRECTION_WITHOUT_LEADS)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Top Results",
        "",
        "| Factor | H | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | Lead | Blockers |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", [])[:25]:
        lines.append(
            "| {factor} | {h} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {ind:.4f} | {size:.4f} | {lead} | {blockers} |".format(
                factor=row.get("factor_name", ""),
                h=int(row.get("horizon", 0)),
                ic=_number(row.get("mean_spearman_ic")),
                icir=_number(row.get("icir")),
                t=_number(row.get("ic_t_stat")),
                pos=_number(row.get("ic_positive_rate")),
                spread=_number(row.get("quantile_spread")),
                ind=_number(row.get("mean_industry_neutral_rank_ic")),
                size=_number(row.get("mean_size_neutral_rank_ic")),
                lead="yes" if row.get("research_lead") else "no",
                blockers=", ".join(row.get("blockers", []) or []),
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This is a PIT event IC and neutralization prescreen, not a portfolio backtest.",
            "- Signals use the index rebalance audit available date; same-day event trading is forbidden.",
            "- Positive results only earn the right to de-dup or walk-forward preflight.",
        ]
    )
    return "\n".join(lines) + "\n"


def default_index_rebalance_passive_flow_specs() -> list[EventFactorCandidateSpec]:
    return [
        EventFactorCandidateSpec(
            factor_name=name,
            family="index_rebalance_passive_flow",
            formula_template=_formula_for(name),
            direction="higher_is_better",
            required_endpoints=("index_weight",),
            required_fields=("available_date", "event_type", "prior_weight", "current_weight", "weight_delta"),
            event_date_fields=("available_date",),
            windows=(1,),
            economic_rationale="Index rebalance adds and weight increases can create short-term passive-flow demand; removals and downweights are encoded as negative pressure.",
            public_reference_tags=("index_rebalance", "passive_flow", "supply_demand_event"),
            expected_failure_modes=("crowded_event_date", "industry_concentration", "event_effect_reversal_after_announcement"),
        )
        for name in INDEX_REBALANCE_PASSIVE_FLOW_FACTOR_NAMES
    ]


def _formula_for(name: str) -> str:
    return {
        "index_rebalance_add_pressure_1d": "current_weight if event_type == added else 0",
        "index_rebalance_remove_pressure_1d": "-prior_weight if event_type == removed else 0",
        "index_rebalance_weight_up_pressure_1d": "max(weight_delta, 0)",
        "index_rebalance_weight_down_pressure_1d": "min(weight_delta, 0)",
        "index_rebalance_abs_flow_pressure_1d": "abs(weight_delta)",
    }[name]


def _factor_values(row: Any) -> dict[str, float]:
    event_type = str(row.event_type)
    prior = float(row.prior_weight)
    current = float(row.current_weight)
    delta = float(row.weight_delta)
    return {
        "index_rebalance_add_pressure_1d": current if event_type == "added" else 0.0,
        "index_rebalance_remove_pressure_1d": -prior if event_type == "removed" else 0.0,
        "index_rebalance_weight_up_pressure_1d": max(delta, 0.0),
        "index_rebalance_weight_down_pressure_1d": min(delta, 0.0),
        "index_rebalance_abs_flow_pressure_1d": abs(delta),
    }


def _normalise_events(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=["date", "asset_id", "event_type", "prior_weight", "current_weight", "weight_delta"])
    required = ["available_date", "asset_id", "event_type", "prior_weight", "current_weight", "weight_delta"]
    missing = [column for column in required if column not in events.columns]
    if missing:
        raise ValueError(f"Index rebalance events are missing required columns: {', '.join(missing)}")
    output = events.copy()
    output["date"] = pd.to_datetime(output["available_date"], errors="coerce")
    output["asset_id"] = output["asset_id"].astype(str)
    output["event_type"] = output["event_type"].astype(str)
    for column in ["prior_weight", "current_weight", "weight_delta"]:
        output[column] = pd.to_numeric(output[column], errors="coerce")
    return output.dropna(subset=["date", "asset_id", "event_type", "prior_weight", "current_weight", "weight_delta"])


def _attach_bar_context(frame: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return _empty_factor_frame()
    context = _bar_context(bars)
    output = frame.merge(context, on=["date", "asset_id", "market"], how="left", validate="many_to_one")
    return output.dropna(subset=["amount", "adv20_amount", "log_adv20"]).reset_index(drop=True)


def _drop_constant_factor_dates(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    if frame.empty:
        return frame, {"rows_dropped": 0, "groups_dropped": 0}
    working = frame.copy()
    working["_factor_numeric"] = pd.to_numeric(working["factor_value"], errors="coerce")
    group_cols = ["factor_name", "date"]
    unique_counts = working.groupby(group_cols)["_factor_numeric"].transform(lambda values: values.nunique(dropna=True))
    keep = unique_counts > 1
    rows_dropped = int((~keep).sum())
    if rows_dropped:
        groups_dropped = int(working.loc[~keep, group_cols].drop_duplicates().shape[0])
    else:
        groups_dropped = 0
    filtered = working.loc[keep].drop(columns=["_factor_numeric"]).reset_index(drop=True)
    return filtered, {"rows_dropped": rows_dropped, "groups_dropped": groups_dropped}


def _bar_context(bars: pd.DataFrame) -> pd.DataFrame:
    frame = _normalise_bars(bars).sort_values(["asset_id", "date"]).copy()
    frame["adv20_amount"] = frame.groupby("asset_id")["amount"].transform(lambda item: item.rolling(20, min_periods=5).mean())
    frame["log_adv20"] = frame["adv20_amount"].map(lambda value: math.log(value) if _is_finite(value) and value > 0 else pd.NA)
    return frame[["date", "asset_id", "market", "amount", "adv20_amount", "log_adv20"]]


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in ["adj_close", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return (
        frame[(frame["market"] == "CN") & (frame["adj_close"] > 0)]
        .dropna(subset=required)
        .drop_duplicates(["date", "asset_id", "market"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _data_window(bars: pd.DataFrame, factors: pd.DataFrame, labels: pd.DataFrame, events: pd.DataFrame) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "min_signal_date": _min_date(factors, "date"),
        "max_signal_date": _max_date(factors, "date"),
        "min_label_date": _min_date(labels, "date"),
        "max_label_date": _max_date(labels, "date"),
        "event_rows": int(len(events)),
        "factor_rows": int(len(factors)),
    }


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "asset_id",
            "market",
            "factor_name",
            "factor_value",
            "source_event_count",
            "amount",
            "adv20_amount",
            "log_adv20",
        ]
    )


def _rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [_sanitize(row) for row in frame.to_dict(orient="records")]


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False
