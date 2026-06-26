from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_preregistration import SAFETY
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    RESULT_COLUMNS,
    _cs_zscore,
    _data_window,
    _sanitize,
    _write_csv,
    load_capacity_safe_bars,
    summarize_capacity_safe_price_volume_prescreen,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "tradeability_structure_quality_prescreen"
DEFAULT_CANDIDATE_PLAN = Path("configs/factor_mining_candidate_plan_round209_tradeability_structure_quality_20260624.json")
DEFAULT_TRADEABILITY_MASK_ROOT = Path("data/processed/round199_tradeability_mask_cache_2015_2025_with_stock_basic_20260623")
NEXT_REQUIRED_GATE = "tradeability_survivorship_residual_audit_before_portfolio_conversion"
BOOL_MASK_COLUMNS = (
    "entry_tradeable",
    "exit_tradeable",
    "fully_tradeable",
    "can_buy",
    "can_sell",
    "suspended_official",
    "limit_up_official",
    "limit_down_official",
    "st_flag_official",
    "new_listing_flag",
    "delisted_or_inactive_flag",
    "board_permission_blocked",
)


def build_tradeability_structure_quality_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    tradeability_mask_root: str | Path = DEFAULT_TRADEABILITY_MASK_ROOT,
    candidate_plan_json: str | Path = DEFAULT_CANDIDATE_PLAN,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
) -> dict[str, Any]:
    candidate_plan = _load_candidate_plan(candidate_plan_json)
    specs = _candidate_specs(candidate_plan)
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    masks = load_tradeability_masks(
        tradeability_mask_root,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = compute_tradeability_structure_quality_factors(
        bars,
        masks,
        candidate_specs=specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_capacity_safe_price_volume_prescreen(
        factor_frame,
        labels,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
    )
    result["stage"] = STAGE
    result["candidate_plan_json"] = str(Path(candidate_plan_json))
    result["family_rotation_policy"] = candidate_plan.get("family_rotation_policy", {})
    result["data_window"] = _data_window(bars, factor_frame, labels)
    result["tradeability_mask_policy"] = _tradeability_mask_policy(masks, tradeability_mask_root)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_tradeability_residual_walk_forward_cost_capacity_clearance_only",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "adv20_amount_filter_enabled": True,
        "portfolio_backtest_allowed_before_prescreen_lead": False,
    }
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": NEXT_REQUIRED_GATE,
        "reason": (
            "This is an IC, quantile, turnover, and multiple-testing prescreen for pre-registered "
            "tradeability-structure candidates. Tradeability status can explain false alpha, so it cannot "
            "be promoted without survivorship, residual, walk-forward, cost, capacity, and regime gates."
        ),
    }
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_tradeability_structure_quality_prescreen_markdown(result)
    return result


def compute_tradeability_structure_quality_factors(
    bars: pd.DataFrame,
    tradeability_masks: pd.DataFrame,
    *,
    candidate_specs: Sequence[dict[str, Any]] | None = None,
    min_signal_date_amount: float = 10_000_000,
) -> pd.DataFrame:
    specs = list(candidate_specs or _candidate_specs(_load_candidate_plan(DEFAULT_CANDIDATE_PLAN)))
    features = _feature_frame(bars, tradeability_masks)
    if features.empty:
        return _empty_factor_frame()
    features = _add_cross_sectional_features(features)
    candidate_values = {
        "tradeability_persistence_quality_20": (
            0.60 * features["z_fully_tradeable_rate_20"]
            + 0.25 * features["z_log_adv20"]
            - 0.15 * features["z_official_blocked_rate_20"]
        ),
        "entry_exit_friction_avoidance_20": (
            -0.45 * features["z_entry_blocked_rate_20"]
            - 0.35 * features["z_exit_blocked_rate_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "limit_lock_pressure_avoidance_20": (
            -0.55 * features["z_limit_lock_rate_20"]
            - 0.25 * features["z_suspension_rate_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "metadata_survivorship_quality_120": (
            -0.55 * features["z_metadata_blocked_rate_120"]
            + 0.25 * features["z_fully_tradeable_rate_20"]
            + 0.20 * features["z_log_adv20"]
        ),
    }
    allowed_names = {_factor_name(spec) for spec in specs}
    rows: list[pd.DataFrame] = []
    base_columns = [
        "date",
        "asset_id",
        "market",
        "amount",
        "adv20_amount",
        "entry_blocked_rate_20",
        "official_blocked_rate_20",
        "metadata_blocked_rate_120",
        "limit_lock_rate_20",
    ]
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )
    for factor_name, values in candidate_values.items():
        if factor_name not in allowed_names:
            continue
        frame = features.loc[capacity_mask, base_columns].copy()
        frame["factor_name"] = factor_name
        frame["factor_value"] = values.loc[capacity_mask]
        frame = frame.dropna(subset=["factor_value", "amount", "adv20_amount"])
        rows.append(frame)
    if not rows:
        return _empty_factor_frame()
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def load_tradeability_masks(
    root: str | Path,
    *,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
) -> pd.DataFrame:
    root_path = Path(root)
    masks_root = root_path / "processed" / "tradeability_masks"
    if not masks_root.exists():
        masks_root = root_path
    files = sorted(masks_root.rglob("*.parquet")) + sorted(masks_root.rglob("*.csv"))
    frames = [_read_mask_file(path) for path in files if "market=CN" in str(path) or "tradeability_masks" in str(path)]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        raise FileNotFoundError(f"No CN tradeability mask files found under: {root_path}")
    masks = _normalise_masks(pd.concat(frames, ignore_index=True))
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    if include_final_holdout:
        end = max(end, masks["date"].max())
    masks = masks[(masks["date"] >= start) & (masks["date"] <= end)]
    return (
        masks.drop_duplicates(["asset_id", "market", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def write_tradeability_structure_quality_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "tradeability_structure_quality_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "tradeability_structure_quality_prescreen.md").write_text(
        render_tradeability_structure_quality_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "tradeability_structure_quality_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "tradeability_structure_quality_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )


def render_tradeability_structure_quality_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    mask_policy = result.get("tradeability_mask_policy", {})
    lines = [
        "# Tradeability Structure Quality Prescreen",
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
        f"- Mask rows: {mask_policy.get('mask_rows', 0)}",
        f"- Mask years: {mask_policy.get('mask_years', [])}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
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
                ic=row["mean_spearman_ic"],
                icir=row["icir"],
                t=row["ic_t_stat"],
                pos=row["ic_positive_rate"],
                spread=row["quantile_spread"],
                mono=row["quantile_monotonicity"],
                turnover=row["avg_top_quantile_turnover"],
                fdr="yes" if row["fdr_significant"] else "no",
                lead="yes" if row["research_lead"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This stage can create research leads only; it cannot promote a factor to paper-ready or live use.",
            "- Tradeability-derived candidates must be audited as survivorship and execution-risk explainers before portfolio conversion.",
            "- Any lead must next pass industry/style residualization, walk-forward, cost/capacity, regime, and final holdout gates.",
        ]
    )
    return "\n".join(lines) + "\n"


def _feature_frame(bars: pd.DataFrame, masks: pd.DataFrame) -> pd.DataFrame:
    bars_frame = bars.copy()
    required_bars = ["date", "asset_id", "market", "adj_close", "amount"]
    missing_bars = [column for column in required_bars if column not in bars_frame.columns]
    if missing_bars:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing_bars)}")
    bars_frame["date"] = pd.to_datetime(bars_frame["date"])
    bars_frame["asset_id"] = bars_frame["asset_id"].astype(str)
    bars_frame["market"] = bars_frame["market"].fillna("CN").astype(str)
    for column in ["adj_close", "amount"]:
        bars_frame[column] = pd.to_numeric(bars_frame[column], errors="coerce")
    mask_frame = _normalise_masks(masks)
    merged = bars_frame.merge(mask_frame, on=["date", "asset_id", "market"], how="inner", validate="one_to_one")
    if merged.empty:
        return pd.DataFrame()
    pieces: list[pd.DataFrame] = []
    for _, group in merged.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        group = group.copy().reset_index(drop=True)
        amount = group["amount"]
        close = group["adj_close"]
        entry_blocked = 1.0 - group["entry_tradeable"].astype(float)
        exit_blocked = 1.0 - group["exit_tradeable"].astype(float)
        official_blocked = group[["suspended_official", "limit_up_official", "limit_down_official", "st_flag_official"]].any(axis=1).astype(float)
        metadata_blocked = group[["new_listing_flag", "delisted_or_inactive_flag", "board_permission_blocked"]].any(axis=1).astype(float)
        limit_lock = group[["limit_up_official", "limit_down_official"]].any(axis=1).astype(float)
        frame = group[["date", "asset_id", "market", "amount"]].copy()
        frame["return_1d"] = close.pct_change()
        frame["adv20_amount"] = amount.rolling(20, min_periods=5).mean()
        frame["fully_tradeable_rate_20"] = group["fully_tradeable"].astype(float).rolling(20, min_periods=5).mean()
        frame["entry_blocked_rate_20"] = entry_blocked.rolling(20, min_periods=5).mean()
        frame["exit_blocked_rate_20"] = exit_blocked.rolling(20, min_periods=5).mean()
        frame["official_blocked_rate_20"] = official_blocked.rolling(20, min_periods=5).mean()
        frame["metadata_blocked_rate_120"] = metadata_blocked.rolling(120, min_periods=5).mean()
        frame["limit_lock_rate_20"] = limit_lock.rolling(20, min_periods=5).mean()
        frame["suspension_rate_20"] = group["suspended_official"].astype(float).rolling(20, min_periods=5).mean()
        pieces.append(frame)
    if not pieces:
        return pd.DataFrame()
    features = pd.concat(pieces, ignore_index=True)
    features["log_adv20"] = features["adv20_amount"].where(features["adv20_amount"] > 0).apply(math.log)
    return features.replace([float("inf"), float("-inf")], pd.NA)


def _add_cross_sectional_features(features: pd.DataFrame) -> pd.DataFrame:
    frame = features.copy()
    z_inputs = {
        "z_fully_tradeable_rate_20": frame["fully_tradeable_rate_20"],
        "z_entry_blocked_rate_20": frame["entry_blocked_rate_20"],
        "z_exit_blocked_rate_20": frame["exit_blocked_rate_20"],
        "z_official_blocked_rate_20": frame["official_blocked_rate_20"],
        "z_metadata_blocked_rate_120": frame["metadata_blocked_rate_120"],
        "z_limit_lock_rate_20": frame["limit_lock_rate_20"],
        "z_suspension_rate_20": frame["suspension_rate_20"],
        "z_log_adv20": frame["log_adv20"],
    }
    for column, series in z_inputs.items():
        frame[column] = _cs_zscore(frame, series)
    return frame


def _normalise_masks(masks: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", *BOOL_MASK_COLUMNS]
    missing = [column for column in required if column not in masks.columns]
    if missing:
        raise ValueError(f"Tradeability masks are missing required columns: {', '.join(missing)}")
    frame = masks[list(required)].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str)
    for column in BOOL_MASK_COLUMNS:
        frame[column] = _bool_series(frame[column])
    return frame.dropna(subset=["date", "asset_id", "market"])


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    text = series.astype(str).str.strip().str.lower()
    return text.isin({"true", "1", "yes", "y", "t"})


def _read_mask_file(path: Path) -> pd.DataFrame:
    columns = ["date", "asset_id", "market", *BOOL_MASK_COLUMNS]
    if path.suffix == ".parquet":
        try:
            return pd.read_parquet(path, columns=columns)
        except Exception:
            frame = pd.read_parquet(path)
            return frame[[column for column in columns if column in frame.columns]]
    frame = pd.read_csv(path)
    return frame[[column for column in columns if column in frame.columns]]


def _tradeability_mask_policy(masks: pd.DataFrame, root: str | Path) -> dict[str, Any]:
    years = sorted({int(pd.Timestamp(value).year) for value in masks["date"]}) if not masks.empty else []
    official_columns = ["suspended_official", "limit_up_official", "limit_down_official", "st_flag_official"]
    metadata_columns = ["new_listing_flag", "delisted_or_inactive_flag", "board_permission_blocked"]
    return {
        "mask_cache_required": True,
        "mask_root": str(Path(root)),
        "mask_rows": int(len(masks)),
        "mask_assets": int(masks["asset_id"].nunique()) if not masks.empty else 0,
        "mask_years": years,
        "official_blocked_rows": int(masks[official_columns].any(axis=1).sum()) if not masks.empty else 0,
        "metadata_blocked_rows": int(masks[metadata_columns].any(axis=1).sum()) if not masks.empty else 0,
        "future_mask_use_allowed": False,
    }


def _load_candidate_plan(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _candidate_specs(candidate_plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(candidate) for candidate in candidate_plan.get("candidates", []) if isinstance(candidate, dict)]


def _factor_name(spec: dict[str, Any]) -> str:
    return str(spec.get("factor_name", "")).strip()


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
            "entry_blocked_rate_20",
            "official_blocked_rate_20",
            "metadata_blocked_rate_120",
            "limit_lock_rate_20",
        ]
    )
