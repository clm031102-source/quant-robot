from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.etf_point_in_time_universe import EtfEligibilityPolicy  # noqa: E402
from quant_robot.factors.etf_skip_momentum import (  # noqa: E402
    ETF_PRICE_ROTATION_REFERENCE_FACTOR_NAMES,
    ETF_SKIP_MOMENTUM_FACTOR_NAMES,
)
from quant_robot.ops.cn_etf_skip_momentum_prescreen import (  # noqa: E402
    DEFAULT_HORIZONS,
    STAGE,
    build_cn_etf_skip_momentum_prescreen,
    write_cn_etf_skip_momentum_prescreen,
)


DEFAULT_CONFIG = Path("configs/cn_etf_skip_momentum_prescreen_20260716.json")
BOUNDARY_KEYS = (
    "portfolio_grid_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_trading_allowed",
)


def run_cn_etf_skip_momentum_prescreen_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    payload = _load_and_validate_config(path)
    eligibility = payload["eligibility"]
    thresholds = payload["thresholds"]
    result = build_cn_etf_skip_momentum_prescreen(
        data_root=payload["data_root"],
        metadata_root=payload["metadata_root"],
        analysis_start_date=payload["analysis_start_date"],
        analysis_end_date=payload["analysis_end_date"],
        horizons=tuple(int(value) for value in payload["horizons"]),
        execution_lag=int(payload["execution_lag"]),
        eligibility_policy=EtfEligibilityPolicy(
            min_prior_observations=int(eligibility["min_prior_observations"]),
            liquidity_window=int(eligibility["liquidity_window"]),
            min_trailing_median_amount=float(eligibility["min_trailing_median_amount"]),
            max_stale_rate=float(eligibility["max_stale_rate"]),
            max_abs_return=float(eligibility["max_abs_return"]),
        ),
        min_cross_section=int(thresholds["min_cross_section"]),
        min_ic_observations=int(thresholds["min_ic_observations"]),
        min_year_ic_observations=int(thresholds["min_year_ic_observations"]),
        min_usable_years=int(thresholds["min_usable_years"]),
        alpha=float(thresholds["alpha"]),
        min_mean_rank_ic=float(thresholds["min_mean_rank_ic"]),
        min_icir=float(thresholds["min_icir"]),
        min_positive_ic_rate=float(thresholds["min_positive_ic_rate"]),
        min_quantile_monotonicity=float(thresholds["min_quantile_monotonicity"]),
        max_top_quantile_turnover=float(thresholds["max_top_quantile_turnover"]),
        min_positive_year_rate=float(thresholds["min_positive_year_rate"]),
        max_abs_reference_correlation=float(thresholds["max_abs_reference_correlation"]),
    )
    result["configuration"] = {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "primary_market": payload["primary_market"],
        "candidate_names_match_frozen_contract": True,
        "reference_names_match_frozen_contract": True,
        "boundary_keys_all_false": True,
    }
    destination = Path(output_dir) if output_dir is not None else Path(payload["output_dir"])
    paths = write_cn_etf_skip_momentum_prescreen(destination, result)
    result["artifacts"] = {name: str(artifact_path) for name, artifact_path in paths.items()}
    return result


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"CN ETF skip-momentum config does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid CN ETF skip-momentum config JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("CN ETF skip-momentum config must be a JSON object")
    if payload.get("stage") != STAGE:
        raise ValueError(f"config stage must be {STAGE}")
    if payload.get("primary_market") != "CN_ETF":
        raise ValueError("config primary_market must be CN_ETF")
    if tuple(payload.get("candidate_names", ())) != ETF_SKIP_MOMENTUM_FACTOR_NAMES:
        raise ValueError("config candidate_names do not match the frozen skip-momentum contract")
    if tuple(payload.get("reference_names", ())) != ETF_PRICE_ROTATION_REFERENCE_FACTOR_NAMES:
        raise ValueError("config reference_names do not match the frozen historical-reference contract")
    if tuple(int(value) for value in payload.get("horizons", ())) != DEFAULT_HORIZONS:
        raise ValueError(f"config horizons must be {list(DEFAULT_HORIZONS)}")
    if int(payload.get("execution_lag", -1)) != 1:
        raise ValueError("config execution_lag must be 1")
    eligibility = payload.get("eligibility")
    thresholds = payload.get("thresholds")
    if not isinstance(eligibility, dict) or not eligibility.get("point_in_time"):
        raise ValueError("config must require point-in-time ETF eligibility")
    if not eligibility.get("official_etf_only"):
        raise ValueError("config must require official ETF metadata")
    if not isinstance(thresholds, dict):
        raise ValueError("config thresholds must be a JSON object")
    required_top_level = (
        "data_root",
        "metadata_root",
        "analysis_start_date",
        "analysis_end_date",
        "output_dir",
    )
    required_eligibility = (
        "min_prior_observations",
        "liquidity_window",
        "min_trailing_median_amount",
        "max_stale_rate",
        "max_abs_return",
    )
    required_thresholds = (
        "alpha",
        "min_cross_section",
        "min_ic_observations",
        "min_year_ic_observations",
        "min_usable_years",
        "min_mean_rank_ic",
        "min_icir",
        "min_positive_ic_rate",
        "min_quantile_monotonicity",
        "max_top_quantile_turnover",
        "min_positive_year_rate",
        "max_abs_reference_correlation",
    )
    _require_keys(payload, required_top_level, "config")
    _require_keys(eligibility, required_eligibility, "config eligibility")
    _require_keys(thresholds, required_thresholds, "config thresholds")
    for key in BOUNDARY_KEYS:
        if payload.get(key) is not False:
            raise ValueError(f"config {key} must be explicitly false")
    return payload


def _require_keys(payload: dict[str, Any], keys: tuple[str, ...], label: str) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError(f"{label} is missing keys: {', '.join(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen CN ETF skip-momentum statistical prescreen.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    result = run_cn_etf_skip_momentum_prescreen_cli(
        config_path=Path(args.config),
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(
        json.dumps(
            {
                "stage": result["stage"],
                "status": result["status"],
                "summary": result["summary"],
                "decision": result["decision"],
                "output_dir": str(Path(args.output_dir) if args.output_dir else Path(result["artifacts"]["json"]).parent),
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
