from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import pandas as pd  # noqa: E402

from quant_robot.data.adapters.public_cn_etf_fund_structure import (  # noqa: E402
    PublicCnEtfFundStructureAdapter,
)
from quant_robot.data.ingest.public_cn_etf_fund_structure import (  # noqa: E402
    MANIFEST_NAME,
    PublicFundStructureAdapter,
    run_public_cn_etf_fund_structure_ingest,
)
from quant_robot.ops.cn_etf_fund_structure_source_readiness import (  # noqa: E402
    BOUNDARY_KEYS,
    STAGE,
    build_cn_etf_fund_structure_source_readiness,
    write_cn_etf_fund_structure_source_readiness,
)
from quant_robot.storage.etf_share_size import load_etf_share_size_inputs  # noqa: E402
from quant_robot.storage.processed_bars import load_processed_bars  # noqa: E402


DEFAULT_CONFIG = Path("configs/cn_etf_fund_structure_source_readiness_20260728.json")

EXPECTED_THRESHOLDS = {
    "minimum_combined_assets_per_date": 30,
    "minimum_combined_date_coverage": 0.8,
    "minimum_exchange_assets_per_date": 30,
    "minimum_exchange_date_coverage": 0.75,
    "minimum_median_share_asset_coverage": 0.5,
    "minimum_nav_intersection_coverage": 0.7,
    "minimum_positive_share_ratio": 0.95,
    "minimum_positive_nav_ratio": 0.95,
}
EXPECTED_PROVIDER_IDENTITIES = {
    "sse_share_source": "sse_official_etf_scale",
    "szse_share_source": "szse_official_fund_scale",
    "nav_source": "eastmoney_fund_detail_history",
    "close_source": "tushare_fund_daily",
}


def run_cn_etf_fund_structure_source_readiness_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    execute: bool = False,
    adapter: PublicFundStructureAdapter | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    payload = _load_and_validate_config(path)
    analysis = payload["analysis"]
    outputs = payload["outputs"]
    providers = payload["providers"]
    data_dir = Path(outputs["data_dir"])
    report_dir = Path(outputs["report_dir"])
    ingest_result: dict[str, Any] | None = None

    if execute:
        ingest_bars = load_processed_bars(
            analysis["bar_root"],
            "CN_ETF",
            start_date=analysis["start_date"],
            end_date=analysis["next_session_read_end"],
        )
        source_adapter = adapter or PublicCnEtfFundStructureAdapter(
            max_retries=int(providers["max_retries"]),
            backoff_factor=float(providers["backoff_factor"]),
            connect_timeout_seconds=float(providers["connect_timeout_seconds"]),
            read_timeout_seconds=float(providers["read_timeout_seconds"]),
        )
        ingest_result = run_public_cn_etf_fund_structure_ingest(
            adapter=source_adapter,
            bars=ingest_bars,
            start_date=analysis["start_date"],
            end_date=analysis["end_date"],
            output_dir=data_dir,
            szse_window_days=int(providers["szse_window_days"]),
            max_workers=int(providers["max_workers"]),
        )

    processed = load_etf_share_size_inputs(data_dir, "CN_ETF")
    audit_bars = load_processed_bars(
        analysis["bar_root"],
        "CN_ETF",
        start_date=analysis["start_date"],
        end_date=analysis["end_date"],
    )
    manifest_path = data_dir / MANIFEST_NAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"Public fund-structure source manifest is missing: {manifest_path}")
    request_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    result = build_cn_etf_fund_structure_source_readiness(
        config=payload,
        processed=processed,
        bars=audit_bars,
        request_manifest=request_manifest,
        configuration_sha256=config_sha256,
    )
    result["configuration"].update(
        {
            "path": str(path),
            "frozen_analysis_boundary": True,
            "frozen_thresholds": True,
            "all_execution_boundaries_false": True,
        }
    )
    result["tushare_probe"] = dict(payload["tushare_probe"])
    if ingest_result is not None:
        result["ingest_result"] = ingest_result
    artifacts = write_cn_etf_fund_structure_source_readiness(report_dir, result)
    result["artifacts"] = {name: str(artifact) for name, artifact in artifacts.items()}
    return result


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"CN ETF fund-structure source config does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid CN ETF fund-structure source config JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("CN ETF fund-structure source config must be a JSON object")
    expected = {
        "schema_version": 1,
        "stage": STAGE,
        "review_date": "2026-07-28",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_fund_structure",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"config {key} must be frozen as {value}")
    _require_keys(
        payload,
        ("analysis", "outputs", "providers", "tushare_probe", "thresholds", "boundaries"),
    )
    analysis = payload["analysis"]
    _require_keys(
        analysis,
        (
            "bar_root",
            "start_date",
            "end_date",
            "next_session_read_end",
            "final_holdout_start",
        ),
    )
    if analysis["start_date"] != "2020-01-02" or analysis["end_date"] != "2024-06-28":
        raise ValueError("config analysis dates do not match the frozen analysis boundary")
    if analysis["final_holdout_start"] != "2026-01-01":
        raise ValueError("config final_holdout_start must be frozen as 2026-01-01")
    start = pd.Timestamp(analysis["start_date"])
    end = pd.Timestamp(analysis["end_date"])
    next_end = pd.Timestamp(analysis["next_session_read_end"])
    holdout = pd.Timestamp(analysis["final_holdout_start"])
    if not start <= end < next_end < holdout:
        raise ValueError("config analysis and next-session dates violate the frozen holdout boundary")
    if not isinstance(analysis["bar_root"], str) or not analysis["bar_root"].strip():
        raise ValueError("config bar_root must be a non-empty path string")
    outputs = payload["outputs"]
    _require_keys(outputs, ("data_dir", "report_dir"))
    if not all(isinstance(outputs[key], str) and outputs[key].strip() for key in outputs):
        raise ValueError("config output paths must be non-empty strings")
    providers = payload["providers"]
    for key, value in EXPECTED_PROVIDER_IDENTITIES.items():
        if providers.get(key) != value:
            raise ValueError(f"config provider {key} must be frozen as {value}")
    numeric_ranges = {
        "max_retries": (0, 8),
        "backoff_factor": (0.0, 10.0),
        "connect_timeout_seconds": (1.0, 120.0),
        "read_timeout_seconds": (1.0, 300.0),
        "max_workers": (1, 16),
        "szse_window_days": (1, 184),
    }
    for key, (minimum, maximum) in numeric_ranges.items():
        value = providers.get(key)
        if not isinstance(value, (int, float)) or not minimum <= value <= maximum:
            raise ValueError(f"config provider {key} is outside the frozen safe range")
    if payload["thresholds"] != EXPECTED_THRESHOLDS:
        raise ValueError("config does not match the frozen readiness thresholds")
    boundaries = payload["boundaries"]
    if set(boundaries) != set(BOUNDARY_KEYS):
        raise ValueError("config boundary keys do not match the frozen boundary contract")
    for key in BOUNDARY_KEYS:
        if boundaries.get(key) is not False:
            raise ValueError(f"config boundary {key} must be false")
    probe = payload["tushare_probe"]
    if (
        probe.get("endpoint") != "etf_share_size"
        or probe.get("status") != "permission_denied"
        or probe.get("retryable") is not False
    ):
        raise ValueError("config Tushare probe evidence does not match the frozen permission denial")
    return payload


def _require_keys(payload: Mapping[str, Any], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError("config missing required keys: " + ", ".join(missing))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect and audit public CN ETF fund-structure source readiness."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    result = run_cn_etf_fund_structure_source_readiness_cli(
        config_path=args.config,
        execute=args.execute,
    )
    print(
        json.dumps(
            {
                "stage": result.get("stage"),
                "status": result.get("status"),
                "blockers": result.get("gate", {}).get("blockers", []),
                "summary": result.get("summary", {}),
                "coverage": result.get("coverage", {}),
                "next_direction": result.get("next_direction"),
                "artifacts": result.get("artifacts", {}),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
