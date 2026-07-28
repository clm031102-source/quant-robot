from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


STAGE = "cn_etf_external_data_unlock_review"
SAFETY = (
    "Source-access review only. No factor, forward return, portfolio, walk-forward, "
    "final holdout, paper signal, broker, account, order, or live-trading access."
)


def classify_external_data_probe(
    *,
    endpoint: str,
    route: str,
    required_points: int | None,
    frame: pd.DataFrame | None = None,
    error: Exception | None = None,
    required_columns: Iterable[str] = (),
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if (frame is None) == (error is None):
        raise ValueError("provide exactly one of frame or error")
    probe = {
        "route": str(route),
        "endpoint": str(endpoint),
        "required_points": int(required_points) if required_points is not None else None,
        "parameters": _public_parameters(parameters or {}),
        "full_history_ready": False,
    }
    if error is not None:
        category = _error_category(error)
        return {
            **probe,
            "status": category,
            "rows": 0,
            "columns": [],
            "missing_required_columns": sorted(str(value) for value in required_columns),
            "error_type": type(error).__name__,
        }
    assert frame is not None
    columns = sorted(str(column) for column in frame.columns)
    missing = sorted(set(str(value) for value in required_columns) - set(columns))
    if frame.empty:
        status = "empty_response"
    elif missing:
        status = "schema_mismatch"
    else:
        status = "probe_ready"
    return {
        **probe,
        "status": status,
        "rows": int(len(frame)),
        "columns": columns,
        "missing_required_columns": missing,
        "error_type": None,
    }


def summarize_cn_etf_external_data_unlock(
    probes: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    rows = sorted(
        (dict(probe) for probe in probes),
        key=lambda item: (
            str(item.get("route", "")),
            str(item.get("endpoint", "")),
            json.dumps(item.get("parameters", {}), sort_keys=True),
        ),
    )
    routes: dict[str, dict[str, Any]] = {}
    for probe in rows:
        route = str(probe["route"])
        summary = routes.setdefault(
            route,
            {
                "probes": 0,
                "ready_probes": 0,
                "permission_denied_probes": 0,
                "empty_probes": 0,
                "schema_blocked_probes": 0,
                "rate_limited_probes": 0,
                "provider_error_probes": 0,
                "full_history_ready": False,
            },
        )
        summary["probes"] += 1
        status = str(probe.get("status"))
        summary["ready_probes"] += int(status == "probe_ready")
        summary["permission_denied_probes"] += int(status == "permission_denied")
        summary["empty_probes"] += int(status == "empty_response")
        summary["schema_blocked_probes"] += int(status == "schema_mismatch")
        summary["rate_limited_probes"] += int(status == "rate_limited")
        summary["provider_error_probes"] += int(status == "provider_error")
    pcf = routes.get("historical_pcf", {})
    pcf_ready = (
        int(pcf.get("probes", 0)) > 0
        and int(pcf.get("ready_probes", 0)) == int(pcf.get("probes", 0))
    )
    status = "probe_ready_backfill_required" if pcf_ready else "blocked_external_data_access"
    next_action = (
        "backfill_and_audit_historical_pcf"
        if pcf_ready
        else "unlock_historical_pcf_first"
    )
    return {
        "stage": STAGE,
        "status": status,
        "safety": SAFETY,
        "probes": rows,
        "routes": routes,
        "decision": {
            "next_action": next_action,
            "historical_pcf_probe_ready": pcf_ready,
            "full_history_ready": False,
            "factor_generation_allowed": False,
            "forward_return_read_allowed": False,
            "portfolio_grid_allowed": False,
            "walk_forward_allowed": False,
            "final_holdout_allowed": False,
            "paper_signal_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "live_boundary_allowed": False,
        },
        "procurement_priority": [
            {
                "priority": 1,
                "source": "historical_daily_etf_pcf_constituents",
                "minimum_scope": "SSE and SZSE, 2020-01-02 through 2024-06-28",
                "required_fields": [
                    "trade_date",
                    "ts_code",
                    "con_code",
                    "qty",
                    "sub_flag",
                    "cpr",
                    "rdr",
                    "cash_substitution_amounts",
                ],
            },
            {
                "priority": 2,
                "source": "point_in_time_etf_tracking_index_and_index_weights",
                "minimum_scope": "historical ETF-to-index mapping plus dated index constituents",
            },
            {
                "priority": 3,
                "source": "historical_etf_iopv_premium_minute_data",
                "minimum_scope": "timestamped price and IOPV with exchange and session coverage",
            },
        ],
    }


def write_cn_etf_external_data_unlock(
    output_dir: str | Path,
    result: dict[str, Any],
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / f"{STAGE}.json",
        "markdown": output / f"{STAGE}.md",
        "probes": output / "source_access_probes.csv",
    }
    paths["json"].write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["markdown"].write_text(render_cn_etf_external_data_unlock(result), encoding="utf-8")
    probe_frame = pd.DataFrame(result.get("probes", []))
    if not probe_frame.empty:
        for column in ("parameters", "columns", "missing_required_columns"):
            if column in probe_frame:
                probe_frame[column] = probe_frame[column].map(
                    lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False)
                )
        probe_frame = probe_frame.sort_values(
            ["route", "endpoint", "parameters"],
            kind="stable",
        ).reset_index(drop=True)
    probe_frame.to_csv(paths["probes"], index=False)
    return paths


def render_cn_etf_external_data_unlock(result: dict[str, Any]) -> str:
    decision = result.get("decision", {})
    lines = [
        "# CN ETF External Data Unlock Review",
        "",
        f"- Status: `{result.get('status', 'unknown')}`",
        f"- Next action: `{decision.get('next_action', 'n/a')}`",
        "- Full-history source ready: false",
        "- Factor generation allowed: false",
        "- Final holdout included: false",
        "- Live boundary allowed: false",
        "",
        "## Access probes",
        "",
        "| Route | Endpoint | Status | Rows | Required points |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for probe in result.get("probes", []):
        points = probe.get("required_points")
        lines.append(
            "| {route} | {endpoint} | {status} | {rows} | {points} |".format(
                route=probe.get("route", ""),
                endpoint=probe.get("endpoint", ""),
                status=probe.get("status", ""),
                rows=int(probe.get("rows", 0)),
                points="" if points is None else int(points),
            )
        )
    lines.extend(
        [
            "",
            "A successful probe is access evidence only. It does not authorize factor "
            "generation until the complete historical source is backfilled, fingerprinted, "
            "point-in-time aligned, and quality-audited.",
            "",
        ]
    )
    return "\n".join(lines)


def _error_category(error: Exception) -> str:
    message = str(error).lower()
    markers = (
        "permission denied",
        "access permission",
        "访问权限",
        "无权限",
        "权限",
        "娌℃湁鎺ュ彛",
        "璁块棶鏉冮檺",
        "鏃犳潈闄",
    )
    if any(marker in message for marker in markers):
        return "permission_denied"
    if "frequency" in message or "rate limit" in message or "每分钟" in message:
        return "rate_limited"
    return "provider_error"


def _public_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    blocked = {"token", "credential", "secret", "password", "key"}
    return {
        str(key): _sanitize(value)
        for key, value in sorted(parameters.items())
        if not any(marker in str(key).lower() for marker in blocked)
    }


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, (pd.Timestamp, date)):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


__all__ = [
    "SAFETY",
    "STAGE",
    "classify_external_data_probe",
    "render_cn_etf_external_data_unlock",
    "summarize_cn_etf_external_data_unlock",
    "write_cn_etf_external_data_unlock",
]
