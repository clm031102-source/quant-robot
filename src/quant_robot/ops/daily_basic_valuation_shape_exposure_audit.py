from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import load_capacity_safe_bars
from quant_robot.ops.daily_basic_non_price_public_carry_preregistration import (
    DailyBasicNonPricePublicCarryCandidateSpec,
)
from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (
    compute_daily_basic_non_price_public_carry_factors,
    load_daily_basic_non_price_public_carry_inputs,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "daily_basic_valuation_shape_exposure_audit"
FACTOR_NAME = "daily_basic_valuation_reversion_dvratio_quality_60"
REQUIRED_STYLE_NAMES = ("size", "value", "lowvol", "momentum", "liquidity")
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def round211_valuation_repair_spec() -> DailyBasicNonPricePublicCarryCandidateSpec:
    return DailyBasicNonPricePublicCarryCandidateSpec(
        factor_name=FACTOR_NAME,
        family="valuation_stability_coverage_repair",
        formula_template="0.45*cs_z(-pb_z_60)+0.30*cs_z(-ps_ttm_z_60)+0.25*cs_z(dv_ratio)",
        direction="higher_is_better",
        windows=(60,),
        required_fields=("pb", "ps_ttm", "dv_ratio"),
        economic_rationale="Coverage-repaired valuation reversion signal from Round211.",
        public_reference_tags=("value_reversion", "fama_french_value", "coverage_repair"),
        expected_failure_modes=("field_substitution_changes_economics", "weak_quantile_shape"),
    )


def build_style_factors_from_bars_daily_basic(bars: pd.DataFrame, daily_basic: pd.DataFrame) -> pd.DataFrame:
    merged = _build_style_wide_from_bars_daily_basic(bars, daily_basic)
    rows = []
    for style_name in REQUIRED_STYLE_NAMES:
        style_rows = merged[["date", "asset_id", "market", style_name]].copy()
        style_rows = style_rows.rename(columns={style_name: "style_value"})
        style_rows["style_name"] = style_name
        rows.append(style_rows)
    output = pd.concat(rows, ignore_index=True)
    return output.dropna(subset=["style_value"]).reset_index(drop=True)


def _build_style_wide_from_bars_daily_basic(bars: pd.DataFrame, daily_basic: pd.DataFrame) -> pd.DataFrame:
    bar_frame = bars.copy()
    daily_frame = daily_basic.copy()
    for frame in (bar_frame, daily_frame):
        frame["date"] = pd.to_datetime(frame["date"])
        frame["asset_id"] = frame["asset_id"].astype(str)
        frame["market"] = frame["market"].astype(str).str.upper()
    bar_frame = bar_frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    bar_frame["adj_close"] = pd.to_numeric(bar_frame["adj_close"], errors="coerce")
    bar_frame["amount"] = pd.to_numeric(bar_frame.get("amount", pd.Series(index=bar_frame.index)), errors="coerce")
    grouped = bar_frame.groupby("asset_id", sort=False)
    bar_frame["ret1"] = grouped["adj_close"].pct_change()
    bar_frame["momentum"] = grouped["adj_close"].pct_change(20)
    bar_frame["lowvol"] = -grouped["ret1"].transform(lambda item: item.rolling(20, min_periods=10).std(ddof=0))
    bar_frame["adv20_amount"] = grouped["amount"].transform(lambda item: item.rolling(20, min_periods=5).mean())
    bar_frame["liquidity"] = _positive_log(bar_frame["adv20_amount"])

    numeric_columns = ["pb", "ps_ttm", "dv_ratio", "circ_mv"]
    for column in numeric_columns:
        daily_frame[column] = pd.to_numeric(daily_frame.get(column, pd.Series(index=daily_frame.index)), errors="coerce")
    daily_frame["size"] = _positive_log(daily_frame["circ_mv"])
    daily_frame["value"] = (
        _cs_zscore(daily_frame, -daily_frame["pb"])
        + _cs_zscore(daily_frame, -daily_frame["ps_ttm"])
        + _cs_zscore(daily_frame, daily_frame["dv_ratio"])
    )
    merged = daily_frame[["date", "asset_id", "market", "size", "value"]].merge(
        bar_frame[["date", "asset_id", "market", "lowvol", "momentum", "liquidity"]],
        on=["date", "asset_id", "market"],
        how="left",
    )
    return merged.dropna(subset=["size", "value"], how="all").reset_index(drop=True)


def summarize_quantile_shape(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    min_cross_section: int = 100,
    min_dates: int = 80,
) -> dict[str, Any]:
    factor_frame = _prepare_factors(factors)
    label_frame = _prepare_labels(labels)
    merged = factor_frame.merge(label_frame, on=["date", "asset_id", "market"], how="inner")
    date_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    group_keys = ["factor_name", "horizon", "execution_lag"]
    for (factor_name, horizon, execution_lag), group in merged.groupby(group_keys, sort=True):
        quantile_rows = []
        for signal_date, date_group in group.groupby("date", sort=True):
            valid = date_group.dropna(subset=["factor_value", "forward_return"])
            if len(valid) < min_cross_section:
                continue
            quantiles = _quantile_labels(valid["factor_value"])
            if quantiles is None:
                continue
            row = {
                "date": pd.Timestamp(signal_date).date().isoformat(),
                "factor_name": str(factor_name),
                "horizon": int(horizon),
                "execution_lag": int(execution_lag),
                "cross_section": int(len(valid)),
            }
            means = []
            for quantile in range(5):
                mean_return = float(valid.loc[quantiles == quantile, "forward_return"].mean())
                row[f"q{quantile + 1}"] = mean_return
                means.append(mean_return)
            date_rows.append(row)
            quantile_rows.append(row)
        if len(quantile_rows) < min_dates:
            summary_rows.append(_empty_shape_summary(str(factor_name), int(horizon), int(execution_lag), len(quantile_rows)))
            continue
        quantile_frame = pd.DataFrame(quantile_rows)
        mean_returns = [float(quantile_frame[f"q{idx}"].mean()) for idx in range(1, 6)]
        monotonicity = _spearman(pd.Series(range(1, 6)), pd.Series(mean_returns))
        best_index = int(pd.Series(mean_returns).idxmax())
        q5_minus_q1 = mean_returns[4] - mean_returns[0]
        q1_is_worst = bool(mean_returns[0] == min(mean_returns))
        q5_is_best = bool(best_index == 4)
        blockers = []
        if len(quantile_rows) < min_dates:
            blockers.append("insufficient_shape_dates")
        if q5_minus_q1 <= 0.0:
            blockers.append("top_minus_bottom_quantile_not_positive")
        if not q5_is_best:
            blockers.append("top_quantile_not_best_bucket")
        if not q1_is_worst:
            blockers.append("bottom_quantile_not_worst_bucket")
        if not math.isfinite(monotonicity) or monotonicity < 0.70:
            blockers.append("quantile_monotonicity_weak")
        summary_rows.append(
            {
                "factor_name": str(factor_name),
                "horizon": int(horizon),
                "execution_lag": int(execution_lag),
                "shape_dates": int(len(quantile_rows)),
                "q1": mean_returns[0],
                "q2": mean_returns[1],
                "q3": mean_returns[2],
                "q4": mean_returns[3],
                "q5": mean_returns[4],
                "q5_minus_q1": q5_minus_q1,
                "quantile_monotonicity": float(monotonicity) if math.isfinite(monotonicity) else 0.0,
                "best_quantile": f"q{best_index + 1}",
                "q5_is_best": q5_is_best,
                "q1_is_worst": q1_is_worst,
                "shape_pass": not blockers,
                "shape_blockers": blockers,
            }
        )
    return {
        "summary": {
            "factor_horizon_count": int(len(summary_rows)),
            "shape_pass_count": int(sum(1 for row in summary_rows if row.get("shape_pass"))),
            "shape_blocker_count": int(sum(1 for row in summary_rows if not row.get("shape_pass"))),
        },
        "quantile_summary": summary_rows,
        "quantile_date_rows": date_rows,
    }


def build_valuation_shape_exposure_audit(
    *,
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    stock_basic: pd.DataFrame,
    style_factors: pd.DataFrame,
    source_report: str | None = None,
    min_dates: int = 80,
    min_cross_section: int = 100,
    min_residual_mean_ic: float = 0.02,
    min_residual_ic_t_stat: float = 2.0,
    min_residual_positive_rate: float = 0.55,
) -> dict[str, Any]:
    shape = summarize_quantile_shape(
        factors,
        labels,
        min_cross_section=min_cross_section,
        min_dates=min_dates,
    )
    exposure = summarize_lightweight_exposure_audit(
        factors=factors,
        labels=labels,
        stock_basic=stock_basic,
        style_factors=style_factors,
        min_dates=min_dates,
        min_cross_section=min_cross_section,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_ic_t_stat=min_residual_ic_t_stat,
        min_residual_positive_rate=min_residual_positive_rate,
    )
    blockers = []
    if shape["summary"]["shape_pass_count"] == 0:
        blockers.append("no_quantile_shape_pass")
    if not exposure["summary"]["passes"]:
        blockers.extend(str(item) for item in exposure["summary"].get("blockers", []))
    blockers = _dedupe(blockers)
    return {
        "stage": STAGE,
        "source_report": source_report,
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "shape_pass_count": shape["summary"]["shape_pass_count"],
            "residual_candidate_factors": exposure["summary"].get("residual_candidate_factors", 0),
            "exposure_passes": exposure["summary"].get("passes", False),
        },
        "shape_audit": shape,
        "exposure_audit": exposure,
        "promotion_policy": {
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "reason": "Shape/exposure audit is diagnostic; portfolio grids require separate approval after passing gates.",
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }


def build_valuation_shape_exposure_audit_from_roots(
    *,
    bars_roots: Iterable[str | Path],
    daily_basic_roots: Iterable[str | Path],
    stock_basic: pd.DataFrame,
    analysis_start_date: str,
    analysis_end_date: str,
    horizons: tuple[int, ...] = (20,),
    execution_lag: int = 1,
    min_dates: int = 80,
    min_cross_section: int = 100,
) -> dict[str, Any]:
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=False,
    )
    daily_basic = load_daily_basic_non_price_public_carry_inputs(
        daily_basic_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=False,
    )
    factors = compute_daily_basic_non_price_public_carry_factors(daily_basic, candidate_specs=[round211_valuation_repair_spec()])
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    style_factors = _build_style_wide_from_bars_daily_basic(bars, daily_basic)
    result = build_valuation_shape_exposure_audit(
        factors=factors,
        labels=labels,
        stock_basic=stock_basic,
        style_factors=style_factors,
        source_report="docs/research/cn_stock_round211_daily_basic_valuation_reversion_coverage_repair_prescreen_2026-06-24.md",
        min_dates=min_dates,
        min_cross_section=min_cross_section,
    )
    result["data_window"] = {
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "bar_rows": int(len(bars)),
        "daily_basic_rows": int(len(daily_basic)),
        "factor_rows": int(len(factors)),
        "label_rows": int(len(labels)),
        "style_factor_rows": int(len(style_factors)),
        "stock_basic_rows": int(len(stock_basic)),
        "horizons": list(horizons),
        "execution_lag": int(execution_lag),
    }
    return result


def summarize_lightweight_exposure_audit(
    *,
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    stock_basic: pd.DataFrame,
    style_factors: pd.DataFrame,
    min_dates: int = 80,
    min_cross_section: int = 100,
    min_residual_mean_ic: float = 0.02,
    min_residual_ic_t_stat: float = 2.0,
    min_residual_positive_rate: float = 0.55,
) -> dict[str, Any]:
    factor_frame = _prepare_factors(factors)
    label_frame = _prepare_labels(labels)
    stock_frame = _prepare_stock_basic(stock_basic)
    style_frame = _prepare_style_wide(style_factors)
    merged = factor_frame.merge(label_frame, on=["date", "asset_id", "market"], how="inner")
    merged = merged.merge(stock_frame, on="asset_id", how="left")
    merged = merged.merge(style_frame, on=["date", "asset_id", "market"], how="left")
    date_rows: list[dict[str, Any]] = []
    style_rows: list[dict[str, Any]] = []
    for key, group in merged.groupby(["date", "market", "factor_name", "horizon", "execution_lag"], sort=True):
        date_value, market, factor_name, horizon, execution_lag = key
        valid = group.dropna(subset=["factor_value", "forward_return"]).copy()
        if len(valid) < min_cross_section:
            continue
        industry_present = valid["industry"].notna() & (valid["industry"].astype(str).str.strip() != "")
        style_present = valid[list(REQUIRED_STYLE_NAMES)].notna().all(axis=1)
        complete = valid[industry_present & style_present].copy()
        raw_ic = _spearman(valid["factor_value"], valid["forward_return"])
        residual = _lightweight_residual(complete)
        residual_ic = (
            _spearman(residual, complete.loc[residual.index, "forward_return"])
            if not residual.empty
            else float("nan")
        )
        date_rows.append(
            {
                "date": pd.Timestamp(date_value).date().isoformat(),
                "market": str(market),
                "factor_name": str(factor_name),
                "horizon": int(horizon),
                "execution_lag": int(execution_lag),
                "observations": int(len(valid)),
                "style_complete_observations": int(style_present.sum()),
                "industry_observations": int(industry_present.sum()),
                "residual_observations": int(len(residual)),
                "industries": int(valid.loc[industry_present, "industry"].nunique()),
                "missing_industry_rows": int((~industry_present).sum()),
                "style_coverage_ratio": _safe_ratio(int(style_present.sum()), int(len(valid))),
                "missing_industry_fraction": _safe_ratio(int((~industry_present).sum()), int(len(valid))),
                "raw_rank_ic": raw_ic,
                "residual_rank_ic": residual_ic,
                "industry_r2": _industry_r2_fast(valid.loc[industry_present, "factor_value"], valid.loc[industry_present, "industry"]),
            }
        )
        for style_name in REQUIRED_STYLE_NAMES:
            style_valid = valid.dropna(subset=["factor_value", style_name])
            style_rows.append(
                {
                    "date": pd.Timestamp(date_value).date().isoformat(),
                    "market": str(market),
                    "factor_name": str(factor_name),
                    "horizon": int(horizon),
                    "execution_lag": int(execution_lag),
                    "style_name": style_name,
                    "observations": int(len(style_valid)),
                    "coverage_ratio": _safe_ratio(int(len(style_valid)), int(len(valid))),
                    "spearman_correlation": _spearman(style_valid["factor_value"], style_valid[style_name]),
                }
            )
    factor_summary = _lightweight_factor_summary(
        date_rows,
        style_rows,
        min_dates=min_dates,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_ic_t_stat=min_residual_ic_t_stat,
        min_residual_positive_rate=min_residual_positive_rate,
    )
    blockers = []
    if not any(row.get("classification") == "residual_candidate" for row in factor_summary):
        blockers.append("no_residual_candidate_after_lightweight_exposure_audit")
    if any(float(row.get("style_coverage_ratio", 0.0)) < 0.90 for row in factor_summary):
        blockers.append("style_coverage_below_threshold")
    if any(float(row.get("missing_industry_fraction", 1.0)) > 0.02 for row in factor_summary):
        blockers.append("industry_coverage_below_threshold")
    return {
        "stage": "lightweight_industry_style_exposure_audit",
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "input_rows": int(len(merged)),
            "factors": int(len(factor_summary)),
            "residual_candidate_factors": int(sum(1 for row in factor_summary if row.get("classification") == "residual_candidate")),
            "style_or_industry_exposure_dominated_factors": int(
                sum(1 for row in factor_summary if row.get("classification") == "style_or_industry_exposure_dominated")
            ),
            "weak_or_unproven_after_residualization_factors": int(
                sum(1 for row in factor_summary if row.get("classification") == "weak_or_unproven_after_residualization")
            ),
            "residual_factor_rows": 0,
            "missing_required_style_names": [],
        },
        "factor_summary": factor_summary,
        "style_exposure_rows": style_rows,
        "industry_date_rows": date_rows,
        "residual_factor_rows": [],
    }


def write_valuation_shape_exposure_audit(output_dir: str | Path, result: Mapping[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "daily_basic_valuation_shape_exposure_audit.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "daily_basic_valuation_shape_exposure_audit.md").write_text(_markdown(result), encoding="utf-8")
    pd.DataFrame(result.get("shape_audit", {}).get("quantile_summary", [])).to_csv(
        output_path / "quantile_shape_summary.csv",
        index=False,
    )
    pd.DataFrame(result.get("shape_audit", {}).get("quantile_date_rows", [])).to_csv(
        output_path / "quantile_shape_date_rows.csv",
        index=False,
    )
    exposure = result.get("exposure_audit", {})
    pd.DataFrame(exposure.get("factor_summary", [])).to_csv(output_path / "factor_summary.csv", index=False)
    pd.DataFrame(exposure.get("style_exposure_rows", [])).to_csv(output_path / "style_exposure_rows.csv", index=False)
    pd.DataFrame(exposure.get("industry_date_rows", [])).to_csv(output_path / "industry_date_rows.csv", index=False)
    pd.DataFrame(exposure.get("residual_factor_rows", [])).to_csv(output_path / "residual_factor_rows.csv", index=False)


def _markdown(result: Mapping[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Daily-Basic Valuation Shape/Exposure Audit",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Shape pass count: {summary.get('shape_pass_count', 0)}",
        f"- Residual candidate factors: {summary.get('residual_candidate_factors', 0)}",
        f"- Exposure passes: {summary.get('exposure_passes', False)}",
        f"- Blockers: {', '.join(summary.get('blockers', [])) or 'none'}",
        f"- Portfolio grid allowed: {result.get('promotion_policy', {}).get('portfolio_grid_allowed', False)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        "",
        "## Quantile Shape",
        "",
    ]
    for row in result.get("shape_audit", {}).get("quantile_summary", []):
        lines.append(
            "- {factor} h{horizon}: q1={q1:.4f}, q2={q2:.4f}, q3={q3:.4f}, q4={q4:.4f}, q5={q5:.4f}, "
            "q5-q1={spread:.4f}, mono={mono:.3f}, best={best}, pass={passed}, blockers={blockers}".format(
                factor=row.get("factor_name"),
                horizon=row.get("horizon"),
                q1=float(row.get("q1", 0.0)),
                q2=float(row.get("q2", 0.0)),
                q3=float(row.get("q3", 0.0)),
                q4=float(row.get("q4", 0.0)),
                q5=float(row.get("q5", 0.0)),
                spread=float(row.get("q5_minus_q1", 0.0)),
                mono=float(row.get("quantile_monotonicity", 0.0)),
                best=row.get("best_quantile"),
                passed=row.get("shape_pass"),
                blockers="|".join(row.get("shape_blockers", [])),
            )
        )
    lines.extend(["", "## Exposure Summary", ""])
    for row in result.get("exposure_audit", {}).get("factor_summary", []):
        lines.append(
            "- {factor} h{horizon}: class={classification}, rawIC={raw:.4f}, residualIC={resid:.4f}, "
            "residual_t={t:.2f}, retention={ret:.3f}, max_style_corr={style:.3f}, industryR2={r2:.3f}".format(
                factor=row.get("factor_name"),
                horizon=row.get("horizon"),
                classification=row.get("classification"),
                raw=float(row.get("mean_raw_rank_ic", 0.0)),
                resid=float(row.get("mean_residual_rank_ic", 0.0)),
                t=float(row.get("residual_rank_ic_t_stat", 0.0)),
                ret=float(row.get("residual_retention_ratio", 0.0)),
                style=float(row.get("max_abs_style_correlation", 0.0)),
                r2=float(row.get("mean_industry_r2", 0.0)),
            )
        )
    return "\n".join(lines) + "\n"


def _prepare_factors(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame[["date", "asset_id", "market", "factor_name", "factor_value"]].copy()
    output["date"] = pd.to_datetime(output["date"])
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].astype(str).str.upper()
    output["factor_value"] = pd.to_numeric(output["factor_value"], errors="coerce")
    return output


def _prepare_labels(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame[["date", "asset_id", "market", "horizon", "execution_lag", "forward_return"]].copy()
    output["date"] = pd.to_datetime(output["date"])
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].astype(str).str.upper()
    output["horizon"] = pd.to_numeric(output["horizon"], errors="coerce").fillna(0).astype(int)
    output["execution_lag"] = pd.to_numeric(output["execution_lag"], errors="coerce").fillna(0).astype(int)
    output["forward_return"] = pd.to_numeric(output["forward_return"], errors="coerce")
    return output


def _prepare_stock_basic(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    if "asset_id" not in output.columns and "ts_code" in output.columns:
        output["asset_id"] = output["ts_code"]
    if "industry" not in output.columns:
        output["industry"] = ""
    output = output[["asset_id", "industry"]].copy()
    output["asset_id"] = output["asset_id"].astype(str)
    output["industry"] = output["industry"].fillna("").astype(str)
    return output.drop_duplicates("asset_id", keep="last").reset_index(drop=True)


def _prepare_style_wide(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"])
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].astype(str).str.upper()
    if {"style_name", "style_value"}.issubset(output.columns):
        output["style_name"] = output["style_name"].astype(str)
        output["style_value"] = pd.to_numeric(output["style_value"], errors="coerce")
        output = (
            output.pivot_table(
                index=["date", "asset_id", "market"],
                columns="style_name",
                values="style_value",
                aggfunc="mean",
            )
            .reset_index()
            .rename_axis(None, axis=1)
        )
    for style_name in REQUIRED_STYLE_NAMES:
        if style_name not in output.columns:
            output[style_name] = float("nan")
        output[style_name] = pd.to_numeric(output[style_name], errors="coerce")
    return output[["date", "asset_id", "market", *REQUIRED_STYLE_NAMES]].reset_index(drop=True)


def _lightweight_residual(frame: pd.DataFrame) -> pd.Series:
    if frame.empty or len(frame) < len(REQUIRED_STYLE_NAMES) + 3:
        return pd.Series(dtype="float64")
    working = frame.dropna(subset=["factor_value", "industry", *REQUIRED_STYLE_NAMES]).copy()
    if len(working) < len(REQUIRED_STYLE_NAMES) + 3 or working["industry"].nunique() < 2:
        return pd.Series(dtype="float64")
    y = _zscore(working["factor_value"])
    y = y - y.groupby(working["industry"].astype(str)).transform("mean")
    design = pd.concat([_zscore(working[name]).rename(name) for name in REQUIRED_STYLE_NAMES], axis=1)
    valid = pd.Series(True, index=working.index)
    valid &= pd.Series(pd.notna(y), index=working.index)
    valid &= design.notna().all(axis=1)
    if int(valid.sum()) < len(REQUIRED_STYLE_NAMES) + 3:
        return pd.Series(dtype="float64")
    y_values = y.loc[valid].to_numpy(dtype=float)
    x_values = design.loc[valid].to_numpy(dtype=float)
    if x_values.shape[0] <= x_values.shape[1] or pd.DataFrame(x_values).nunique().min() <= 1:
        return pd.Series(dtype="float64")
    beta, *_ = np.linalg.lstsq(x_values, y_values, rcond=None)
    residual = y_values - x_values @ beta
    if float(pd.Series(residual).std(ddof=0)) <= 1e-12:
        return pd.Series(dtype="float64")
    return pd.Series(residual, index=working.index[valid])


def _industry_r2_fast(values: pd.Series, industries: pd.Series) -> float:
    valid = pd.DataFrame({"value": pd.to_numeric(values, errors="coerce"), "industry": industries}).dropna()
    if len(valid) < 3 or valid["industry"].nunique() < 2:
        return float("nan")
    overall = float(valid["value"].mean())
    total = float(((valid["value"] - overall) ** 2).sum())
    if total <= 1e-12:
        return float("nan")
    industry_mean = valid.groupby("industry")["value"].transform("mean")
    between = float(((industry_mean - overall) ** 2).sum())
    return max(0.0, min(1.0, between / total))


def _lightweight_factor_summary(
    date_rows: list[dict[str, Any]],
    style_rows: list[dict[str, Any]],
    *,
    min_dates: int,
    min_residual_mean_ic: float,
    min_residual_ic_t_stat: float,
    min_residual_positive_rate: float,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int, int], list[dict[str, Any]]] = {}
    for row in date_rows:
        key = (str(row["market"]), str(row["factor_name"]), int(row["horizon"]), int(row["execution_lag"]))
        grouped.setdefault(key, []).append(row)
    style_grouped: dict[tuple[str, str, int, int], list[dict[str, Any]]] = {}
    for row in style_rows:
        key = (str(row["market"]), str(row["factor_name"]), int(row["horizon"]), int(row["execution_lag"]))
        style_grouped.setdefault(key, []).append(row)
    result = []
    for (market, factor_name, horizon, execution_lag), rows in grouped.items():
        raw_values = _finite_list(row.get("raw_rank_ic") for row in rows)
        residual_values = _finite_list(row.get("residual_rank_ic") for row in rows)
        raw_mean = _mean(raw_values)
        residual_mean = _mean(residual_values)
        residual_t = _mean_t_stat(residual_values)
        residual_positive_rate = _safe_ratio(sum(1 for value in residual_values if value > 0.0), len(residual_values))
        retention = abs(residual_mean) / abs(raw_mean) if raw_mean and math.isfinite(raw_mean) else float("nan")
        style_corrs = _finite_list(row.get("spearman_correlation") for row in style_grouped.get((market, factor_name, horizon, execution_lag), []))
        max_style = max((abs(value) for value in style_corrs), default=0.0)
        industry_r2 = _mean(_finite_list(row.get("industry_r2") for row in rows))
        style_coverage = _mean(_finite_list(row.get("style_coverage_ratio") for row in rows))
        missing_industry = _safe_ratio(
            sum(int(row.get("missing_industry_rows", 0)) for row in rows),
            sum(int(row.get("observations", 0)) for row in rows),
        )
        residual_candidate = (
            len(residual_values) >= min_dates
            and abs(residual_mean) >= min_residual_mean_ic
            and abs(residual_t) >= min_residual_ic_t_stat
            and residual_positive_rate >= min_residual_positive_rate
            and math.isfinite(retention)
            and retention >= 0.35
            and style_coverage >= 0.90
            and missing_industry <= 0.02
        )
        exposure_high = max_style >= 0.70 or (math.isfinite(industry_r2) and industry_r2 >= 0.50)
        if residual_candidate:
            classification = "residual_candidate"
            blockers: list[str] = []
        elif exposure_high:
            classification = "style_or_industry_exposure_dominated"
            blockers = ["residual_ic_gate_failed"]
        else:
            classification = "weak_or_unproven_after_residualization"
            blockers = ["residual_ic_gate_failed"]
        if style_coverage < 0.90:
            blockers.append("style_coverage_below_threshold")
        if missing_industry > 0.02:
            blockers.append("industry_coverage_below_threshold")
        result.append(
            {
                "market": market,
                "factor_name": factor_name,
                "horizon": int(horizon),
                "execution_lag": int(execution_lag),
                "classification": classification,
                "factor_blockers": _dedupe(blockers),
                "dates": int(len(rows)),
                "raw_valid_dates": int(len(raw_values)),
                "residual_valid_dates": int(len(residual_values)),
                "mean_raw_rank_ic": raw_mean,
                "raw_rank_ic_t_stat": _mean_t_stat(raw_values),
                "raw_positive_ic_rate": _safe_ratio(sum(1 for value in raw_values if value > 0.0), len(raw_values)),
                "mean_residual_rank_ic": residual_mean,
                "residual_rank_ic_t_stat": residual_t,
                "residual_positive_ic_rate": residual_positive_rate,
                "residual_retention_ratio": retention,
                "max_abs_style_correlation": max_style,
                "mean_abs_style_correlation": _mean(abs(value) for value in style_corrs),
                "mean_industry_r2": industry_r2,
                "style_coverage_ratio": style_coverage,
                "missing_industry_fraction": missing_industry,
                "total_observations": int(sum(int(row.get("observations", 0)) for row in rows)),
                "missing_industry_rows": int(sum(int(row.get("missing_industry_rows", 0)) for row in rows)),
            }
        )
    return result


def _quantile_labels(values: pd.Series) -> pd.Series | None:
    if values.nunique(dropna=True) < 5:
        return None
    try:
        return pd.qcut(values.rank(method="first"), 5, labels=False)
    except ValueError:
        return None


def _empty_shape_summary(factor_name: str, horizon: int, execution_lag: int, shape_dates: int) -> dict[str, Any]:
    return {
        "factor_name": factor_name,
        "horizon": int(horizon),
        "execution_lag": int(execution_lag),
        "shape_dates": int(shape_dates),
        "q1": 0.0,
        "q2": 0.0,
        "q3": 0.0,
        "q4": 0.0,
        "q5": 0.0,
        "q5_minus_q1": 0.0,
        "quantile_monotonicity": 0.0,
        "best_quantile": "",
        "q5_is_best": False,
        "q1_is_worst": False,
        "shape_pass": False,
        "shape_blockers": ["insufficient_shape_dates"],
    }


def _positive_log(values: pd.Series) -> pd.Series:
    series = pd.to_numeric(values, errors="coerce")
    return series.where(series > 0).map(math.log)


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby(frame["date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return (values - mean) / std.replace(0, pd.NA)


def _spearman(left: pd.Series, right: pd.Series) -> float:
    aligned = pd.concat([left, right], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    return float(aligned.iloc[:, 0].rank(method="average").corr(aligned.iloc[:, 1].rank(method="average")))


def _zscore(values: pd.Series) -> pd.Series:
    series = pd.to_numeric(values, errors="coerce").astype(float)
    std = float(series.std(ddof=0))
    if not math.isfinite(std) or std <= 1e-12:
        return pd.Series(0.0, index=series.index)
    return (series - float(series.mean())) / std


def _finite_list(values: Iterable[Any]) -> list[float]:
    output = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            output.append(number)
    return output


def _mean(values: Iterable[float]) -> float:
    finite = [float(value) for value in values if math.isfinite(float(value))]
    if not finite:
        return 0.0
    return float(pd.Series(finite, dtype="float64").mean())


def _mean_t_stat(values: Iterable[float]) -> float:
    finite = [float(value) for value in values if math.isfinite(float(value))]
    if len(finite) < 2:
        return 0.0
    series = pd.Series(finite, dtype="float64")
    std = float(series.std(ddof=1))
    if std <= 1e-12:
        return math.copysign(1e12, float(series.mean())) if float(series.mean()) != 0.0 else 0.0
    return float(series.mean() / (std / math.sqrt(len(series))))


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    denominator_value = float(denominator)
    if denominator_value <= 0:
        return 0.0
    return float(numerator) / denominator_value


def _dedupe(values: Iterable[str]) -> list[str]:
    output = []
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
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
