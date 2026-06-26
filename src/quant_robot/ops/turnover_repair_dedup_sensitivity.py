from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


STAGE = "turnover_repair_dedup_sensitivity"
DEFAULT_BASE_CAPITAL = 100_000
DEFAULT_CAPITAL_GRID = (100_000, 500_000, 1_000_000, 5_000_000)
DEFAULT_MAX_PARTICIPATION = 0.01
DEFAULT_EXTREME_RETURN_RATE_LIMIT = 0.03
EXACT_RAW_CLONE_CORR = 0.995
HIGH_REDUNDANCY_CORR = 0.75
MODERATE_REDUNDANCY_CORR = 0.60
NEXT_CHAMPION_CONVERSION = "round126_turnover_repair_champion_costed_portfolio_conversion"
NEXT_ROTATE = "round126_rotate_after_turnover_repair_capacity_or_dedup_failure"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."

DEDUP_COLUMNS = [
    "factor_name",
    "horizon",
    "raw_source_factor",
    "repair_family",
    "mean_spearman_ic",
    "icir",
    "ic_t_stat",
    "ic_positive_rate",
    "quantile_spread",
    "quantile_monotonicity",
    "avg_top_quantile_turnover",
    "raw_factor_spearman_corr",
    "redundancy_class",
    "capacity_clean_all_capitals",
    "extreme_forward_return_rate",
    "is_champion",
    "action",
    "blockers",
]
SENSITIVITY_COLUMNS = [
    "factor_name",
    "horizon",
    "capital",
    "scaled_max_estimated_participation",
    "scaled_median_estimated_participation",
    "capacity_clean",
]


def load_turnover_repair_prescreen_results(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def summarize_turnover_repair_dedup_sensitivity(
    round124_results: pd.DataFrame | Iterable[dict[str, Any]],
    *,
    capital_grid: Iterable[int | float] = DEFAULT_CAPITAL_GRID,
    base_capital: int | float = DEFAULT_BASE_CAPITAL,
    max_participation: float = DEFAULT_MAX_PARTICIPATION,
    extreme_return_rate_limit: float = DEFAULT_EXTREME_RETURN_RATE_LIMIT,
) -> dict[str, Any]:
    frame = _normalise_round124_results(round124_results)
    capitals = tuple(int(capital) for capital in capital_grid)
    lead_rows = [row for row in frame if row["research_lead"]]
    sensitivity = _capital_sensitivity(
        lead_rows,
        capitals=capitals,
        base_capital=float(base_capital),
        max_participation=max_participation,
    )
    capacity_by_key = _capacity_clean_by_key(sensitivity)
    annotated = _annotate_leads(
        lead_rows,
        capacity_by_key=capacity_by_key,
        extreme_return_rate_limit=extreme_return_rate_limit,
    )
    champion = _select_champion(annotated)
    next_action_blockers = _next_action_blockers(champion)
    allowed_conversion = champion is not None and not next_action_blockers
    if champion is not None:
        champion["is_champion"] = allowed_conversion
        champion["action"] = (
            "single_frozen_champion_costed_portfolio_conversion"
            if allowed_conversion
            else "blocked_before_portfolio_conversion"
        )
    promotion_blockers = _promotion_blockers(annotated)
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": _summary(frame, lead_rows, annotated, capacity_by_key),
        "thresholds": {
            "base_capital": int(base_capital),
            "capital_grid": list(capitals),
            "max_participation": max_participation,
            "extreme_return_rate_limit": extreme_return_rate_limit,
            "exact_raw_clone_corr": EXACT_RAW_CLONE_CORR,
            "high_redundancy_corr": HIGH_REDUNDANCY_CORR,
            "moderate_redundancy_corr": MODERATE_REDUNDANCY_CORR,
        },
        "champion": _champion_payload(champion),
        "portfolio_conversion_policy": {
            "allowed_candidate_count": 1 if allowed_conversion else 0,
            "allowed_candidates": [_champion_payload(champion)] if allowed_conversion and champion else [],
            "scope": "single frozen champion only; no broad parameter grid before costed portfolio evidence",
            "reason": (
                "Capacity sensitivity is clean through the requested small-capital grid; this permits one costed portfolio conversion audit, not promotion."
                if allowed_conversion
                else "No candidate cleared the next-action gate for costed portfolio conversion."
            ),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "allowed_candidate_count": 0,
            "blockers": promotion_blockers,
            "reason": "Dedup and capacity sensitivity are pre-portfolio diagnostics; promotion still requires costed walk-forward, regime coverage, overlap-aware returns, and final holdout discipline.",
        },
        "gate": {
            "next_action_blockers": next_action_blockers,
            "required_before_promotion": [
                "costed_topn_portfolio_conversion",
                "rolling_walk_forward_train_test_split",
                "transaction_cost_and_capacity_stress",
                "market_regime_coverage",
                "overlap_aware_return_statistics",
                "final_holdout_read_once_after_oos_clearance",
            ],
        },
        "next_direction": NEXT_CHAMPION_CONVERSION if allowed_conversion else NEXT_ROTATE,
        "dedup_rows": annotated,
        "capital_sensitivity": sensitivity,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_turnover_repair_dedup_sensitivity_markdown(result)
    return result


def write_turnover_repair_dedup_sensitivity(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "turnover_repair_dedup_sensitivity.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "turnover_repair_dedup_sensitivity.md").write_text(
        render_turnover_repair_dedup_sensitivity_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "turnover_repair_dedup_rows.csv", result.get("dedup_rows", []), DEDUP_COLUMNS)
    _write_csv(
        output_path / "turnover_repair_capital_sensitivity.csv",
        result.get("capital_sensitivity", []),
        SENSITIVITY_COLUMNS,
    )


def render_turnover_repair_dedup_sensitivity_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    champion = result.get("champion", {})
    conversion = result.get("portfolio_conversion_policy", {})
    promotion = result.get("promotion_policy", {})
    lines = [
        "# Turnover Repair Dedup And Small-Capital Sensitivity",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Input research-lead rows: {summary.get('input_research_lead_rows', 0)}",
        f"- Unique research-lead factor names: {summary.get('unique_research_lead_factor_names', 0)}",
        f"- Raw-source clusters: {summary.get('raw_source_clusters', 0)}",
        f"- Raw-clone lead rows: {summary.get('raw_clone_lead_rows', 0)}",
        f"- High-redundancy lead rows: {summary.get('high_redundancy_lead_rows', 0)}",
        f"- Nonredundant research leads: {summary.get('nonredundant_research_leads', 0)}",
        f"- Capacity-clean lead rows at all capitals: {summary.get('capacity_clean_lead_rows_at_all_capitals', 0)}",
        f"- Portfolio conversion allowed candidates: {conversion.get('allowed_candidate_count', 0)}",
        f"- Promotion allowed: {promotion.get('promotion_allowed', False)}",
        f"- Next direction: {result.get('next_direction', NEXT_ROTATE)}",
        "",
        "## Champion",
        "",
        f"- Factor: {champion.get('factor_name', 'none')}",
        f"- Horizon: {champion.get('horizon', 'none')}",
        f"- IC: {_fmt(champion.get('mean_spearman_ic'))}",
        f"- ICIR: {_fmt(champion.get('icir'))}",
        f"- t-stat: {_fmt(champion.get('ic_t_stat'))}",
        f"- Raw correlation: {_fmt(champion.get('raw_factor_spearman_corr'))}",
        f"- Action: {champion.get('action', 'none')}",
        "",
        "## Dedup Rows",
        "",
        "| Factor | H | IC | ICIR | t | Raw corr | Class | Capacity all clean | Action |",
        "|---|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in result.get("dedup_rows", []):
        lines.append(
            "| {factor} | {horizon} | {ic} | {icir} | {t_stat} | {raw_corr} | {klass} | {cap} | {action} |".format(
                factor=row.get("factor_name", "unknown"),
                horizon=row.get("horizon", ""),
                ic=_fmt(row.get("mean_spearman_ic")),
                icir=_fmt(row.get("icir")),
                t_stat=_fmt(row.get("ic_t_stat")),
                raw_corr=_fmt(row.get("raw_factor_spearman_corr")),
                klass=row.get("redundancy_class", "unknown"),
                cap=row.get("capacity_clean_all_capitals", False),
                action=row.get("action", "unknown"),
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            f"- Next-action blockers: {', '.join(result.get('gate', {}).get('next_action_blockers', [])) or 'none'}",
            f"- Promotion blockers: {', '.join(promotion.get('blockers', [])) or 'none'}",
            "- This round can authorize only a narrow costed portfolio conversion audit; it cannot authorize promotion or live/manual use.",
        ]
    )
    return "\n".join(lines) + "\n"


def _normalise_round124_results(round124_results: pd.DataFrame | Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(round124_results, pd.DataFrame):
        records = round124_results.to_dict("records")
    else:
        records = list(round124_results)
    normalised = []
    for row in records:
        factor_name = str(row.get("factor_name", "")).strip()
        horizon = _to_int(row.get("horizon"), default=0)
        normalised.append(
            {
                "factor_name": factor_name,
                "horizon": horizon,
                "raw_source_factor": _raw_source_factor(factor_name),
                "repair_family": _repair_family(factor_name),
                "mean_spearman_ic": _to_float(row.get("mean_spearman_ic")),
                "icir": _to_float(row.get("icir")),
                "ic_t_stat": _to_float(row.get("ic_t_stat")),
                "ic_positive_rate": _to_float(row.get("ic_positive_rate")),
                "quantile_spread": _to_float(row.get("quantile_spread")),
                "quantile_monotonicity": _to_float(row.get("quantile_monotonicity")),
                "avg_top_quantile_turnover": _to_float(row.get("avg_top_quantile_turnover")),
                "max_estimated_participation": _to_float(row.get("max_estimated_participation")),
                "median_estimated_participation": _to_float(row.get("median_estimated_participation")),
                "extreme_forward_return_rate": _to_float(row.get("extreme_forward_return_rate")),
                "raw_factor_spearman_corr": _to_float(row.get("raw_factor_spearman_corr")),
                "capacity_clean": _to_bool(row.get("capacity_clean")),
                "research_lead": _to_bool(row.get("research_lead")),
                "input_blockers": _split_blockers(row.get("blockers")),
            }
        )
    return normalised


def _capital_sensitivity(
    rows: list[dict[str, Any]],
    *,
    capitals: tuple[int, ...],
    base_capital: float,
    max_participation: float,
) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        for capital in capitals:
            scale = float(capital) / base_capital
            scaled_max = row["max_estimated_participation"] * scale
            scaled_median = row["median_estimated_participation"] * scale
            output.append(
                {
                    "factor_name": row["factor_name"],
                    "horizon": row["horizon"],
                    "capital": int(capital),
                    "scaled_max_estimated_participation": scaled_max,
                    "scaled_median_estimated_participation": scaled_median,
                    "capacity_clean": bool(row["capacity_clean"] and scaled_max <= max_participation),
                }
            )
    return output


def _capacity_clean_by_key(sensitivity: list[dict[str, Any]]) -> dict[tuple[str, int], bool]:
    by_key: dict[tuple[str, int], list[bool]] = {}
    for row in sensitivity:
        key = (row["factor_name"], int(row["horizon"]))
        by_key.setdefault(key, []).append(bool(row["capacity_clean"]))
    return {key: bool(values) and all(values) for key, values in by_key.items()}


def _annotate_leads(
    rows: list[dict[str, Any]],
    *,
    capacity_by_key: dict[tuple[str, int], bool],
    extreme_return_rate_limit: float,
) -> list[dict[str, Any]]:
    annotated = []
    for row in rows:
        item = dict(row)
        item["redundancy_class"] = _redundancy_class(item["raw_factor_spearman_corr"])
        item["capacity_clean_all_capitals"] = capacity_by_key.get((item["factor_name"], item["horizon"]), False)
        blockers = list(item.pop("input_blockers"))
        if item["redundancy_class"] in {"exact_raw_clone", "high_redundancy_soft_variant"}:
            blockers.append("not_independent_alpha_after_raw_reference_dedup")
        if not item["capacity_clean_all_capitals"]:
            blockers.append("small_capital_capacity_stress_failed")
        if item["extreme_forward_return_rate"] > extreme_return_rate_limit:
            blockers.append("extreme_forward_return_rate_above_policy")
        item["is_champion"] = False
        item["action"] = _default_action(item["redundancy_class"])
        item["blockers"] = blockers
        annotated.append(item)
    return annotated


def _select_champion(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    ranked = sorted(
        rows,
        key=lambda row: (
            row.get("mean_spearman_ic", 0.0),
            row.get("icir", 0.0),
            row.get("ic_t_stat", 0.0),
            row.get("horizon", 0),
        ),
        reverse=True,
    )
    return ranked[0]


def _next_action_blockers(champion: dict[str, Any] | None) -> list[str]:
    if champion is None:
        return ["no_research_lead_champion"]
    blockers = []
    if not champion.get("capacity_clean_all_capitals", False):
        blockers.append("small_capital_capacity_stress_failed")
    if "extreme_forward_return_rate_above_policy" in champion.get("blockers", []):
        blockers.append("extreme_forward_return_rate_above_policy")
    return blockers


def _promotion_blockers(rows: list[dict[str, Any]]) -> list[str]:
    blockers = [
        "costed_topn_portfolio_missing",
        "rolling_walk_forward_cost_regime_overlap_gates_missing",
        "final_holdout_not_read_for_promotion",
    ]
    if not any(row.get("redundancy_class") == "potentially_independent" for row in rows):
        blockers.insert(0, "dedup_revealed_zero_independent_new_alpha")
    return blockers


def _summary(
    frame: list[dict[str, Any]],
    lead_rows: list[dict[str, Any]],
    annotated: list[dict[str, Any]],
    capacity_by_key: dict[tuple[str, int], bool],
) -> dict[str, Any]:
    unique_names = {row["factor_name"] for row in lead_rows}
    raw_sources = {row["raw_source_factor"] for row in lead_rows}
    exact = [row for row in annotated if row["redundancy_class"] == "exact_raw_clone"]
    high = [row for row in annotated if row["redundancy_class"] == "high_redundancy_soft_variant"]
    nonredundant = [row for row in annotated if row["redundancy_class"] == "potentially_independent"]
    all_clean = sum(1 for row in lead_rows if capacity_by_key.get((row["factor_name"], row["horizon"]), False))
    return {
        "input_rows": len(frame),
        "input_research_lead_rows": len(lead_rows),
        "unique_research_lead_factor_names": len(unique_names),
        "raw_source_clusters": len(raw_sources),
        "raw_clone_lead_rows": len(exact),
        "high_redundancy_lead_rows": len(high),
        "nonredundant_research_leads": len(nonredundant),
        "capacity_clean_lead_rows_at_all_capitals": all_clean,
        "promotion_allowed_count": 0,
    }


def _champion_payload(champion: dict[str, Any] | None) -> dict[str, Any]:
    if champion is None:
        return {}
    keys = [
        "factor_name",
        "horizon",
        "raw_source_factor",
        "repair_family",
        "mean_spearman_ic",
        "icir",
        "ic_t_stat",
        "ic_positive_rate",
        "quantile_spread",
        "quantile_monotonicity",
        "avg_top_quantile_turnover",
        "max_estimated_participation",
        "median_estimated_participation",
        "extreme_forward_return_rate",
        "raw_factor_spearman_corr",
        "redundancy_class",
        "capacity_clean_all_capitals",
        "action",
    ]
    return {key: champion.get(key) for key in keys}


def _raw_source_factor(factor_name: str) -> str:
    if factor_name.startswith("turnover_rate_f_low"):
        return "turnover_rate_f_low"
    if factor_name.startswith("turnover_rate_low"):
        return "turnover_rate_low"
    return "unknown"


def _repair_family(factor_name: str) -> str:
    if "participation_budget" in factor_name:
        return "participation_budget"
    if "adv_soft_rank" in factor_name:
        return "adv_soft_rank"
    if "adv_mv_soft_blend" in factor_name:
        return "adv_mv_soft_blend"
    return "unknown"


def _redundancy_class(raw_corr: float) -> str:
    abs_corr = abs(raw_corr)
    if abs_corr >= EXACT_RAW_CLONE_CORR:
        return "exact_raw_clone"
    if abs_corr >= HIGH_REDUNDANCY_CORR:
        return "high_redundancy_soft_variant"
    if abs_corr >= MODERATE_REDUNDANCY_CORR:
        return "moderate_redundancy_variant"
    return "potentially_independent"


def _default_action(redundancy_class: str) -> str:
    if redundancy_class == "exact_raw_clone":
        return "dedup_block_as_independent_alpha"
    if redundancy_class == "high_redundancy_soft_variant":
        return "secondary_diagnostic_only"
    if redundancy_class == "moderate_redundancy_variant":
        return "requires_incremental_reference_test"
    return "eligible_for_future_independent_alpha_review"


def _split_blockers(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(number) else number


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_value(row.get(column)) for column in columns})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return value


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    return value
