from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

try:
    from scripts.run_walk_forward import assert_walk_forward_succeeded, run_walk_forward
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from run_walk_forward import assert_walk_forward_succeeded, run_walk_forward

from quant_robot.validation.walk_forward import load_walk_forward_config
from quant_robot.ops.batch12_validation_preflight import validate_batch12_validation_preflight_packet


DEFAULT_CONFIG_PATH = Path("configs/walk_forward_tushare_moneyflow_residual_regime.json")
DEFAULT_DATA_ROOT = Path("configs/cn_stock_authority_bars_2015_2025.json")


def run_desktop_factor_validation(
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    source: str = "processed-bars",
    data_root: str | Path = DEFAULT_DATA_ROOT,
    output_dir: str | Path | None = None,
    require_accepted: bool = False,
    batch12_validation_preflight_packet: str | Path | None = None,
) -> dict[str, object]:
    config_path = Path(config_path)
    data_root = Path(data_root)
    _validate_optional_batch12_preflight(batch12_validation_preflight_packet)
    _preflight_desktop_inputs(config_path, source, data_root)
    result = run_walk_forward(
        config_path=config_path,
        source=source,
        data_root=data_root,
        output_dir=Path(output_dir) if output_dir is not None else None,
    )
    assert_walk_forward_succeeded(result, allow_no_accepted=not require_accepted)
    return result


def _validate_optional_batch12_preflight(packet_path: str | Path | None) -> None:
    if packet_path is None:
        return
    validate_batch12_validation_preflight_packet(Path(packet_path))


def _preflight_desktop_inputs(config_path: str | Path, source: str, data_root: str | Path) -> None:
    if source != "processed-bars":
        return
    root = Path(data_root)
    if not root.exists():
        raise FileNotFoundError(f"Processed bars data root does not exist: {root}")
    config = load_walk_forward_config(config_path)
    factor_input_root = config.experiment_grid.factor_input_root
    if config.experiment_grid.factor_source in {
        "tushare_daily_basic",
        "daily_basic_technical_combo",
        "daily_basic_smart_money_quality",
        "daily_basic_public_risk_filter_bridge",
        "daily_basic_value_liquidity_tail",
    }:
        _require_factor_input_root(factor_input_root, label="daily-basic")
        _validate_factor_input_coverage(root, factor_input_root, label="daily-basic")
    moneyflow_root = config.experiment_grid.moneyflow_input_root
    if config.experiment_grid.factor_source in {"tushare_moneyflow", "moneyflow_technical_combo"}:
        _require_factor_input_root(moneyflow_root, label="moneyflow")
        _validate_factor_input_coverage(root, moneyflow_root, label="moneyflow")
    _validate_strict_desktop_validation_contract(config)


def _validate_strict_desktop_validation_contract(config: Any) -> None:
    grid = config.experiment_grid
    blockers: list[str] = []
    rolling_values = {
        "rolling_train_days": config.rolling_train_days,
        "rolling_test_days": config.rolling_test_days,
        "rolling_step_days": config.rolling_step_days,
    }
    for name, value in rolling_values.items():
        if value is None or int(value) < 1:
            blockers.append(name)
    if config.min_test_trades < 30:
        blockers.append("min_test_trades")
    if grid.min_trades < 30:
        blockers.append("experiment_grid.min_trades")
    if config.min_test_relative_return is None:
        blockers.append("min_test_relative_return")
    if grid.min_relative_return is None:
        blockers.append("experiment_grid.min_relative_return")
    if config.max_test_drawdown is None:
        blockers.append("max_test_drawdown")
    if grid.max_drawdown_limit is None:
        blockers.append("experiment_grid.max_drawdown_limit")
    if not (0.0 < config.multiple_testing_alpha <= 0.05):
        blockers.append("multiple_testing_alpha")
    if grid.execution_lag < 1:
        blockers.append("experiment_grid.execution_lag")
    if grid.forward_horizon < 1:
        blockers.append("experiment_grid.forward_horizon")
    if not grid.rebalance_intervals or any(interval < 1 for interval in grid.rebalance_intervals):
        blockers.append("experiment_grid.rebalance_intervals")
    if not grid.cost_bps_values or not any(cost > 0 for cost in grid.cost_bps_values):
        blockers.append("experiment_grid.cost_bps_values")
    if grid.market_impact_bps <= 0:
        blockers.append("experiment_grid.market_impact_bps")
    if grid.max_participation_rate is None or not (0.0 < grid.max_participation_rate <= 0.05):
        blockers.append("experiment_grid.max_participation_rate")
    if grid.portfolio_value <= 0:
        blockers.append("experiment_grid.portfolio_value")
    if not grid.regime_filter:
        blockers.append("experiment_grid.regime_filter")
    if grid.regime_lookback_values is None or len(grid.regime_lookback_values) < 2:
        blockers.append("experiment_grid.regime_lookback_values")
    if not grid.precompute_factor_matrix:
        blockers.append("experiment_grid.precompute_factor_matrix")
    if not grid.reuse_research_inputs:
        blockers.append("experiment_grid.reuse_research_inputs")
    if not grid.resume_completed_cases:
        blockers.append("experiment_grid.resume_completed_cases")
    if blockers:
        raise ValueError(
            "strict desktop validation contract is not satisfied; missing or weak controls: "
            + ", ".join(blockers)
        )


def _require_factor_input_root(path: Path | None, *, label: str) -> None:
    if path is not None and path.exists():
        return
    target = path if path is not None else "<missing>"
    input_name = "moneyflow inputs" if label == "moneyflow" else f"{label} factor inputs"
    raise FileNotFoundError(
        f"Desktop factor validation requires Tushare {input_name} at "
        f"{target}. Run or sync the local Tushare {label} input pipeline before validation."
    )


def _validate_factor_input_coverage(data_root: Path, factor_input_root: Path | None, *, label: str) -> None:
    if factor_input_root is None or not data_root.is_file() or not factor_input_root.is_file():
        return
    bars_end = _authority_config_end_date(data_root)
    inputs_end = _authority_config_end_date(factor_input_root)
    if bars_end is None or inputs_end is None or inputs_end >= bars_end:
        return
    raise ValueError(
        f"{label} factor input coverage ends at {inputs_end.isoformat()}, "
        f"before authority bars coverage ends at {bars_end.isoformat()}. "
        "Use a bars config whose date range matches available factor inputs or backfill the factor inputs first."
    )


def _authority_config_end_date(path: Path) -> date | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    end_dates = [
        parsed
        for parsed in (_parse_date(segment.get("end_date")) for segment in _segments(data))
        if parsed is not None
    ]
    return max(end_dates) if end_dates else None


def _segments(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    segments = data.get("segments", [])
    if not isinstance(segments, list):
        return []
    return [segment for segment in segments if isinstance(segment, dict)]


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the desktop strict residual-regime factor validation profile."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="processed-bars")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--output-dir")
    parser.add_argument(
        "--require-accepted",
        action="store_true",
        help="Fail when validation completes but every candidate is rejected.",
    )
    parser.add_argument(
        "--batch12-validation-preflight-packet",
        help="Require and validate a cleared Batch 12 CN stock validation preflight packet before running.",
    )
    args = parser.parse_args()
    try:
        result = run_desktop_factor_validation(
            config_path=Path(args.config),
            source=args.source,
            data_root=Path(args.data_root),
            output_dir=Path(args.output_dir) if args.output_dir else None,
            require_accepted=args.require_accepted,
            batch12_validation_preflight_packet=(
                Path(args.batch12_validation_preflight_packet)
                if args.batch12_validation_preflight_packet
                else None
            ),
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({"summary": result["summary"], "top": result["leaderboard"][:20]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
