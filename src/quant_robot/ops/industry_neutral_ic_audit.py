from __future__ import annotations

from collections import Counter
from collections import defaultdict
from datetime import date
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "industry_neutral_ic_audit"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_industry_neutral_ic_audit(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    stock_basic: pd.DataFrame,
    *,
    source_report: str | None = None,
    min_overall_rank_ic: float = 0.02,
    min_neutral_rank_ic: float = 0.01,
    min_rank_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.5,
    min_industry_rank_ic: float = 0.02,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
) -> dict[str, Any]:
    factor_frame = _prepare_factors(factors)
    label_frame = _prepare_labels(labels)
    metadata = _prepare_stock_basic(stock_basic)
    merged = _merge_inputs(factor_frame, label_frame, metadata)
    date_audits = _build_date_audits(
        merged,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
    )
    factor_summary = _build_factor_summary(
        date_audits,
        min_overall_rank_ic=min_overall_rank_ic,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_rank_ic_t_stat=min_rank_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
        min_industry_rank_ic=min_industry_rank_ic,
    )
    audit = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "source_report": source_report,
        "thresholds": {
            "min_overall_rank_ic": min_overall_rank_ic,
            "min_neutral_rank_ic": min_neutral_rank_ic,
            "min_rank_ic_t_stat": min_rank_ic_t_stat,
            "min_neutral_retention": min_neutral_retention,
            "min_industry_rank_ic": min_industry_rank_ic,
            "min_industries": min_industries,
            "min_assets_per_industry": min_assets_per_industry,
        },
        "summary": _summary(merged, date_audits, factor_summary),
        "recommended_next_actions": _recommended_next_actions(factor_summary, merged),
        "factor_summary": factor_summary,
        "date_audits": date_audits,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    audit["markdown"] = render_industry_neutral_ic_markdown(audit)
    return audit


def write_industry_neutral_ic_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "industry_neutral_ic_audit.json").write_text(
        json.dumps(_sanitize(audit), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "industry_neutral_ic_audit.md").write_text(
        render_industry_neutral_ic_markdown(audit),
        encoding="utf-8",
    )
    pd.DataFrame(audit.get("date_audits", [])).to_csv(output_path / "date_audits.csv", index=False)
    pd.DataFrame(audit.get("factor_summary", [])).to_csv(output_path / "factor_summary.csv", index=False)


def render_industry_neutral_ic_markdown(audit: dict[str, Any]) -> str:
    summary = _dict(audit.get("summary"))
    lines = [
        "# Industry-Neutral IC Audit",
        "",
        f"- Stage: {audit.get('stage', STAGE)}",
        f"- Source report: {audit.get('source_report') or 'unknown'}",
        f"- Factors: {summary.get('factors', 0)}",
        f"- Date-factor rows: {summary.get('date_factor_rows', 0)}",
        f"- Industry-neutral signal factors: {summary.get('industry_neutral_signal_factors', 0)}",
        f"- Industry-exposure dominated factors: {summary.get('industry_exposure_dominated_factors', 0)}",
        f"- Weak or unproven factors: {summary.get('weak_or_unproven_signal_factors', 0)}",
        f"- Missing industry rows: {summary.get('missing_industry_rows', 0)}",
        f"- Live boundary allowed: {audit.get('live_boundary_allowed', False)}",
        f"- Safety: {audit.get('safety', SAFETY)}",
        "",
        "## Recommended Next Actions",
        "",
    ]
    actions = _list(audit.get("recommended_next_actions"))
    lines.extend(f"- {action}" for action in actions) if actions else lines.append("- none")
    lines.extend(["", "## Classification Counts", ""])
    classification_counts = _dict(summary.get("classification_counts"))
    if classification_counts:
        for classification, count in sorted(classification_counts.items(), key=lambda item: (-int(item[1]), item[0])):
            lines.append(f"- {classification}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Factor Summary", ""])
    for row in audit.get("factor_summary", []):
        lines.append(
            "- {factor} h{horizon}/lag{lag}: {classification}, dates={dates}, overall_rank_ic={overall:.4f} "
            "(t={overall_t:.2f}), neutral_rank_ic={neutral:.4f} (t={neutral_t:.2f}), "
            "industry_rank_ic={industry:.4f} (t={industry_t:.2f}), retention={retention:.2f}".format(
                factor=row.get("factor_name"),
                horizon=row.get("horizon"),
                lag=row.get("execution_lag"),
                classification=row.get("classification"),
                dates=int(row.get("dates", 0)),
                overall=_number(row.get("mean_overall_rank_ic"), default=float("nan")),
                overall_t=_number(row.get("overall_rank_ic_t_stat"), default=float("nan")),
                neutral=_number(row.get("mean_neutral_rank_ic"), default=float("nan")),
                neutral_t=_number(row.get("neutral_rank_ic_t_stat"), default=float("nan")),
                industry=_number(row.get("mean_industry_rank_ic"), default=float("nan")),
                industry_t=_number(row.get("industry_rank_ic_t_stat"), default=float("nan")),
                retention=_number(row.get("neutral_retention_ratio"), default=float("nan")),
            )
        )
    return "\n".join(lines) + "\n"


def _prepare_factors(factors: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    _require_columns(factors, required, "factors")
    frame = factors[required].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str).str.upper()
    frame["factor_name"] = frame["factor_name"].astype(str)
    frame["factor_value"] = pd.to_numeric(frame["factor_value"], errors="coerce")
    return frame


def _prepare_labels(labels: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "forward_return"]
    _require_columns(labels, required, "labels")
    frame = labels.copy()
    if "horizon" not in frame.columns:
        frame["horizon"] = 0
    if "execution_lag" not in frame.columns:
        frame["execution_lag"] = 0
    columns = required + ["horizon", "execution_lag"]
    frame = frame[columns].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str).str.upper()
    frame["forward_return"] = pd.to_numeric(frame["forward_return"], errors="coerce")
    frame["horizon"] = pd.to_numeric(frame["horizon"], errors="coerce").fillna(0).astype(int)
    frame["execution_lag"] = pd.to_numeric(frame["execution_lag"], errors="coerce").fillna(0).astype(int)
    return frame


def _prepare_stock_basic(stock_basic: pd.DataFrame) -> pd.DataFrame:
    frame = stock_basic.copy()
    if "asset_id" not in frame.columns and "ts_code" in frame.columns:
        frame["asset_id"] = frame["ts_code"]
    _require_columns(frame, ["asset_id", "industry"], "stock_basic")
    frame = frame[["asset_id", "industry"]].copy()
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["industry"] = frame["industry"].map(_clean_industry)
    return frame.drop_duplicates(subset=["asset_id"], keep="last").reset_index(drop=True)


def _merge_inputs(factors: pd.DataFrame, labels: pd.DataFrame, stock_basic: pd.DataFrame) -> pd.DataFrame:
    merged = factors.merge(labels, on=["date", "asset_id", "market"], how="inner")
    merged = merged.merge(stock_basic, on="asset_id", how="left")
    return merged.reset_index(drop=True)


def _build_date_audits(
    merged: pd.DataFrame,
    *,
    min_industries: int,
    min_assets_per_industry: int,
) -> list[dict[str, Any]]:
    rows = []
    group_keys = ["date", "market", "factor_name", "horizon", "execution_lag"]
    for key, group in merged.groupby(group_keys, sort=True):
        date_value, market, factor_name, horizon, execution_lag = key
        valid = group.dropna(subset=["factor_value", "forward_return"]).copy()
        overall = _rank_corr_stats(valid["factor_value"], valid["forward_return"])
        industry_valid = valid[valid["industry"].notna() & (valid["industry"].astype(str).str.strip() != "")].copy()
        missing_industry_rows = len(valid) - len(industry_valid)
        eligible = _eligible_industry_rows(
            industry_valid,
            min_industries=min_industries,
            min_assets_per_industry=min_assets_per_industry,
        )
        neutral = _within_industry_rank_ic(eligible, min_industries=min_industries)
        industry = _industry_mean_rank_ic(eligible, min_industries=min_industries)
        rows.append(
            {
                "date": date_value,
                "market": market,
                "factor_name": factor_name,
                "horizon": int(horizon),
                "execution_lag": int(execution_lag),
                "observations": int(len(valid)),
                "industry_observations": int(len(industry_valid)),
                "eligible_observations": int(len(eligible)),
                "industries": int(industry_valid["industry"].nunique()) if not industry_valid.empty else 0,
                "eligible_industries": int(eligible["industry"].nunique()) if not eligible.empty else 0,
                "missing_industry_rows": int(missing_industry_rows),
                "overall_rank_ic": overall["correlation"],
                "overall_rank_ic_t_stat": overall["t_stat"],
                "overall_rank_ic_p_value": overall["p_value"],
                "neutral_rank_ic": neutral["correlation"],
                "neutral_rank_ic_t_stat": neutral["t_stat"],
                "neutral_rank_ic_p_value": neutral["p_value"],
                "industry_rank_ic": industry["correlation"],
                "industry_rank_ic_t_stat": industry["t_stat"],
                "industry_rank_ic_p_value": industry["p_value"],
            }
        )
    return rows


def _eligible_industry_rows(
    frame: pd.DataFrame,
    *,
    min_industries: int,
    min_assets_per_industry: int,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    counts = frame.groupby("industry")["asset_id"].nunique()
    eligible_industries = set(counts[counts >= min_assets_per_industry].index)
    eligible = frame[frame["industry"].isin(eligible_industries)].copy()
    if eligible["industry"].nunique() < min_industries:
        return eligible.iloc[0:0].copy()
    return eligible


def _within_industry_rank_ic(frame: pd.DataFrame, *, min_industries: int) -> dict[str, float]:
    if frame.empty or frame["industry"].nunique() < min_industries:
        return _empty_stats()
    working = frame.copy()
    working["factor_rank_within_industry"] = working.groupby("industry")["factor_value"].rank(pct=True)
    working["return_rank_within_industry"] = working.groupby("industry")["forward_return"].rank(pct=True)
    return _corr_stats(working["factor_rank_within_industry"], working["return_rank_within_industry"])


def _industry_mean_rank_ic(frame: pd.DataFrame, *, min_industries: int) -> dict[str, float]:
    if frame.empty or frame["industry"].nunique() < min_industries:
        return _empty_stats()
    means = (
        frame.groupby("industry", as_index=False)
        .agg(factor_value=("factor_value", "mean"), forward_return=("forward_return", "mean"))
        .dropna(subset=["factor_value", "forward_return"])
    )
    if len(means) < min_industries:
        return _empty_stats()
    return _rank_corr_stats(means["factor_value"], means["forward_return"])


def _build_factor_summary(
    date_audits: list[dict[str, Any]],
    *,
    min_overall_rank_ic: float,
    min_neutral_rank_ic: float,
    min_rank_ic_t_stat: float,
    min_neutral_retention: float,
    min_industry_rank_ic: float,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in date_audits:
        grouped[
            (
                str(row.get("market")),
                str(row.get("factor_name")),
                int(row.get("horizon", 0)),
                int(row.get("execution_lag", 0)),
            )
        ].append(row)

    result = []
    for (market, factor_name, horizon, execution_lag), rows in grouped.items():
        overall = _finite_values(row.get("overall_rank_ic") for row in rows)
        neutral = _finite_values(row.get("neutral_rank_ic") for row in rows)
        industry = _finite_values(row.get("industry_rank_ic") for row in rows)
        mean_overall = _mean_or_zero(overall)
        mean_neutral = _mean_or_zero(neutral)
        mean_industry = _mean_or_zero(industry)
        overall_t = _stat_or_zero(_mean_t_stat(overall))
        neutral_t = _stat_or_zero(_mean_t_stat(neutral))
        industry_t = _stat_or_zero(_mean_t_stat(industry))
        retention = _retention_ratio(mean_neutral, mean_overall)
        classification = _classify_factor(
            mean_overall=mean_overall,
            overall_t=overall_t,
            mean_neutral=mean_neutral,
            neutral_t=neutral_t,
            retention=retention,
            mean_industry=mean_industry,
            industry_t=industry_t,
            min_overall_rank_ic=min_overall_rank_ic,
            min_neutral_rank_ic=min_neutral_rank_ic,
            min_rank_ic_t_stat=min_rank_ic_t_stat,
            min_neutral_retention=min_neutral_retention,
            min_industry_rank_ic=min_industry_rank_ic,
        )
        result.append(
            {
                "market": market,
                "factor_name": factor_name,
                "horizon": int(horizon),
                "execution_lag": int(execution_lag),
                "classification": classification,
                "dates": len(rows),
                "overall_valid_dates": len(overall),
                "neutral_valid_dates": len(neutral),
                "industry_valid_dates": len(industry),
                "mean_overall_rank_ic": mean_overall,
                "overall_rank_ic_t_stat": overall_t,
                "overall_rank_ic_p_value": _normal_two_sided_p_value(overall_t),
                "mean_neutral_rank_ic": mean_neutral,
                "neutral_rank_ic_t_stat": neutral_t,
                "neutral_rank_ic_p_value": _normal_two_sided_p_value(neutral_t),
                "mean_industry_rank_ic": mean_industry,
                "industry_rank_ic_t_stat": industry_t,
                "industry_rank_ic_p_value": _normal_two_sided_p_value(industry_t),
                "neutral_retention_ratio": retention,
                "mean_observations": _mean(_finite_values(row.get("observations") for row in rows)),
                "mean_eligible_observations": _mean(_finite_values(row.get("eligible_observations") for row in rows)),
                "mean_eligible_industries": _mean(_finite_values(row.get("eligible_industries") for row in rows)),
                "missing_industry_rows": sum(int(_number(row.get("missing_industry_rows"))) for row in rows),
            }
        )
    return sorted(
        result,
        key=lambda row: (
            _classification_rank(str(row["classification"])),
            -abs(_number(row.get("overall_rank_ic_t_stat"))),
            str(row["factor_name"]),
        ),
    )


def _classify_factor(
    *,
    mean_overall: float,
    overall_t: float,
    mean_neutral: float,
    neutral_t: float,
    retention: float,
    mean_industry: float,
    industry_t: float,
    min_overall_rank_ic: float,
    min_neutral_rank_ic: float,
    min_rank_ic_t_stat: float,
    min_neutral_retention: float,
    min_industry_rank_ic: float,
) -> str:
    overall_strong = _abs_ge(mean_overall, min_overall_rank_ic) and _abs_ge(overall_t, min_rank_ic_t_stat)
    neutral_strong = _abs_ge(mean_neutral, min_neutral_rank_ic) and _abs_ge(neutral_t, min_rank_ic_t_stat)
    industry_strong = _abs_ge(mean_industry, min_industry_rank_ic) and _abs_ge(industry_t, min_rank_ic_t_stat)
    retention_ok = math.isfinite(retention) and retention >= min_neutral_retention
    if neutral_strong and (retention_ok or not overall_strong):
        return "industry_neutral_signal"
    if overall_strong and industry_strong and (not neutral_strong or not retention_ok):
        return "industry_exposure_dominated"
    if overall_strong:
        return "industry_mix_or_translation_unknown"
    return "weak_or_unproven_signal"


def _summary(
    merged: pd.DataFrame,
    date_audits: list[dict[str, Any]],
    factor_summary: list[dict[str, Any]],
) -> dict[str, Any]:
    classifications = Counter(str(row.get("classification")) for row in factor_summary)
    return {
        "input_rows": int(len(merged)),
        "date_factor_rows": len(date_audits),
        "factors": len(factor_summary),
        "factor_names": len({str(row.get("factor_name")) for row in factor_summary}),
        "industry_neutral_signal_factors": classifications.get("industry_neutral_signal", 0),
        "industry_exposure_dominated_factors": classifications.get("industry_exposure_dominated", 0),
        "industry_mix_or_translation_unknown_factors": classifications.get("industry_mix_or_translation_unknown", 0),
        "weak_or_unproven_signal_factors": classifications.get("weak_or_unproven_signal", 0),
        "missing_industry_rows": int(sum(int(_number(row.get("missing_industry_rows"))) for row in date_audits)),
        "classification_counts": dict(sorted(classifications.items())),
    }


def _recommended_next_actions(factor_summary: list[dict[str, Any]], merged: pd.DataFrame) -> list[str]:
    actions: list[str] = []
    classifications = {str(row.get("classification")) for row in factor_summary}
    if "industry_exposure_dominated" in classifications:
        actions.extend(
            [
                "stock_to_etf_or_industry_breadth_bridge",
                "industry_neutral_sort_before_portfolio_test",
                "stop_raw_topn_parameter_sweeps",
            ]
        )
    if "industry_neutral_signal" in classifications:
        actions.append("run_industry_neutral_portfolio_backtest")
    if not classifications or classifications == {"weak_or_unproven_signal"}:
        actions.append("rotate_factor_family_with_public_hypothesis")
    if _missing_industry_fraction(merged) > 0.02:
        actions.append("repair_industry_metadata_coverage")
    return _dedupe(actions)


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
    p_value = _normal_two_sided_p_value(t_stat)
    return t_stat, p_value


def _mean_t_stat(values: list[float]) -> float:
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


def _empty_stats() -> dict[str, float]:
    return {"correlation": float("nan"), "t_stat": float("nan"), "p_value": float("nan")}


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} missing required columns: {', '.join(missing)}")


def _clean_industry(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text or None


def _finite_values(values: Any) -> list[float]:
    result = []
    for value in values:
        number = _number(value, default=float("nan"))
        if math.isfinite(number):
            result.append(number)
    return result


def _mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return float("nan")
    return float(pd.Series(finite, dtype="float64").mean())


def _mean_or_zero(values: list[float]) -> float:
    mean = _mean(values)
    return mean if math.isfinite(mean) else 0.0


def _stat_or_zero(value: float) -> float:
    return value if math.isfinite(value) else 0.0


def _retention_ratio(mean_neutral: float, mean_overall: float) -> float:
    if not math.isfinite(mean_neutral) or not math.isfinite(mean_overall) or mean_overall == 0.0:
        return float("nan")
    return abs(mean_neutral) / abs(mean_overall)


def _abs_ge(value: float, threshold: float) -> bool:
    return math.isfinite(value) and abs(value) >= threshold


def _classification_rank(classification: str) -> int:
    order = {
        "industry_neutral_signal": 0,
        "industry_exposure_dominated": 1,
        "industry_mix_or_translation_unknown": 2,
        "weak_or_unproven_signal": 3,
    }
    return order.get(classification, 99)


def _missing_industry_fraction(merged: pd.DataFrame) -> float:
    if merged.empty or "industry" not in merged:
        return 0.0
    missing = merged["industry"].isna() | (merged["industry"].astype(str).str.strip() == "")
    return float(missing.mean())


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
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


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
