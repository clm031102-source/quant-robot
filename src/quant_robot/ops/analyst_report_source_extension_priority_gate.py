from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

from quant_robot.ops.cn_stock_local_source_queue_audit import SAFETY


STAGE = "analyst_report_source_extension_priority_gate"
SOURCE_GATE_STAGE = "cn_stock_non_lpr_orthogonal_source_gate"
SELECTED_SOURCE = "analyst_report_revision"
PRESCREEN_STAGE_ALIASES = {"", "analyst_report_revision_prescreen", "analyst_report_revision_pit_prescreen"}
NEXT_ACTION_WAIT_QUOTA = "wait_for_report_rc_quota_reset_then_cache_next_analyst_month"
NEXT_ACTION_CACHE = "cache_next_analyst_month_then_rerun_frozen_prescreen"

PRIORITY_COLUMNS = [
    "rank",
    "factor_name",
    "horizon",
    "priority_score",
    "mean_spearman_ic",
    "ic_t_stat",
    "icir",
    "fdr_significant",
    "bonferroni_significant",
    "mean_size_neutral_rank_ic",
    "size_neutral_rank_ic_t_stat",
    "mean_industry_neutral_rank_ic",
    "industry_neutral_rank_ic_t_stat",
    "ic_year_count",
    "research_lead",
    "promotion_allowed",
    "extension_status",
    "blockers",
]


def run_analyst_report_source_extension_priority_gate(
    *,
    source_gate_path: str | Path,
    analyst_prescreen_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    source_gate = json.loads(Path(source_gate_path).read_text(encoding="utf-8"))
    analyst_prescreen = json.loads(Path(analyst_prescreen_path).read_text(encoding="utf-8"))
    result = build_analyst_report_source_extension_priority_gate(
        source_gate=source_gate,
        analyst_prescreen=analyst_prescreen,
        source_gate_path=source_gate_path,
        analyst_prescreen_path=analyst_prescreen_path,
    )
    write_analyst_report_source_extension_priority_gate(output_dir, result)
    return result


def build_analyst_report_source_extension_priority_gate(
    *,
    source_gate: dict[str, Any],
    analyst_prescreen: dict[str, Any],
    source_gate_path: str | Path | None = None,
    analyst_prescreen_path: str | Path | None = None,
) -> dict[str, Any]:
    source_blockers = _source_blockers(source_gate)
    prescreen_blockers = _prescreen_blockers(analyst_prescreen)
    rows = _priority_rows(analyst_prescreen) if not source_blockers else []
    priority = rows[0] if rows else {}
    provider_allowed = _dict(source_gate.get("decision")).get("provider_request_allowed") is True
    blockers = _unique([*source_blockers, *prescreen_blockers])
    if rows:
        if not provider_allowed:
            blockers.append("provider_quota_preflight_blocked")
        if int(_number(priority.get("ic_year_count"))) < 2:
            blockers.append("priority_row_year_coverage_below_gate")
        if not priority.get("fdr_significant", False):
            blockers.append("priority_row_not_fdr_significant")
        if priority.get("promotion_allowed", False):
            blockers.append("priority_row_promotion_unexpectedly_allowed")
    blockers = _unique(blockers)
    status = "ready_to_cache_next_month" if rows and provider_allowed and not blockers else (
        "blocked_waiting_for_quota" if rows and "provider_quota_preflight_blocked" in blockers else "blocked"
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "source_gate_path": str(Path(source_gate_path)) if source_gate_path is not None else None,
        "analyst_prescreen_path": str(Path(analyst_prescreen_path)) if analyst_prescreen_path is not None else None,
        "summary": {
            "candidate_rows": len(rows),
            "priority_factor_name": priority.get("factor_name", ""),
            "priority_horizon": int(_number(priority.get("horizon"))),
            "priority_score": _number(priority.get("priority_score")),
            "latest_report_date": _latest_report_date(analyst_prescreen),
            "research_lead_count": int(_number(_dict(analyst_prescreen.get("summary")).get("research_lead_count"))),
            "year_coverage_pass_count": int(_number(_dict(analyst_prescreen.get("summary")).get("year_coverage_pass_count"))),
        },
        "decision": {
            "blockers": blockers,
            "priority_source": SELECTED_SOURCE if not source_blockers else "",
            "priority_factor_name": priority.get("factor_name", ""),
            "priority_horizon": int(_number(priority.get("horizon"))),
            "provider_cache_allowed_now": bool(status == "ready_to_cache_next_month"),
            "cache_next_month_after_quota_reset": bool(rows and not source_blockers),
            "next_action": NEXT_ACTION_CACHE if status == "ready_to_cache_next_month" else NEXT_ACTION_WAIT_QUOTA,
            "frozen_prescreen_required": bool(rows and not source_blockers),
            "formula_tuning_allowed": False,
            "window_tuning_allowed": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "priority_table": rows,
        "holdout_policy": {
            "final_holdout_included": False,
            "final_holdout_use": "blocked_until_year_coverage_walk_forward_cost_capacity_and_regime_gates_clear",
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_analyst_report_source_extension_priority_gate_markdown(result)
    return result


def write_analyst_report_source_extension_priority_gate(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "analyst_report_source_extension_priority_gate.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "analyst_report_source_extension_priority_gate.md").write_text(
        render_analyst_report_source_extension_priority_gate_markdown(clean),
        encoding="utf-8",
    )
    _write_csv(output_path / "analyst_report_source_extension_priority_rows.csv", clean["priority_table"], PRIORITY_COLUMNS)


def render_analyst_report_source_extension_priority_gate_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    decision = _dict(result.get("decision"))
    lines = [
        "# Analyst Report Source Extension Priority Gate",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Status: {result.get('status', 'unknown')}",
        f"- Priority source: `{decision.get('priority_source', '')}`",
        f"- Priority factor: `{decision.get('priority_factor_name', '')}`",
        f"- Priority horizon: {decision.get('priority_horizon', 0)}",
        f"- Priority score: {float(summary.get('priority_score', 0.0) or 0.0):.4f}",
        f"- Latest report date: {summary.get('latest_report_date', '')}",
        f"- Provider cache allowed now: {decision.get('provider_cache_allowed_now', False)}",
        f"- Cache next month after quota reset: {decision.get('cache_next_month_after_quota_reset', False)}",
        f"- Frozen prescreen required: {decision.get('frozen_prescreen_required', False)}",
        f"- Formula tuning allowed: {decision.get('formula_tuning_allowed', False)}",
        f"- Portfolio grid allowed: {decision.get('portfolio_grid_allowed', False)}",
        f"- Promotion allowed: {decision.get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Priority Rows",
        "",
        "| Rank | Factor | H | Score | IC | t | ICIR | FDR | Size t | Industry t | Years | Status |",
        "|---:|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for row in result.get("priority_table", []):
        lines.append(
            "| {rank} | {factor} | {horizon} | {score:.4f} | {ic:.4f} | {t:.2f} | {icir:.3f} | {fdr} | {size_t:.2f} | {industry_t:.2f} | {years} | {status} |".format(
                rank=int(_number(row.get("rank"))),
                factor=row.get("factor_name", ""),
                horizon=int(_number(row.get("horizon"))),
                score=_number(row.get("priority_score")),
                ic=_number(row.get("mean_spearman_ic")),
                t=_number(row.get("ic_t_stat")),
                icir=_number(row.get("icir")),
                fdr="yes" if row.get("fdr_significant", False) else "no",
                size_t=_number(row.get("size_neutral_rank_ic_t_stat")),
                industry_t=_number(row.get("industry_neutral_rank_ic_t_stat")),
                years=int(_number(row.get("ic_year_count"))),
                status=row.get("extension_status", ""),
            )
        )
    lines.extend(["", "## Blockers", ""])
    blockers = _as_list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is a source-extension priority gate, not a research-lead or promotion gate.",
            "- The selected row must be rerun with the same frozen prescreen after the next monthly cache.",
            "- Formula tuning, window tuning, portfolio grids, promotion, paper signals, and live use remain closed.",
        ]
    )
    return "\n".join(lines) + "\n"


def _source_blockers(source_gate: dict[str, Any]) -> list[str]:
    decision = _dict(source_gate.get("decision"))
    blockers: list[str] = []
    if source_gate.get("stage") != SOURCE_GATE_STAGE:
        blockers.append("unexpected_source_gate_stage")
    if decision.get("selected_source") != SELECTED_SOURCE or decision.get("source_gate_selected") is not True:
        blockers.append("analyst_source_not_selected")
    if decision.get("local_cached_prescreen_allowed") is not True:
        blockers.append("analyst_local_prescreen_not_allowed")
    if decision.get("portfolio_grid_allowed") is not False:
        blockers.append("portfolio_grid_unexpectedly_allowed")
    if decision.get("promotion_allowed") is not False:
        blockers.append("promotion_unexpectedly_allowed")
    if source_gate.get("live_boundary_allowed") is not False:
        blockers.append("live_boundary_unexpectedly_allowed")
    return _unique(blockers)


def _prescreen_blockers(analyst_prescreen: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if str(analyst_prescreen.get("stage", "") or "") not in PRESCREEN_STAGE_ALIASES:
        blockers.append("unexpected_analyst_prescreen_stage")
    summary = _dict(analyst_prescreen.get("summary"))
    if int(_number(summary.get("promotion_allowed_candidates"))) > 0:
        blockers.append("prescreen_promotion_unexpectedly_allowed")
    if analyst_prescreen.get("live_boundary_allowed") is not False:
        blockers.append("prescreen_live_boundary_unexpectedly_allowed")
    if not _dict_rows(analyst_prescreen.get("results")):
        blockers.append("analyst_prescreen_results_missing")
    return _unique(blockers)


def _priority_rows(analyst_prescreen: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in _dict_rows(analyst_prescreen.get("results")):
        clean = {
            "factor_name": str(row.get("factor_name", "")),
            "horizon": int(_number(row.get("horizon"))),
            "mean_spearman_ic": _number(row.get("mean_spearman_ic")),
            "ic_t_stat": _number(row.get("ic_t_stat")),
            "icir": _number(row.get("icir")),
            "fdr_significant": bool(row.get("fdr_significant", False)),
            "bonferroni_significant": bool(row.get("bonferroni_significant", False)),
            "mean_size_neutral_rank_ic": _number(row.get("mean_size_neutral_rank_ic")),
            "size_neutral_rank_ic_t_stat": _number(row.get("size_neutral_rank_ic_t_stat")),
            "mean_industry_neutral_rank_ic": _number(row.get("mean_industry_neutral_rank_ic")),
            "industry_neutral_rank_ic_t_stat": _number(row.get("industry_neutral_rank_ic_t_stat")),
            "ic_year_count": int(_number(row.get("ic_year_count"))),
            "research_lead": bool(row.get("research_lead", False)),
            "promotion_allowed": bool(row.get("promotion_allowed", False)),
            "blockers": _as_list(row.get("blockers")),
        }
        clean["priority_score"] = _priority_score(clean)
        clean["extension_status"] = _extension_status(clean)
        rows.append(clean)
    rows.sort(key=lambda item: item["priority_score"], reverse=True)
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def _priority_score(row: dict[str, Any]) -> float:
    score = abs(_number(row.get("mean_spearman_ic"))) * 10.0
    score += max(_number(row.get("ic_t_stat")), 0.0) * 0.20
    score += max(_number(row.get("icir")), 0.0)
    score += max(_number(row.get("size_neutral_rank_ic_t_stat")), 0.0) * 0.15
    score += max(_number(row.get("industry_neutral_rank_ic_t_stat")), 0.0) * 0.03
    if row.get("fdr_significant", False):
        score += 1.0
    if row.get("bonferroni_significant", False):
        score += 0.5
    if int(_number(row.get("ic_year_count"))) < 2:
        score -= 0.75
    if row.get("promotion_allowed", False):
        score -= 10.0
    return float(score)


def _extension_status(row: dict[str, Any]) -> str:
    if row.get("promotion_allowed", False):
        return "unexpected_promotion_allowed"
    if not row.get("fdr_significant", False):
        return "watch_only_not_extension_priority"
    if int(_number(row.get("ic_year_count"))) < 2:
        return "priority_source_extension_pending_year_coverage"
    return "priority_source_extension_ready_for_quota_check"


def _latest_report_date(analyst_prescreen: dict[str, Any]) -> str:
    return str(_dict(analyst_prescreen.get("data_window")).get("max_report_date", ""))


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dict_rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _as_list(value: object) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return sorted(value)
    return [value]


def _unique(values: Iterable[object]) -> list:
    seen = set()
    result = []
    for value in values:
        if value is None:
            continue
        key = str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _number(value: object) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _write_csv(path: Path, rows: Sequence[dict[str, Any]], columns: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_value(row.get(column)) for column in columns})


def _csv_value(value: object) -> object:
    if isinstance(value, (list, tuple, set)):
        return ";".join(str(item) for item in value)
    return value


def _sanitize(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value
