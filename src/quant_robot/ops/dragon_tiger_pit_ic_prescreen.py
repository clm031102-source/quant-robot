from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    load_capacity_safe_bars,
)
from quant_robot.ops.event_factor_pit_ic_prescreen import summarize_event_factor_pit_ic_prescreen
from quant_robot.ops.event_factor_preregistration import SAFETY
from quant_robot.research.labels import make_forward_returns
from quant_robot.storage.dataset_store import DatasetStore


STAGE = "dragon_tiger_pit_event_ic_prescreen"
NEXT_DIRECTION_WITH_LEADS = "round233_dragon_tiger_neutral_lead_dedup_before_portfolio_grid_preflight"
NEXT_DIRECTION_WITH_REPAIR = "round233_dragon_tiger_size_residual_repair_before_portfolio_grid_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round233_rotate_or_repair_dragon_tiger_after_pit_ic_prescreen_failure"
DRAGON_TIGER_DEFAULT_HORIZONS = (1,)
DRAGON_TIGER_CANDIDATE_NAMES = (
    "dragon_tiger_abnormal_attention_reversal_1d",
    "dragon_tiger_net_buy_continuation_1d",
    "dragon_tiger_net_sell_exhaustion_reversal_1d",
    "dragon_tiger_institutional_net_buy_pressure_1d",
    "dragon_tiger_institutional_disagreement_abs_pressure_1d",
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
    "avg_top_quantile_turnover",
    "industry_neutral_observations",
    "mean_industry_neutral_rank_ic",
    "industry_neutral_rank_ic_t_stat",
    "industry_neutral_rank_ic_p_value",
    "industry_neutral_retention_ratio",
    "size_neutral_observations",
    "mean_size_neutral_rank_ic",
    "size_neutral_rank_ic_t_stat",
    "size_neutral_rank_ic_p_value",
    "size_neutral_retention_ratio",
    "median_cross_section",
    "unique_dates",
    "unique_assets",
    "research_lead",
    "style_residual_repair_candidate",
    "promotion_allowed",
    "blockers",
]
NEUTRAL_OBSERVATION_COLUMNS = [
    "factor_name",
    "horizon",
    "date",
    "industry_neutral_rank_ic",
    "size_neutral_rank_ic",
    "cross_section",
    "industry_count",
]


def build_dragon_tiger_pit_ic_prescreen(
    *,
    stock_day: pd.DataFrame | None = None,
    processed_root: str | Path | None = None,
    bars: pd.DataFrame | None = None,
    bars_roots: Iterable[str | Path] | None = None,
    stock_basic: pd.DataFrame | None = None,
    stock_basic_path: str | Path | None = None,
    candidate_plan_json: str | Path | None = None,
    candidate_plan_gate_json: str | Path | None = None,
    market: str = "CN",
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DRAGON_TIGER_DEFAULT_HORIZONS,
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.50,
    alpha: float = 0.05,
) -> dict[str, Any]:
    if bars is None:
        if bars_roots is None:
            raise ValueError("Either bars or bars_roots must be provided")
        bars = load_capacity_safe_bars(
            bars_roots,
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
        )
    else:
        bars = _normalise_bars(bars)
        start = pd.Timestamp(analysis_start_date)
        end = bars["date"].max() if include_final_holdout else pd.Timestamp(analysis_end_date)
        bars = bars[(bars["date"] >= start) & (bars["date"] <= end)].reset_index(drop=True)
    if stock_day is None:
        if processed_root is None:
            raise ValueError("Either stock_day or processed_root must be provided")
        stock_day = load_dragon_tiger_stock_day(
            processed_root,
            market=market,
            start_year=pd.Timestamp(analysis_start_date).year,
            end_year=pd.Timestamp(analysis_end_date).year,
        )
    if stock_basic is None:
        stock_basic = load_stock_basic(stock_basic_path)
    specs = _candidate_specs(candidate_plan_json, candidate_plan_gate_json)
    factor_frame = compute_dragon_tiger_factor_frame(
        stock_day,
        bars,
        candidate_specs=specs,
        pit_lag_trade_days=pit_lag_trade_days,
    )
    factor_frame = _filter_date_window(
        factor_frame,
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=tuple(horizons),
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_event_factor_pit_ic_prescreen(
        factor_frame,
        labels,
        stock_basic,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=tuple(horizons),
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
        alpha=alpha,
    )
    _specialize_result(
        result,
        bars=bars,
        stock_day=stock_day,
        factor_frame=factor_frame,
        labels=labels,
        specs=specs,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        execution_lag=execution_lag,
        pit_lag_trade_days=pit_lag_trade_days,
        processed_root=processed_root,
        candidate_plan_json=candidate_plan_json,
        candidate_plan_gate_json=candidate_plan_gate_json,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
    )
    return result


def compute_dragon_tiger_factor_frame(
    stock_day: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    candidate_specs: Sequence[dict[str, Any]] | None = None,
    pit_lag_trade_days: int = 1,
) -> pd.DataFrame:
    clean = _normalise_stock_day(stock_day)
    if clean.empty:
        return _empty_factor_frame()
    clean = clean[pd.to_datetime(clean["available_date"]) > pd.to_datetime(clean["event_date"])].copy()
    if clean.empty:
        return _empty_factor_frame()
    clean["date"] = _signal_dates(clean, bars, pit_lag_trade_days=pit_lag_trade_days)
    clean = clean.dropna(subset=["date"]).reset_index(drop=True)
    allowed = {candidate["factor_name"] for candidate in (candidate_specs or _default_candidate_specs())}
    rows: list[pd.DataFrame] = []
    list_mask = _num(clean, "top_list_event_count") > 0
    inst_mask = _num(clean, "top_inst_event_count") > 0
    list_denom = _positive(_num(clean, "top_list_amount_sum"))
    net_ratio = _safe_ratio(_num(clean, "top_list_net_amount_sum"), list_denom)
    inst_gross = _num(clean, "top_inst_buy_sum").abs() + _num(clean, "top_inst_sell_sum").abs()
    inst_denom = list_denom.combine_first(_positive(inst_gross)).combine_first(_positive(_num(clean, "top_inst_abs_net_buy_sum")))
    factor_values = {
        "dragon_tiger_abnormal_attention_reversal_1d": (
            -_num(clean, "top_list_abs_pct_change_max").abs()
            * _num(clean, "top_list_amount_rate_max").clip(lower=0)
            * _num(clean, "top_list_event_count").map(lambda value: math.log1p(value) if _is_finite(value) and value > 0 else 0.0)
        ),
        "dragon_tiger_net_buy_continuation_1d": net_ratio,
        "dragon_tiger_net_sell_exhaustion_reversal_1d": (-net_ratio).where(net_ratio < 0.0, 0.0),
        "dragon_tiger_institutional_net_buy_pressure_1d": _safe_ratio(_num(clean, "top_inst_net_buy_sum"), inst_denom),
        "dragon_tiger_institutional_disagreement_abs_pressure_1d": _safe_ratio(
            _num(clean, "top_inst_abs_net_buy_sum"),
            inst_denom,
        ),
    }
    masks = {
        "dragon_tiger_abnormal_attention_reversal_1d": list_mask,
        "dragon_tiger_net_buy_continuation_1d": list_mask,
        "dragon_tiger_net_sell_exhaustion_reversal_1d": list_mask,
        "dragon_tiger_institutional_net_buy_pressure_1d": inst_mask,
        "dragon_tiger_institutional_disagreement_abs_pressure_1d": inst_mask,
    }
    event_counts = {
        "dragon_tiger_abnormal_attention_reversal_1d": _num(clean, "top_list_event_count"),
        "dragon_tiger_net_buy_continuation_1d": _num(clean, "top_list_event_count"),
        "dragon_tiger_net_sell_exhaustion_reversal_1d": _num(clean, "top_list_event_count"),
        "dragon_tiger_institutional_net_buy_pressure_1d": _num(clean, "top_inst_event_count"),
        "dragon_tiger_institutional_disagreement_abs_pressure_1d": _num(clean, "top_inst_event_count"),
    }
    base_columns = ["date", "event_date", "asset_id", "market"]
    for factor_name, values in factor_values.items():
        if factor_name not in allowed:
            continue
        frame = clean.loc[masks[factor_name], base_columns].copy()
        frame["factor_name"] = factor_name
        frame["factor_value"] = pd.to_numeric(values.loc[frame.index], errors="coerce")
        frame["pit_lag_trade_days"] = int(pit_lag_trade_days)
        frame["source_event_count"] = pd.to_numeric(event_counts[factor_name].loc[frame.index], errors="coerce").fillna(0)
        frame = frame.dropna(subset=["date", "event_date", "asset_id", "factor_value"])
        rows.append(frame)
    if not rows:
        return _empty_factor_frame()
    frame = pd.concat(rows, ignore_index=True)
    frame = _attach_bar_context(frame, bars)
    return (
        frame.groupby(["date", "asset_id", "market", "factor_name"], as_index=False, dropna=False)
        .agg(
            factor_value=("factor_value", "mean"),
            event_date=("event_date", "min"),
            amount=("amount", "median"),
            adv20_amount=("adv20_amount", "median"),
            log_adv20=("log_adv20", "median"),
            pit_lag_trade_days=("pit_lag_trade_days", "max"),
            source_event_count=("source_event_count", "sum"),
        )
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )


def load_dragon_tiger_stock_day(
    processed_root: str | Path,
    *,
    market: str = "CN",
    start_year: int = 2015,
    end_year: int = 2025,
) -> pd.DataFrame:
    store = DatasetStore(processed_root)
    frames = []
    for year in range(int(start_year), int(end_year) + 1):
        partitions = {"frequency": "1d", "market": market.upper(), "year": str(year)}
        if store.exists("processed/dragon_tiger_stock_day", partitions):
            frames.append(store.read_frame("processed/dragon_tiger_stock_day", partitions))
    if not frames:
        raise FileNotFoundError(f"No processed Dragon-Tiger stock-day data found under {processed_root}")
    return pd.concat(frames, ignore_index=True)


def load_stock_basic(path: str | Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame(columns=["asset_id", "symbol", "industry"])
    root = Path(path)
    files = [root] if root.is_file() else sorted([*root.rglob("*.parquet"), *root.rglob("*.csv")])
    frames = []
    for file in files:
        try:
            frame = pd.read_parquet(file) if file.suffix.lower() == ".parquet" else pd.read_csv(file)
        except Exception:
            continue
        if "asset_id" in frame.columns or "ts_code" in frame.columns:
            frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["asset_id", "symbol", "industry"])
    output = pd.concat(frames, ignore_index=True)
    if "asset_id" not in output and "ts_code" in output:
        output["asset_id"] = output["ts_code"].map(_symbol_to_asset_id)
    for column in ["asset_id", "symbol", "industry"]:
        if column not in output:
            output[column] = ""
    return output.drop_duplicates("asset_id", keep="last").reset_index(drop=True)


def write_dragon_tiger_pit_ic_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "dragon_tiger_pit_ic_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "dragon_tiger_pit_ic_prescreen.md").write_text(
        render_dragon_tiger_pit_ic_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "dragon_tiger_pit_ic_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "dragon_tiger_pit_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )
    _write_csv(
        output_path / "dragon_tiger_pit_neutral_observations.csv",
        result.get("neutral_observations", []),
        NEUTRAL_OBSERVATION_COLUMNS,
    )


def render_dragon_tiger_pit_ic_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    neutral = result.get("neutral_policy", {})
    lines = [
        "# Dragon-Tiger PIT Event IC Prescreen Round232",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Style residual repair candidates: {summary.get('style_residual_repair_candidate_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Neutral-gate pass tests: {summary.get('neutral_gate_pass_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: {summary.get('next_direction', NEXT_DIRECTION_WITHOUT_LEADS)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## PIT Policy",
        "",
        f"- Signal date rule: {result.get('pit_policy', {}).get('event_signal_date_rule', '')}",
        f"- Same-day Dragon-Tiger trading allowed: {result.get('pit_policy', {}).get('same_day_event_trading_allowed', False)}",
        "",
        "## Neutral Policy",
        "",
        f"- Min neutral RankIC: {float(neutral.get('min_neutral_rank_ic', 0.0)):.4f}",
        f"- Min neutral t-stat: {float(neutral.get('min_neutral_ic_t_stat', 0.0)):.2f}",
        f"- Min neutral retention: {float(neutral.get('min_neutral_retention', 0.0)):.2f}",
        "",
        "## Top Results",
        "",
        "| Factor | Horizon | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | IndT | SizeNeuIC | SizeT | Lead | Repair |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", [])[:25]:
        lines.append(
            "| {factor_name} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {ind:.4f} | {indt:.2f} | {size:.4f} | {sizet:.2f} | {lead} | {repair} |".format(
                factor_name=row.get("factor_name", ""),
                horizon=int(row.get("horizon", 0)),
                ic=_number(row.get("mean_spearman_ic")),
                icir=_number(row.get("icir")),
                t=_number(row.get("ic_t_stat")),
                pos=_number(row.get("ic_positive_rate")),
                spread=_number(row.get("quantile_spread")),
                ind=_number(row.get("mean_industry_neutral_rank_ic")),
                indt=_number(row.get("industry_neutral_rank_ic_t_stat")),
                size=_number(row.get("mean_size_neutral_rank_ic")),
                sizet=_number(row.get("size_neutral_rank_ic_t_stat")),
                lead="yes" if row.get("research_lead") else "no",
                repair="yes" if row.get("style_residual_repair_candidate") else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This is a point-in-time event IC prescreen, not a portfolio backtest.",
            "- Dragon-Tiger rows are shifted to `available_date`; same-day event trading is blocked.",
            "- Portfolio grids remain blocked until neutral IC, de-dup, walk-forward, cost/capacity, regime, and final-holdout gates clear.",
        ]
    )
    return "\n".join(lines) + "\n"


def _specialize_result(
    result: dict[str, Any],
    *,
    bars: pd.DataFrame,
    stock_day: pd.DataFrame,
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    specs: Sequence[dict[str, Any]],
    analysis_start_date: str,
    analysis_end_date: str,
    include_final_holdout: bool,
    execution_lag: int,
    pit_lag_trade_days: int,
    processed_root: str | Path | None,
    candidate_plan_json: str | Path | None,
    candidate_plan_gate_json: str | Path | None,
    min_neutral_rank_ic: float,
    min_neutral_ic_t_stat: float,
) -> None:
    result["stage"] = STAGE
    summary = result.get("summary", {})
    repair_count = _mark_style_repair_candidates(
        result.get("results", []),
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
    )
    summary["style_residual_repair_candidate_count"] = repair_count
    if summary.get("research_lead_count", 0):
        summary["next_direction"] = NEXT_DIRECTION_WITH_LEADS
    elif repair_count:
        summary["next_direction"] = NEXT_DIRECTION_WITH_REPAIR
    else:
        summary["next_direction"] = NEXT_DIRECTION_WITHOUT_LEADS
    result["data_window"] = _data_window(bars, stock_day, factor_frame, labels)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "blocked_until_walk_forward_oos_clearance",
    }
    result["pit_policy"] = {
        "pit_lag_trade_days": int(pit_lag_trade_days),
        "event_signal_date_rule": "tushare_dragon_tiger_available_date_strictly_after_trade_date",
        "execution_lag": int(execution_lag),
        "same_day_event_trading_allowed": False,
    }
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": "dragon_tiger_neutral_lead_dedup_before_portfolio_grid_preflight",
        "reason": "This is a Dragon-Tiger PIT event IC prescreen. Portfolio grids remain blocked until neutral IC, de-dup, walk-forward, cost/capacity, regime, and final-holdout gates clear.",
    }
    result["candidate_specs"] = [dict(spec) for spec in specs]
    result["processed_root"] = str(Path(processed_root)) if processed_root else None
    result["candidate_plan_json"] = str(Path(candidate_plan_json)) if candidate_plan_json else None
    result["candidate_plan_gate_json"] = str(Path(candidate_plan_gate_json)) if candidate_plan_gate_json else None
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_dragon_tiger_pit_ic_prescreen_markdown(result)


def _mark_style_repair_candidates(
    rows: list[dict[str, Any]],
    *,
    min_neutral_rank_ic: float,
    min_neutral_ic_t_stat: float,
) -> int:
    repair_count = 0
    for row in rows:
        blockers = [
            blocker
            for blocker in row.get("blockers", [])
            if blocker
            not in {
                "promotion_requires_later_walk_forward_cost_capacity_regime_gates",
                "promotion_requires_later_walk_forward_cost_capacity_regime_final_holdout",
            }
        ]
        raw_pass = bool(
            row.get("fdr_significant")
            and _number(row.get("mean_spearman_ic")) >= 0.02
            and _number(row.get("icir")) >= 0.30
            and _number(row.get("ic_positive_rate")) >= 0.55
            and _number(row.get("quantile_spread")) > 0.0
            and _number(row.get("quantile_monotonicity")) >= 0.70
        )
        industry_pass = (
            "industry_neutral_ic_below_gate" not in blockers
            and _number(row.get("mean_industry_neutral_rank_ic")) >= min_neutral_rank_ic
            and _number(row.get("industry_neutral_rank_ic_t_stat")) >= min_neutral_ic_t_stat
        )
        size_signal_exists = bool(
            _number(row.get("mean_size_neutral_rank_ic")) >= min_neutral_rank_ic
            and _number(row.get("size_neutral_rank_ic_t_stat")) >= min_neutral_ic_t_stat
        )
        repair_candidate = bool(raw_pass and industry_pass and size_signal_exists and "size_neutral_ic_below_gate" in blockers)
        row["style_residual_repair_candidate"] = repair_candidate
        if repair_candidate:
            repair_count += 1
            blockers.append("size_neutral_retention_below_gate_repair_required")
        blockers.append("promotion_requires_later_walk_forward_cost_capacity_regime_final_holdout")
        row["blockers"] = _dedupe(blockers)
    return repair_count


def _normalise_stock_day(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "available_date", "asset_id", "market"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Dragon-Tiger stock-day data is missing required columns: {', '.join(missing)}")
    output = frame.copy()
    output["event_date"] = pd.to_datetime(output["date"], errors="coerce")
    output["available_date"] = pd.to_datetime(output["available_date"], errors="coerce")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    for column in [
        "top_list_event_count",
        "top_list_reason_count",
        "top_list_amount_sum",
        "top_list_net_amount_sum",
        "top_list_abs_pct_change_max",
        "top_list_amount_rate_max",
        "top_inst_event_count",
        "top_inst_reason_count",
        "top_inst_buy_sum",
        "top_inst_sell_sum",
        "top_inst_net_buy_sum",
        "top_inst_abs_net_buy_sum",
    ]:
        if column not in output:
            output[column] = 0.0
        output[column] = pd.to_numeric(output[column], errors="coerce").fillna(0.0)
    return output.dropna(subset=["event_date", "available_date", "asset_id", "market"]).reset_index(drop=True)


def _signal_dates(stock_day: pd.DataFrame, bars: pd.DataFrame, *, pit_lag_trade_days: int) -> pd.Series:
    signal_dates = pd.to_datetime(stock_day["available_date"], errors="coerce")
    extra_lag = max(int(pit_lag_trade_days), 1) - 1
    if extra_lag <= 0:
        return signal_dates
    trade_dates = pd.DatetimeIndex(sorted(pd.to_datetime(bars["date"], errors="coerce").dropna().unique()))
    shifted = []
    for signal_date in signal_dates:
        if pd.isna(signal_date) or trade_dates.empty:
            shifted.append(pd.NaT)
            continue
        index = trade_dates.searchsorted(signal_date, side="left") + extra_lag
        shifted.append(trade_dates[index] if index < len(trade_dates) else pd.NaT)
    return pd.Series(shifted, index=stock_day.index)


def _attach_bar_context(frame: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    context = _bar_context(bars, frame[["date", "asset_id", "market"]].drop_duplicates())
    output = frame.merge(context, on=["date", "asset_id", "market"], how="left", validate="many_to_one")
    return output


def _bar_context(bars: pd.DataFrame, needed_pairs: pd.DataFrame) -> pd.DataFrame:
    frame = _normalise_bar_amounts(bars)
    if frame.empty or needed_pairs.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "amount", "adv20_amount", "log_adv20"])
    pairs = needed_pairs.copy()
    pairs["date"] = pd.to_datetime(pairs["date"], errors="coerce")
    pairs["asset_id"] = pairs["asset_id"].astype(str)
    pairs["market"] = pairs["market"].fillna("CN").astype(str).str.upper()
    assets = set(pairs["asset_id"])
    start = pairs["date"].min() - pd.Timedelta(days=90)
    end = pairs["date"].max()
    frame = frame[(frame["asset_id"].isin(assets)) & (frame["date"] >= start) & (frame["date"] <= end)].copy()
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    frame["adv20_amount"] = (
        frame.groupby("asset_id")["amount"]
        .rolling(20, min_periods=5)
        .mean()
        .reset_index(level=0, drop=True)
    )
    frame["log_adv20"] = _safe_log(frame["adv20_amount"])
    context = frame[["date", "asset_id", "market", "amount", "adv20_amount", "log_adv20"]]
    return context.merge(pairs, on=["date", "asset_id", "market"], how="inner")


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
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


def _normalise_bar_amounts(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars[required + (["adj_close"] if "adj_close" in bars.columns else [])].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    if "adj_close" in frame:
        frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
        frame = frame[frame["adj_close"] > 0]
    return (
        frame[(frame["market"] == "CN")]
        .dropna(subset=required)
        .drop_duplicates(["date", "asset_id", "market"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _filter_date_window(
    frame: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
    include_final_holdout: bool,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    end = output["date"].max() if include_final_holdout else pd.Timestamp(end_date)
    return output[(output["date"] >= pd.Timestamp(start_date)) & (output["date"] <= end)].reset_index(drop=True)


def _candidate_specs(candidate_plan_json: str | Path | None, candidate_plan_gate_json: str | Path | None) -> list[dict[str, Any]]:
    specs = _default_candidate_specs()
    plan = _load_json(candidate_plan_json)
    if plan:
        plan_specs = [
            dict(candidate)
            for candidate in _list_of_dicts(plan.get("candidates"))
            if candidate.get("factor_name") in DRAGON_TIGER_CANDIDATE_NAMES
        ]
        if plan_specs:
            specs = plan_specs
    gate = _load_json(candidate_plan_gate_json)
    if gate:
        active_names = {
            str(row.get("factor_name"))
            for row in _list_of_dicts(gate.get("candidate_rows"))
            if row.get("active_for_gate")
        }
        if active_names:
            specs = [spec for spec in specs if spec.get("factor_name") in active_names]
    return specs


def _default_candidate_specs() -> list[dict[str, Any]]:
    rationales = {
        "dragon_tiger_abnormal_attention_reversal_1d": "Abnormal Dragon-Tiger attention can overreact and reverse after public disclosure.",
        "dragon_tiger_net_buy_continuation_1d": "Large disclosed net buying can proxy short-horizon demand continuation.",
        "dragon_tiger_net_sell_exhaustion_reversal_1d": "Large disclosed net selling can proxy temporary supply exhaustion.",
        "dragon_tiger_institutional_net_buy_pressure_1d": "Institutional net buy pressure may contain cleaner informed-flow information.",
        "dragon_tiger_institutional_disagreement_abs_pressure_1d": "Absolute institutional pressure can proxy attention and disagreement.",
    }
    return [
        {
            "factor_name": name,
            "family": "dragon_tiger_attention_reversal_event",
            "formula_template": name,
            "direction": "higher_is_better",
            "required_endpoints": ["top_list", "top_inst"],
            "required_fields": [
                "date",
                "available_date",
                "top_list_amount_sum",
                "top_list_net_amount_sum",
                "top_inst_net_buy_sum",
            ],
            "event_date_fields": ["date", "available_date"],
            "windows": [1],
            "economic_rationale": rationales[name],
            "public_reference_tags": ["dragon_tiger", "event_study", "alphalens"],
            "expected_failure_modes": ["event_sparse_coverage", "same_day_disclosure_lookahead", "industry_size_attention_beta"],
            "portfolio_backtest_allowed": False,
            "promotion_allowed": False,
        }
        for name in DRAGON_TIGER_CANDIDATE_NAMES
    ]


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denom = pd.to_numeric(denominator, errors="coerce")
    return pd.to_numeric(numerator, errors="coerce") / denom.where(denom.abs() > 0)


def _positive(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.where(values > 0)


def _num(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _safe_log(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.where(values > 0).map(lambda value: math.log(value) if _is_finite(value) and value > 0 else pd.NA)


def _data_window(bars: pd.DataFrame, stock_day: pd.DataFrame, factor_frame: pd.DataFrame, labels: pd.DataFrame) -> dict[str, Any]:
    clean_stock_day = _normalise_stock_day(stock_day) if not stock_day.empty else stock_day
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "min_event_date": _min_date(clean_stock_day, "event_date"),
        "max_event_date": _max_date(clean_stock_day, "event_date"),
        "min_available_date": _min_date(clean_stock_day, "available_date"),
        "max_available_date": _max_date(clean_stock_day, "available_date"),
        "min_signal_date": _min_date(factor_frame, "date"),
        "max_signal_date": _max_date(factor_frame, "date"),
        "min_label_date": _min_date(labels, "date"),
        "max_label_date": _max_date(labels, "date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
        "stock_day_rows": int(len(stock_day)),
        "stock_day_assets": int(stock_day["asset_id"].nunique()) if not stock_day.empty and "asset_id" in stock_day else 0,
        "factor_rows": int(len(factor_frame)),
    }


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "event_date",
            "asset_id",
            "market",
            "factor_name",
            "factor_value",
            "amount",
            "adv20_amount",
            "log_adv20",
            "pit_lag_trade_days",
            "source_event_count",
        ]
    )


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _symbol_to_asset_id(symbol: Any) -> str | None:
    text = str(symbol).strip()
    if not text or "." not in text:
        return None
    code, suffix = text.split(".", 1)
    exchange = {"SZ": "XSHE", "SH": "XSHG", "BJ": "XBEI"}.get(suffix.upper())
    if not exchange:
        return None
    return f"CN_{exchange}_{code}"


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


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
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


def _dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
