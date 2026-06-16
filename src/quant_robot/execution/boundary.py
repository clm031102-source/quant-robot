from __future__ import annotations

from datetime import date
from typing import Any


def build_execution_boundary_status() -> dict[str, Any]:
    return {
        "generated_at": date.today().isoformat(),
        "broker_connection": "disabled",
        "account_reads": "disabled",
        "order_placement": "disabled",
        "live_order_allowed": False,
        "kill_switch_enabled": True,
        "safety": "Research-only boundary. No broker connection, no account reads, no order placement, no live trading.",
    }


def build_manual_approval_packet(candidate: dict[str, Any], reviewer: str | None = None) -> dict[str, Any]:
    return {
        "generated_at": date.today().isoformat(),
        "reviewer": reviewer,
        "candidate": dict(candidate),
        "requires_manual_approval": True,
        "executable": False,
        "boundary": build_execution_boundary_status(),
    }


def refuse_live_execution(request: dict[str, Any] | None = None) -> None:
    _ = request
    raise PermissionError("Live execution is disabled by the research-only execution boundary.")
