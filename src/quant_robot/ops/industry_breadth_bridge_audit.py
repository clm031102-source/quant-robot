from __future__ import annotations

from collections import Counter
from collections import defaultdict
from datetime import date
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "industry_breadth_bridge_audit"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_industry_breadth_bridge_audit(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    stock_basic: pd.DataFrame,
    *,
    source_report: str | None = None,
    rebalance_interval: int = 1,
    top_industries: int = 3,
    min_assets_per_industry: int = 5,
    min_industries_per_date: int = 5,
    top_stock_quantile: float = 0.8,
    bottom_stock_quantile: float = 0.2,
    min_dates: int = 20,
    min_mean_excess_return: float = 0.0,
    min_excess_t_stat: float = 2.0,
    min_positive_excess_rate: float = 0.55,
    min_industry_rank_ic: float = 0.02,
    min_rank_ic_t_stat: float = 2.0,
) -> dict[str, Any]:
    if rebalance_interval < 1:
        raise ValueError("rebalance_interval must be at least 1")
    if top_industries < 1:
        raise ValueError("top_industries must be positive")
    if min_assets_per_industry < 1:
        raise ValueError("min_assets_per_industry must be positive")
    if min_industries_per_date < 2:
        raise ValueError("min_industries_per_date must be at least 2")
    if not 0.0 < bottom_stock_quantile < top_stock_quantile < 1.0:
        raise ValueError("stock quantile thresholds must satisfy 0 < bottom < top < 1")

    factor_frame = _filter_rebalance_dates(_prepare_factors(factors), rebalance_interval)
    label_frame = _prepare_labels(labels)
    stock_basic_frame = _prepare_stock_basic(stock_basic)
    merged = _merge_inputs(factor_frame, label_frame, stock_basic_frame)
    date_audits = _build_date_audits(
        merged,
        top_industries=top_industries,
        min_assets_per_industry=min_assets_per_industry,
        min_industries_per_date=min_industries_per_date,
        top_stock_quantile=top_stock_quantile,
        bottom_stock_quantile=bottom_stock_quantile,
    )
    factor_summary = _build_factor_summary(
        date_audits,
        min_dates=min_dates,
        min_mean_excess_return=min_mean_excess_return,
        min_excess_t_stat=min_excess_t_stat,
        min_positive_excess_rate=min_positive_excess_rate,
        min_industry_rank_ic=min_industry_rank_ic,
        min_rank_ic_t_stat=min_rank_ic_t_stat,
    )
    audit = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "source_report": source_report,
        "thresholds": {
            "rebalance_interval": rebalance_interval,
            "top_industries": top_industries,
            "min_assets_per_industry": min_assets_per_industry,
            "min_industries_per_date": min_industries_per_date,
            "top_stock_quantile": top_stock_quantile,
            "bottom_stock_quantile": bottom_stock_quantile,
            "min_dates": min_dates,
            "min_mean_excess_return": min_mean_excess_return,
            "min_excess_t_stat": min_excess_t_stat,
            "min_positive_excess_rate": min_positive_excess_rate,
            "min_industry_rank_ic": min_industry_rank_ic,
            "min_rank_ic_t_stat": min_rank_ic_t_stat,
        },
        "summary": _summary(merged, date_audits, factor_summary),
        "recommended_next_actions": _recommended_next_actions(factor_summary),
        "factor_summary": factor_summary,
        "date_audits": date_audits,
        "diagnostic_only": True,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    audit["markdown"] = render_industry_breadth_bridge_markdown(audit)
    return audit


def write_industry_breadth_bridge_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "industry_breadth_bridge_audit.json").write_text(
        json.dumps(_sanitize(audit), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "industry_breadth_bridge_audit.md").write_text(
        render_industry_breadth_bridge_markdown(audit),
        encoding="utf-8",
    )
    pd.DataFrame(audit.get("date_audits", [])).to_csv(output_path / "date_audits.csv", index=False)
    pd.DataFrame(audit.get("factor_summary", [])).to_csv(output_path / "factor_summary.csv", index=False)


def render_industry_breadth_bridge_markdown(audit: dict[str, Any]) -> str:
    summary = _dict(audit.get("summary"))
    thresholds = _dict(audit.get("thresholds"))
    lines = [
        "# Industry-Breadth Bridge Audit",
        "",
        f"- Stage: {audit.get('stage', STAGE)}",
        f"- Source report: {audit.get('source_report') or 'unknown'}",
        f"- Rebalance interval: {int(_number(thresholds.get('rebalance_interval'), default=1))}",
        f"- Top industries: {int(_number(thresholds.get('top_industries'), default=3))}",
        f"- Factors: {summary.get('factors', 0)}",
        f"- Date-factor rows: {summary.get('date_factor_rows', 0)}",
        f"- Bridge candidates: {summary.get('industry_breadth_bridge_candidate_factors', 0)}",
        f"- Ranking-only signals: {summary.get('ranking_signal_without_portfolio_edge_factors', 0)}",
        f"- Weak or unproven bridge factors: {summary.get('weak_or_unproven_bridge_factors', 0)}",
        f"- Diagnostic only: {audit.get('diagnostic_only', True)}",
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
            "- {factor} h{horizon}/lag{lag}: {classification}, dates={dates}, "
            "industry_rank_ic={rank_ic:.4f} (t={rank_ic_t:.2f}), "
            "top_excess={excess:.4f} (t={excess_t:.2f}), positive_rate={positive:.2f}, "
            "top_bottom_spread={spread:.4f}, top_compounded={top_compounded:.4f}, all_compounded={all_compounded:.4f}".format(
                factor=row.get("factor_name"),
                horizon=row.get("horizon"),
                lag=row.get("execution_lag"),
                classification=row.get("classification"),
                dates=int(row.get("dates", 0)),
                rank_ic=_number(row.get("mean_industry_rank_ic")),
                rank_ic_t=_number(row.get("industry_rank_ic_t_stat")),
                excess=_number(row.get("mean_top_industry_excess_return")),
                excess_t=_number(row.get("top_industry_excess_t_stat")),
                positive=_number(row.get("positive_excess_rate")),
                spread=_number(row.get("mean_top_bottom_industry_spread")),
                top_compounded=_number(row.get("compounded_top_industry_return")),
                all_compounded=_number(row.get("compounded_all_industry_return")),
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
    frame = frame[required + ["horizon", "execution_lag"]].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str).str.upper()
    frame["forward_return"] = pd.to_numeric(frame["forward_return"], errors="coerce")
    frame["horizon"] = pd.to_numeric(frame["horizon"], errors="coerce").fillna(0).astype(int)
    frame["execution_lag"] = pd.to_numeric(frame["execution_lag"], errors="coerce").fillna(0).astype(int)
    return frame


def _prepare_stock_basic(stock_basic: pd.DataFrame) -> pd.DataFrame:
    _require_columns(stock_basic, ["asset_id", "industry"], "stock_basic")
    frame = stock_basic[["asset_id", "industry"]].copy()
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["industry"] = frame["industry"].map(_clean_industry)
    return frame.dropna(subset=["industry"]).drop_duplicates("asset_id", keep="last")


def _merge_inputs(factors: pd.DataFrame, labels: pd.DataFrame, stock_basic: pd.DataFrame) -> pd.DataFrame:
    merged = factors.merge(labels, on=["date", "asset_id", "market"], how="inner")
    return merged.merge(stock_basic, on="asset_id", how="left").reset_index(drop=True)


def _filter_rebalance_dates(factors: pd.DataFrame, rebalance_interval: int) -> pd.DataFrame:
    if rebalance_interval <= 1 or factors.empty:
        return factors.reset_index(drop=True)
    rows = []
    for _, group in factors.groupby(["market", "factor_name"], sort=True):
        signal_dates = sorted(pd.to_datetime(group["date"]).dt.date.unique())
        keep_dates = set(signal_dates[::rebalance_interval])
        rows.append(group[pd.to_datetime(group["date"]).dt.date.isin(keep_dates)])
    if not rows:
        return factors.iloc[0:0].copy()
    return pd.concat(rows, ignore_index=True).reset_index(drop=True)


def _build_date_audits(
    merged: pd.DataFrame,
    *,
    top_industries: int,
    min_assets_per_industry: int,
    min_industries_per_date: int,
    top_stock_quantile: float,
    bottom_stock_quantile: float,
) -> list[dict[str, Any]]:
    rows = []
    group_keys = ["date", "market", "factor_name", "horizon", "execution_lag"]
    for key, group in merged.groupby(group_keys, sort=True):
        date_value, market, factor_name, horizon, execution_lag = key
        valid = group.dropna(subset=["factor_value", "forward_return", "industry"]).copy()
        industry_frame = _industry_frame(
            valid,
            min_assets_per_industry=min_assets_per_industry,
            top_stock_quantile=top_stock_quantile,
            bottom_stock_quantile=bottom_stock_quantile,
        )
        industry_count = len(industry_frame)
        eligible = industry_count >= min_industries_per_date
        if eligible:
            ranked = industry_frame.sort_values(["breadth_score", "industry"], ascending=[False, True])
            selected_count = min(top_industries, max(1, industry_count - 1))
            top = ranked.head(selected_count)
            bottom = ranked.tail(selected_count)
            industry_rank_ic = _rank_corr(ranked["breadth_score"], ranked["industry_forward_return"])
            top_return = _mean_or_nan(top["industry_forward_return"])
            all_return = _mean_or_nan(ranked["industry_forward_return"])
            bottom_return = _mean_or_nan(bottom["industry_forward_return"])
            excess = top_return - all_return if math.isfinite(top_return) and math.isfinite(all_return) else float("nan")
            spread = top_return - bottom_return if math.isfinite(top_return) and math.isfinite(bottom_return) else float("nan")
        else:
            top_return = all_return = bottom_return = excess = spread = industry_rank_ic = float("nan")
        rows.append(
            {
                "date": date_value,
                "market": market,
                "factor_name": factor_name,
                "horizon": int(horizon),
                "execution_lag": int(execution_lag),
                "stock_observations": int(len(valid)),
                "industry_count": int(industry_count),
                "eligible": bool(eligible),
                "mean_assets_per_industry": _mean_or_zero(industry_frame["asset_count"].tolist()) if industry_count else 0.0,
                "industry_rank_ic": industry_rank_ic,
                "top_industry_return": top_return,
                "all_industry_return": all_return,
                "bottom_industry_return": bottom_return,
                "top_industry_excess_return": excess,
                "top_bottom_industry_spread": spread,
            }
        )
    return rows


def _industry_frame(
    frame: pd.DataFrame,
    *,
    min_assets_per_industry: int,
    top_stock_quantile: float,
    bottom_stock_quantile: float,
) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "industry",
                "asset_count",
                "mean_factor_rank",
                "top_stock_share",
                "bottom_stock_share",
                "breadth_score",
                "industry_forward_return",
            ]
        )
    work = frame.copy()
    work["factor_rank"] = work["factor_value"].rank(method="average", pct=True)
    grouped = work.groupby("industry", sort=True)
    result = grouped.agg(
        asset_count=("asset_id", "nunique"),
        mean_factor_rank=("factor_rank", "mean"),
        top_stock_share=("factor_rank", lambda values: float((values >= top_stock_quantile).mean())),
        bottom_stock_share=("factor_rank", lambda values: float((values <= bottom_stock_quantile).mean())),
        industry_forward_return=("forward_return", "mean"),
    ).reset_index()
    result = result[result["asset_count"] >= min_assets_per_industry].copy()
    result["breadth_score"] = (
        pd.to_numeric(result["mean_factor_rank"], errors="coerce")
        + pd.to_numeric(result["top_stock_share"], errors="coerce")
        - pd.to_numeric(result["bottom_stock_share"], errors="coerce")
    )
    return result


def _build_factor_summary(
    date_audits: list[dict[str, Any]],
    *,
    min_dates: int,
    min_mean_excess_return: float,
    min_excess_t_stat: float,
    min_positive_excess_rate: float,
    min_industry_rank_ic: float,
    min_rank_ic_t_stat: float,
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
        eligible_rows = [row for row in rows if row.get("eligible")]
        excess_returns = _finite_values(row.get("top_industry_excess_return") for row in eligible_rows)
        top_returns = _finite_values(row.get("top_industry_return") for row in eligible_rows)
        all_returns = _finite_values(row.get("all_industry_return") for row in eligible_rows)
        bottom_returns = _finite_values(row.get("bottom_industry_return") for row in eligible_rows)
        spreads = _finite_values(row.get("top_bottom_industry_spread") for row in eligible_rows)
        rank_ics = _finite_values(row.get("industry_rank_ic") for row in eligible_rows)
        excess_t = _stat_or_zero(_mean_t_stat(excess_returns))
        rank_ic_t = _stat_or_zero(_mean_t_stat(rank_ics))
        positive_rate = (
            float(sum(1 for value in excess_returns if value > 0.0) / len(excess_returns))
            if excess_returns
            else 0.0
        )
        classification = _classify_factor(
            dates=len(eligible_rows),
            mean_excess=_mean_or_zero(excess_returns),
            excess_t=excess_t,
            positive_rate=positive_rate,
            mean_rank_ic=_mean_or_zero(rank_ics),
            rank_ic_t=rank_ic_t,
            min_dates=min_dates,
            min_mean_excess_return=min_mean_excess_return,
            min_excess_t_stat=min_excess_t_stat,
            min_positive_excess_rate=min_positive_excess_rate,
            min_industry_rank_ic=min_industry_rank_ic,
            min_rank_ic_t_stat=min_rank_ic_t_stat,
        )
        result.append(
            {
                "market": market,
                "factor_name": factor_name,
                "horizon": int(horizon),
                "execution_lag": int(execution_lag),
                "classification": classification,
                "dates": len(eligible_rows),
                "raw_dates": len(rows),
                "mean_stock_observations": _mean(_finite_values(row.get("stock_observations") for row in rows)),
                "mean_industry_count": _mean(_finite_values(row.get("industry_count") for row in rows)),
                "mean_assets_per_industry": _mean(_finite_values(row.get("mean_assets_per_industry") for row in rows)),
                "mean_industry_rank_ic": _mean_or_zero(rank_ics),
                "industry_rank_ic_t_stat": rank_ic_t,
                "industry_rank_ic_p_value": _normal_two_sided_p_value(rank_ic_t),
                "mean_top_industry_return": _mean_or_zero(top_returns),
                "mean_all_industry_return": _mean_or_zero(all_returns),
                "mean_bottom_industry_return": _mean_or_zero(bottom_returns),
                "mean_top_industry_excess_return": _mean_or_zero(excess_returns),
                "top_industry_excess_t_stat": excess_t,
                "top_industry_excess_p_value": _normal_two_sided_p_value(excess_t),
                "positive_excess_rate": positive_rate,
                "mean_top_bottom_industry_spread": _mean_or_zero(spreads),
                "compounded_top_industry_return": _compounded_return(top_returns),
                "compounded_all_industry_return": _compounded_return(all_returns),
                "compounded_bottom_industry_return": _compounded_return(bottom_returns),
            }
        )
    return sorted(
        result,
        key=lambda row: (
            _classification_rank(str(row.get("classification"))),
            -_number(row.get("top_industry_excess_t_stat")),
            -_number(row.get("mean_top_industry_excess_return")),
            str(row.get("factor_name")),
        ),
    )


def _classify_factor(
    *,
    dates: int,
    mean_excess: float,
    excess_t: float,
    positive_rate: float,
    mean_rank_ic: float,
    rank_ic_t: float,
    min_dates: int,
    min_mean_excess_return: float,
    min_excess_t_stat: float,
    min_positive_excess_rate: float,
    min_industry_rank_ic: float,
    min_rank_ic_t_stat: float,
) -> str:
    rank_ok = (
        dates >= min_dates
        and mean_rank_ic >= min_industry_rank_ic
        and rank_ic_t >= min_rank_ic_t_stat
    )
    excess_ok = (
        mean_excess > min_mean_excess_return
        and excess_t >= min_excess_t_stat
        and positive_rate >= min_positive_excess_rate
    )
    if rank_ok and excess_ok:
        return "industry_breadth_bridge_candidate"
    if rank_ok:
        return "ranking_signal_without_portfolio_edge"
    return "weak_or_unproven_bridge"


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
        "industry_breadth_bridge_candidate_factors": classifications.get("industry_breadth_bridge_candidate", 0),
        "ranking_signal_without_portfolio_edge_factors": classifications.get("ranking_signal_without_portfolio_edge", 0),
        "weak_or_unproven_bridge_factors": classifications.get("weak_or_unproven_bridge", 0),
        "classification_counts": dict(sorted(classifications.items())),
    }


def _recommended_next_actions(factor_summary: list[dict[str, Any]]) -> list[str]:
    classifications = {str(row.get("classification")) for row in factor_summary}
    actions: list[str] = []
    if "industry_breadth_bridge_candidate" in classifications:
        actions.append("map_industry_signal_to_liquid_etf_or_theme_universe")
        actions.append("test_costed_industry_or_etf_rotation_before_promotion")
    if "ranking_signal_without_portfolio_edge" in classifications:
        actions.append("use_as_regime_or_risk_state_not_standalone_alpha")
    if not classifications or classifications == {"weak_or_unproven_bridge"}:
        actions.append("rotate_factor_family_with_public_hypothesis")
    actions.append("do_not_promote_without_costed_walk_forward_and_multiple_testing_review")
    return _dedupe(actions)


def _rank_corr(left: pd.Series, right: pd.Series) -> float:
    valid = pd.DataFrame({"left": left, "right": right}).dropna()
    if len(valid) < 2:
        return float("nan")
    return float(valid["left"].rank(pct=True).corr(valid["right"].rank(pct=True)))


def _mean_t_stat(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if len(finite) < 2:
        return 0.0
    mean = sum(finite) / len(finite)
    variance = sum((value - mean) ** 2 for value in finite) / (len(finite) - 1)
    if variance == 0.0:
        if mean > 0.0:
            return float("inf")
        if mean < 0.0:
            return float("-inf")
        return 0.0
    return mean / math.sqrt(variance / len(finite))


def _normal_two_sided_p_value(t_stat: float) -> float:
    if not math.isfinite(t_stat):
        return 0.0 if abs(t_stat) == float("inf") else 1.0
    return math.erfc(abs(t_stat) / math.sqrt(2.0))


def _compounded_return(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return 0.0
    compounded = 1.0
    for value in finite:
        compounded *= 1.0 + value
    return compounded - 1.0


def _mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return float("nan")
    return sum(finite) / len(finite)


def _mean_or_nan(values: pd.Series) -> float:
    finite = _finite_values(values)
    return _mean(finite)


def _mean_or_zero(values: list[float]) -> float:
    value = _mean(values)
    return value if math.isfinite(value) else 0.0


def _finite_values(values: Any) -> list[float]:
    result = []
    for value in values:
        number = _number(value, default=float("nan"))
        if math.isfinite(number):
            result.append(number)
    return result


def _number(value: Any, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _stat_or_zero(value: float) -> float:
    if value == float("inf"):
        return 1_000_000.0
    if value == float("-inf"):
        return -1_000_000.0
    return value if math.isfinite(value) else 0.0


def _clean_industry(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def _classification_rank(classification: str) -> int:
    return {
        "industry_breadth_bridge_candidate": 0,
        "ranking_signal_without_portfolio_edge": 1,
        "weak_or_unproven_bridge": 2,
    }.get(classification, 99)


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} are missing columns: {', '.join(missing)}")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return 1_000_000.0 if value > 0 else -1_000_000.0
    return value
