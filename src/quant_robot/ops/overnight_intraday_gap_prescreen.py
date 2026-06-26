from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence
import warnings

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_preregistration import DEFAULT_CAPACITY_FILTERS, SAFETY
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    RESULT_COLUMNS,
    summarize_capacity_safe_price_volume_prescreen,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "overnight_intraday_gap_prescreen"
NEXT_DEDUP_DIRECTION = "round110_overnight_intraday_gap_lead_dedup"
NEXT_ROTATE_DIRECTION = "round110_family_rotation_after_overnight_intraday_gap_failure"
PUBLIC_REFERENCE_PROJECTS = ("alphalens", "qlib", "overnight_intraday_return_decomposition")


@dataclass(frozen=True)
class OvernightIntradayGapCandidateSpec:
    factor_name: str
    family: str
    formula_template: str
    direction: str
    windows: tuple[int, ...]
    required_fields: tuple[str, ...]
    economic_rationale: str
    public_reference_tags: tuple[str, ...]
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_overnight_intraday_gap_candidate_specs() -> list[OvernightIntradayGapCandidateSpec]:
    family = "overnight_intraday_gap"
    refs = ("alphalens", "qlib", "overnight_intraday_return_decomposition")
    return [
        OvernightIntradayGapCandidateSpec(
            "overnight_reversal_5",
            family,
            "-rolling_mean(overnight_return, 5)",
            "higher_is_better",
            (5,),
            ("open", "adj_close", "amount"),
            "Tests whether recent weak overnight gaps overreact and revert over the next holding window.",
            refs,
        ),
        OvernightIntradayGapCandidateSpec(
            "overnight_reversal_20",
            family,
            "-rolling_mean(overnight_return, 20)",
            "higher_is_better",
            (20,),
            ("open", "adj_close", "amount"),
            "Longer overnight overreaction hypothesis with fewer degrees of freedom than a parameter grid.",
            refs,
        ),
        OvernightIntradayGapCandidateSpec(
            "intraday_momentum_5",
            family,
            "rolling_mean(intraday_return, 5)",
            "higher_is_better",
            (5,),
            ("open", "adj_close", "amount"),
            "Tests whether repeated open-to-close strength carries short-horizon information.",
            refs,
        ),
        OvernightIntradayGapCandidateSpec(
            "intraday_momentum_20",
            family,
            "rolling_mean(intraday_return, 20)",
            "higher_is_better",
            (20,),
            ("open", "adj_close", "amount"),
            "Longer intraday strength persistence hypothesis.",
            refs,
        ),
        OvernightIntradayGapCandidateSpec(
            "gap_down_intraday_recovery_10",
            family,
            "rolling_mean(-min(overnight_return,0)+max(intraday_return,0), 10)",
            "higher_is_better",
            (10,),
            ("open", "adj_close", "amount"),
            "Looks for stocks that gap down but recover during the trading day, a simple overreaction repair pattern.",
            refs,
        ),
        OvernightIntradayGapCandidateSpec(
            "gap_up_intraday_fade_10",
            family,
            "rolling_mean(max(overnight_return,0)-min(intraday_return,0), 10)",
            "higher_is_better",
            (10,),
            ("open", "adj_close", "amount"),
            "Tests whether gap-up names that are sold intraday carry contrarian or exhaustion information.",
            refs,
        ),
        OvernightIntradayGapCandidateSpec(
            "gap_fill_efficiency_20",
            family,
            "-rolling_mean(overnight_return*intraday_return, 20)",
            "higher_is_better",
            (20,),
            ("open", "adj_close", "amount"),
            "Rewards opposite-signed overnight and intraday components, i.e. gap filling rather than gap extension.",
            refs,
        ),
        OvernightIntradayGapCandidateSpec(
            "overnight_intraday_disagreement_20",
            family,
            "-rolling_corr(overnight_return, intraday_return, 20)",
            "higher_is_better",
            (20,),
            ("open", "adj_close", "amount"),
            "Captures persistent disagreement between overnight and regular-session pricing.",
            refs,
        ),
        OvernightIntradayGapCandidateSpec(
            "gap_extreme_avoidance_20",
            family,
            "-rolling_mean(abs(overnight_return), 20)",
            "higher_is_better",
            (20,),
            ("open", "adj_close", "amount"),
            "Avoids names dominated by repeated overnight event gaps that are hard to execute and risk-control.",
            refs,
        ),
        OvernightIntradayGapCandidateSpec(
            "gap_reversal_lowvol_liquid_20",
            family,
            "0.50*cs_z(overnight_reversal_20)+0.25*cs_z(-realized_vol_20)+0.25*cs_z(log_adv20)",
            "higher_is_better",
            (20,),
            ("open", "adj_close", "amount"),
            "Combines overnight overreaction with low volatility and liquidity so this family does not become a tail-only effect.",
            refs,
        ),
    ]


def build_overnight_intraday_gap_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    candidate_specs: Sequence[OvernightIntradayGapCandidateSpec] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> dict[str, Any]:
    specs = list(candidate_specs or default_overnight_intraday_gap_candidate_specs())
    bars = load_overnight_intraday_gap_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = compute_overnight_intraday_gap_factors(
        bars,
        candidate_specs=specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_overnight_intraday_gap_prescreen(
        factor_frame,
        labels,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
    )
    result["data_window"] = _data_window(bars, factor_frame, labels)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "adv20_amount_filter_enabled": True,
        "portfolio_backtest_allowed_before_prescreen_lead": False,
    }
    result["candidate_specs"] = [_spec_payload(spec) for spec in specs]
    result["markdown"] = render_overnight_intraday_gap_prescreen_markdown(result)
    return result


def load_overnight_intraday_gap_bars(
    bars_roots: Iterable[str | Path],
    *,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
) -> pd.DataFrame:
    files: list[Path] = []
    for root in bars_roots:
        root_path = Path(root)
        if (root_path / "processed" / "bars").exists():
            bars_root = root_path / "processed" / "bars"
        elif (root_path / "bars").exists():
            bars_root = root_path / "bars"
        else:
            bars_root = root_path
        files.extend(sorted(bars_root.rglob("*.parquet")))
        files.extend(sorted(bars_root.rglob("*.csv")))
    frames = [_read_bars_file(file) for file in files]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        raise FileNotFoundError(f"No CN bars files found under: {', '.join(str(root) for root in bars_roots)}")
    bars = pd.concat(frames, ignore_index=True)
    bars = _normalise_bars(bars)
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    if include_final_holdout:
        end = max(end, bars["date"].max())
    bars = bars[(bars["date"] >= start) & (bars["date"] <= end)]
    return (
        bars.drop_duplicates(["asset_id", "market", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def compute_overnight_intraday_gap_factors(
    bars: pd.DataFrame,
    *,
    candidate_specs: Sequence[OvernightIntradayGapCandidateSpec] | None = None,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> pd.DataFrame:
    specs = list(candidate_specs or default_overnight_intraday_gap_candidate_specs())
    features = _feature_frame(bars)
    if features.empty:
        return _empty_factor_frame()
    features = _add_cross_sectional_features(features)
    candidate_values = {
        "overnight_reversal_5": features["z_overnight_reversal_5"],
        "overnight_reversal_20": features["z_overnight_reversal_20"],
        "intraday_momentum_5": features["z_intraday_momentum_5"],
        "intraday_momentum_20": features["z_intraday_momentum_20"],
        "gap_down_intraday_recovery_10": features["z_gap_down_intraday_recovery_10"],
        "gap_up_intraday_fade_10": features["z_gap_up_intraday_fade_10"],
        "gap_fill_efficiency_20": features["z_gap_fill_efficiency_20"],
        "overnight_intraday_disagreement_20": features["z_overnight_intraday_disagreement_20"],
        "gap_extreme_avoidance_20": features["z_gap_extreme_avoidance_20"],
        "gap_reversal_lowvol_liquid_20": (
            0.50 * features["z_overnight_reversal_20"]
            + 0.25 * features["z_neg_realized_vol_20"]
            + 0.25 * features["z_log_adv20"]
        ),
    }
    allowed_names = {spec.factor_name for spec in specs}
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )
    rows: list[pd.DataFrame] = []
    base_columns = ["date", "asset_id", "market", "amount", "adv20_amount"]
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


def summarize_overnight_intraday_gap_prescreen(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    expected_candidate_count: int | None = None,
    candidate_specs: Sequence[OvernightIntradayGapCandidateSpec] | None = None,
    horizons: tuple[int, ...] | None = None,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
) -> dict[str, Any]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = summarize_capacity_safe_price_volume_prescreen(
            factor_frame,
            labels,
            expected_candidate_count=expected_candidate_count,
            candidate_specs=candidate_specs,
            horizons=horizons,
            min_cross_section=min_cross_section,
            min_ic_observations=min_ic_observations,
        )
    result["stage"] = STAGE
    result["public_reference_review"] = {
        "projects_reviewed": list(PUBLIC_REFERENCE_PROJECTS),
        "method": "Public OHLC decomposition hypothesis; Alphalens-style prescreen only, no portfolio grid.",
    }
    result["next_direction"] = (
        NEXT_DEDUP_DIRECTION if result["summary"].get("research_lead_count", 0) else NEXT_ROTATE_DIRECTION
    )
    result["promotion_policy"]["promotion_allowed"] = False
    result["promotion_policy"]["next_allowed_action"] = result["next_direction"]
    result["safety"] = SAFETY
    result["markdown"] = render_overnight_intraday_gap_prescreen_markdown(result)
    return result


def write_overnight_intraday_gap_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "overnight_intraday_gap_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "overnight_intraday_gap_prescreen.md").write_text(
        render_overnight_intraday_gap_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "overnight_intraday_gap_candidates.csv", _candidate_csv_rows(result), _candidate_columns())
    _write_csv(output_path / "overnight_intraday_gap_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "overnight_intraday_gap_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )


def render_overnight_intraday_gap_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Overnight-Intraday Gap Prescreen",
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
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Next direction: {result.get('next_direction', NEXT_ROTATE_DIRECTION)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Public Reference Review",
        "",
        "- Projects reviewed: "
        + ", ".join(result.get("public_reference_review", {}).get("projects_reviewed", []) or []),
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
            "- Any lead must next pass correlation de-duplication, long-cycle walk-forward, cost/capacity, and regime checks.",
        ]
    )
    return "\n".join(lines) + "\n"


def _read_bars_file(file: Path) -> pd.DataFrame:
    columns = ["date", "asset_id", "symbol", "market", "open", "high", "low", "close", "adj_close", "amount", "volume"]
    if file.suffix == ".parquet":
        try:
            return pd.read_parquet(file, columns=columns)
        except Exception:
            frame = pd.read_parquet(file)
            return frame[[column for column in columns if column in frame.columns]]
    frame = pd.read_csv(file)
    return frame[[column for column in columns if column in frame.columns]]


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "open", "high", "low", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["market"] = frame["market"].fillna("CN").astype(str)
    frame["asset_id"] = frame["asset_id"].astype(str)
    for column in ["open", "high", "low", "close", "adj_close", "amount", "volume"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=required)
    frame = frame[
        (frame["market"] == "CN")
        & (frame["open"] > 0)
        & (frame["high"] > 0)
        & (frame["low"] > 0)
        & (frame["adj_close"] > 0)
        & (frame["amount"] > 0)
    ]
    return frame


def _feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    bars = _normalise_bars(bars)
    pieces: list[pd.DataFrame] = []
    for _, group in bars.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        group = group.copy().reset_index(drop=True)
        close = group["adj_close"]
        open_ = group["open"]
        amount = group["amount"]
        prev_close = close.shift(1)
        overnight = open_ / prev_close - 1.0
        intraday = close / open_ - 1.0
        returns = close.pct_change()
        frame = group[["date", "asset_id", "market", "amount"]].copy()
        frame["return_1d"] = returns
        frame["overnight_return"] = overnight
        frame["intraday_return"] = intraday
        frame["adv20_amount"] = amount.rolling(20, min_periods=5).mean()
        frame["overnight_reversal_5"] = -overnight.rolling(5, min_periods=3).mean()
        frame["overnight_reversal_20"] = -overnight.rolling(20, min_periods=5).mean()
        frame["intraday_momentum_5"] = intraday.rolling(5, min_periods=3).mean()
        frame["intraday_momentum_20"] = intraday.rolling(20, min_periods=5).mean()
        frame["gap_down_intraday_recovery_10"] = (
            (-overnight.clip(upper=0.0)) + intraday.clip(lower=0.0)
        ).rolling(10, min_periods=4).mean()
        frame["gap_up_intraday_fade_10"] = (
            overnight.clip(lower=0.0) + (-intraday.clip(upper=0.0))
        ).rolling(10, min_periods=4).mean()
        frame["gap_fill_efficiency_20"] = -(overnight * intraday).rolling(20, min_periods=5).mean()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            frame["overnight_intraday_disagreement_20"] = -overnight.rolling(20, min_periods=8).corr(intraday)
        frame["gap_extreme_avoidance_20"] = -overnight.abs().rolling(20, min_periods=5).mean()
        frame["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        pieces.append(frame)
    if not pieces:
        return pd.DataFrame()
    features = pd.concat(pieces, ignore_index=True)
    features["log_adv20"] = features["adv20_amount"].where(features["adv20_amount"] > 0).apply(math.log)
    return features.replace([float("inf"), float("-inf")], pd.NA)


def _add_cross_sectional_features(features: pd.DataFrame) -> pd.DataFrame:
    frame = features.copy()
    z_inputs = {
        "z_overnight_reversal_5": frame["overnight_reversal_5"],
        "z_overnight_reversal_20": frame["overnight_reversal_20"],
        "z_intraday_momentum_5": frame["intraday_momentum_5"],
        "z_intraday_momentum_20": frame["intraday_momentum_20"],
        "z_gap_down_intraday_recovery_10": frame["gap_down_intraday_recovery_10"],
        "z_gap_up_intraday_fade_10": frame["gap_up_intraday_fade_10"],
        "z_gap_fill_efficiency_20": frame["gap_fill_efficiency_20"],
        "z_overnight_intraday_disagreement_20": frame["overnight_intraday_disagreement_20"],
        "z_gap_extreme_avoidance_20": frame["gap_extreme_avoidance_20"],
        "z_neg_realized_vol_20": -frame["realized_vol_20"],
        "z_log_adv20": frame["log_adv20"],
    }
    for column, series in z_inputs.items():
        frame[column] = _cs_zscore(frame, series)
    return frame


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby(frame["date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return (values - mean) / std.replace(0, pd.NA)


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "asset_id", "market", "factor_name", "factor_value", "amount", "adv20_amount"]
    )


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "factor_name": spec["factor_name"],
            "family": spec["family"],
            "direction": spec["direction"],
            "windows": ",".join(str(window) for window in spec.get("windows", []) or []),
            "required_fields": ",".join(spec.get("required_fields", []) or []),
            "public_reference_tags": ",".join(spec.get("public_reference_tags", []) or []),
            "portfolio_backtest_allowed": spec.get("portfolio_backtest_allowed", False),
            "promotion_allowed": spec.get("promotion_allowed", False),
        }
        for spec in result.get("candidate_specs", []) or []
    ]


def _candidate_columns() -> list[str]:
    return [
        "factor_name",
        "family",
        "direction",
        "windows",
        "required_fields",
        "public_reference_tags",
        "portfolio_backtest_allowed",
        "promotion_allowed",
    ]


def _spec_payload(spec: Any) -> dict[str, Any]:
    if hasattr(spec, "__dataclass_fields__"):
        payload = asdict(spec)
        payload["windows"] = list(payload["windows"])
        payload["required_fields"] = list(payload["required_fields"])
        payload["public_reference_tags"] = list(payload["public_reference_tags"])
        return payload
    return dict(spec)


def _data_window(bars: pd.DataFrame, factor_frame: pd.DataFrame, labels: pd.DataFrame) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "min_signal_date": _min_date(factor_frame, "date"),
        "max_signal_date": _max_date(factor_frame, "date"),
        "min_label_date": _min_date(labels, "date"),
        "max_label_date": _max_date(labels, "date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
    }


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
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
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
