from __future__ import annotations

import json
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
