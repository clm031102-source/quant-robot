from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    RESULT_COLUMNS,
    _sanitize,
    _write_csv,
    load_capacity_safe_bars,
    summarize_capacity_safe_price_volume_prescreen,
)
from quant_robot.research.labels import make_forward_returns
from quant_robot.storage.dataset_store import DatasetStore


STAGE = "external_feed_margin_credit_prescreen"
DEFAULT_SEED_CONFIG = Path("configs/external_feed_factor_seed_preregistration_round170_20260623.json")
DEFAULT_MARGIN_CREDIT_HORIZONS = (20,)
MARGIN_CREDIT_FACTOR_NAMES = (
    "margin_financing_acceleration_exhaustion_20",
    "margin_balance_crowding_reversal_20",
)
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"


def build_external_feed_margin_credit_prescreen(
    *,
    bars: pd.DataFrame | None = None,
    bars_roots: Iterable[str | Path] | None = None,
    margin_detail: pd.DataFrame | None = None,
    processed_root: str | Path | None = None,
    seed_config_path: str | Path = DEFAULT_SEED_CONFIG,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_MARGIN_CREDIT_HORIZONS,
    execution_lag: int = 1,
    lookback: int = 20,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    market: str = "CN",
) -> dict[str, Any]:
    specs = _margin_credit_candidate_specs(seed_config_path)
    if bars is None:
        if bars_roots is None:
            raise ValueError("Either bars or bars_roots must be provided")
        bars = load_capacity_safe_bars(
            bars_roots,
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
        )
    clean_bars = _normalise_bars(bars)
    if margin_detail is None:
        if processed_root is None:
            raise ValueError("Either margin_detail or processed_root must be provided")
        margin_detail = _read_processed_dataset(Path(processed_root), "external_margin_detail", market)

    factor_frame = compute_external_feed_margin_credit_factors(
        bars=clean_bars,
        margin_detail=margin_detail,
        candidate_specs=specs,
        lookback=lookback,
        min_signal_date_amount=min_signal_date_amount,
    )
    factor_frame = _filter_date_window(
        factor_frame,
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    label_end = _max_timestamp(clean_bars["date"]) if include_final_holdout else pd.Timestamp(analysis_end_date)
    labels = make_forward_returns(
        clean_bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= label_end].reset_index(drop=True)
    result = summarize_capacity_safe_price_volume_prescreen(
        factor_frame,
        labels,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        max_top_quantile_turnover=1.0,
    )
    result["stage"] = STAGE
    result["generated_at"] = date.today().isoformat()
    result["summary"]["promotion_allowed_candidates"] = 0
    result["summary"]["portfolio_backtest_allowed_candidates"] = 0
    result["summary"]["next_direction"] = "round193_margin_credit_dedup_or_family_rotation_after_prescreen"
    result["summary"]["margin_credit_candidate_count"] = len(specs)
    result["data_window"] = _data_window(clean_bars, factor_frame, labels, margin_detail)
    result["holdout_policy"] = {
        "final_holdout_included": bool(include_final_holdout),
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "blocked_until_oos_neutral_dedup_cost_capacity_regime_clearance",
    }
    result["pit_policy"] = {
        "join_date_column": "available_date",
        "forbidden_join_date_column": "date",
        "raw_date_must_be_before_signal_date": True,
        "execution_lag": int(execution_lag),
        "lookback_observations": int(lookback),
    }
    result["external_feed_policy"] = {
        "margin_detail_unblocked_for_prescreen": True,
        "lpr_still_blocked": True,
        "allowed_stage": "ic_quantile_turnover_prescreen_only",
        "blocked_uses": [
            "portfolio_grid_before_redundancy_cost_capacity_walk_forward_regime",
            "lpr_dependent_regime_factor_before_lpr_coverage_repair",
            "same_day_raw_external_feed_join",
            "direction_flip_after_viewing_results",
        ],
    }
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": "external_margin_credit_reference_dedup_and_neutral_review",
        "blockers": [
            "prescreen_is_not_portfolio_evidence",
            "requires_reference_correlation_dedup",
            "requires_industry_size_liquidity_neutral_review",
            "requires_cost_capacity_walk_forward",
            "requires_china_regime_stress_audit",
            "requires_final_holdout_clearance",
        ],
        "reason": "Round192 can only create external margin-credit research leads. Promotion and portfolio grids remain blocked.",
    }
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_external_feed_margin_credit_prescreen_markdown(result)
    return result


def compute_external_feed_margin_credit_factors(
    *,
    bars: pd.DataFrame,
    margin_detail: pd.DataFrame,
    candidate_specs: Sequence[dict[str, Any]] | None = None,
    lookback: int = 20,
    min_signal_date_amount: float = 10_000_000,
) -> pd.DataFrame:
    specs = list(candidate_specs or _default_margin_credit_candidate_specs())
    allowed_names = {
        str(spec["factor_name"])
        for spec in specs
        if str(spec.get("factor_name", "")) in MARGIN_CREDIT_FACTOR_NAMES
    }
    if not allowed_names:
        return _empty_factor_frame()
    bar_context = _bar_context(bars)
    margin = _normalise_margin_detail(margin_detail, lookback=lookback)
    if bar_context.empty or margin.empty:
        return _empty_factor_frame()
    joined = _join_latest_by_asset(bar_context, margin)
    if joined.empty:
        return _empty_factor_frame()
    joined = joined[
        (joined["amount"] >= min_signal_date_amount)
        & (joined["adv20_amount"] >= min_signal_date_amount)
        & (joined["return_1d"].abs() <= 0.50)
        & (pd.to_datetime(joined["raw_date"]) < pd.to_datetime(joined["date"]))
        & (pd.to_datetime(joined["available_date"]) <= pd.to_datetime(joined["date"]))
    ].copy()
    if joined.empty:
        return _empty_factor_frame()

    rows: list[pd.DataFrame] = []
    base_columns = [
        "date",
        "asset_id",
        "market",
        "factor_name",
        "factor_value",
        "amount",
        "adv20_amount",
        "log_adv20",
        "raw_date",
        "available_date",
        "rzye",
        "rzmre",
        "rqye",
        "rzrqye",
    ]
    if "margin_financing_acceleration_exhaustion_20" in allowed_names:
        frame = joined.copy()
        frame["factor_name"] = "margin_financing_acceleration_exhaustion_20"
        frame["factor_value"] = -frame["rzmre_acceleration"] * (1.0 + frame["rzye_crowding"].clip(lower=0.0))
        rows.append(frame[base_columns])
    if "margin_balance_crowding_reversal_20" in allowed_names:
        frame = joined.copy()
        frame["factor_name"] = "margin_balance_crowding_reversal_20"
        frame["factor_value"] = -frame["rzye_crowding"]
        rows.append(frame[base_columns])
    if not rows:
        return _empty_factor_frame()
    factors = pd.concat(rows, ignore_index=True)
    return (
        factors.dropna(subset=["factor_value", "amount", "adv20_amount"])
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )


def write_external_feed_margin_credit_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "external_feed_margin_credit_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "external_feed_margin_credit_prescreen.md").write_text(
        render_external_feed_margin_credit_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "external_feed_margin_credit_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "external_feed_margin_credit_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )


def render_external_feed_margin_credit_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    policy = _dict(result.get("promotion_policy"))
    lines = [
        "# External Feed Margin Credit Prescreen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Portfolio backtest allowed candidates: {summary.get('portfolio_backtest_allowed_candidates', 0)}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Promotion allowed: {policy.get('promotion_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Top Results",
        "",
        "| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Turnover | FDR | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", [])[:20]:
        lines.append(
            "| {factor_name} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {mono:.3f} | {turnover:.1%} | {fdr} | {lead} |".format(
                factor_name=row["factor_name"],
                horizon=row["horizon"],
                ic=float(row["mean_spearman_ic"]),
                icir=float(row["icir"]),
                t=float(row["ic_t_stat"]),
                pos=float(row["ic_positive_rate"]),
                spread=float(row["quantile_spread"]),
                mono=float(row["quantile_monotonicity"]),
                turnover=float(row["avg_top_quantile_turnover"]),
                fdr="yes" if row["fdr_significant"] else "no",
                lead="yes" if row["research_lead"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This stage is an IC/quantile/turnover prescreen for preregistered margin-credit external-feed seeds.",
            "- It uses available_date joins and rejects same-day raw external-feed observations.",
            "- Factor direction is preregistered as crowding/exhaustion reversal; direction is not flipped after viewing results.",
            "- It cannot promote factors or start portfolio grids before redundancy, neutralization, cost/capacity, walk-forward, regime, and final-holdout gates.",
            "",
            "## Promotion Blockers",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in _list(policy.get("blockers")))
    lines.append("")
    return "\n".join(lines)


def _bar_context(bars: pd.DataFrame) -> pd.DataFrame:
    frame = _normalise_bars(bars)
    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("asset_id", sort=False):
        group = group.sort_values("date").copy()
        group["return_1d"] = group["adj_close"].pct_change()
        group["adv20_amount"] = group["amount"].rolling(20, min_periods=5).mean()
        pieces.append(group)
    if not pieces:
        return pd.DataFrame()
    output = pd.concat(pieces, ignore_index=True)
    output["log_adv20"] = pd.to_numeric(output["adv20_amount"], errors="coerce").where(
        output["adv20_amount"] > 0
    ).map(lambda value: math.log(value) if pd.notna(value) else pd.NA)
    return output.dropna(subset=["date", "asset_id", "market", "amount", "adv20_amount"]).reset_index(drop=True)


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).astype("datetime64[ns]")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    if "symbol" not in frame:
        frame["symbol"] = frame["asset_id"].map(_asset_id_to_symbol)
    for column in ["adj_close", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return (
        frame[(frame["market"] == "CN") & (frame["adj_close"] > 0) & (frame["amount"] > 0)]
        .dropna(subset=required)
        .drop_duplicates(["date", "asset_id", "market"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _normalise_margin_detail(margin_detail: pd.DataFrame, *, lookback: int) -> pd.DataFrame:
    if margin_detail.empty:
        return pd.DataFrame()
    required = ["date", "available_date", "rzye", "rzmre"]
    missing = [column for column in required if column not in margin_detail.columns]
    if missing:
        raise ValueError(f"Margin detail feed is missing required columns: {', '.join(missing)}")
    frame = margin_detail.copy()
    frame["date"] = pd.to_datetime(frame["date"]).astype("datetime64[ns]")
    frame["available_date"] = pd.to_datetime(frame["available_date"]).astype("datetime64[ns]")
    if "asset_id" not in frame:
        if "symbol" not in frame:
            raise ValueError("Margin detail feed requires asset_id or symbol")
        frame["asset_id"] = frame["symbol"].map(_asset_id_from_tushare_symbol)
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame.get("market", "CN")
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in ["rzye", "rqye", "rzmre", "rzrqye"]:
        if column not in frame:
            frame[column] = 0.0
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame[(frame["market"] == "CN")].dropna(subset=["date", "available_date", "asset_id", "rzye", "rzmre"])
    frame = frame.sort_values(["asset_id", "date", "available_date"]).drop_duplicates(
        ["asset_id", "date"],
        keep="last",
    )
    pieces: list[pd.DataFrame] = []
    min_periods = max(5, min(int(lookback), 10))
    for _, group in frame.groupby("asset_id", sort=False):
        group = group.sort_values("date").copy()
        abs_mean = group["rzmre"].abs().rolling(int(lookback), min_periods=min_periods).mean().replace(0, pd.NA)
        rzmre_5 = group["rzmre"].rolling(5, min_periods=3).sum()
        group["rzmre_acceleration"] = (rzmre_5 - rzmre_5.shift(5)) / abs_mean
        rzye_mean = group["rzye"].rolling(int(lookback), min_periods=min_periods).mean().replace(0, pd.NA)
        group["rzye_crowding"] = group["rzye"] / rzye_mean - 1.0
        pieces.append(group)
    if not pieces:
        return pd.DataFrame()
    output = pd.concat(pieces, ignore_index=True).rename(columns={"date": "raw_date"})
    return output[
        [
            "asset_id",
            "raw_date",
            "available_date",
            "rzye",
            "rqye",
            "rzmre",
            "rzrqye",
            "rzmre_acceleration",
            "rzye_crowding",
        ]
    ].reset_index(drop=True)


def _join_latest_by_asset(bar_context: pd.DataFrame, margin: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    margin_by_asset = {
        asset_id: group.sort_values("available_date") for asset_id, group in margin.groupby("asset_id", sort=False)
    }
    for asset_id, bar_group in bar_context.groupby("asset_id", sort=False):
        margin_group = margin_by_asset.get(asset_id)
        if margin_group is None or margin_group.empty:
            continue
        merged = pd.merge_asof(
            bar_group.sort_values("date"),
            margin_group.sort_values("available_date"),
            left_on="date",
            right_on="available_date",
            direction="backward",
            allow_exact_matches=True,
        )
        merged["asset_id"] = asset_id
        rows.append(merged)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def _margin_credit_candidate_specs(seed_config_path: str | Path) -> list[dict[str, Any]]:
    path = Path(seed_config_path)
    if not path.exists():
        return _default_margin_credit_candidate_specs()
    config = json.loads(path.read_text(encoding="utf-8"))
    specs = []
    for seed in config.get("factor_seeds", []):
        name = str(seed.get("factor_name", ""))
        if name in MARGIN_CREDIT_FACTOR_NAMES:
            specs.append(dict(seed))
    return specs or _default_margin_credit_candidate_specs()


def _default_margin_credit_candidate_specs() -> list[dict[str, Any]]:
    return [
        {
            "factor_name": "margin_financing_acceleration_exhaustion_20",
            "family": "external_margin_credit",
            "horizons": [20],
            "hypothesis": "Rapid financing-buy acceleration can mark crowded demand exhaustion; direction is negative.",
        },
        {
            "factor_name": "margin_balance_crowding_reversal_20",
            "family": "external_margin_credit",
            "horizons": [20],
            "hypothesis": "High financing balance versus trailing level can proxy crowded-position reversal.",
        },
    ]


def _read_processed_dataset(root: Path, dataset: str, market: str) -> pd.DataFrame:
    store_root = _normalize_processed_root(root, dataset)
    store = DatasetStore(store_root)
    market = market.upper()
    base = store_root / "processed" / dataset / "frequency=1d" / f"market={market}"
    frames = []
    for year_path in sorted(base.glob("year=*")):
        year = year_path.name.split("=", 1)[1]
        frames.append(store.read_frame(f"processed/{dataset}", {"frequency": "1d", "market": market, "year": year}))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _normalize_processed_root(root: Path, dataset: str) -> Path:
    if (root / dataset).exists() and not (root / "processed" / dataset).exists():
        return root.parent
    return root


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
    output["date"] = pd.to_datetime(output["date"]).astype("datetime64[ns]")
    end = output["date"].max() if include_final_holdout else pd.Timestamp(end_date)
    return output[(output["date"] >= pd.Timestamp(start_date)) & (output["date"] <= end)].reset_index(drop=True)


def _data_window(
    bars: pd.DataFrame,
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    margin_detail: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "min_signal_date": _min_date(factor_frame, "date"),
        "max_signal_date": _max_date(factor_frame, "date"),
        "min_label_date": _min_date(labels, "date"),
        "max_label_date": _max_date(labels, "date"),
        "min_margin_raw_date": _min_date(margin_detail, "date"),
        "max_margin_raw_date": _max_date(margin_detail, "date"),
        "min_margin_available_date": _min_date(margin_detail, "available_date"),
        "max_margin_available_date": _max_date(margin_detail, "available_date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
        "margin_detail_rows": int(len(margin_detail)),
        "margin_detail_assets": int(margin_detail["asset_id"].nunique()) if "asset_id" in margin_detail else 0,
        "factor_rows": int(len(factor_frame)),
        "factor_assets": int(factor_frame["asset_id"].nunique()) if not factor_frame.empty else 0,
    }


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "asset_id",
            "market",
            "factor_name",
            "factor_value",
            "amount",
            "adv20_amount",
            "log_adv20",
            "raw_date",
            "available_date",
            "rzye",
            "rzmre",
            "rqye",
            "rzrqye",
        ]
    )


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_datetime(frame[column]).dropna()
    if values.empty:
        return None
    return values.min().date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_datetime(frame[column]).dropna()
    if values.empty:
        return None
    return values.max().date().isoformat()


def _max_timestamp(series: pd.Series) -> pd.Timestamp:
    return pd.Timestamp(pd.to_datetime(series).max())


def _asset_id_from_tushare_symbol(symbol: str) -> str:
    parts = str(symbol).split(".")
    if len(parts) != 2:
        raise ValueError(f"Unsupported Tushare symbol: {symbol}")
    code, suffix = parts
    exchange_by_suffix = {"SZ": "XSHE", "SH": "XSHG", "BJ": "XBEI"}
    try:
        exchange = exchange_by_suffix[suffix.upper()]
    except KeyError as exc:
        raise ValueError(f"Unsupported Tushare symbol suffix: {symbol}") from exc
    return f"CN_{exchange}_{code}"


def _asset_id_to_symbol(asset_id: str) -> str:
    text = str(asset_id)
    parts = text.split("_")
    if len(parts) < 3:
        return text
    exchange = parts[-2]
    code = parts[-1]
    suffix = {"XSHE": "SZ", "XSHG": "SH", "XBEI": "BJ"}.get(exchange, "")
    return f"{code}.{suffix}" if suffix else text


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]
