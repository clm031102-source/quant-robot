from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import pandas as pd  # noqa: E402

from quant_robot.data.adapters.tushare_adapter import TushareAdapter  # noqa: E402
from quant_robot.data.cn_trading_calendar import (  # noqa: E402
    validate_cn_trading_calendar_artifact,
)
from quant_robot.data.ingest.tushare_fund_nav import (  # noqa: E402
    REQUEST_MANIFEST_NAME,
    FundNavAdapter,
    run_tushare_fund_nav_ingest,
)
from quant_robot.ops.cn_etf_tushare_nav_source_readiness import (  # noqa: E402
    BOUNDARY_KEYS,
    STAGE,
    build_cn_etf_tushare_nav_source_readiness,
    write_cn_etf_tushare_nav_source_readiness,
)
from quant_robot.storage.etf_share_size import load_etf_share_size_inputs  # noqa: E402


DEFAULT_CONFIG = Path("configs/cn_etf_tushare_nav_source_readiness_20260729.json")
EXPECTED_THRESHOLDS = {
    "minimum_terminal_request_ratio": 1.0,
    "minimum_valid_announcement_ratio": 0.99,
    "minimum_positive_unit_nav_ratio": 0.999,
    "minimum_public_key_intersection_ratio": 0.9,
    "minimum_public_asset_match_ratio": 0.9,
    "minimum_within_10bp_ratio": 0.99,
    "maximum_severe_disagreement_ratio": 0.001,
    "severe_disagreement_threshold": 0.05,
    "minimum_usable_assets_per_session": 30,
    "minimum_usable_session_coverage": 0.8,
}


def run_cn_etf_tushare_nav_source_readiness_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    execute: bool = False,
    adapter: FundNavAdapter | None = None,
    current_branch: str | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    payload = _load_and_validate_config(path)
    branch = current_branch or _current_branch()
    if branch == "main":
        raise ValueError("CN ETF NAV source work must not run on main")

    analysis = payload["analysis"]
    outputs = payload["outputs"]
    provider = payload["provider"]
    data_dir = Path(outputs["data_dir"])
    report_dir = Path(outputs["report_dir"])
    canonical_path = data_dir / "canonical" / "nav.parquet"
    request_manifest_path = data_dir / REQUEST_MANIFEST_NAME
    trading_sessions = _load_trading_sessions(analysis)
    ingest_summary: dict[str, Any] | None = None

    if execute:
        target_path = Path(analysis["target_universe_path"])
        if not target_path.is_file():
            raise FileNotFoundError(f"CN ETF target universe is missing: {target_path}")
        target_universe = pd.read_csv(target_path)
        source_adapter = adapter or TushareAdapter(request_sleep_seconds=0.0)
        ingest = run_tushare_fund_nav_ingest(
            adapter=source_adapter,
            target_universe=target_universe,
            trading_sessions=trading_sessions,
            output_dir=data_dir,
            start_date=analysis["start_date"],
            end_date=analysis["end_date"],
            request_sleep_seconds=float(provider["request_sleep_seconds"]),
        )
        ingest_summary = ingest.summary

    if not canonical_path.is_file():
        raise FileNotFoundError(f"Local canonical NAV source is missing: {canonical_path}")
    if not request_manifest_path.is_file():
        raise FileNotFoundError(
            f"Local Tushare fund NAV request manifest is missing: {request_manifest_path}"
        )
    nav = pd.read_parquet(canonical_path)
    request_manifest = json.loads(request_manifest_path.read_text(encoding="utf-8"))
    public_source = load_etf_share_size_inputs(analysis["public_nav_root"], "CN_ETF")
    public_nav = public_source[["date", "asset_id", "nav"]].copy()
    configuration_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    result = build_cn_etf_tushare_nav_source_readiness(
        config=payload,
        nav=nav,
        request_manifest=request_manifest,
        public_nav=public_nav,
        official_sessions=trading_sessions,
        configuration_sha256=configuration_sha256,
    )
    result["configuration"].update(
        {
            "path": str(path),
            "branch": branch,
            "frozen_analysis_boundary": True,
            "frozen_thresholds": True,
            "all_execution_boundaries_false": True,
        }
    )
    artifacts = write_cn_etf_tushare_nav_source_readiness(report_dir, result)
    result["artifacts"] = {name: str(artifact) for name, artifact in artifacts.items()}
    if ingest_summary is not None:
        result["ingest_result"] = ingest_summary
    return result


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"CN ETF Tushare NAV source config does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid CN ETF Tushare NAV source config JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("CN ETF Tushare NAV source config must be a JSON object")
    expected = {
        "schema_version": 1,
        "stage": STAGE,
        "review_date": "2026-07-29",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_nav_premium_relative_value",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"config {key} must be frozen as {value}")
    _require_keys(payload, ("analysis", "outputs", "provider", "thresholds", "boundaries"))
    analysis = payload["analysis"]
    _require_keys(
        analysis,
        (
            "target_universe_path",
            "public_nav_root",
            "bar_root",
            "trading_calendar_path",
            "trading_calendar_manifest_path",
            "start_date",
            "end_date",
            "next_session_read_end",
            "final_holdout_start",
        ),
    )
    if analysis["start_date"] != "2020-01-02" or analysis["end_date"] != "2024-06-28":
        raise ValueError("config dates do not match the frozen analysis boundary")
    if (
        analysis["next_session_read_end"] != "2024-07-05"
        or analysis["final_holdout_start"] != "2026-01-01"
    ):
        raise ValueError("config dates violate the frozen analysis boundary and holdout")
    start = pd.Timestamp(analysis["start_date"])
    end = pd.Timestamp(analysis["end_date"])
    next_end = pd.Timestamp(analysis["next_session_read_end"])
    holdout = pd.Timestamp(analysis["final_holdout_start"])
    if not start <= end < next_end < holdout:
        raise ValueError("config dates violate the frozen analysis boundary and holdout")
    for key in (
        "target_universe_path",
        "public_nav_root",
        "bar_root",
        "trading_calendar_path",
        "trading_calendar_manifest_path",
    ):
        if not isinstance(analysis[key], str) or not analysis[key].strip():
            raise ValueError(f"config {key} must be a non-empty path string")
    outputs = payload["outputs"]
    _require_keys(outputs, ("data_dir", "report_dir"))
    if not all(isinstance(outputs[key], str) and outputs[key].strip() for key in outputs):
        raise ValueError("config output paths must be non-empty strings")
    provider = payload["provider"]
    if provider.get("endpoint") != "fund_nav" or provider.get("market") != "E":
        raise ValueError("config provider contract must remain Tushare fund_nav market E")
    if provider.get("request_sleep_seconds") != 0.35:
        raise ValueError("config provider request_sleep_seconds must be frozen as 0.35")
    if payload["thresholds"] != EXPECTED_THRESHOLDS:
        raise ValueError("config does not match the frozen readiness thresholds")
    boundaries = payload["boundaries"]
    if set(boundaries) != set(BOUNDARY_KEYS):
        raise ValueError("config boundary keys do not match the frozen boundary contract")
    for key in BOUNDARY_KEYS:
        if boundaries.get(key) is not False:
            raise ValueError(f"config boundary {key} must be false")
    return payload


def _load_trading_sessions(analysis: Mapping[str, Any]) -> list[str]:
    calendar_path = Path(str(analysis["trading_calendar_path"]))
    manifest_path = Path(str(analysis["trading_calendar_manifest_path"]))
    validate_cn_trading_calendar_artifact(calendar_path, manifest_path)
    calendar = pd.read_csv(calendar_path)
    dates = pd.to_datetime(calendar["date"], errors="raise")
    start = pd.Timestamp(analysis["start_date"])
    next_end = pd.Timestamp(analysis["next_session_read_end"])
    sessions = (
        dates.loc[dates.between(start, next_end)]
        .dt.strftime("%Y-%m-%d")
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    if not sessions:
        raise ValueError("validated CN trading calendar does not cover the analysis window")
    analysis_end = pd.Timestamp(analysis["end_date"])
    if not any(pd.Timestamp(value) > analysis_end for value in sessions):
        raise ValueError("validated CN trading calendar lacks a next session after analysis end")
    return sessions


def _current_branch() -> str:
    completed = subprocess.run(
        ["git", "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    )
    branch = completed.stdout.strip()
    if not branch:
        raise ValueError("current Git branch could not be determined")
    return branch


def _require_keys(payload: Mapping[str, Any], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError("config missing required keys: " + ", ".join(missing))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acquire or audit point-in-time Tushare CN ETF NAV source readiness."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    result = run_cn_etf_tushare_nav_source_readiness_cli(
        config_path=args.config,
        execute=args.execute,
    )
    print(
        json.dumps(
            {
                "stage": result["stage"],
                "status": result["status"],
                "blockers": result["gate"]["blockers"],
                "summary": result["summary"],
                "quality": result["quality"],
                "coverage": result["coverage"],
                "agreement": result["agreement"],
                "request_summary": result["request_summary"],
                "next_direction": result["next_direction"],
                "artifacts": result["artifacts"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if not result["gate"]["cleared"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
