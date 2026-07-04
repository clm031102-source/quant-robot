from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.adapters.tushare_adapter import TushareAdapter


DATA_PIPELINE_MACHINES = {"office_desktop", "highspec_desktop"}
DATA_PIPELINE_TASK = "data_pipeline"
DEFAULT_RECENT_DATA_REFRESH_PACK = Path(
    "data/reports/round491_recent_data_refresh_postgap_to_20260703_clean_action_20260704/recent_data_refresh_pack.json"
)
DEFAULT_OUTPUT_DIR = Path("data/processed/required_asset_target_end_retry")
DEFAULT_REPORT_DIR = Path("data/reports/required_asset_target_end_recent_refresh")


def build_required_asset_target_end_check(
    *,
    recent_data_refresh_pack: dict[str, Any] | None,
    recent_data_refresh_pack_path: str | Path | None,
    machine: str | None,
    task: str | None,
    current_branch: str,
    python_executable: str,
    profile_observation_pack_path: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    execute: bool = False,
    adapter: Any | None = None,
) -> dict[str, Any]:
    pack = recent_data_refresh_pack or {}
    target_end_gap = _target_end_gap(pack, source_path=recent_data_refresh_pack_path)
    blockers: list[str] = []
    if machine not in DATA_PIPELINE_MACHINES:
        blockers.append("machine_must_allow_data_pipeline")
    if task != DATA_PIPELINE_TASK:
        blockers.append("task_must_be_data_pipeline")
    if not target_end_gap:
        blockers.append("target_end_gap_missing")

    provider_checks: list[dict[str, Any]] = []
    if execute and not blockers and target_end_gap:
        provider_checks = _provider_checks(
            adapter or TushareAdapter(request_sleep_seconds=0.2),
            target_end_gap=target_end_gap,
        )

    if blockers:
        status = "blocked"
    elif not execute:
        status = "ready_to_check"
    elif all(row["target_rows"] > 0 for row in provider_checks):
        status = "target_end_available"
    elif _has_non_current_etf_gap(provider_checks):
        status = "target_end_asset_not_current_etf"
    else:
        status = "target_end_missing"

    return {
        "stage": "required_asset_target_end_check",
        "status": status,
        "mode": "execute" if execute else "plan",
        "blockers": blockers,
        "selected": {
            "machine": machine,
            "task": task,
        },
        "git": {
            "current_branch": current_branch,
        },
        "recent_data_refresh": {
            "source_path": _path_text(recent_data_refresh_pack_path) if recent_data_refresh_pack_path else None,
            "status": pack.get("status", "missing") if pack else "missing",
        },
        "target_end_gap": target_end_gap,
        "provider_checks": provider_checks,
        "next_actions": _next_actions(
            status=status,
            machine=machine,
            recent_data_refresh_pack_path=recent_data_refresh_pack_path,
            target_end_gap=target_end_gap,
            profile_observation_pack_path=profile_observation_pack_path,
            output_dir=output_dir,
            report_dir=report_dir,
            python_executable=python_executable,
        ),
        "safety": {
            "research_to_paper_only": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_reads_allowed": False,
            "order_placement_allowed": False,
        },
    }


def asset_id_to_tushare_symbol(asset_id: str) -> str:
    parts = str(asset_id).split("_")
    if len(parts) < 2:
        return str(asset_id)
    exchange = parts[-2]
    code = parts[-1]
    suffix = {"XSHE": "SZ", "XSHG": "SH"}.get(exchange)
    return f"{code}.{suffix}" if suffix else str(asset_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check whether required assets now cover a recent-refresh target end.")
    parser.add_argument("--recent-data-refresh-pack", default=str(DEFAULT_RECENT_DATA_REFRESH_PACK))
    parser.add_argument("--profile-observation-pack")
    parser.add_argument("--machine", required=True)
    parser.add_argument("--task", default=DATA_PIPELINE_TASK)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    recent_pack_path = Path(args.recent_data_refresh_pack)
    result = build_required_asset_target_end_check(
        recent_data_refresh_pack=_read_optional_json(recent_pack_path),
        recent_data_refresh_pack_path=recent_pack_path,
        profile_observation_pack_path=Path(args.profile_observation_pack) if args.profile_observation_pack else None,
        machine=args.machine,
        task=args.task,
        current_branch=_git_stdout(["branch", "--show-current"]),
        python_executable=sys.executable,
        output_dir=Path(args.output_dir),
        report_dir=Path(args.report_dir),
        execute=args.execute,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def _target_end_gap(pack: dict[str, Any], *, source_path: str | Path | None) -> dict[str, Any] | None:
    coverage = _dict(pack.get("coverage"))
    if coverage.get("target_end_covered") is not False:
        return None
    target = _dict(pack.get("target_window"))
    target_start = _date_text(target.get("start_date"))
    target_end = _date_text(target.get("end_date"))
    if not target_start or not target_end:
        return None

    rows = coverage.get("required_asset_coverage", [])
    if not isinstance(rows, list):
        return None
    required_asset_ids: list[str] = []
    clean_end_dates: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("target_start_covered") is False or row.get("target_end_covered") is not False:
            continue
        clean_end = _date_text(row.get("end_date"))
        if not clean_end or clean_end >= target_end or clean_end < target_start:
            continue
        asset_id = str(row.get("asset_id") or "").strip()
        if asset_id:
            required_asset_ids.append(asset_id)
        clean_end_dates.append(clean_end)
    if not required_asset_ids or not clean_end_dates:
        return None
    unique_assets = sorted(dict.fromkeys(required_asset_ids))
    return {
        "source_path": _path_text(source_path) if source_path else None,
        "target_start_date": target_start,
        "target_end_date": target_end,
        "latest_clean_end_date": min(clean_end_dates),
        "required_asset_ids": unique_assets,
        "required_symbols": [asset_id_to_tushare_symbol(asset_id) for asset_id in unique_assets],
    }


def _provider_checks(adapter: Any, *, target_end_gap: dict[str, Any]) -> list[dict[str, Any]]:
    target_end = str(target_end_gap["target_end_date"])
    required_assets = list(target_end_gap.get("required_asset_ids", []))
    frame = adapter.fetch_etf_daily_by_trade_date(target_end)
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame()
    symbols = frame["symbol"].astype(str) if "symbol" in frame.columns else pd.Series([], dtype=str)
    fund_basic_by_symbol = _fund_basic_by_symbol(adapter)
    return [
        _with_fund_basic_metadata(
            {
                "asset_id": asset_id,
                "symbol": asset_id_to_tushare_symbol(asset_id),
                "target_end_date": target_end,
                "fund_daily_rows": int(len(frame)),
                "target_rows": int(symbols.eq(asset_id_to_tushare_symbol(asset_id)).sum()),
            },
            fund_basic_by_symbol.get(asset_id_to_tushare_symbol(asset_id).upper(), {}),
        )
        for asset_id in required_assets
    ]


def _with_fund_basic_metadata(check: dict[str, Any], fund: dict[str, Any]) -> dict[str, Any]:
    if not fund:
        return {**check, "fund_basic_present": False}
    return {
        **check,
        "fund_basic_present": True,
        "fund_basic_name": fund.get("name"),
        "fund_basic_status": fund.get("status"),
        "fund_basic_market": fund.get("market"),
        "fund_basic_fund_type": fund.get("fund_type"),
        "fund_basic_type": fund.get("type"),
        "fund_basic_invest_type": fund.get("invest_type"),
        "fund_basic_is_exchange_traded": _optional_bool(fund.get("is_exchange_traded")),
        "fund_basic_is_etf": _optional_bool(fund.get("is_etf")),
    }


def _fund_basic_by_symbol(adapter: Any) -> dict[str, dict[str, Any]]:
    fetch = getattr(adapter, "fetch_fund_basic", None)
    if fetch is None:
        return {}
    try:
        frame = fetch(market="E", status="")
    except Exception:
        return {}
    if not isinstance(frame, pd.DataFrame) or "symbol" not in frame.columns:
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict("records"):
        symbol = str(row.get("symbol") or "").upper()
        if symbol:
            rows[symbol] = row
    return rows


def _has_non_current_etf_gap(provider_checks: list[dict[str, Any]]) -> bool:
    for row in provider_checks:
        if int(row.get("target_rows", 0)) > 0:
            continue
        if row.get("fund_basic_present") is not True:
            continue
        if row.get("fund_basic_is_etf") is False or row.get("fund_basic_is_exchange_traded") is False:
            return True
        if str(row.get("fund_basic_status") or "").upper() not in {"", "L"}:
            return True
    return False


def _optional_bool(value: Any) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _next_actions(
    *,
    status: str,
    machine: str | None,
    recent_data_refresh_pack_path: str | Path | None,
    target_end_gap: dict[str, Any] | None,
    profile_observation_pack_path: str | Path | None,
    output_dir: str | Path,
    report_dir: str | Path,
    python_executable: str,
) -> list[dict[str, str]]:
    if not target_end_gap:
        return []
    if status == "target_end_available" and profile_observation_pack_path:
        return [
            {
                "action": "run_recent_refresh_to_target_end",
                "command": " ".join(
                    [
                        python_executable,
                        "scripts/run_recent_data_refresh.py",
                        "--machine",
                        str(machine),
                        "--profile-observation-pack",
                        _path_text(profile_observation_pack_path),
                        "--start-date",
                        str(target_end_gap["target_start_date"]),
                        "--end-date",
                        str(target_end_gap["target_end_date"]),
                        "--output-dir",
                        _path_text(output_dir),
                        "--report-dir",
                        _path_text(report_dir),
                        "--execute",
                    ]
                ),
                "reason": "required asset target-end provider rows are now available",
            }
        ]
    if status == "target_end_available":
        return [
            {
                "action": "provide_profile_observation_pack",
                "command": "python scripts/run_required_asset_target_end_check.py --profile-observation-pack <path>",
                "reason": "target end is available, but a profile observation pack is required to emit the refresh command",
            }
        ]
    if status == "target_end_asset_not_current_etf":
        return [
            {
                "action": "rerun_observation_after_universe_filter",
                "command": "python scripts/run_post_refresh_replay.py",
                "reason": "required asset is no longer classified as a current ETF; rerun the signal/profile observation chain with the corrected ETF universe filter",
            }
        ]
    return [
        {
            "action": "recheck_required_asset_target_end",
            "command": " ".join(
                [
                    python_executable,
                    "scripts/run_required_asset_target_end_check.py",
                    "--machine",
                    str(machine),
                    "--task",
                    DATA_PIPELINE_TASK,
                    "--recent-data-refresh-pack",
                    _path_text(recent_data_refresh_pack_path) if recent_data_refresh_pack_path else str(DEFAULT_RECENT_DATA_REFRESH_PACK),
                    "--execute",
                ]
            ),
            "reason": (
                "required assets still need provider rows for target end "
                f"{target_end_gap.get('target_end_date')}"
            ),
        }
    ]


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)[:10]
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _path_text(path: str | Path) -> str:
    return Path(path).as_posix()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _git_stdout(args: list[str]) -> str:
    return _git(args).stdout.strip()


def _git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


if __name__ == "__main__":
    main()
