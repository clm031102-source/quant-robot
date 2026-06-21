from __future__ import annotations

from collections import Counter
from collections import defaultdict
from datetime import date
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "bottom_exclusion_overlay_audit"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_bottom_exclusion_overlay_audit(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    source_report: str | None = None,
    bottom_quantile: float = 0.2,
    rebalance_interval: int = 1,
    min_dates: int = 5,
    min_overlay_t_stat: float = 2.0,
    min_positive_overlay_rate: float = 0.55,
    min_mean_overlay_excess_return: float = 0.0,
) -> dict[str, Any]:
    if bottom_quantile <= 0.0 or bottom_quantile >= 1.0:
        raise ValueError("bottom_quantile must be greater than 0 and less than 1")
    if rebalance_interval < 1:
        raise ValueError("rebalance_interval must be at least 1")
    if min_dates < 1:
        raise ValueError("min_dates must be positive")

    factor_frame = _prepare_factors(factors)
    factor_frame = _filter_rebalance_dates(factor_frame, rebalance_interval)
    label_frame = _prepare_labels(labels)
    merged = _merge_inputs(factor_frame, label_frame)
    date_audits = _build_date_audits(merged, bottom_quantile=bottom_quantile)
    factor_summary = _build_factor_summary(
        date_audits,
        min_dates=min_dates,
        min_overlay_t_stat=min_overlay_t_stat,
        min_positive_overlay_rate=min_positive_overlay_rate,
        min_mean_overlay_excess_return=min_mean_overlay_excess_return,
    )
    audit = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "source_report": source_report,
        "thresholds": {
            "bottom_quantile": bottom_quantile,
            "rebalance_interval": rebalance_interval,
            "min_dates": min_dates,
            "min_overlay_t_stat": min_overlay_t_stat,
            "min_positive_overlay_rate": min_positive_overlay_rate,
            "min_mean_overlay_excess_return": min_mean_overlay_excess_return,
        },
        "summary": _summary(merged, date_audits, factor_summary),
        "recommended_next_actions": _recommended_next_actions(factor_summary),
        "factor_summary": factor_summary,
        "date_audits": date_audits,
        "diagnostic_only": True,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    audit["markdown"] = render_bottom_exclusion_overlay_markdown(audit)
    return audit


def write_bottom_exclusion_overlay_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "bottom_exclusion_overlay_audit.json").write_text(
        json.dumps(_sanitize(audit), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "bottom_exclusion_overlay_audit.md").write_text(
        render_bottom_exclusion_overlay_markdown(audit),
        encoding="utf-8",
    )
    pd.DataFrame(audit.get("date_audits", [])).to_csv(output_path / "date_audits.csv", index=False)
    pd.DataFrame(audit.get("factor_summary", [])).to_csv(output_path / "factor_summary.csv", index=False)


def render_bottom_exclusion_overlay_markdown(audit: dict[str, Any]) -> str:
    summary = _dict(audit.get("summary"))
    thresholds = _dict(audit.get("thresholds"))
    lines = [
        "# Bottom-Exclusion Overlay Audit",
        "",
        f"- Stage: {audit.get('stage', STAGE)}",
        f"- Source report: {audit.get('source_report') or 'unknown'}",
        f"- Bottom quantile: {_number(thresholds.get('bottom_quantile')):.2f}",
        f"- Factors: {summary.get('factors', 0)}",
        f"- Date-factor rows: {summary.get('date_factor_rows', 0)}",
        f"- Bottom-exclusion candidate factors: {summary.get('bottom_exclusion_candidate_factors', 0)}",
        f"- Weak or unproven exclusion factors: {summary.get('weak_or_unproven_exclusion_factors', 0)}",
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
            "full={full:.4f}, kept={kept:.4f}, bottom={bottom:.4f}, "
            "overlay={overlay:.4f} (t={t_stat:.2f}), positive_rate={positive:.2f}, "
            "kept_compounded={kept_compounded:.4f}, full_compounded={full_compounded:.4f}".format(
                factor=row.get("factor_name"),
                horizon=row.get("horizon"),
                lag=row.get("execution_lag"),
                classification=row.get("classification"),
                dates=int(row.get("dates", 0)),
                full=_number(row.get("mean_full_return")),
                kept=_number(row.get("mean_kept_return")),
                bottom=_number(row.get("mean_bottom_return")),
                overlay=_number(row.get("mean_overlay_excess_return")),
                t_stat=_number(row.get("overlay_t_stat")),
                positive=_number(row.get("positive_overlay_rate")),
                kept_compounded=_number(row.get("compounded_kept_return")),
                full_compounded=_number(row.get("compounded_full_return")),
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


def _merge_inputs(factors: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    return factors.merge(labels, on=["date", "asset_id", "market"], how="inner").reset_index(drop=True)


def _filter_rebalance_dates(factors: pd.DataFrame, rebalance_interval: int) -> pd.DataFrame:
    if rebalance_interval <= 1 or factors.empty:
        return factors.reset_index(drop=True)
    rows = []
    group_keys = ["market", "factor_name"]
    for _, group in factors.groupby(group_keys, sort=True):
        signal_dates = sorted(pd.to_datetime(group["date"]).dt.date.unique())
        keep_dates = set(signal_dates[::rebalance_interval])
        rows.append(group[pd.to_datetime(group["date"]).dt.date.isin(keep_dates)])
    if not rows:
        return factors.iloc[0:0].copy()
    return pd.concat(rows, ignore_index=True).reset_index(drop=True)


def _build_date_audits(merged: pd.DataFrame, *, bottom_quantile: float) -> list[dict[str, Any]]:
    rows = []
    group_keys = ["date", "market", "factor_name", "horizon", "execution_lag"]
    for key, group in merged.groupby(group_keys, sort=True):
        date_value, market, factor_name, horizon, execution_lag = key
        valid = group.dropna(subset=["factor_value", "forward_return"]).copy()
        bucket = _bottom_and_kept(valid, bottom_quantile=bottom_quantile)
        bottom = bucket["bottom"]
        kept = bucket["kept"]
        full_return = _mean_or_nan(valid["forward_return"])
        kept_return = _mean_or_nan(kept["forward_return"])
        bottom_return = _mean_or_nan(bottom["forward_return"])
        overlay_excess = kept_return - full_return if math.isfinite(kept_return) and math.isfinite(full_return) else float("nan")
        bottom_drag = full_return - bottom_return if math.isfinite(full_return) and math.isfinite(bottom_return) else float("nan")
        rows.append(
            {
                "date": date_value,
                "market": market,
                "factor_name": factor_name,
                "horizon": int(horizon),
                "execution_lag": int(execution_lag),
                "observations": int(len(valid)),
                "bottom_count": int(len(bottom)),
                "kept_count": int(len(kept)),
                "full_mean_forward_return": full_return,
                "kept_mean_forward_return": kept_return,
                "bottom_mean_forward_return": bottom_return,
                "overlay_excess_return": overlay_excess,
                "bottom_drag_return": bottom_drag,
            }
        )
    return rows


def _bottom_and_kept(frame: pd.DataFrame, *, bottom_quantile: float) -> dict[str, pd.DataFrame]:
    if frame.empty:
        return {"bottom": frame.copy(), "kept": frame.copy()}
    sorted_frame = frame.sort_values(["factor_value", "asset_id"], ascending=[True, True]).copy()
    bottom_count = max(1, int(math.floor(len(sorted_frame) * bottom_quantile)))
    bottom_count = min(bottom_count, max(len(sorted_frame) - 1, 1))
    bottom = sorted_frame.head(bottom_count)
    kept = sorted_frame.iloc[bottom_count:]
    return {"bottom": bottom, "kept": kept}


def _build_factor_summary(
    date_audits: list[dict[str, Any]],
    *,
    min_dates: int,
    min_overlay_t_stat: float,
    min_positive_overlay_rate: float,
    min_mean_overlay_excess_return: float,
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
        overlays = _finite_values(row.get("overlay_excess_return") for row in rows)
        full_returns = _finite_values(row.get("full_mean_forward_return") for row in rows)
        kept_returns = _finite_values(row.get("kept_mean_forward_return") for row in rows)
        bottom_returns = _finite_values(row.get("bottom_mean_forward_return") for row in rows)
        bottom_drags = _finite_values(row.get("bottom_drag_return") for row in rows)
        overlay_t = _stat_or_zero(_mean_t_stat(overlays))
        positive_rate = float(sum(1 for value in overlays if value > 0.0) / len(overlays)) if overlays else 0.0
        classification = _classify_factor(
            dates=len(rows),
            mean_overlay=_mean_or_zero(overlays),
            overlay_t=overlay_t,
            positive_rate=positive_rate,
            min_dates=min_dates,
            min_overlay_t_stat=min_overlay_t_stat,
            min_positive_overlay_rate=min_positive_overlay_rate,
            min_mean_overlay_excess_return=min_mean_overlay_excess_return,
        )
        result.append(
            {
                "market": market,
                "factor_name": factor_name,
                "horizon": int(horizon),
                "execution_lag": int(execution_lag),
                "classification": classification,
                "dates": len(rows),
                "valid_overlay_dates": len(overlays),
                "mean_observations": _mean(_finite_values(row.get("observations") for row in rows)),
                "mean_bottom_count": _mean(_finite_values(row.get("bottom_count") for row in rows)),
                "mean_kept_count": _mean(_finite_values(row.get("kept_count") for row in rows)),
                "mean_full_return": _mean_or_zero(full_returns),
                "mean_kept_return": _mean_or_zero(kept_returns),
                "mean_bottom_return": _mean_or_zero(bottom_returns),
                "mean_overlay_excess_return": _mean_or_zero(overlays),
                "overlay_t_stat": overlay_t,
                "overlay_p_value": _normal_two_sided_p_value(overlay_t),
                "positive_overlay_rate": positive_rate,
                "mean_bottom_drag_return": _mean_or_zero(bottom_drags),
                "compounded_full_return": _compounded_return(full_returns),
                "compounded_kept_return": _compounded_return(kept_returns),
                "compounded_bottom_return": _compounded_return(bottom_returns),
            }
        )
    return sorted(
        result,
        key=lambda row: (
            _classification_rank(str(row.get("classification"))),
            -_number(row.get("overlay_t_stat")),
            -_number(row.get("mean_overlay_excess_return")),
            str(row.get("factor_name")),
        ),
    )


def _classify_factor(
    *,
    dates: int,
    mean_overlay: float,
    overlay_t: float,
    positive_rate: float,
    min_dates: int,
    min_overlay_t_stat: float,
    min_positive_overlay_rate: float,
    min_mean_overlay_excess_return: float,
) -> str:
    if (
        dates >= min_dates
        and mean_overlay > min_mean_overlay_excess_return
        and overlay_t >= min_overlay_t_stat
        and positive_rate >= min_positive_overlay_rate
    ):
        return "bottom_exclusion_candidate"
    return "weak_or_unproven_exclusion"


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
        "bottom_exclusion_candidate_factors": classifications.get("bottom_exclusion_candidate", 0),
        "weak_or_unproven_exclusion_factors": classifications.get("weak_or_unproven_exclusion", 0),
        "classification_counts": dict(sorted(classifications.items())),
    }


def _recommended_next_actions(factor_summary: list[dict[str, Any]]) -> list[str]:
    classifications = {str(row.get("classification")) for row in factor_summary}
    actions: list[str] = []
    if "bottom_exclusion_candidate" in classifications:
        actions.append("test_bottom_exclusion_as_risk_filter_in_portfolio")
        actions.append("validate_against_costed_walk_forward_before_promotion")
    if not classifications or classifications == {"weak_or_unproven_exclusion"}:
        actions.append("rotate_factor_family_with_public_hypothesis")
    actions.append("do_not_promote_without_costed_walk_forward_backtest")
    return _dedupe(actions)


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


def _compounded_return(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return 0.0
    product = 1.0
    for value in finite:
        product *= 1.0 + value
    return product - 1.0


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} missing required columns: {', '.join(missing)}")


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


def _mean_or_nan(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return float("nan")
    return float(clean.mean())


def _mean_or_zero(values: list[float]) -> float:
    mean = _mean(values)
    return mean if math.isfinite(mean) else 0.0


def _stat_or_zero(value: float) -> float:
    return value if math.isfinite(value) else 0.0


def _classification_rank(classification: str) -> int:
    order = {
        "bottom_exclusion_candidate": 0,
        "weak_or_unproven_exclusion": 1,
    }
    return order.get(classification, 99)


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
