from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable


STAGE = "analyst_report_quota_preflight"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
DEFAULT_MAX_DAILY_REQUESTS = 2
COUNTED_WINDOW_STATUSES = {"ok", "cap_warning", "failed"}


def build_analyst_report_quota_preflight(
    *,
    report_roots: Iterable[str | Path],
    target_date: str | None = None,
    max_daily_requests: int = DEFAULT_MAX_DAILY_REQUESTS,
) -> dict[str, Any]:
    target = target_date or date.today().isoformat()
    rows = _scan_cache_reports(report_roots=report_roots, target_date=target)
    counted = [row for row in rows if row["counts_against_quota"]]
    rate_limited = [row for row in rows if row.get("provider_rate_limit")]
    next_retry_values = [
        int(row["retry_after_seconds"])
        for row in rate_limited
        if row.get("retry_after_seconds") is not None
    ]
    blockers: list[str] = []
    if rate_limited:
        blockers.append("provider_rate_limit_observed")
    if len(counted) >= int(max_daily_requests):
        blockers.append("daily_provider_request_budget_exhausted")

    packet = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "target_date": target,
        "max_daily_requests": int(max_daily_requests),
        "summary": {
            "cache_report_count": len({row["report_path"] for row in rows}),
            "same_day_window_rows": len(rows),
            "counted_provider_request_windows": len(counted),
            "rate_limited_windows": len(rate_limited),
            "remaining_request_windows": max(0, int(max_daily_requests) - len(counted)),
            "next_retry_after_seconds": max(next_retry_values) if next_retry_values else None,
        },
        "window_rows": rows,
        "decision": {
            "request_allowed": not blockers,
            "blockers": blockers,
            "next_action": "run_cache_once" if not blockers else "wait_or_review_provider_quota",
        },
        "safety": SAFETY,
        "live_boundary_allowed": False,
    }
    packet["markdown"] = render_analyst_report_quota_preflight_markdown(packet)
    return packet


def write_analyst_report_quota_preflight(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(packet)
    (output_path / "analyst_report_quota_preflight.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "analyst_report_quota_preflight.md").write_text(
        render_analyst_report_quota_preflight_markdown(clean),
        encoding="utf-8",
    )


def render_analyst_report_quota_preflight_markdown(packet: dict[str, Any]) -> str:
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    blockers = _list(decision.get("blockers"))
    lines = [
        "# Analyst Report Quota Preflight",
        "",
        f"- Stage: {packet.get('stage', STAGE)}",
        f"- Target date: {packet.get('target_date', '')}",
        f"- Max daily requests: {packet.get('max_daily_requests', DEFAULT_MAX_DAILY_REQUESTS)}",
        f"- Counted provider request windows: {summary.get('counted_provider_request_windows', 0)}",
        f"- Rate-limited windows: {summary.get('rate_limited_windows', 0)}",
        f"- Remaining request windows: {summary.get('remaining_request_windows', 0)}",
        f"- Request allowed: {decision.get('request_allowed', False)}",
        f"- Live boundary allowed: {packet.get('live_boundary_allowed', False)}",
        f"- Safety: {packet.get('safety', SAFETY)}",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(
        [
            "",
            "## Counted Windows",
            "",
            "| Report | Window | Status | Counts | Rate Limit |",
            "|---|---|---|---:|---|",
        ]
    )
    for row in _list_of_dicts(packet.get("window_rows")):
        if not row.get("counts_against_quota") and not row.get("provider_rate_limit"):
            continue
        lines.append(
            "| {path} | {start}..{end} | {status} | {counts} | {limit} |".format(
                path=row.get("report_path", ""),
                start=row.get("window_start", ""),
                end=row.get("window_end", ""),
                status=row.get("status", ""),
                counts=row.get("counts_against_quota", False),
                limit=row.get("provider_rate_limit", "") or "none",
            )
        )
    return "\n".join(lines) + "\n"


def _scan_cache_reports(*, report_roots: Iterable[str | Path], target_date: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in _cache_report_paths(report_roots):
        packet = _load_json(path)
        if packet.get("stage") != "tushare_analyst_report_cache":
            continue
        if packet.get("source") != "tushare_report_rc":
            continue
        if packet.get("generated_at") != target_date:
            continue
        for item in _list_of_dicts(packet.get("rows_by_window")):
            status = str(item.get("status", ""))
            rate_limit = item.get("provider_rate_limit")
            rows.append(
                {
                    "report_path": str(path),
                    "generated_at": str(packet.get("generated_at", "")),
                    "window_start": str(item.get("window_start", "")),
                    "window_end": str(item.get("window_end", "")),
                    "status": status,
                    "counts_against_quota": status in COUNTED_WINDOW_STATUSES,
                    "provider_rate_limit": str(rate_limit) if rate_limit else "",
                    "retry_after_seconds": item.get("retry_after_seconds"),
                }
            )
    return rows


def _cache_report_paths(report_roots: Iterable[str | Path]) -> list[Path]:
    paths: list[Path] = []
    for root in report_roots:
        root_path = Path(root)
        if root_path.is_file() and root_path.name == "tushare_analyst_report_cache.json":
            paths.append(root_path)
        elif root_path.exists():
            paths.extend(root_path.rglob("tushare_analyst_report_cache.json"))
    return sorted(set(paths))


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value
