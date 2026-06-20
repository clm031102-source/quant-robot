from __future__ import annotations

from collections import Counter
import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "long_cycle_factor_replay"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."

PARAMETER_FIELDS = (
    "factor_name",
    "factor_source",
    "top_n",
    "cost_bps",
    "forward_horizon",
    "holding_period",
    "rebalance_interval",
    "schedule_interval",
    "schedule_offset",
    "previous_month_return_threshold",
    "gate_name",
    "portfolio_scope",
)

SOURCE_AUDIT_TEXT_FIELDS = (
    "source_kind",
    "source_report",
)

SOURCE_AUDIT_NUMBER_FIELDS = (
    ("mean_ic", ("mean_ic",)),
    ("mean_rank_ic", ("mean_rank_ic", "discovery_rank_ic")),
    ("tail_mean_ic", ("tail_mean_ic",)),
    ("tail_mean_rank_ic", ("tail_mean_rank_ic", "discovery_tail_rank_ic")),
    ("long_short_mean_return", ("long_short_mean_return",)),
    (
        "long_short_positive_rate",
        ("long_short_positive_rate", "monthly_return_prob_gt_zero", "discovery_monthly_probability_gt_zero"),
    ),
    ("total_return", ("total_return", "discovery_total_return")),
    ("relative_return", ("relative_return",)),
    ("sharpe", ("sharpe", "discovery_sharpe")),
    ("max_drawdown", ("max_drawdown", "discovery_max_drawdown")),
    ("turnover", ("turnover",)),
    ("avg_participation_rate", ("avg_participation_rate",)),
    ("max_participation_rate", ("max_participation_rate", "test_max_participation_rate")),
    ("capacity_limited_trades", ("capacity_limited_trades",)),
    ("trades", ("trades",)),
    ("cost_bps", ("cost_bps", "test_cost_bps")),
    ("execution_lag", ("execution_lag", "lag")),
    ("overlap_autocorr_adjusted_sharpe", ("overlap_autocorr_adjusted_sharpe", "test_overlap_autocorr_adjusted_sharpe")),
)

SOURCE_AUDIT_DATE_FIELDS = (
    "train_start_date",
    "train_end_date",
    "test_start_date",
    "test_end_date",
)


def build_candidate_registry(candidate_rows: list[dict[str, Any]] | pd.DataFrame) -> list[dict[str, Any]]:
    frame = _frame(candidate_rows)
    if frame.empty or "case_id" not in frame.columns:
        return []

    rows: dict[str, dict[str, Any]] = {}
    source_reports: dict[str, list[str]] = {}
    for raw in frame.to_dict(orient="records"):
        case_id = str(raw.get("case_id", "")).strip()
        if not case_id:
            continue
        if case_id not in rows:
            rows[case_id] = {
                "case_id": case_id,
                "market": str(raw.get("market") or _infer_market(case_id)),
                "factor_name": str(raw.get("factor_name") or ""),
                "replay_status": "pending",
                "frozen_parameters": _frozen_parameters(raw),
            }
            source_reports[case_id] = []
        source = str(raw.get("source_report") or raw.get("source_file") or "").strip()
        if source and source not in source_reports[case_id]:
            source_reports[case_id].append(source)

    registry = []
    for case_id in sorted(rows):
        row = rows[case_id]
        row["source_reports"] = source_reports.get(case_id, [])
        registry.append(row)
    return registry


def build_long_cycle_coverage(
    bars: pd.DataFrame,
    *,
    market: str,
    required_start: str = "2015-01-01",
) -> dict[str, Any]:
    frame = _market_bars(bars, market)
    blockers: list[str] = []
    if frame.empty:
        blockers.append("market_bars_missing")
        return {
            "status": "insufficient",
            "market": market,
            "required_start": required_start,
            "date_start": None,
            "date_end": None,
            "bar_rows": 0,
            "asset_ids": 0,
            "blockers": blockers,
            "bar_trade_dates_by_year": {},
            "missing_years": [],
            "thin_years": [],
        }

    dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
    date_start = dates.min().date()
    date_end = dates.max().date()
    year_counts = _trade_dates_by_year(dates)
    blockers.extend(_year_coverage_blockers(date_start.isoformat(), date_end.isoformat(), required_start, year_counts))

    required = pd.to_datetime(required_start).date()
    if date_start.year > required.year:
        blockers.append("history_starts_after_required_cycle_start")

    return {
        "status": "sufficient" if not blockers else "insufficient",
        "market": market,
        "required_start": required_start,
        "date_start": date_start.isoformat(),
        "date_end": date_end.isoformat(),
        "bar_rows": int(len(frame)),
        "asset_ids": int(frame["asset_id"].nunique()) if "asset_id" in frame.columns else 0,
        "blockers": blockers,
        "bar_trade_dates_by_year": year_counts,
        "missing_years": _missing_required_years(date_end.isoformat(), required_start, year_counts),
        "thin_years": _thin_required_years(date_end.isoformat(), year_counts),
    }


def build_long_cycle_coverage_from_manifest(
    manifest: dict[str, Any],
    *,
    market: str,
    required_start: str = "2015-01-01",
) -> dict[str, Any]:
    summary = _dict(manifest.get("summary"))
    date_start = str(summary.get("date_start") or "")[:10] or None
    date_end = str(summary.get("date_end") or "")[:10] or None
    blockers: list[str] = []
    if date_start is None or date_end is None:
        blockers.append("manifest_date_range_missing")
    else:
        required = pd.to_datetime(required_start).date()
        observed_start = pd.to_datetime(date_start).date()
        if observed_start.year > required.year:
            blockers.append("history_starts_after_required_cycle_start")
        year_counts = _coerce_year_counts(summary.get("bar_trade_dates_by_year"))
        blockers.extend(_year_coverage_blockers(date_start, date_end, required_start, year_counts))
    if date_start is None or date_end is None:
        year_counts = {}
    return {
        "status": "sufficient" if not blockers else "insufficient",
        "market": market,
        "required_start": required_start,
        "date_start": date_start,
        "date_end": date_end,
        "bar_rows": int(_number(summary.get("bar_rows"), 0.0)),
        "asset_ids": int(_number(summary.get("bar_asset_ids", summary.get("bar_symbols")), 0.0)),
        "blockers": blockers,
        "bar_trade_dates_by_year": year_counts,
        "missing_years": _missing_required_years(date_end, required_start, year_counts) if date_end else [],
        "thin_years": _thin_required_years(date_end, year_counts) if date_end else [],
    }


def build_long_cycle_replay_pack(
    candidate_rows: list[dict[str, Any]] | pd.DataFrame,
    bars: pd.DataFrame,
    *,
    market: str,
    required_start: str = "2015-01-01",
) -> dict[str, Any]:
    coverage = build_long_cycle_coverage(bars, market=market, required_start=required_start)
    return build_long_cycle_replay_pack_from_coverage(
        candidate_rows,
        coverage,
        market=market,
        required_start=required_start,
    )


def build_long_cycle_replay_pack_from_coverage(
    candidate_rows: list[dict[str, Any]] | pd.DataFrame,
    coverage: dict[str, Any],
    *,
    market: str,
    required_start: str = "2015-01-01",
) -> dict[str, Any]:
    registry = build_candidate_registry(candidate_rows)
    source_rows = {str(row.get("case_id")): row for row in _frame(candidate_rows).to_dict(orient="records")}
    decisions = [_candidate_decision(row, source_rows.get(str(row["case_id"]), {}), coverage) for row in registry]
    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "market": market,
        "required_start": required_start,
        "summary": {
            "candidates": len(registry),
            "discard": sum(1 for row in decisions if row["decision_status"] == "discard"),
            "research_lead": sum(1 for row in decisions if row["decision_status"] == "research_lead"),
            "validation_candidate": sum(1 for row in decisions if row["decision_status"] == "validation_candidate"),
            "paper_candidate": sum(1 for row in decisions if row["decision_status"] == "paper_candidate"),
            "reason_counts": _reason_counts(decisions),
            "audit_status_counts": _audit_status_counts(decisions),
            "source_audit_missing_counts": _source_audit_missing_counts(decisions),
        },
        "coverage": coverage,
        "candidate_registry": registry,
        "candidate_decisions": decisions,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    pack["markdown"] = render_long_cycle_replay_markdown(pack)
    return pack


def write_long_cycle_replay_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "long_cycle_replay_pack.json").write_text(
        json.dumps(_sanitize(pack), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "long_cycle_replay_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("candidate_registry", [])).to_csv(output_path / "candidate_registry.csv", index=False)
    pd.DataFrame(pack.get("candidate_decisions", [])).to_csv(output_path / "candidate_decisions.csv", index=False)


def render_long_cycle_replay_markdown(pack: dict[str, Any]) -> str:
    coverage = _dict(pack.get("coverage"))
    summary = _dict(pack.get("summary"))
    lines = [
        "# Long-Cycle Factor Replay",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Market: {pack.get('market', 'unknown')}",
        f"- Candidates: {summary.get('candidates', 0)}",
        f"- Coverage status: {coverage.get('status', 'unknown')}",
        f"- Date range: {coverage.get('date_start')} to {coverage.get('date_end')}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', SAFETY)}",
        "",
        "## Coverage Blockers",
        "",
    ]
    blockers = _list(coverage.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(["", "## Decision Summary", ""])
    lines.extend(
        [
            f"- discard: {summary.get('discard', 0)}",
            f"- research_lead: {summary.get('research_lead', 0)}",
            f"- validation_candidate: {summary.get('validation_candidate', 0)}",
            f"- paper_candidate: {summary.get('paper_candidate', 0)}",
        ]
    )
    lines.extend(["", "## Top Rejection Reasons", ""])
    reason_counts = _dict(summary.get("reason_counts"))
    if reason_counts:
        for reason, count in sorted(reason_counts.items(), key=lambda item: (-int(item[1]), item[0])):
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Audit Status Counts", ""])
    audit_counts = _dict(summary.get("audit_status_counts"))
    if audit_counts:
        for field, counts in sorted(audit_counts.items()):
            rendered = ", ".join(f"{status}={count}" for status, count in sorted(_dict(counts).items()))
            lines.append(f"- {field}: {rendered}")
    else:
        lines.append("- none")
    lines.extend(["", "## Source Audit Missing Counts", ""])
    missing_counts = _dict(summary.get("source_audit_missing_counts"))
    if missing_counts:
        for field, count in sorted(missing_counts.items(), key=lambda item: (-int(item[1]), item[0])):
            lines.append(f"- {field}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Candidate Decisions", ""])
    for row in pack.get("candidate_decisions", []):
        reasons = ", ".join(_list(row.get("reasons"))) or "none"
        lines.append(f"- {row.get('case_id')}: {row.get('decision_status')} ({reasons})")
    return "\n".join(lines) + "\n"


def _candidate_decision(registry_row: dict[str, Any], source_row: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    case_id = str(registry_row.get("case_id", ""))
    reasons: list[str] = []
    if coverage.get("status") != "sufficient":
        reasons.append("long_cycle_coverage_insufficient")
    sharpe = _number(source_row.get("sharpe", source_row.get("discovery_sharpe")), 0.0)
    if sharpe > 3.0:
        reasons.append("high_sharpe_overfit_warning")
    total_return = _number(source_row.get("total_return", source_row.get("discovery_total_return")), 0.0)
    if total_return < 0.0:
        reasons.append("negative_return")
    lookahead_status = _lookahead_audit_status(source_row, reasons)
    cost_capacity_status = _cost_capacity_audit_status(source_row, reasons)
    overlap_status = _overlap_audit_status(source_row, reasons)
    strict_split_status = _strict_split_status(source_row, reasons)
    overfit_status = "warning" if "high_sharpe_overfit_warning" in reasons else "pass"

    if "negative_return" in reasons:
        status = "discard"
    elif reasons:
        status = "research_lead"
    else:
        status = "validation_candidate"

    decision = {
        "case_id": case_id,
        "market": registry_row.get("market"),
        "factor_name": registry_row.get("factor_name"),
        "decision_status": status,
        "replay_status": "blocked" if coverage.get("status") != "sufficient" else "audit_only",
        "reasons": reasons,
        "long_cycle_coverage_status": coverage.get("status"),
        "lookahead_audit_status": lookahead_status,
        "overfit_audit_status": overfit_status,
        "cost_capacity_audit_status": cost_capacity_status,
        "overlap_audit_status": overlap_status,
        "strict_split_status": strict_split_status,
    }
    decision.update(_source_audit_fields(source_row))
    return decision


def _lookahead_audit_status(row: dict[str, Any], reasons: list[str]) -> str:
    lag = _optional_number(row.get("execution_lag", row.get("lag")))
    if lag is None:
        reasons.append("execution_lag_missing")
        return "warning"
    if lag < 1:
        reasons.append("same_day_execution_lag")
        return "block"
    return "pass"


def _cost_capacity_audit_status(row: dict[str, Any], reasons: list[str]) -> str:
    status = "pass"
    cost = _optional_number(row.get("cost_bps", row.get("test_cost_bps")))
    if cost is None:
        reasons.append("transaction_cost_missing")
        status = "warning"
    elif cost <= 0:
        reasons.append("missing_positive_transaction_cost")
        status = "block"
    participation = _optional_number(row.get("max_participation_rate", row.get("test_max_participation_rate")))
    if participation is None:
        reasons.append("capacity_participation_missing")
        return "block" if status == "block" else "warning"
    if participation > 0.01:
        reasons.append("capacity_participation_too_high")
        return "block"
    return status


def _overlap_audit_status(row: dict[str, Any], reasons: list[str]) -> str:
    value = _optional_number(
        row.get(
            "overlap_autocorr_adjusted_sharpe",
            row.get("test_overlap_autocorr_adjusted_sharpe"),
        )
    )
    if value is None:
        reasons.append("overlap_adjusted_sharpe_missing")
        return "warning"
    if abs(value) > 3.0:
        reasons.append("overlap_adjusted_sharpe_overfit_warning")
        return "warning"
    return "pass"


def _strict_split_status(row: dict[str, Any], reasons: list[str]) -> str:
    train_start = _optional_date(row.get("train_start_date"))
    train_end = _optional_date(row.get("train_end_date"))
    test_start = _optional_date(row.get("test_start_date"))
    if test_start is None or (train_start is None and train_end is None):
        reasons.append("strict_split_dates_missing")
        return "warning"
    split_boundary = train_end or train_start
    if test_start <= split_boundary:
        reasons.append("test_starts_before_train_end")
        return "block"
    return "pass"


def _reason_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(reason for row in rows for reason in _list(row.get("reasons")))
    return dict(sorted(counts.items()))


def _audit_status_counts(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    fields = (
        "lookahead_audit_status",
        "overfit_audit_status",
        "cost_capacity_audit_status",
        "overlap_audit_status",
        "strict_split_status",
    )
    result: dict[str, dict[str, int]] = {}
    for field in fields:
        counts = Counter(str(row.get(field) or "missing") for row in rows)
        result[field] = dict(sorted(counts.items()))
    return result


def _source_audit_missing_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    fields = (
        list(SOURCE_AUDIT_TEXT_FIELDS)
        + [output_field for output_field, _ in SOURCE_AUDIT_NUMBER_FIELDS]
        + list(SOURCE_AUDIT_DATE_FIELDS)
    )
    return {
        field: sum(1 for row in rows if _missing(row.get(field)))
        for field in fields
    }


def _source_audit_fields(row: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for field in SOURCE_AUDIT_TEXT_FIELDS:
        value = row.get(field)
        fields[field] = None if _missing(value) else str(value)
    for output_field, source_fields in SOURCE_AUDIT_NUMBER_FIELDS:
        fields[output_field] = _first_optional_number(row, source_fields)
    for field in SOURCE_AUDIT_DATE_FIELDS:
        value = _optional_date(row.get(field))
        fields[field] = value.isoformat() if value else None
    return fields


def _frame(rows: list[dict[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame(rows)


def _market_bars(bars: pd.DataFrame, market: str) -> pd.DataFrame:
    if bars.empty or "date" not in bars.columns:
        return pd.DataFrame()
    if "market" not in bars.columns:
        return bars.copy()
    return bars[bars["market"].astype(str).str.upper() == market.upper()].copy()


def _frozen_parameters(row: dict[str, Any]) -> dict[str, Any]:
    return {field: _sanitize(row[field]) for field in PARAMETER_FIELDS if field in row and not _missing(row[field])}


def _infer_market(case_id: str) -> str:
    if case_id.startswith("CN_ETF_"):
        return "CN_ETF"
    return case_id.split("_", 1)[0] if "_" in case_id else "unknown"


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


def _optional_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _first_optional_number(row: dict[str, Any], fields: tuple[str, ...]) -> float | None:
    for field in fields:
        number = _optional_number(row.get(field))
        if number is not None:
            return number
    return None


def _optional_date(value: Any) -> date | None:
    if value is None:
        return None
    try:
        parsed = pd.to_datetime(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed.date()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _trade_dates_by_year(dates: pd.Series) -> dict[str, int]:
    clean = pd.to_datetime(dates, errors="coerce").dropna()
    if clean.empty:
        return {}
    normalized = clean.dt.date
    grouped = pd.Series(normalized).groupby(pd.Series(normalized).map(lambda value: value.year)).nunique()
    return {str(int(year)): int(count) for year, count in grouped.sort_index().items()}


def _coerce_year_counts(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    counts: dict[str, int] = {}
    for key, raw in value.items():
        try:
            counts[str(int(key))] = int(raw)
        except (TypeError, ValueError):
            continue
    return counts


def _year_coverage_blockers(
    date_start: str | None,
    date_end: str | None,
    required_start: str,
    year_counts: dict[str, int],
) -> list[str]:
    if not date_start or not date_end:
        return []
    blockers = []
    if not year_counts:
        blockers.append("year_coverage_summary_missing")
        return blockers
    if _missing_required_years(date_end, required_start, year_counts):
        blockers.append("missing_required_years")
    if _thin_required_years(date_end, year_counts):
        blockers.append("thin_required_years")
    return blockers


def _missing_required_years(
    date_end: str | None,
    required_start: str,
    year_counts: dict[str, int],
) -> list[int]:
    if not date_end:
        return []
    required_year = pd.to_datetime(required_start).year
    end_year = pd.to_datetime(date_end).year
    return [year for year in range(required_year, end_year + 1) if int(year_counts.get(str(year), 0)) <= 0]


def _thin_required_years(
    date_end: str | None,
    year_counts: dict[str, int],
    *,
    minimum_trade_dates: int = 180,
) -> list[int]:
    if not date_end:
        return []
    end_year = pd.to_datetime(date_end).year
    return [
        int(year)
        for year_text, count in sorted(year_counts.items())
        for year in [int(year_text)]
        if year < end_year and int(count) < minimum_trade_dates
    ]


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
