from __future__ import annotations

from collections import Counter
from collections import defaultdict
from datetime import date
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd


STAGE = "industry_style_exposure_audit"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
DEFAULT_REQUIRED_STYLE_NAMES = ("size", "value", "lowvol", "momentum", "liquidity")


def build_industry_style_exposure_audit(
    *,
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    stock_basic: pd.DataFrame,
    style_factors: pd.DataFrame,
    source_report: str | None = None,
    required_style_names: Sequence[str] = DEFAULT_REQUIRED_STYLE_NAMES,
    min_dates: int = 20,
    min_cross_section: int = 30,
    min_industries: int = 2,
    min_style_coverage_ratio: float = 0.90,
    max_missing_industry_fraction: float = 0.02,
    high_style_corr_threshold: float = 0.70,
    high_industry_r2_threshold: float = 0.50,
    min_residual_mean_ic: float = 0.02,
    min_residual_ic_t_stat: float = 2.0,
    min_residual_positive_rate: float = 0.55,
    min_residual_retention: float = 0.35,
) -> dict[str, Any]:
    factor_frame = _prepare_factors(factors)
    label_frame = _prepare_labels(labels)
    metadata = _prepare_stock_basic(stock_basic)
    style_frame, observed_style_names = _prepare_style_factors(style_factors)
    required_styles = tuple(_clean_style_name(name) for name in required_style_names)
    missing_required_style_names = [name for name in required_styles if name not in observed_style_names]
    merged = _merge_inputs(factor_frame, label_frame, metadata, style_frame, required_styles)
    date_rows, style_rows, residual_rows = _build_date_rows(
        merged,
        required_style_names=required_styles,
        min_cross_section=min_cross_section,
        min_industries=min_industries,
    )
    factor_summary = _build_factor_summary(
        date_rows,
        style_rows,
        min_dates=min_dates,
        min_style_coverage_ratio=min_style_coverage_ratio,
        max_missing_industry_fraction=max_missing_industry_fraction,
        high_style_corr_threshold=high_style_corr_threshold,
        high_industry_r2_threshold=high_industry_r2_threshold,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_ic_t_stat=min_residual_ic_t_stat,
        min_residual_positive_rate=min_residual_positive_rate,
        min_residual_retention=min_residual_retention,
    )
    blockers = _summary_blockers(
        factor_summary,
        missing_required_style_names=missing_required_style_names,
        min_style_coverage_ratio=min_style_coverage_ratio,
        max_missing_industry_fraction=max_missing_industry_fraction,
    )
    summary = _summary(
        merged,
        factor_summary,
        residual_rows,
        blockers=blockers,
        missing_required_style_names=missing_required_style_names,
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "source_report": source_report,
        "summary": summary,
        "thresholds": {
            "required_style_names": list(required_styles),
            "min_dates": int(min_dates),
            "min_cross_section": int(min_cross_section),
            "min_industries": int(min_industries),
            "min_style_coverage_ratio": float(min_style_coverage_ratio),
            "max_missing_industry_fraction": float(max_missing_industry_fraction),
            "high_style_corr_threshold": float(high_style_corr_threshold),
            "high_industry_r2_threshold": float(high_industry_r2_threshold),
            "min_residual_mean_ic": float(min_residual_mean_ic),
            "min_residual_ic_t_stat": float(min_residual_ic_t_stat),
            "min_residual_positive_rate": float(min_residual_positive_rate),
            "min_residual_retention": float(min_residual_retention),
        },
        "promotion_policy": {
            "portfolio_grid_allowed_after_audit": summary["passes"],
            "promotion_claim_allowed": False,
            "required_next_gate": "cost_capacity_walk_forward_after_residual_factor_matrix",
            "raw_topn_without_residual_audit_allowed": False,
        },
        "factor_summary": factor_summary,
        "industry_date_rows": date_rows,
        "style_exposure_rows": style_rows,
        "residual_factor_rows": residual_rows,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_industry_style_exposure_audit_markdown(result)
    return result


def write_industry_style_exposure_audit(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "industry_style_exposure_audit.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "industry_style_exposure_audit.md").write_text(
        render_industry_style_exposure_audit_markdown(result),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("factor_summary", [])).to_csv(output_path / "factor_summary.csv", index=False)
    pd.DataFrame(result.get("style_exposure_rows", [])).to_csv(output_path / "style_exposure_rows.csv", index=False)
    pd.DataFrame(result.get("industry_date_rows", [])).to_csv(output_path / "industry_date_rows.csv", index=False)
    pd.DataFrame(result.get("residual_factor_rows", [])).to_csv(output_path / "residual_factor_rows.csv", index=False)


def render_industry_style_exposure_audit_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    policy = _dict(result.get("promotion_policy"))
    lines = [
        "# Industry/Style Exposure Audit",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Factors: {summary.get('factors', 0)}",
        f"- Residual candidate factors: {summary.get('residual_candidate_factors', 0)}",
        f"- Exposure dominated factors: {summary.get('style_or_industry_exposure_dominated_factors', 0)}",
        f"- Insufficient coverage factors: {summary.get('insufficient_exposure_coverage_factors', 0)}",
        f"- Residual factor rows: {summary.get('residual_factor_rows', 0)}",
        f"- Missing required style names: {', '.join(_list(summary.get('missing_required_style_names'))) or 'none'}",
        f"- Blockers: {', '.join(_list(summary.get('blockers'))) or 'none'}",
        f"- Portfolio grid allowed after audit: {policy.get('portfolio_grid_allowed_after_audit', False)}",
        f"- Raw TopN without residual audit allowed: {policy.get('raw_topn_without_residual_audit_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Interpretation",
        "",
        "- This audit separates candidate signal from industry and common style exposure before portfolio grids.",
        "- Passing this audit is not a profit or promotion claim; it only permits the residual candidate to enter later cost, capacity, walk-forward, regime, and holdout gates.",
        "",
        "## Factor Summary",
        "",
    ]
    for row in result.get("factor_summary", []):
        lines.append(
            "- {factor} h{horizon}/lag{lag}: {classification}, dates={dates}, rawIC={raw:.4f}, "
            "residualIC={resid:.4f}, residual_t={t:.2f}, residual_pos={pos:.2f}, "
            "style|max|={style:.3f}, industryR2={industry:.3f}".format(
                factor=row.get("factor_name"),
                horizon=row.get("horizon"),
                lag=row.get("execution_lag"),
                classification=row.get("classification"),
                dates=int(row.get("dates", 0)),
                raw=_number(row.get("mean_raw_rank_ic"), default=float("nan")),
                resid=_number(row.get("mean_residual_rank_ic"), default=float("nan")),
                t=_number(row.get("residual_rank_ic_t_stat"), default=float("nan")),
                pos=_number(row.get("residual_positive_ic_rate"), default=float("nan")),
                style=_number(row.get("max_abs_style_correlation"), default=float("nan")),
                industry=_number(row.get("mean_industry_r2"), default=float("nan")),
            )
        )
    if not result.get("factor_summary"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _prepare_factors(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    _require_columns(frame, required, "factors")
    output = frame[required].copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce").dt.date
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].astype(str).str.upper()
    output["factor_name"] = output["factor_name"].astype(str)
    output["factor_value"] = pd.to_numeric(output["factor_value"], errors="coerce")
    return output.dropna(subset=["date"]).reset_index(drop=True)


def _prepare_labels(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "forward_return"]
    _require_columns(frame, required, "labels")
    output = frame.copy()
    if "horizon" not in output.columns:
        output["horizon"] = 0
    if "execution_lag" not in output.columns:
        output["execution_lag"] = 0
    output = output[required + ["horizon", "execution_lag"]].copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce").dt.date
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].astype(str).str.upper()
    output["forward_return"] = pd.to_numeric(output["forward_return"], errors="coerce")
    output["horizon"] = pd.to_numeric(output["horizon"], errors="coerce").fillna(0).astype(int)
    output["execution_lag"] = pd.to_numeric(output["execution_lag"], errors="coerce").fillna(0).astype(int)
    return output.dropna(subset=["date"]).reset_index(drop=True)


def _prepare_stock_basic(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    if "asset_id" not in output.columns and "ts_code" in output.columns:
        output["asset_id"] = output["ts_code"]
    _require_columns(output, ["asset_id", "industry"], "stock_basic")
    output = output[["asset_id", "industry"]].copy()
    output["asset_id"] = output["asset_id"].astype(str)
    output["industry"] = output["industry"].map(_clean_optional_text)
    return output.drop_duplicates("asset_id", keep="last").reset_index(drop=True)


def _prepare_style_factors(frame: pd.DataFrame) -> tuple[pd.DataFrame, set[str]]:
    if frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market"]), set()
    output = frame.copy()
    if "style_name" not in output.columns and "factor_name" in output.columns:
        output["style_name"] = output["factor_name"]
    if "style_value" not in output.columns and "factor_value" in output.columns:
        output["style_value"] = output["factor_value"]
    _require_columns(output, ["date", "asset_id", "market", "style_name", "style_value"], "style_factors")
    output = output[["date", "asset_id", "market", "style_name", "style_value"]].copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce").dt.date
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].astype(str).str.upper()
    output["style_name"] = output["style_name"].map(_clean_style_name)
    output["style_value"] = pd.to_numeric(output["style_value"], errors="coerce")
    output = output.dropna(subset=["date", "style_name"]).reset_index(drop=True)
    observed = {str(name) for name in output["style_name"].dropna().unique()}
    wide = (
        output.pivot_table(
            index=["date", "asset_id", "market"],
            columns="style_name",
            values="style_value",
            aggfunc="mean",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    return wide, observed


def _merge_inputs(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    stock_basic: pd.DataFrame,
    style_factors: pd.DataFrame,
    required_style_names: Sequence[str],
) -> pd.DataFrame:
    merged = factors.merge(labels, on=["date", "asset_id", "market"], how="inner")
    merged = merged.merge(stock_basic, on="asset_id", how="left")
    if not style_factors.empty:
        merged = merged.merge(style_factors, on=["date", "asset_id", "market"], how="left")
    for style_name in required_style_names:
        if style_name not in merged.columns:
            merged[style_name] = float("nan")
    return merged.reset_index(drop=True)


def _build_date_rows(
    merged: pd.DataFrame,
    *,
    required_style_names: Sequence[str],
    min_cross_section: int,
    min_industries: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    date_rows: list[dict[str, Any]] = []
    style_rows: list[dict[str, Any]] = []
    residual_rows: list[dict[str, Any]] = []
    if merged.empty:
        return date_rows, style_rows, residual_rows
    group_keys = ["date", "market", "factor_name", "horizon", "execution_lag"]
    for key, group in merged.groupby(group_keys, sort=True):
        date_value, market, factor_name, horizon, execution_lag = key
        valid = group.dropna(subset=["factor_value", "forward_return"]).copy()
        industry_present = valid["industry"].notna() & (valid["industry"].astype(str).str.strip() != "")
        style_present = valid[list(required_style_names)].notna().all(axis=1)
        complete = valid[industry_present & style_present].copy()
        raw_ic = _rank_corr_stats(valid["factor_value"], valid["forward_return"])
        industry_r2 = _industry_r2(valid.loc[industry_present, "factor_value"], valid.loc[industry_present, "industry"])
        residual = _residualize_factor(
            complete,
            required_style_names=required_style_names,
            min_cross_section=min_cross_section,
            min_industries=min_industries,
        )
        residual_ic = _rank_corr_stats(residual, complete.loc[residual.index, "forward_return"]) if not residual.empty else _empty_stats()
        date_rows.append(
            {
                "date": _iso_date(date_value),
                "market": str(market),
                "factor_name": str(factor_name),
                "horizon": int(horizon),
                "execution_lag": int(execution_lag),
                "observations": int(len(valid)),
                "industry_observations": int(industry_present.sum()),
                "style_complete_observations": int(style_present.sum()),
                "residual_observations": int(len(residual)),
                "industries": int(valid.loc[industry_present, "industry"].nunique()),
                "missing_industry_rows": int((~industry_present).sum()),
                "style_coverage_ratio": _safe_ratio(int(style_present.sum()), int(len(valid))),
                "missing_industry_fraction": _safe_ratio(int((~industry_present).sum()), int(len(valid))),
                "raw_rank_ic": raw_ic["correlation"],
                "raw_rank_ic_t_stat": raw_ic["t_stat"],
                "raw_rank_ic_p_value": raw_ic["p_value"],
                "residual_rank_ic": residual_ic["correlation"],
                "residual_rank_ic_t_stat": residual_ic["t_stat"],
                "residual_rank_ic_p_value": residual_ic["p_value"],
                "industry_r2": industry_r2,
            }
        )
        for style_name in required_style_names:
            style_valid = valid.dropna(subset=["factor_value", style_name])
            style_ic = _rank_corr_stats(style_valid["factor_value"], style_valid[style_name])
            style_rows.append(
                {
                    "date": _iso_date(date_value),
                    "market": str(market),
                    "factor_name": str(factor_name),
                    "horizon": int(horizon),
                    "execution_lag": int(execution_lag),
                    "style_name": str(style_name),
                    "observations": int(len(style_valid)),
                    "coverage_ratio": _safe_ratio(int(len(style_valid)), int(len(valid))),
                    "spearman_correlation": style_ic["correlation"],
                    "correlation_t_stat": style_ic["t_stat"],
                    "correlation_p_value": style_ic["p_value"],
                }
            )
        for row_index, residual_value in residual.items():
            row = complete.loc[row_index]
            residual_rows.append(
                {
                    "date": _iso_date(date_value),
                    "asset_id": str(row["asset_id"]),
                    "market": str(market),
                    "factor_name": f"{factor_name}__industry_style_residual",
                    "source_factor_name": str(factor_name),
                    "factor_value": float(residual_value),
                    "horizon": int(horizon),
                    "execution_lag": int(execution_lag),
                }
            )
    return date_rows, style_rows, residual_rows


def _residualize_factor(
    frame: pd.DataFrame,
    *,
    required_style_names: Sequence[str],
    min_cross_section: int,
    min_industries: int,
) -> pd.Series:
    if len(frame) < min_cross_section or frame["industry"].nunique() < min_industries:
        return pd.Series(dtype="float64")
    working = frame.dropna(subset=["factor_value", "industry", *required_style_names]).copy()
    if len(working) < min_cross_section or working["industry"].nunique() < min_industries:
        return pd.Series(dtype="float64")
    y = _zscore(working["factor_value"])
    design_parts = [pd.Series(1.0, index=working.index, name="intercept")]
    dummies = pd.get_dummies(working["industry"].astype(str), prefix="industry", dtype=float)
    if dummies.shape[1] > 1:
        design_parts.append(dummies.iloc[:, 1:])
    for style_name in required_style_names:
        design_parts.append(_zscore(working[style_name]).rename(f"style_{style_name}"))
    design = pd.concat(design_parts, axis=1)
    valid_mask = np.isfinite(y.to_numpy(dtype=float)) & np.isfinite(design.to_numpy(dtype=float)).all(axis=1)
    if int(valid_mask.sum()) < min_cross_section:
        return pd.Series(dtype="float64")
    y_values = y.loc[valid_mask].to_numpy(dtype=float)
    x_values = design.loc[valid_mask].to_numpy(dtype=float)
    if np.linalg.matrix_rank(x_values) < 2:
        return pd.Series(dtype="float64")
    beta, *_ = np.linalg.lstsq(x_values, y_values, rcond=None)
    residual = y_values - x_values @ beta
    if float(np.std(residual)) <= 1e-12:
        return pd.Series(dtype="float64")
    return pd.Series(residual, index=working.index[valid_mask])


def _build_factor_summary(
    date_rows: list[dict[str, Any]],
    style_rows: list[dict[str, Any]],
    *,
    min_dates: int,
    min_style_coverage_ratio: float,
    max_missing_industry_fraction: float,
    high_style_corr_threshold: float,
    high_industry_r2_threshold: float,
    min_residual_mean_ic: float,
    min_residual_ic_t_stat: float,
    min_residual_positive_rate: float,
    min_residual_retention: float,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in date_rows:
        grouped[
            (
                str(row.get("market")),
                str(row.get("factor_name")),
                int(row.get("horizon", 0)),
                int(row.get("execution_lag", 0)),
            )
        ].append(row)
    style_grouped: dict[tuple[str, str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in style_rows:
        style_grouped[
            (
                str(row.get("market")),
                str(row.get("factor_name")),
                int(row.get("horizon", 0)),
                int(row.get("execution_lag", 0)),
            )
        ].append(row)
    result = []
    for (market, factor_name, horizon, execution_lag), rows in grouped.items():
        raw_values = _finite_values(row.get("raw_rank_ic") for row in rows)
        residual_values = _finite_values(row.get("residual_rank_ic") for row in rows)
        industry_r2_values = _finite_values(row.get("industry_r2") for row in rows)
        raw_mean = _mean_or_zero(raw_values)
        residual_mean = _mean_or_zero(residual_values)
        raw_t = _stat_or_zero(_mean_t_stat(raw_values))
        residual_t = _stat_or_zero(_mean_t_stat(residual_values))
        residual_positive_rate = _safe_ratio(sum(1 for value in residual_values if value > 0.0), len(residual_values))
        retention = _retention_ratio(residual_mean, raw_mean)
        total_observations = sum(int(_number(row.get("observations"))) for row in rows)
        missing_industry_rows = sum(int(_number(row.get("missing_industry_rows"))) for row in rows)
        style_coverage_ratio = _mean(_finite_values(row.get("style_coverage_ratio") for row in rows))
        missing_industry_fraction = _safe_ratio(missing_industry_rows, total_observations)
        style_stats = style_grouped.get((market, factor_name, horizon, execution_lag), [])
        style_correlations = _finite_values(row.get("spearman_correlation") for row in style_stats)
        max_abs_style_corr = max((abs(value) for value in style_correlations), default=0.0)
        mean_abs_style_corr = _mean([abs(value) for value in style_correlations])
        mean_industry_r2 = _mean(industry_r2_values)
        classification, blockers = _classify_factor(
            dates=len(rows),
            residual_dates=len(residual_values),
            style_coverage_ratio=style_coverage_ratio,
            missing_industry_fraction=missing_industry_fraction,
            max_abs_style_corr=max_abs_style_corr,
            mean_industry_r2=mean_industry_r2,
            residual_mean=residual_mean,
            residual_t=residual_t,
            residual_positive_rate=residual_positive_rate,
            retention=retention,
            min_dates=min_dates,
            min_style_coverage_ratio=min_style_coverage_ratio,
            max_missing_industry_fraction=max_missing_industry_fraction,
            high_style_corr_threshold=high_style_corr_threshold,
            high_industry_r2_threshold=high_industry_r2_threshold,
            min_residual_mean_ic=min_residual_mean_ic,
            min_residual_ic_t_stat=min_residual_ic_t_stat,
            min_residual_positive_rate=min_residual_positive_rate,
            min_residual_retention=min_residual_retention,
        )
        result.append(
            {
                "market": market,
                "factor_name": factor_name,
                "horizon": int(horizon),
                "execution_lag": int(execution_lag),
                "classification": classification,
                "factor_blockers": blockers,
                "dates": len(rows),
                "raw_valid_dates": len(raw_values),
                "residual_valid_dates": len(residual_values),
                "mean_raw_rank_ic": raw_mean,
                "raw_rank_ic_t_stat": raw_t,
                "raw_positive_ic_rate": _safe_ratio(sum(1 for value in raw_values if value > 0.0), len(raw_values)),
                "mean_residual_rank_ic": residual_mean,
                "residual_rank_ic_t_stat": residual_t,
                "residual_positive_ic_rate": residual_positive_rate,
                "residual_retention_ratio": retention,
                "max_abs_style_correlation": max_abs_style_corr,
                "mean_abs_style_correlation": mean_abs_style_corr,
                "mean_industry_r2": mean_industry_r2,
                "style_coverage_ratio": style_coverage_ratio,
                "missing_industry_fraction": missing_industry_fraction,
                "total_observations": total_observations,
                "missing_industry_rows": missing_industry_rows,
            }
        )
    return sorted(
        result,
        key=lambda row: (
            _classification_rank(str(row.get("classification"))),
            -abs(_number(row.get("residual_rank_ic_t_stat"))),
            str(row.get("factor_name")),
        ),
    )


def _classify_factor(
    *,
    dates: int,
    residual_dates: int,
    style_coverage_ratio: float,
    missing_industry_fraction: float,
    max_abs_style_corr: float,
    mean_industry_r2: float,
    residual_mean: float,
    residual_t: float,
    residual_positive_rate: float,
    retention: float,
    min_dates: int,
    min_style_coverage_ratio: float,
    max_missing_industry_fraction: float,
    high_style_corr_threshold: float,
    high_industry_r2_threshold: float,
    min_residual_mean_ic: float,
    min_residual_ic_t_stat: float,
    min_residual_positive_rate: float,
    min_residual_retention: float,
) -> tuple[str, list[str]]:
    blockers: list[str] = []
    if dates < min_dates or residual_dates < min_dates:
        blockers.append("insufficient_residual_dates")
    if style_coverage_ratio < min_style_coverage_ratio:
        blockers.append("style_coverage_below_threshold")
    if missing_industry_fraction > max_missing_industry_fraction:
        blockers.append("industry_coverage_below_threshold")
    coverage_ok = not any(blocker.endswith("coverage_below_threshold") or blocker == "insufficient_residual_dates" for blocker in blockers)
    residual_strong = (
        abs(residual_mean) >= min_residual_mean_ic
        and abs(residual_t) >= min_residual_ic_t_stat
        and residual_positive_rate >= min_residual_positive_rate
        and (math.isfinite(retention) and retention >= min_residual_retention)
    )
    exposure_high = (
        math.isfinite(max_abs_style_corr)
        and max_abs_style_corr >= high_style_corr_threshold
    ) or (
        math.isfinite(mean_industry_r2)
        and mean_industry_r2 >= high_industry_r2_threshold
    )
    if not residual_strong:
        blockers.append("residual_ic_gate_failed")
    if not coverage_ok:
        return "insufficient_exposure_coverage", _dedupe(blockers)
    if residual_strong:
        return "residual_candidate", _dedupe([blocker for blocker in blockers if blocker != "residual_ic_gate_failed"])
    if exposure_high:
        return "style_or_industry_exposure_dominated", _dedupe(blockers)
    return "weak_or_unproven_after_residualization", _dedupe(blockers)


def _summary(
    merged: pd.DataFrame,
    factor_summary: list[dict[str, Any]],
    residual_rows: list[dict[str, Any]],
    *,
    blockers: list[str],
    missing_required_style_names: list[str],
) -> dict[str, Any]:
    counts = Counter(str(row.get("classification")) for row in factor_summary)
    return {
        "passes": not blockers,
        "blockers": blockers,
        "input_rows": int(len(merged)),
        "factors": int(len(factor_summary)),
        "factor_names": int(len({str(row.get("factor_name")) for row in factor_summary})),
        "residual_candidate_factors": int(counts.get("residual_candidate", 0)),
        "style_or_industry_exposure_dominated_factors": int(counts.get("style_or_industry_exposure_dominated", 0)),
        "insufficient_exposure_coverage_factors": int(counts.get("insufficient_exposure_coverage", 0)),
        "weak_or_unproven_after_residualization_factors": int(counts.get("weak_or_unproven_after_residualization", 0)),
        "residual_factor_rows": int(len(residual_rows)),
        "missing_required_style_names": missing_required_style_names,
        "classification_counts": dict(sorted(counts.items())),
    }


def _summary_blockers(
    factor_summary: list[dict[str, Any]],
    *,
    missing_required_style_names: list[str],
    min_style_coverage_ratio: float,
    max_missing_industry_fraction: float,
) -> list[str]:
    blockers: list[str] = []
    if missing_required_style_names:
        blockers.append("missing_required_style_names")
    if not factor_summary:
        blockers.append("missing_factor_summary")
    if any(_number(row.get("style_coverage_ratio"), default=0.0) < min_style_coverage_ratio for row in factor_summary):
        blockers.append("style_coverage_below_threshold")
    if any(_number(row.get("missing_industry_fraction"), default=1.0) > max_missing_industry_fraction for row in factor_summary):
        blockers.append("industry_coverage_below_threshold")
    if not any(row.get("classification") == "residual_candidate" for row in factor_summary):
        blockers.append("no_residual_candidate_after_industry_style_audit")
    return _dedupe(blockers)


def _industry_r2(values: pd.Series, industries: pd.Series) -> float:
    valid = pd.DataFrame({"value": values, "industry": industries}).dropna()
    if len(valid) < 3 or valid["industry"].nunique() < 2:
        return float("nan")
    y = valid["value"].astype(float).to_numpy()
    dummies = pd.get_dummies(valid["industry"].astype(str), dtype=float).to_numpy()
    if dummies.size == 0:
        return float("nan")
    beta, *_ = np.linalg.lstsq(dummies, y, rcond=None)
    fitted = dummies @ beta
    total = float(np.sum((y - np.mean(y)) ** 2))
    if total <= 1e-12:
        return float("nan")
    residual = float(np.sum((y - fitted) ** 2))
    return max(0.0, min(1.0, 1.0 - residual / total))


def _rank_corr_stats(left: pd.Series, right: pd.Series) -> dict[str, float]:
    return _corr_stats(left.rank(), right.rank())


def _corr_stats(left: pd.Series, right: pd.Series) -> dict[str, float]:
    valid = pd.concat([left, right], axis=1).dropna()
    if len(valid) < 2:
        return _empty_stats()
    left_values = valid.iloc[:, 0]
    right_values = valid.iloc[:, 1]
    if left_values.nunique() < 2 or right_values.nunique() < 2:
        return _empty_stats()
    correlation = float(left_values.corr(right_values))
    t_stat, p_value = _corr_t_test(correlation, len(valid))
    return {"correlation": correlation, "t_stat": t_stat, "p_value": p_value}


def _corr_t_test(correlation: float, observations: int) -> tuple[float, float]:
    if observations < 3 or not math.isfinite(correlation):
        return float("nan"), float("nan")
    bounded = max(min(correlation, 1.0), -1.0)
    if abs(bounded) >= 1.0:
        return math.copysign(1e12, bounded), 0.0
    denominator = max(1.0 - bounded * bounded, 0.0)
    if denominator == 0.0:
        return math.copysign(1e12, bounded), 0.0
    t_stat = bounded * math.sqrt((observations - 2) / denominator)
    return t_stat, _normal_two_sided_p_value(t_stat)


def _mean_t_stat(values: Iterable[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if len(finite) < 2:
        return float("nan")
    series = pd.Series(finite, dtype="float64")
    mean = float(series.mean())
    std = float(series.std(ddof=1))
    if std == 0.0:
        if mean == 0.0:
            return float("nan")
        return math.copysign(1e12, mean)
    return float(mean / (std / math.sqrt(len(series))))


def _normal_two_sided_p_value(t_stat: float) -> float:
    if not math.isfinite(t_stat):
        return float("nan")
    return max(min(math.erfc(abs(t_stat) / math.sqrt(2.0)), 1.0), 0.0)


def _zscore(values: pd.Series) -> pd.Series:
    series = pd.to_numeric(values, errors="coerce").astype(float)
    std = float(series.std(ddof=0))
    if not math.isfinite(std) or std <= 1e-12:
        return pd.Series(0.0, index=series.index)
    return (series - float(series.mean())) / std


def _empty_stats() -> dict[str, float]:
    return {"correlation": float("nan"), "t_stat": float("nan"), "p_value": float("nan")}


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} missing required columns: {', '.join(missing)}")


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text or None


def _clean_style_name(value: Any) -> str:
    return str(value).strip().lower()


def _finite_values(values: Iterable[Any]) -> list[float]:
    output = []
    for value in values:
        number = _number(value, default=float("nan"))
        if math.isfinite(number):
            output.append(number)
    return output


def _mean(values: Iterable[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return float("nan")
    return float(pd.Series(finite, dtype="float64").mean())


def _mean_or_zero(values: Iterable[float]) -> float:
    value = _mean(values)
    return value if math.isfinite(value) else 0.0


def _stat_or_zero(value: float) -> float:
    return value if math.isfinite(value) else 0.0


def _retention_ratio(residual_mean: float, raw_mean: float) -> float:
    if not math.isfinite(residual_mean) or not math.isfinite(raw_mean) or raw_mean == 0.0:
        return float("nan")
    return abs(residual_mean) / abs(raw_mean)


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    denominator_value = float(denominator)
    if denominator_value <= 0.0:
        return 0.0
    return float(numerator) / denominator_value


def _classification_rank(classification: str) -> int:
    order = {
        "residual_candidate": 0,
        "style_or_industry_exposure_dominated": 1,
        "weak_or_unproven_after_residualization": 2,
        "insufficient_exposure_coverage": 3,
    }
    return order.get(classification, 99)


def _iso_date(value: Any) -> str | None:
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        return None
    return timestamp.date().isoformat()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value in output:
            continue
        output.append(value)
    return output


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
