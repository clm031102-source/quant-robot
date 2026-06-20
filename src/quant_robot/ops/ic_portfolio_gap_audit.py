from __future__ import annotations

from collections import Counter, defaultdict
import ast
import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "ic_portfolio_gap_audit"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_ic_portfolio_gap_audit(
    rows: list[dict[str, Any]] | pd.DataFrame,
    *,
    source_report: str | None = None,
    min_abs_rank_ic: float = 0.02,
    min_rank_ic_t_stat: float = 2.0,
    min_long_short_mean_return: float = 0.0,
    min_promotable_sharpe: float = 0.5,
    min_promotable_overlap_sharpe: float = 0.3,
    min_promotable_relative_return: float = 0.0,
) -> dict[str, Any]:
    frame = _frame(rows)
    records = frame.to_dict(orient="records")
    case_audits = [
        _audit_case(
            row,
            source_report=source_report,
            min_abs_rank_ic=min_abs_rank_ic,
            min_rank_ic_t_stat=min_rank_ic_t_stat,
            min_long_short_mean_return=min_long_short_mean_return,
            min_promotable_sharpe=min_promotable_sharpe,
            min_promotable_overlap_sharpe=min_promotable_overlap_sharpe,
            min_promotable_relative_return=min_promotable_relative_return,
        )
        for row in records
    ]
    factor_summary = _factor_summary(case_audits)
    audit = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "source_report": source_report,
        "thresholds": {
            "min_abs_rank_ic": min_abs_rank_ic,
            "min_rank_ic_t_stat": min_rank_ic_t_stat,
            "min_long_short_mean_return": min_long_short_mean_return,
            "min_promotable_sharpe": min_promotable_sharpe,
            "min_promotable_overlap_sharpe": min_promotable_overlap_sharpe,
            "min_promotable_relative_return": min_promotable_relative_return,
        },
        "summary": _summary(case_audits),
        "recommended_next_actions": _recommended_next_actions(case_audits),
        "case_audits": case_audits,
        "factor_summary": factor_summary,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    audit["markdown"] = render_ic_portfolio_gap_markdown(audit)
    return audit


def load_leaderboard_rows(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if source.suffix.lower() == ".csv":
        return pd.read_csv(source).to_dict(orient="records")
    if source.suffix.lower() in {".jsonl", ".ndjson"}:
        rows = []
        for line in source.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
        return rows
    data = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        for key in ("leaderboard", "rows", "case_audits"):
            value = data.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    raise ValueError(f"Unsupported leaderboard format: {source}")


def write_ic_portfolio_gap_audit(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "ic_portfolio_gap_audit.json").write_text(
        json.dumps(_sanitize(audit), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "ic_portfolio_gap_audit.md").write_text(
        render_ic_portfolio_gap_markdown(audit),
        encoding="utf-8",
    )
    pd.DataFrame(audit.get("case_audits", [])).to_csv(output_path / "case_audits.csv", index=False)
    pd.DataFrame(audit.get("factor_summary", [])).to_csv(output_path / "factor_summary.csv", index=False)


def render_ic_portfolio_gap_markdown(audit: dict[str, Any]) -> str:
    summary = _dict(audit.get("summary"))
    lines = [
        "# IC-to-Portfolio Gap Audit",
        "",
        f"- Stage: {audit.get('stage', STAGE)}",
        f"- Source report: {audit.get('source_report') or 'unknown'}",
        f"- Cases: {summary.get('cases', 0)}",
        f"- Strong RankIC cases: {summary.get('strong_rank_ic_cases', 0)}",
        f"- IC-to-portfolio gap cases: {summary.get('ic_to_portfolio_gap_cases', 0)}",
        f"- Exclusion signal cases: {summary.get('exclusion_signal_cases', 0)}",
        f"- Capacity-limited cases: {summary.get('capacity_limited_cases', 0)}",
        f"- Promotable long-only cases: {summary.get('promotable_long_only_cases', 0)}",
        f"- Live boundary allowed: {audit.get('live_boundary_allowed', False)}",
        f"- Safety: {audit.get('safety', SAFETY)}",
        "",
        "## Recommended Next Actions",
        "",
    ]
    actions = _list(audit.get("recommended_next_actions"))
    lines.extend(f"- {action}" for action in actions) if actions else lines.append("- none")
    lines.extend(["", "## Translation Status Counts", ""])
    status_counts = _dict(summary.get("translation_status_counts"))
    if status_counts:
        for status, count in sorted(status_counts.items(), key=lambda item: (-int(item[1]), item[0])):
            lines.append(f"- {status}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Top Decision Reasons", ""])
    reason_counts = _dict(summary.get("decision_reason_counts"))
    if reason_counts:
        for reason, count in sorted(reason_counts.items(), key=lambda item: (-int(item[1]), item[0]))[:12]:
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Factor Summary", ""])
    for row in audit.get("factor_summary", []):
        lines.append(
            "- {factor}: cases={cases}, strong_rank_ic={strong}, gaps={gaps}, capacity={capacity}, "
            "best_rank_ic={rank_ic:.4f}, best_overlap_sharpe={overlap:.4f}, best_total_return={total:.4f}".format(
                factor=row.get("factor_name"),
                cases=int(row.get("cases", 0)),
                strong=int(row.get("strong_rank_ic_cases", 0)),
                gaps=int(row.get("ic_to_portfolio_gap_cases", 0)),
                capacity=int(row.get("capacity_limited_cases", 0)),
                rank_ic=_number(row.get("best_rank_ic")),
                overlap=_number(row.get("best_overlap_sharpe")),
                total=_number(row.get("best_total_return")),
            )
        )
    lines.extend(["", "## Case Audits", ""])
    for row in audit.get("case_audits", [])[:30]:
        tags = ", ".join(_list(row.get("tags"))) or "none"
        lines.append(f"- {row.get('case_id')}: {row.get('translation_status')} ({tags})")
    return "\n".join(lines) + "\n"


def _audit_case(
    row: dict[str, Any],
    *,
    source_report: str | None,
    min_abs_rank_ic: float,
    min_rank_ic_t_stat: float,
    min_long_short_mean_return: float,
    min_promotable_sharpe: float,
    min_promotable_overlap_sharpe: float,
    min_promotable_relative_return: float,
) -> dict[str, Any]:
    rank_ic = _number(_first(row, ("mean_rank_ic", "rank_ic", "test_mean_rank_ic")))
    rank_ic_t = _number(_first(row, ("rank_ic_t_stat", "test_rank_ic_t_stat")))
    long_short_mean = _number(_first(row, ("long_short_mean_return", "test_long_short_mean_return")))
    total_return = _number(_first(row, ("total_return", "test_total_return")))
    relative_return = _number(_first(row, ("relative_return", "test_relative_return")))
    sharpe = _number(_first(row, ("sharpe", "test_sharpe")))
    overlap_sharpe = _number(
        _first(row, ("overlap_autocorr_adjusted_sharpe", "test_overlap_autocorr_adjusted_sharpe"))
    )
    capacity_limited_trades = int(_number(_first(row, ("capacity_limited_trades", "test_capacity_limited_trades"))))
    extreme_trade_return_flag = _bool(_first(row, ("extreme_trade_return_flag", "test_extreme_trade_return_flag")))
    decision_reasons = _decision_reasons(row.get("decision_reasons"))
    decision_status = str(row.get("decision_status") or row.get("test_decision_status") or "unknown")

    strong_rank_ic = abs(rank_ic) >= min_abs_rank_ic and abs(rank_ic_t) >= min_rank_ic_t_stat
    long_short_positive = long_short_mean > min_long_short_mean_return
    long_only_failure = (
        relative_return < min_promotable_relative_return
        or total_return <= 0.0
        or sharpe < min_promotable_sharpe
        or overlap_sharpe < min_promotable_overlap_sharpe
        or "relative_return_below_threshold" in decision_reasons
    )
    capacity_blocked = capacity_limited_trades > 0 or "capacity_limited_trades_present" in decision_reasons
    promotable = (
        strong_rank_ic
        and not long_only_failure
        and not capacity_blocked
        and not extreme_trade_return_flag
        and decision_status.lower() in {"approved", "validation_candidate", "paper_candidate"}
    )

    tags: list[str] = []
    if strong_rank_ic:
        tags.append("strong_rank_ic")
    if long_short_positive:
        tags.append("positive_long_short_spread")
    if strong_rank_ic and long_only_failure:
        tags.append("long_only_translation_gap")
    if strong_rank_ic and long_short_positive and long_only_failure:
        tags.append("exclusion_signal_candidate")
    if capacity_blocked:
        tags.append("capacity_blocked")
    if extreme_trade_return_flag:
        tags.append("extreme_trade_return")
    if promotable:
        tags.append("promotable_long_only")

    if extreme_trade_return_flag:
        translation_status = "data_artifact_blocked"
    elif promotable:
        translation_status = "promotable_long_only"
    elif capacity_blocked and strong_rank_ic:
        translation_status = "capacity_blocked"
    elif strong_rank_ic and long_only_failure:
        translation_status = "translation_gap"
    elif strong_rank_ic:
        translation_status = "ranking_signal_only"
    else:
        translation_status = "weak_or_unproven_signal"

    return {
        "case_id": str(row.get("case_id") or ""),
        "factor_name": str(row.get("factor_name") or ""),
        "source_report": source_report,
        "decision_status": decision_status,
        "decision_reasons": decision_reasons,
        "translation_status": translation_status,
        "tags": tags,
        "strong_rank_ic": strong_rank_ic,
        "long_only_failure": long_only_failure,
        "exclusion_signal_candidate": strong_rank_ic and long_short_positive and long_only_failure,
        "capacity_blocked": capacity_blocked,
        "promotable_long_only": promotable,
        "mean_rank_ic": rank_ic,
        "rank_ic_t_stat": rank_ic_t,
        "long_short_mean_return": long_short_mean,
        "total_return": total_return,
        "relative_return": relative_return,
        "sharpe": sharpe,
        "overlap_autocorr_adjusted_sharpe": overlap_sharpe,
        "capacity_limited_trades": capacity_limited_trades,
        "extreme_trade_return_flag": extreme_trade_return_flag,
    }


def _summary(case_audits: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": len(case_audits),
        "strong_rank_ic_cases": sum(1 for row in case_audits if row["strong_rank_ic"]),
        "ic_to_portfolio_gap_cases": sum(1 for row in case_audits if row["strong_rank_ic"] and row["long_only_failure"]),
        "exclusion_signal_cases": sum(1 for row in case_audits if row["exclusion_signal_candidate"]),
        "capacity_limited_cases": sum(1 for row in case_audits if row["capacity_blocked"]),
        "extreme_trade_cases": sum(1 for row in case_audits if row["extreme_trade_return_flag"]),
        "promotable_long_only_cases": sum(1 for row in case_audits if row["promotable_long_only"]),
        "translation_status_counts": dict(sorted(Counter(row["translation_status"] for row in case_audits).items())),
        "decision_reason_counts": _reason_counts(case_audits),
    }


def _factor_summary(case_audits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in case_audits:
        grouped[str(row.get("factor_name") or "unknown")].append(row)
    result = []
    for factor_name, rows in grouped.items():
        result.append(
            {
                "factor_name": factor_name,
                "cases": len(rows),
                "strong_rank_ic_cases": sum(1 for row in rows if row["strong_rank_ic"]),
                "ic_to_portfolio_gap_cases": sum(1 for row in rows if row["strong_rank_ic"] and row["long_only_failure"]),
                "exclusion_signal_cases": sum(1 for row in rows if row["exclusion_signal_candidate"]),
                "capacity_limited_cases": sum(1 for row in rows if row["capacity_blocked"]),
                "promotable_long_only_cases": sum(1 for row in rows if row["promotable_long_only"]),
                "best_rank_ic": max(_number(row.get("mean_rank_ic")) for row in rows),
                "best_rank_ic_t_stat": max(_number(row.get("rank_ic_t_stat")) for row in rows),
                "best_long_short_mean_return": max(_number(row.get("long_short_mean_return")) for row in rows),
                "best_overlap_sharpe": max(_number(row.get("overlap_autocorr_adjusted_sharpe")) for row in rows),
                "best_total_return": max(_number(row.get("total_return")) for row in rows),
                "best_relative_return": max(_number(row.get("relative_return")) for row in rows),
                "best_sharpe": max(_number(row.get("sharpe")) for row in rows),
            }
        )
    return sorted(
        result,
        key=lambda row: (
            -int(row["promotable_long_only_cases"]),
            -int(row["strong_rank_ic_cases"]),
            -float(row["best_rank_ic_t_stat"]),
            str(row["factor_name"]),
        ),
    )


def _recommended_next_actions(case_audits: list[dict[str, Any]]) -> list[str]:
    if not case_audits:
        return ["run_factor_experiment_before_audit"]
    actions: list[str] = []
    strong_cases = [row for row in case_audits if row["strong_rank_ic"]]
    gap_cases = [row for row in strong_cases if row["long_only_failure"]]
    if gap_cases:
        actions.extend(
            [
                "bottom_quantile_exclusion_overlay",
                "stock_to_etf_breadth_bridge",
                "beta_sector_size_diagnostic",
                "stop_raw_formula_topn_sweeps",
            ]
        )
    if any(row["capacity_blocked"] for row in case_audits):
        actions.append("capacity_filter_or_liquidity_gate")
    if any(row["extreme_trade_return_flag"] for row in case_audits):
        actions.append("data_quality_repair_before_mining")
    if not strong_cases:
        actions.append("rotate_factor_family_with_public_hypothesis")
    if any(row["promotable_long_only"] for row in case_audits):
        actions.append("walk_forward_oos_validation")
    return _dedupe(actions)


def _reason_counts(case_audits: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(reason for row in case_audits for reason in _list(row.get("decision_reasons")))
    return dict(sorted(counts.items()))


def _decision_reasons(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        parsed = None
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [part.strip() for part in text.split(",") if part.strip()]


def _frame(rows: list[dict[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame(rows)


def _first(row: dict[str, Any], fields: tuple[str, ...]) -> Any:
    for field in fields:
        value = row.get(field)
        if not _missing(value):
            return value
    return None


def _missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value) and not (isinstance(value, float) and math.isnan(value))
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


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
