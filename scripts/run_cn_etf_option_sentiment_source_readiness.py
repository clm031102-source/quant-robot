from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import pandas as pd  # noqa: E402

from quant_robot.config.secrets import require_env_secret  # noqa: E402
from quant_robot.ops.cn_etf_option_sentiment_source_readiness import (  # noqa: E402
    SAFETY_BOUNDARIES,
    STAGE,
    build_cn_etf_option_sentiment_source_readiness,
    normalise_option_contracts,
    write_cn_etf_option_sentiment_source_readiness,
)
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402


DEFAULT_CONFIG = Path("configs/cn_etf_option_sentiment_source_readiness_20260728.json")
EXPECTED_ANALYSIS = {
    "start_date": "2020-01-02",
    "end_date": "2024-06-28",
    "final_holdout_start": "2026-01-01",
}
EXPECTED_PROVIDERS = {
    "contract_source": "tushare_opt_basic",
    "daily_source": "tushare_opt_daily",
    "exchanges": ["SSE", "SZSE"],
    "contract_fields": "ts_code,exchange,opt_code,call_put,list_date,delist_date",
    "daily_fields": "ts_code,trade_date,exchange,close,vol,amount,oi",
}
EXPECTED_PROBE_DATES = [
    "2020-01-02",
    "2021-01-04",
    "2022-01-04",
    "2023-01-03",
    "2024-06-28",
]
EXPECTED_THRESHOLDS = {
    "minimum_etf_underlyings": 30,
    "minimum_positive_close_ratio_per_probe": 0.95,
}


def run_cn_etf_option_sentiment_source_readiness_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    config = _load_and_validate_config(path)
    destination = Path(output_dir or config["outputs"]["report_dir"])
    destination.mkdir(parents=True, exist_ok=True)
    source = client or _default_client()

    contract_parts = [
        source.opt_basic(
            exchange=exchange,
            fields=config["providers"]["contract_fields"],
        )
        for exchange in config["providers"]["exchanges"]
    ]
    raw_contracts = pd.concat(contract_parts, ignore_index=True)
    contracts = normalise_option_contracts(
        raw_contracts,
        start=pd.Timestamp(config["analysis"]["start_date"]),
        end=pd.Timestamp(config["analysis"]["end_date"]),
    )

    daily_probes: dict[str, pd.DataFrame] = {}
    daily_parts: list[pd.DataFrame] = []
    for date in config["probes"]["dates"]:
        exchange_parts = [
            source.opt_daily(
                trade_date=date.replace("-", ""),
                exchange=exchange,
                fields=config["providers"]["daily_fields"],
            )
            for exchange in config["providers"]["exchanges"]
        ]
        probe = pd.concat(exchange_parts, ignore_index=True)
        probe = _stable_daily_rows(probe)
        daily_probes[date] = probe
        daily_parts.append(probe)

    contract_path = destination / "contracts.csv"
    daily_path = destination / "daily_rows.csv"
    _stable_contract_rows(contracts).to_csv(contract_path, index=False)
    pd.concat(daily_parts, ignore_index=True).to_csv(daily_path, index=False)

    result = build_cn_etf_option_sentiment_source_readiness(
        contracts=contracts,
        daily_probes=daily_probes,
        config=config,
        config_sha256=sha256_file(path),
    )
    result["configuration"].update(
        {
            "path": str(path),
            "frozen_analysis_boundary": True,
            "frozen_thresholds": True,
            "all_execution_boundaries_false": True,
        }
    )
    result["source_evidence"] = {
        "contracts": {
            "path": str(contract_path),
            "sha256": sha256_file(contract_path),
        },
        "daily_rows": {
            "path": str(daily_path),
            "sha256": sha256_file(daily_path),
        },
    }
    readiness_paths = write_cn_etf_option_sentiment_source_readiness(
        destination,
        result,
    )
    paths = {
        "contracts": contract_path,
        "daily_rows": daily_path,
        **readiness_paths,
    }
    result["artifacts"] = {name: str(artifact) for name, artifact in paths.items()}
    result["artifact_hashes"] = {
        name: sha256_file(artifact)
        for name, artifact in sorted(paths.items())
    }
    return result


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"CN ETF option-sentiment config does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid CN ETF option-sentiment config JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("CN ETF option-sentiment config must be a JSON object")
    expected = {
        "schema_version": 1,
        "stage": STAGE,
        "review_date": "2026-07-28",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_option_sentiment",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"config {key} must be frozen as {value}")
    _require_keys(
        payload,
        ("analysis", "providers", "probes", "thresholds", "outputs", "boundaries"),
    )
    if payload["analysis"] != EXPECTED_ANALYSIS:
        raise ValueError("config analysis boundary does not match the frozen window")
    if payload["providers"] != EXPECTED_PROVIDERS:
        raise ValueError("config providers do not match the frozen source contract")
    if payload["probes"] != {"dates": EXPECTED_PROBE_DATES}:
        raise ValueError("config probes do not match the frozen representative dates")
    if payload["thresholds"] != EXPECTED_THRESHOLDS:
        raise ValueError("config thresholds do not match the frozen readiness gate")
    output = payload["outputs"].get("report_dir")
    if not isinstance(output, str) or not output.strip():
        raise ValueError("config outputs.report_dir must be a non-empty path")
    boundaries = payload["boundaries"]
    if set(boundaries) != set(SAFETY_BOUNDARIES):
        raise ValueError("config boundary keys do not match the frozen boundary contract")
    for key in SAFETY_BOUNDARIES:
        if boundaries.get(key) is not False:
            raise ValueError(f"config boundary {key} must be false")
    start = pd.Timestamp(payload["analysis"]["start_date"])
    end = pd.Timestamp(payload["analysis"]["end_date"])
    holdout = pd.Timestamp(payload["analysis"]["final_holdout_start"])
    if not start <= end < holdout:
        raise ValueError("config analysis window violates the sealed final holdout")
    return payload


def _default_client() -> Any:
    import tushare as ts

    return ts.pro_api(require_env_secret("TUSHARE_TOKEN"))


def _stable_contract_rows(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in ("list_date", "delist_date"):
        result[column] = pd.to_datetime(result[column]).dt.strftime("%Y-%m-%d")
    return result.sort_values(
        ["exchange", "underlying_symbol", "ts_code"],
    ).reset_index(drop=True)


def _stable_daily_rows(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    required = ["ts_code", "trade_date", "exchange", "close", "vol", "amount", "oi"]
    missing = [column for column in required if column not in result.columns]
    if missing:
        raise ValueError("option daily source is missing columns: " + ", ".join(missing))
    result = result[required]
    result["trade_date"] = pd.to_datetime(result["trade_date"], errors="raise").dt.strftime(
        "%Y-%m-%d"
    )
    result["exchange"] = result["exchange"].astype(str).str.upper()
    return result.sort_values(["trade_date", "exchange", "ts_code"]).reset_index(drop=True)


def _require_keys(payload: Mapping[str, Any], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError("config missing required keys: " + ", ".join(missing))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit CN ETF option-sentiment source readiness."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    result = run_cn_etf_option_sentiment_source_readiness_cli(
        config_path=args.config,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "stage": result["stage"],
                "status": result["status"],
                "summary": result["summary"],
                "blockers": result["gate"]["blockers"],
                "next_direction": result["next_direction"],
                "artifacts": result["artifacts"],
                "artifact_hashes": result["artifact_hashes"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
