from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_5_7_tushare_recent_data_refresh"
DEFAULT_OUTPUT_DIR = Path("data/processed/tushare_etf_recent")


def build_recent_data_refresh_pack(
    profile_observation_pack: dict[str, Any],
    *,
    readiness: dict[str, Any] | None = None,
    ingest_result: dict[str, Any] | None = None,
    execute: bool = False,
    machine: str | None = None,
    workstation_config: dict[str, Any] | None = None,
    source: str = "tushare",
    market: str = "CN_ETF",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    readiness_pack = readiness or {"ready": False, "missing": []}
    target_window = resolve_refresh_window(profile_observation_pack, start_date=start_date, end_date=end_date)
    coverage = _coverage_from_ingest(ingest_result, target_window, profile_observation_pack)
    workstation = build_workstation_refresh_context(machine, workstation_config)
    can_run_data_pipeline = bool(workstation.get("can_run_data_pipeline", True))
    readiness_missing = list(readiness_pack.get("missing", [])) if isinstance(readiness_pack.get("missing", []), list) else []
    source_name = source.strip().lower()
    readiness_blocks = source_name == "tushare" and not bool(readiness_pack.get("ready", False))
    effective_execute = bool(execute and can_run_data_pipeline)
    will_download = bool(effective_execute and not readiness_blocks)

    if readiness_blocks:
        status = "blocked"
    elif not effective_execute:
        status = "ready_to_execute" if bool(readiness_pack.get("ready", False)) or source_name == "tushare-fixture" else "blocked"
    elif coverage["coverage_status"] == "pass":
        status = "completed"
    else:
        status = "data_quality_blocked"

    blockers = _decision_blockers(status, readiness_missing, coverage)
    stale_cleared = status == "completed" and coverage["coverage_status"] == "pass"
    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "source": source_name,
        "market": market.upper(),
        "mode": "execute" if effective_execute else "dry_run",
        "execute_requested": bool(execute),
        "will_download": will_download,
        "output_dir": str(output_dir),
        "target_window": target_window,
        "workstation": workstation,
        "readiness": readiness_pack,
        "ingest": ingest_result or {},
        "coverage": coverage,
        "decision": {
            "signal_data_stale_cleared": stale_cleared,
            "recent_data_ready": stale_cleared,
            "blockers": blockers,
            "next_daily_ops_allowed": stale_cleared,
        },
        "live_boundary_allowed": False,
        "safety": _safety(),
    }
    pack["next_actions"] = _next_actions(pack)
    pack["markdown"] = render_recent_data_refresh_markdown(pack)
    return _sanitize(pack)


def build_workstation_refresh_context(
    machine: str | None = None,
    workstation_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = workstation_config if isinstance(workstation_config, dict) else {}
    machines = config.get("machines", {}) if isinstance(config.get("machines", {}), dict) else {}
    tasks = config.get("tasks", {}) if isinstance(config.get("tasks", {}), dict) else {}
    selected = machines.get(machine, {}) if machine else {}
    selected = selected if isinstance(selected, dict) else {}
    allowed_tasks = _string_list(selected.get("allowed_tasks"))
    data_pipeline_machines = [
        str(name)
        for name, payload in machines.items()
        if isinstance(payload, dict) and "data_pipeline" in _string_list(payload.get("allowed_tasks"))
    ]
    task_config = tasks.get("data_pipeline", {}) if isinstance(tasks.get("data_pipeline", {}), dict) else {}
    if machine:
        can_run_data_pipeline = "data_pipeline" in allowed_tasks
    else:
        can_run_data_pipeline = True
    return {
        "machine": machine,
        "allowed_tasks": allowed_tasks,
        "can_run_data_pipeline": can_run_data_pipeline,
        "data_pipeline_machines": data_pipeline_machines,
        "data_pipeline_branch": task_config.get("branch"),
    }


def resolve_refresh_window(
    profile_observation_pack: dict[str, Any],
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    ledger = profile_observation_pack.get("ledger", [])
    first_ledger = ledger[0] if isinstance(ledger, list) and ledger and isinstance(ledger[0], dict) else {}
    signal_date = start_date or str(first_ledger.get("signal_date") or profile_observation_pack.get("signal_date") or "")
    target_start = start_date or (_next_day(signal_date) if signal_date else None)
    target_end = end_date or str(profile_observation_pack.get("run_date") or date.today().isoformat())
    return {
        "signal_date": signal_date or None,
        "start_date": target_start,
        "end_date": target_end,
        "reason": "refresh bars after the stale signal date through the current observation run date",
    }


def write_recent_data_refresh_pack(report_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(report_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "recent_data_refresh_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "recent_data_refresh_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame([pack.get("coverage", {})]).to_csv(output_path / "recent_data_refresh_coverage.csv", index=False)
    pd.DataFrame(pack.get("next_actions", [])).to_csv(output_path / "recent_data_refresh_next_actions.csv", index=False)


def render_recent_data_refresh_markdown(pack: dict[str, Any]) -> str:
    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    coverage = pack.get("coverage", {}) if isinstance(pack.get("coverage"), dict) else {}
    window = pack.get("target_window", {}) if isinstance(pack.get("target_window"), dict) else {}
    lines = [
        "# Phase 5.7 Tushare Recent Data Refresh",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Status: {pack.get('status', 'unknown')}",
        f"- Mode: {pack.get('mode', 'dry_run')}",
        f"- Source: {pack.get('source', 'tushare')}",
        f"- Market: {pack.get('market', 'CN_ETF')}",
        f"- Target window: {window.get('start_date')} to {window.get('end_date')}",
        f"- Will download: {pack.get('will_download', False)}",
        f"- Signal data stale cleared: {decision.get('signal_data_stale_cleared', False)}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        f"- Safety: {pack.get('safety', _safety())}",
        "",
        "## Coverage",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Coverage status | {coverage.get('coverage_status', 'unknown')} |",
        f"| Latest data date | {coverage.get('latest_data_date')} |",
        f"| Coverage scope | {coverage.get('coverage_scope', 'provider_universe')} |",
        f"| Effective start date | {coverage.get('effective_start_date')} |",
        f"| Effective end date | {coverage.get('effective_end_date')} |",
        f"| Processed rows | {coverage.get('processed_rows')} |",
        f"| Missing date rows | {coverage.get('missing_date_rows')} |",
        f"| Provider missing date rows | {coverage.get('provider_missing_date_rows')} |",
        f"| Duplicate bars | {coverage.get('duplicate_bars')} |",
        f"| Zero-volume rows | {coverage.get('zero_volume_rows')} |",
        "",
        "## Next Actions",
        "",
    ]
    actions = pack.get("next_actions", [])
    if actions:
        lines.extend(f"- {row.get('action')}: {row.get('reason')}" for row in actions if isinstance(row, dict))
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _coverage_from_ingest(
    ingest_result: dict[str, Any] | None,
    target_window: dict[str, Any],
    profile_observation_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not ingest_result:
        return {
            "coverage_status": "missing",
            "coverage_scope": "provider_universe",
            "processed_rows": 0,
            "latest_data_date": None,
            "target_end_covered": False,
            "missing_date_rows": None,
            "duplicate_bars": None,
            "zero_volume_rows": None,
        }
    report = ingest_result.get("quality_report", {}) if isinstance(ingest_result.get("quality_report"), dict) else {}
    latest_date = _date_str(report.get("end_date"))
    earliest_date = _date_str(report.get("start_date"))
    processed_rows = _int(ingest_result.get("processed_rows"), _int(report.get("rows"), 0))
    missing_date_rows = _int(report.get("missing_date_rows"), 0)
    duplicate_bars = _int(report.get("duplicate_bars"), 0)
    zero_volume_rows = _int(report.get("zero_volume_rows"), 0)
    target_start = _date_str(target_window.get("start_date"))
    target_end = _date_str(target_window.get("end_date"))
    expected_trade_dates = _expected_trade_dates(ingest_result)
    effective_start = _effective_start(target_start, expected_trade_dates)
    effective_end = _effective_end(target_end, expected_trade_dates)
    required_asset_ids = _required_asset_ids(profile_observation_pack)
    asset_rows = _asset_coverage_rows(report)
    if required_asset_ids and asset_rows:
        return _required_assets_coverage(
            required_asset_ids,
            asset_rows,
            processed_rows=processed_rows,
            earliest_date=earliest_date,
            latest_date=latest_date,
            target_start=target_start,
            target_end=target_end,
            effective_start=effective_start,
            effective_end=effective_end,
            expected_trade_dates=expected_trade_dates,
            provider_missing_date_rows=missing_date_rows,
            duplicate_bars=duplicate_bars,
            zero_volume_rows=zero_volume_rows,
        )
    target_start_covered = bool(earliest_date and effective_start and earliest_date <= effective_start)
    target_end_covered = bool(latest_date and effective_end and latest_date >= effective_end)
    pass_status = (
        processed_rows > 0
        and target_start_covered
        and target_end_covered
        and missing_date_rows == 0
        and duplicate_bars == 0
        and zero_volume_rows == 0
    )
    return {
        "coverage_status": "pass" if pass_status else "fail",
        "coverage_scope": "provider_universe",
        "processed_rows": processed_rows,
        "earliest_data_date": earliest_date,
        "latest_data_date": latest_date,
        "target_start_date": target_start,
        "target_end_date": target_end,
        "effective_start_date": effective_start,
        "effective_end_date": effective_end,
        "expected_trade_dates_count": _expected_trade_dates_count(expected_trade_dates, effective_start, effective_end),
        "target_start_covered": target_start_covered,
        "target_end_covered": target_end_covered,
        "missing_date_rows": missing_date_rows,
        "provider_missing_date_rows": missing_date_rows,
        "duplicate_bars": duplicate_bars,
        "zero_volume_rows": zero_volume_rows,
    }


def _required_assets_coverage(
    required_asset_ids: list[str],
    asset_rows: dict[str, dict[str, Any]],
    *,
    processed_rows: int,
    earliest_date: str | None,
    latest_date: str | None,
    target_start: str | None,
    target_end: str | None,
    effective_start: str | None,
    effective_end: str | None,
    expected_trade_dates: list[str],
    provider_missing_date_rows: int,
    duplicate_bars: int,
    zero_volume_rows: int,
) -> dict[str, Any]:
    asset_coverage = []
    expected_rows = _expected_trade_dates_count(expected_trade_dates, effective_start, effective_end)
    required_asset_missing_date_rows = 0
    for asset_id in required_asset_ids:
        row = asset_rows.get(asset_id, {})
        asset_start = _date_str(row.get("start_date"))
        asset_end = _date_str(row.get("end_date"))
        asset_rows_count = _int(row.get("rows"), 0)
        start_covered = bool(asset_start and effective_start and asset_start <= effective_start)
        end_covered = bool(asset_end and effective_end and asset_end >= effective_end)
        missing_date_rows = _required_asset_missing_rows(asset_rows_count, expected_rows, start_covered, end_covered)
        required_asset_missing_date_rows += missing_date_rows
        covered = asset_rows_count > 0 and start_covered and end_covered and missing_date_rows == 0
        asset_coverage.append(
            {
                "asset_id": asset_id,
                "rows": asset_rows_count,
                "expected_rows": expected_rows,
                "missing_date_rows": missing_date_rows,
                "start_date": asset_start,
                "end_date": asset_end,
                "target_start_covered": start_covered,
                "target_end_covered": end_covered,
                "covered": covered,
            }
        )
    required_assets_covered = all(row["covered"] for row in asset_coverage)
    target_start_covered = all(row["target_start_covered"] for row in asset_coverage)
    target_end_covered = all(row["target_end_covered"] for row in asset_coverage)
    scoped_missing_date_rows = required_asset_missing_date_rows if expected_rows is not None else 0 if required_assets_covered else provider_missing_date_rows
    pass_status = (
        processed_rows > 0
        and required_assets_covered
        and duplicate_bars == 0
        and zero_volume_rows == 0
    )
    return {
        "coverage_status": "pass" if pass_status else "fail",
        "coverage_scope": "required_assets",
        "required_asset_ids": required_asset_ids,
        "required_assets_covered": required_assets_covered,
        "required_asset_coverage": asset_coverage,
        "processed_rows": processed_rows,
        "earliest_data_date": earliest_date,
        "latest_data_date": latest_date,
        "target_start_date": target_start,
        "target_end_date": target_end,
        "effective_start_date": effective_start,
        "effective_end_date": effective_end,
        "expected_trade_dates_count": expected_rows,
        "target_start_covered": target_start_covered,
        "target_end_covered": target_end_covered,
        "missing_date_rows": scoped_missing_date_rows,
        "required_asset_missing_date_rows": required_asset_missing_date_rows,
        "provider_missing_date_rows": provider_missing_date_rows,
        "duplicate_bars": duplicate_bars,
        "zero_volume_rows": zero_volume_rows,
    }


def _required_asset_ids(profile_observation_pack: dict[str, Any] | None) -> list[str]:
    if not isinstance(profile_observation_pack, dict):
        return []
    assets: list[str] = []
    seen: set[str] = set()

    def add(value: Any) -> None:
        text = str(value or "").strip()
        if text and text not in seen:
            assets.append(text)
            seen.add(text)

    top_level = profile_observation_pack.get("observed_assets", [])
    if isinstance(top_level, list):
        for item in top_level:
            add(item)
    elif isinstance(top_level, str):
        for item in _split_observed_assets(top_level):
            add(item)

    ledger = profile_observation_pack.get("ledger", [])
    if isinstance(ledger, list):
        for row in ledger:
            if not isinstance(row, dict):
                continue
            ledger_assets = row.get("observed_assets")
            if isinstance(ledger_assets, list):
                for item in ledger_assets:
                    add(item)
            elif isinstance(ledger_assets, str):
                for item in _split_observed_assets(ledger_assets):
                    add(item)
    return assets


def _split_observed_assets(value: str) -> list[str]:
    return [item.strip() for item in value.replace(",", "/").split("/") if item.strip()]


def _asset_coverage_rows(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    coverage = report.get("coverage_by_asset", [])
    if not isinstance(coverage, list):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for row in coverage:
        if not isinstance(row, dict):
            continue
        asset_id = str(row.get("asset_id") or "").strip()
        if asset_id:
            rows[asset_id] = row
    return rows


def _expected_trade_dates(ingest_result: dict[str, Any]) -> list[str]:
    values = []
    for key in ("downloaded_trade_dates", "skipped_trade_dates"):
        items = ingest_result.get(key, [])
        if isinstance(items, list):
            values.extend(items)
    dates = []
    seen: set[str] = set()
    for value in values:
        parsed = _trade_date_str(value)
        if parsed and parsed not in seen:
            dates.append(parsed)
            seen.add(parsed)
    return sorted(dates)


def _effective_start(value: str | None, expected_trade_dates: list[str]) -> str | None:
    if value and expected_trade_dates:
        for trade_date in expected_trade_dates:
            if trade_date >= value:
                return trade_date
    return _weekend_adjusted_start(value)


def _effective_end(value: str | None, expected_trade_dates: list[str]) -> str | None:
    if value and expected_trade_dates:
        for trade_date in reversed(expected_trade_dates):
            if trade_date <= value:
                return trade_date
    return _weekend_adjusted_end(value)


def _expected_trade_dates_count(
    expected_trade_dates: list[str],
    effective_start: str | None,
    effective_end: str | None,
) -> int | None:
    if not expected_trade_dates or not effective_start or not effective_end:
        return None
    return sum(1 for trade_date in expected_trade_dates if effective_start <= trade_date <= effective_end)


def _required_asset_missing_rows(
    asset_rows_count: int,
    expected_rows: int | None,
    start_covered: bool,
    end_covered: bool,
) -> int:
    boundary_missing = 0 if start_covered and end_covered else 1
    if expected_rows is None:
        return boundary_missing
    return max(boundary_missing, max(0, expected_rows - asset_rows_count))


def _weekend_adjusted_start(value: str | None) -> str | None:
    day = _date_value(value)
    if day is None:
        return value
    if day.weekday() == 5:
        return (day + timedelta(days=2)).isoformat()
    if day.weekday() == 6:
        return (day + timedelta(days=1)).isoformat()
    return day.isoformat()


def _weekend_adjusted_end(value: str | None) -> str | None:
    day = _date_value(value)
    if day is None:
        return value
    if day.weekday() == 5:
        return (day - timedelta(days=1)).isoformat()
    if day.weekday() == 6:
        return (day - timedelta(days=2)).isoformat()
    return day.isoformat()


def _decision_blockers(status: str, readiness_missing: list[str], coverage: dict[str, Any]) -> list[str]:
    blockers = list(readiness_missing)
    if status == "data_quality_blocked":
        if coverage.get("coverage_scope") == "required_assets" and not coverage.get("required_assets_covered"):
            blockers.append("required_assets_not_covered")
        if not coverage.get("target_start_covered"):
            blockers.append("target_start_not_covered")
        if not coverage.get("target_end_covered"):
            blockers.append("target_end_not_covered")
        if _int(coverage.get("processed_rows"), 0) <= 0:
            blockers.append("no_processed_rows")
        if _int(coverage.get("missing_date_rows"), 0) > 0:
            blockers.append("missing_date_rows")
        if _int(coverage.get("duplicate_bars"), 0) > 0:
            blockers.append("duplicate_bars")
        if _int(coverage.get("zero_volume_rows"), 0) > 0:
            blockers.append("zero_volume_rows")
    if status == "blocked" and not blockers:
        blockers.append("recent_data_refresh_not_ready")
    return blockers


def _next_actions(pack: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = pack.get("decision", {}).get("blockers", []) if isinstance(pack.get("decision"), dict) else []
    actions: list[dict[str, Any]] = []
    workstation = pack.get("workstation", {}) if isinstance(pack.get("workstation"), dict) else {}
    if pack.get("status") in {"blocked", "ready_to_execute", "data_quality_blocked"} and not bool(
        workstation.get("can_run_data_pipeline", True)
    ):
        return [_handoff_refresh_action(pack, workstation)]
    if any("TUSHARE_TOKEN" in str(item) for item in blockers):
        actions.append(
            {
                "action": "set_tushare_token_env",
                "local_only": True,
                "command": "setx TUSHARE_TOKEN <your-token>",
                "reason": "Tushare token is required before a real recent-data refresh can run.",
            }
        )
    if any("tushare package" in str(item).lower() for item in blockers):
        actions.append(
            {
                "action": "install_tushare_package",
                "local_only": True,
                "command": ".\\.venv\\Scripts\\python.exe -m pip install tushare",
                "reason": "The Tushare Python package must be installed before execute mode.",
            }
        )
    if pack.get("status") == "ready_to_execute":
        actions.append(
            {
                "action": "execute_recent_tushare_refresh",
                "local_only": True,
                "command": "python scripts\\run_recent_data_refresh.py --execute",
                "reason": "Readiness is clear; execute mode can refresh recent CN ETF bars.",
            }
        )
    if pack.get("status") == "data_quality_blocked":
        actions.append(
            {
                "action": "inspect_recent_data_quality",
                "local_only": True,
                "reason": "Recent provider data did not fully cover the target window or failed quality checks.",
            }
        )
    if pack.get("status") == "completed":
        actions.extend(
            [
                {
                    "action": "rerun_daily_ops_on_refreshed_data",
                    "local_only": True,
                    "command": "python scripts\\run_daily_ops.py --data-root data\\processed\\tushare_etf_recent --output-dir data\\reports\\daily_ops",
                    "reason": "Recent data is available; rerun the activated paper profile on refreshed bars.",
                },
                {
                    "action": "rerun_profile_observation",
                    "local_only": True,
                    "command": "python scripts\\run_profile_observation.py --output-dir data\\reports\\profile_observation",
                    "reason": "Recompute the observation ledger after Daily Ops uses refreshed data.",
                },
            ]
        )
    if not actions:
        actions.append(
            {
                "action": "wait_for_readiness_or_execute_flag",
                "local_only": True,
                "reason": "Dry-run refresh pack recorded the current blocker state without downloading data.",
            }
        )
    return actions


def _handoff_refresh_action(pack: dict[str, Any], workstation: dict[str, Any]) -> dict[str, Any]:
    recommended = _string_list(workstation.get("data_pipeline_machines"))
    primary_machine = recommended[0] if recommended else "highspec_desktop"
    branch = workstation.get("data_pipeline_branch") or "codex/tushare-data-pipeline"
    return {
        "action": "handoff_recent_tushare_refresh",
        "local_only": False,
        "requires_machine_handoff": True,
        "recommended_machines": recommended,
        "recommended_branch": branch,
        "command": f"python scripts\\run_recent_data_refresh.py --machine {primary_machine} --execute",
        "reason": (
            f"{workstation.get('machine') or 'Current machine'} is not configured for data_pipeline; "
            "run the recent Tushare refresh on a data-pipeline workstation before rerunning Daily Ops."
        ),
        "blocked_local_action": "execute_recent_tushare_refresh" if pack.get("status") == "ready_to_execute" else pack.get("status"),
    }


def _next_day(value: str) -> str | None:
    try:
        return (date.fromisoformat(value[:10]) + timedelta(days=1)).isoformat()
    except (TypeError, ValueError):
        return None


def _date_str(value: Any) -> str | None:
    day = _date_value(value)
    return day.isoformat() if day is not None else None


def _trade_date_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return _date_str(text)


def _date_value(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _safety() -> str:
    return "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading."
