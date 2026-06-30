from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


LEDGER_PATH = Path("data/reports/gui_operation_ledger/gui_operation_ledger.json")
MAX_LEDGER_ENTRIES = 50
SAFETY_NOTICE = "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading."


def append_operation_ledger_entry(
    *,
    repo_root: str | Path,
    workflow_id: str,
    label: str,
    status: str,
    command: str = "",
    request: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    entry = _build_entry(
        workflow_id=workflow_id,
        label=label,
        status=status,
        command=command,
        request=request or {},
        result=result or {},
    )
    packet = _read_packet(root)
    rows = [entry, *packet.get("rows", [])][:MAX_LEDGER_ENTRIES]
    packet = _packet(rows)
    _write_packet(root, packet)
    return entry


def build_operation_ledger_snapshot(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    packet = _read_packet(root)
    rows = packet.get("rows", [])
    return _packet(rows)


def build_daily_closure_ledger_snapshot(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    packet = _read_packet(root)
    grouped: dict[str, dict[str, Any]] = {}
    for entry in packet.get("rows", []):
        if not isinstance(entry, dict):
            continue
        workflow_id = str(entry.get("workflow_id") or "")
        if workflow_id not in {"daily_trade_advisory", "paper_simulation", "post_close_journal"}:
            continue
        date_key = _closure_date_key(entry)
        if not date_key:
            continue
        row = grouped.setdefault(date_key, _empty_closure_row(date_key))
        _apply_closure_entry(row, entry)

    rows = [_finalize_closure_row(row) for row in grouped.values()]
    rows.sort(key=lambda item: str(item.get("date") or ""), reverse=True)
    rows = rows[:5]
    closed = sum(1 for row in rows if row.get("completed_loop"))
    blocked = sum(
        1
        for row in rows
        if row.get("manual_execution_blocked") or row.get("manual_execution_missing_review")
    )
    clean = sum(1 for row in rows if row.get("manual_execution_clean"))
    status = (
        "server_closure_ready"
        if len(rows) >= 5 and closed >= 5 and blocked == 0
        else "blocked_by_manual_execution"
        if blocked
        else "needs_more_closure_receipts"
    )
    return {
        "stage": "gui_daily_closure_ledger",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "summary": {
            "status": status,
            "server_observed_days": len(rows),
            "closed_loop_days": closed,
            "clean_execution_days": clean,
            "blocked_execution_days": blocked,
            "lookback_days": 5,
            "source": LEDGER_PATH.as_posix(),
            "next_action": _closure_next_action(rows),
            "paper_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "auto_order_allowed": False,
        },
        "rows": rows,
        "safety": _safety(),
    }


def _build_entry(
    *,
    workflow_id: str,
    label: str,
    status: str,
    command: str,
    request: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    metrics = result.get("metrics", {}) if isinstance(result.get("metrics"), dict) else {}
    return {
        "operation_id": f"{workflow_id}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}",
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "workflow_id": workflow_id,
        "label": label,
        "status": status,
        "command": command,
        "request": _json_safe(request),
        "metrics": _json_safe(metrics),
        "request_summary": _request_summary(request),
        "metric_summary": _metric_summary(metrics, result),
        "stage": result.get("stage", ""),
        "safety": _safety(),
    }


def _packet(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest = rows[0] if rows else {}
    return {
        "stage": "gui_operation_ledger",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "summary": {
            "entry_count": len(rows),
            "max_entries": MAX_LEDGER_ENTRIES,
            "latest_workflow_id": latest.get("workflow_id", ""),
            "latest_status": latest.get("status", ""),
            "path": LEDGER_PATH.as_posix(),
            "paper_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
        },
        "rows": rows,
        "safety": _safety(),
    }


def _read_packet(root: Path) -> dict[str, Any]:
    path = root / LEDGER_PATH
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _packet([])
    rows = packet.get("rows", [])
    if not isinstance(rows, list):
        rows = []
    return _packet([row for row in rows if isinstance(row, dict)][:MAX_LEDGER_ENTRIES])


def _write_packet(root: Path, packet: dict[str, Any]) -> None:
    path = root / LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")


def _request_summary(request: dict[str, Any]) -> str:
    keys = [
        "market",
        "factor_name",
        "factor",
        "top_n",
        "cost_bps",
        "as_of_date",
        "run_date",
        "start_date",
        "end_date",
        "initial_cash",
        "gate_id",
    ]
    parts = [f"{key}={request[key]}" for key in keys if request.get(key) not in {None, ""}]
    return " / ".join(parts)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _metric_summary(metrics: dict[str, Any], result: dict[str, Any]) -> str:
    metric_keys = [
        "total_return",
        "annualized_return",
        "sharpe",
        "max_drawdown",
        "win_rate",
        "ending_equity",
        "target_count",
        "signal_count",
        "manual_ticket_count",
        "manual_execution_decision",
        "manual_execution_missing_review_count",
        "manual_execution_guardrail_breach_count",
        "manual_execution_slippage_breach_count",
        "returncode",
    ]
    values: list[str] = []
    for key in metric_keys:
        value = metrics.get(key, result.get(key))
        if value not in {None, ""}:
            values.append(f"{key}={_format_metric(value)}")
    return " / ".join(values) or str(result.get("status", ""))


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _safety() -> dict[str, Any]:
    return {
        "notice": SAFETY_NOTICE,
        "paper_only": True,
        "live_trading_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
    }


def _closure_date_key(entry: dict[str, Any]) -> str:
    request = entry.get("request", {}) if isinstance(entry.get("request"), dict) else {}
    candidates = [
        request.get("as_of_date"),
        request.get("run_date"),
        request.get("end_date"),
        entry.get("recorded_at"),
    ]
    for value in candidates:
        key = _normalize_date_key(value)
        if key:
            return key
    return ""


def _normalize_date_key(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def _empty_closure_row(date_key: str) -> dict[str, Any]:
    return {
        "date": date_key,
        "top3_signal_ready": False,
        "same_parameter_paper_ready": False,
        "post_close_journal_ready": False,
        "manual_execution_clean": False,
        "manual_execution_blocked": False,
        "manual_execution_missing_review": False,
        "latest_daily_trade_receipt": "",
        "latest_paper_receipt": "",
        "latest_post_close_receipt": "",
        "missing_steps": [],
        "completed_loop": False,
    }


def _apply_closure_entry(row: dict[str, Any], entry: dict[str, Any]) -> None:
    workflow_id = str(entry.get("workflow_id") or "")
    status = str(entry.get("status") or "")
    if status not in {"completed", "passed"}:
        return
    metrics = entry.get("metrics", {}) if isinstance(entry.get("metrics"), dict) else {}
    request = entry.get("request", {}) if isinstance(entry.get("request"), dict) else {}
    recorded_at = str(entry.get("recorded_at") or "")
    if workflow_id == "daily_trade_advisory":
        signal_count = _num(metrics.get("signal_count"), _num(request.get("signal_count"), 0.0))
        selected_count = _num(metrics.get("selected_factor_count"), _num(request.get("selected_factor_count"), 0.0))
        if signal_count > 0 or selected_count > 0:
            row["top3_signal_ready"] = True
            row["latest_daily_trade_receipt"] = recorded_at
    elif workflow_id == "paper_simulation":
        row["same_parameter_paper_ready"] = True
        row["latest_paper_receipt"] = recorded_at
    elif workflow_id == "post_close_journal":
        row["post_close_journal_ready"] = bool(metrics.get("manual_review_recorded", True))
        row["latest_post_close_receipt"] = recorded_at
        status_text = str(metrics.get("manual_execution_decision") or "")
        missing = _num(metrics.get("manual_execution_missing_review_count"), 0.0)
        blocked = (
            _num(metrics.get("manual_execution_guardrail_breach_count"), 0.0)
            + _num(metrics.get("manual_execution_slippage_breach_count"), 0.0)
            + _num(metrics.get("manual_execution_blocked_count"), 0.0)
        )
        if status_text == "manual_execution_evidence_ready" and missing <= 0 and blocked <= 0:
            row["manual_execution_clean"] = True
        elif status_text == "manual_execution_review_incomplete" or missing > 0:
            row["manual_execution_missing_review"] = True
        elif status_text == "guardrail_breach_review_required" or blocked > 0:
            row["manual_execution_blocked"] = True


def _finalize_closure_row(row: dict[str, Any]) -> dict[str, Any]:
    missing = []
    if not row.get("top3_signal_ready"):
        missing.append("daily_trade_advisory")
    if not row.get("same_parameter_paper_ready"):
        missing.append("paper_simulation")
    if not row.get("post_close_journal_ready"):
        missing.append("post_close_journal")
    if not row.get("manual_execution_clean"):
        missing.append("manual_execution_clean")
    completed = not missing and not row.get("manual_execution_blocked") and not row.get("manual_execution_missing_review")
    return {
        **row,
        "missing_steps": missing,
        "completed_loop": completed,
        "live_trading_allowed": False,
        "order_placement_allowed": False,
    }


def _closure_next_action(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Run daily trade advisory, paper simulation, and post-close review to start the server-side closure ledger."
    latest = rows[0]
    if latest.get("completed_loop"):
        return "Continue collecting five clean server-side closure days before any small-capital observation."
    missing = latest.get("missing_steps") if isinstance(latest.get("missing_steps"), list) else []
    return "Refresh missing closure step: " + (" / ".join(str(item) for item in missing) or "manual review")


def _num(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
