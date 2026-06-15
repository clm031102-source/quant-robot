from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quant_robot.ops.duplicate_registry import build_duplicate_registry


def build_promotion_operations_console(
    promotion_report: str | Path,
    provider_status: str | Path | None = None,
    quality_report: str | Path | None = None,
    paper_observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = _read_json(promotion_report)
    providers = _read_optional_json(provider_status)
    quality = _read_optional_json(quality_report)
    candidates = sorted(report.get("candidates", []), key=lambda row: int(row.get("promotion_rank", 999999)))
    duplicate_registry = build_duplicate_registry(report)
    summary = _summary(report.get("summary", {}), candidates)
    top = _top_candidate(candidates)
    live_review_blockers = _live_review_blockers(top, providers, quality)
    return {
        "stage": "phase_2_8_promotion_operations",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_report": str(promotion_report),
        "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
        "summary": summary,
        "live_review_allowed": bool(summary.get("manual_live_review", 0)) and not live_review_blockers,
        "live_review_blockers": live_review_blockers,
        "top_candidate": _candidate_card(top),
        "candidates": [_candidate_card(candidate) for candidate in candidates],
        "duplicate_clusters": _duplicate_clusters(candidates),
        "duplicate_registry_summary": duplicate_registry["summary"],
        "duplicate_canonical_registry": duplicate_registry["canonical_registry"],
        "duplicate_members": duplicate_registry["duplicate_members"],
        "evidence": _evidence_status(providers, quality, paper_observation, summary, top),
        "next_actions": _next_actions(live_review_blockers, summary, paper_observation),
    }


def _read_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _read_optional_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    target = Path(path)
    if not target.exists():
        return None
    return _read_json(target)


def _summary(existing: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, int]:
    if existing:
        return {str(key): int(value) for key, value in existing.items()}
    statuses = [str(candidate.get("promotion_status", "unknown")) for candidate in candidates]
    return {
        "candidates": len(candidates),
        "blocked": statuses.count("blocked"),
        "research_only": statuses.count("research_only"),
        "paper_ready": statuses.count("paper_ready"),
        "manual_live_review": statuses.count("manual_live_review"),
        "duplicates": sum(1 for candidate in candidates if candidate.get("duplicate_of")),
    }


def _top_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    for status in ("manual_live_review", "paper_ready", "research_only"):
        for candidate in candidates:
            if str(candidate.get("promotion_status")) == status:
                return candidate
    return candidates[0] if candidates else None


def _candidate_card(candidate: dict[str, Any] | None) -> dict[str, Any] | None:
    if candidate is None:
        return None
    paper = candidate.get("paper", {}) if isinstance(candidate.get("paper"), dict) else {}
    walk = candidate.get("walk_forward", {}) if isinstance(candidate.get("walk_forward"), dict) else {}
    return {
        "rank": candidate.get("promotion_rank"),
        "case_id": candidate.get("case_id"),
        "market": candidate.get("market"),
        "factor_name": candidate.get("factor_name"),
        "promotion_status": candidate.get("promotion_status"),
        "score": candidate.get("score"),
        "risk_profile_id": paper.get("risk_profile_id"),
        "paper_matched": paper.get("matched"),
        "paper_sharpe": paper.get("sharpe"),
        "paper_max_drawdown": paper.get("max_drawdown"),
        "test_sharpe": walk.get("test_sharpe"),
        "test_relative_return": walk.get("test_relative_return"),
        "test_trades": walk.get("test_trades"),
        "blocking_reasons": list(candidate.get("blocking_reasons", [])),
        "warnings": list(candidate.get("warnings", [])),
        "duplicate_of": candidate.get("duplicate_of"),
    }


def _live_review_blockers(
    top_candidate: dict[str, Any] | None,
    provider_status: dict[str, Any] | None,
    quality_report: dict[str, Any] | None,
) -> list[str]:
    blockers: list[str] = []
    if top_candidate is None:
        blockers.append("no_promotable_candidate")
        return blockers
    blockers.extend(str(value) for value in top_candidate.get("blocking_reasons", []))
    warning_blockers = _live_review_warnings(top_candidate)
    if provider_status is None:
        blockers.append("provider_status_missing")
    else:
        providers = provider_status.get("providers", {})
        if isinstance(providers, dict):
            if not _candidate_market_provider_ready(top_candidate, providers):
                blockers.append("providers_not_ready_for_live_review")
            else:
                warning_blockers = [reason for reason in warning_blockers if reason != "providers_not_ready_for_live_review"]
    blockers.extend(warning_blockers)
    if quality_report is None:
        blockers.append("quality_report_missing")
    else:
        if float(quality_report.get("duplicate_bars", 0) or 0) > 0:
            blockers.append("duplicate_bars_present")
        if float(quality_report.get("missing_date_rows", 0) or 0) > 0:
            blockers.append("missing_dates_present")
        if float(quality_report.get("zero_volume_rows", 0) or 0) > 0:
            blockers.append("zero_volume_rows_present")
    if str(top_candidate.get("promotion_status")) != "manual_live_review":
        blockers.append("manual_live_review_not_enabled")
    return _dedupe(blockers)


def _live_review_warnings(candidate: dict[str, Any]) -> list[str]:
    live_review_warnings = {
        "providers_not_ready_for_live_review",
        "provider_status_missing",
        "quality_report_missing",
        "missing_dates_present",
        "zero_volume_rows_present",
    }
    return [str(value) for value in candidate.get("warnings", []) if str(value) in live_review_warnings]


def _duplicate_clusters(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_canonical: dict[str, list[str]] = {}
    for candidate in candidates:
        duplicate_of = candidate.get("duplicate_of")
        if duplicate_of:
            by_canonical.setdefault(str(duplicate_of), []).append(str(candidate.get("case_id")))
    return [
        {"canonical_case_id": canonical, "duplicates": duplicates, "duplicate_count": len(duplicates)}
        for canonical, duplicates in sorted(by_canonical.items())
    ]


def _evidence_status(
    provider_status: dict[str, Any] | None,
    quality_report: dict[str, Any] | None,
    paper_observation: dict[str, Any] | None,
    summary: dict[str, int],
    top_candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    providers = provider_status.get("providers", {}) if provider_status else {}
    paper_summary = paper_observation.get("summary", {}) if isinstance(paper_observation, dict) else {}
    observed = int(float(paper_summary.get("observed_candidates", 0) or 0)) if isinstance(paper_summary, dict) else 0
    completed = int(float(paper_summary.get("completed_candidates", 0) or 0)) if isinstance(paper_summary, dict) else 0
    market_ready, market_total = _candidate_market_provider_counts(top_candidate, providers if isinstance(providers, dict) else {})
    return {
        "provider_status_present": provider_status is not None,
        "quality_report_present": quality_report is not None,
        "providers_ready": bool(providers) and all(bool(provider.get("ready")) for provider in providers.values() if isinstance(provider, dict)),
        "candidate_market_provider_ready": market_ready > 0,
        "candidate_market_ready_providers": market_ready,
        "candidate_market_providers": market_total,
        "missing_date_rows": int(float(quality_report.get("missing_date_rows", 0) or 0)) if quality_report else None,
        "duplicate_bars": int(float(quality_report.get("duplicate_bars", 0) or 0)) if quality_report else None,
        "zero_volume_rows": int(float(quality_report.get("zero_volume_rows", 0) or 0)) if quality_report else None,
        "paper_observation_present": paper_observation is not None,
        "paper_observed_candidates": observed,
        "paper_completed_candidates": completed,
        "paper_observation_complete": _paper_observation_complete(summary, paper_observation),
    }


def _next_actions(blockers: list[str], summary: dict[str, int], paper_observation: dict[str, Any] | None = None) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    if "missing_dates_present" in blockers or "quality_report_missing" in blockers:
        actions.append({"action": "refresh_data_quality", "reason": "local evidence still has missing or stale quality coverage"})
    if "providers_not_ready_for_live_review" in blockers or "provider_status_missing" in blockers:
        actions.append({"action": "refresh_provider_status", "reason": "manual review cannot start until provider readiness is explicit"})
    if summary.get("paper_ready", 0) > 0 and not _paper_observation_complete(summary, paper_observation):
        actions.append({"action": "extend_paper_observation", "reason": "paper-ready candidates need more local evidence before any API boundary"})
    if summary.get("duplicates", 0) > 0:
        actions.append({"action": "collapse_duplicate_candidates", "reason": "duplicate signal clusters should not be counted as independent edges"})
    if not actions:
        actions.append({"action": "rerun_promotion_gate", "reason": "refresh the evidence set before changing phase state"})
    return actions


def _paper_observation_complete(summary: dict[str, int], paper_observation: dict[str, Any] | None) -> bool:
    if not isinstance(paper_observation, dict):
        return False
    paper_summary = paper_observation.get("summary", {})
    if not isinstance(paper_summary, dict):
        return False
    observed = int(float(paper_summary.get("observed_candidates", 0) or 0))
    completed = int(float(paper_summary.get("completed_candidates", 0) or 0))
    required = max(1, int(summary.get("paper_ready", 0) or 0))
    return observed >= required and completed >= required


def _candidate_market_provider_ready(top_candidate: dict[str, Any] | None, providers: dict[str, Any]) -> bool:
    ready, _total = _candidate_market_provider_counts(top_candidate, providers)
    return ready > 0


def _candidate_market_provider_counts(top_candidate: dict[str, Any] | None, providers: dict[str, Any]) -> tuple[int, int]:
    market = str(top_candidate.get("market", "")) if isinstance(top_candidate, dict) else ""
    if not market:
        ready = sum(1 for provider in providers.values() if isinstance(provider, dict) and bool(provider.get("ready")))
        total = sum(1 for provider in providers.values() if isinstance(provider, dict))
        return ready, total
    ready = 0
    total = 0
    for provider in providers.values():
        if not isinstance(provider, dict):
            continue
        markets = [str(value) for value in provider.get("markets", [])] if isinstance(provider.get("markets", []), list) else []
        if market not in markets:
            continue
        total += 1
        if bool(provider.get("ready")):
            ready += 1
    return ready, total


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
