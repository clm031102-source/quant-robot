from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Mapping

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import pandas as pd  # noqa: E402

from quant_robot.data.adapters.tushare_adapter import TushareAdapter  # noqa: E402
from quant_robot.ops.cn_etf_external_data_unlock import (  # noqa: E402
    STAGE,
    classify_external_data_probe,
    summarize_cn_etf_external_data_unlock,
    write_cn_etf_external_data_unlock,
)
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402
from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate  # noqa: E402


DEFAULT_CONFIG = Path("configs/cn_etf_external_data_unlock_review_20260728.json")
EXPECTED_BRANCH = "codex/factor-review-cn-etf-external-data-unlock-20260728"
FALSE_BOUNDARIES = (
    "factor_generation_allowed",
    "forward_return_read_allowed",
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "final_holdout_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_boundary_allowed",
)


def run_cn_etf_external_data_unlock_review(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    adapter: TushareAdapter | None = None,
    enforce_startup_gate: bool = True,
) -> dict[str, Any]:
    path = Path(config_path)
    config = _load_and_validate_config(path)
    if enforce_startup_gate:
        gate = run_quant_pm_startup_gate(
            machine="office_desktop",
            task="factor_review",
            branch=EXPECTED_BRANCH,
        )
        if gate.get("status") != "ready":
            raise ValueError("Quant PM startup gate did not authorize source-access review")
    provider = adapter or TushareAdapter(max_retries=1)
    probes = [_run_probe(provider, probe) for probe in config["probes"]]
    result = summarize_cn_etf_external_data_unlock(probes)
    result["as_of_date"] = config["as_of_date"]
    result["market"] = config["market"]
    result["analysis_boundary"] = config["analysis_boundary"]
    result["config_path"] = str(path)
    result["config_sha256"] = sha256_file(path)
    result["documentation"] = config["documentation"]
    result["documented_but_not_historical"] = config["documented_but_not_historical"]
    paths = write_cn_etf_external_data_unlock(config["output_dir"], result)
    return {
        **result,
        "artifacts": {name: str(value) for name, value in paths.items()},
        "artifact_hashes": {name: sha256_file(value) for name, value in paths.items()},
    }


def _run_probe(adapter: TushareAdapter, probe: Mapping[str, Any]) -> dict[str, Any]:
    endpoint = str(probe["endpoint"])
    parameters = dict(probe["parameters"])
    calls: dict[str, Callable[[], pd.DataFrame]] = {
        "etf_sh_cons": lambda: adapter.fetch_etf_sh_constituents(**parameters),
        "etf_sz_cons": lambda: adapter.fetch_etf_sz_constituents(**parameters),
        "etf_basic": lambda: adapter.fetch_etf_basic(**parameters),
        "fund_basic": lambda: adapter.fetch_fund_basic(**parameters),
        "index_weight": lambda: adapter.fetch_index_weight(**parameters),
    }
    if endpoint not in calls:
        raise ValueError(f"unsupported external-data probe endpoint: {endpoint}")
    common = {
        "endpoint": endpoint,
        "route": str(probe["route"]),
        "required_points": probe.get("required_points"),
        "required_columns": tuple(probe.get("required_columns", [])),
        "parameters": parameters,
    }
    try:
        return classify_external_data_probe(frame=calls[endpoint](), **common)
    except Exception as exc:  # provider failures are the evidence under review
        return classify_external_data_probe(error=exc, **common)


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"external-data unlock config is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("stage") != STAGE:
        raise ValueError("external-data unlock config stage mismatch")
    if payload.get("market") != "CN_ETF":
        raise ValueError("external-data unlock review must remain CN_ETF")
    boundary = payload.get("analysis_boundary", {})
    if boundary.get("forward_returns_allowed") is not False:
        raise ValueError("source-access review must not read forward returns")
    if str(boundary.get("end_date", "")) >= str(boundary.get("final_holdout_start", "")):
        raise ValueError("analysis boundary must precede the final holdout")
    if not payload.get("probes"):
        raise ValueError("external-data unlock config must define probes")
    for key in FALSE_BOUNDARIES:
        if payload.get("boundaries", {}).get(key) is not False:
            raise ValueError(f"external-data unlock boundary must remain false: {key}")
    output = Path(str(payload.get("output_dir", ""))).resolve()
    if Path("data/reports").resolve() not in output.parents:
        raise ValueError("external-data unlock output must remain under data/reports")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe orthogonal CN ETF data access without reading factors or returns."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    result = run_cn_etf_external_data_unlock_review(config_path=args.config)
    print(
        json.dumps(
            {
                "stage": result["stage"],
                "status": result["status"],
                "decision": result["decision"],
                "routes": result["routes"],
                "artifacts": result["artifacts"],
                "artifact_hashes": result["artifact_hashes"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
