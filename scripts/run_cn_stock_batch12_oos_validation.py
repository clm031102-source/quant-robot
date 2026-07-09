from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.batch12_oos_validation import run_batch12_oos_validation
from quant_robot.ops.cn_stock_data_manifest import validate_cn_stock_data_manifest_packet
from quant_robot.ops.factor_batch_readiness_gate import validate_factor_batch_readiness_gate_packet
from quant_robot.ops.factor_mining_startup import validate_cleared_startup_gate_packet
from quant_robot.storage.authority_bars import (
    load_authority_processed_bars_from_config,
    load_authority_processed_dataset_from_config,
)


DEFAULT_HANDOFF = Path("configs/cn_stock_batch12_validation_handoff_20260617.json")
DEFAULT_PREFLIGHT = Path("data/reports/cn_stock_batch12_validation_preflight_20260620_current/batch12_validation_preflight.json")
DEFAULT_BARS = Path("configs/cn_stock_authority_bars_2015_2025.json")
DEFAULT_DAILY_BASIC = Path("configs/cn_stock_authority_daily_basic_inputs_2015_2025.json")
DEFAULT_OUTPUT = Path("data/reports/cn_stock_batch12_oos_validation_20260620")


def run_cn_stock_batch12_oos_validation_from_files(
    *,
    handoff: str | Path = DEFAULT_HANDOFF,
    preflight: str | Path = DEFAULT_PREFLIGHT,
    authority_bars_config: str | Path = DEFAULT_BARS,
    daily_basic_config: str | Path = DEFAULT_DAILY_BASIC,
    output_dir: str | Path = DEFAULT_OUTPUT,
    data_root: str | Path = "data/processed",
    startup_gate_packet: str | Path | None = Path("data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json"),
    data_manifest_packet: str | Path | None = Path("data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json"),
    factor_batch_readiness_gate_packet: str | Path | None = Path(
        "data/reports/factor_batch_readiness_gate/factor_batch_readiness_gate.json"
    ),
    allow_review_required_data_manifest: bool = False,
    feature_window_start: str = "2024-10-01",
    final_holdout_touched: bool = False,
) -> dict[str, object]:
    handoff_packet = json.loads(Path(handoff).read_text(encoding="utf-8"))
    preflight_packet = json.loads(Path(preflight).read_text(encoding="utf-8"))
    _enforce_cn_stock_batch12_oos_inputs(
        startup_gate_packet=startup_gate_packet,
        data_manifest_packet=data_manifest_packet,
        factor_batch_readiness_gate_packet=factor_batch_readiness_gate_packet,
        data_root=Path(data_root),
        allow_review_required_data_manifest=allow_review_required_data_manifest,
    )
    bars = load_authority_processed_bars_from_config(authority_bars_config, markets=("CN",))
    daily_basic = load_authority_processed_dataset_from_config(
        daily_basic_config,
        market="CN",
        dataset="processed/factor_inputs",
    )
    return run_batch12_oos_validation(
        bars=bars,
        daily_basic_inputs=daily_basic,
        handoff=handoff_packet,
        preflight=preflight_packet,
        output_dir=Path(output_dir),
        final_holdout_touched=final_holdout_touched,
        feature_window_start=feature_window_start,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run locked 2025 OOS validation for Batch12 CN stock candidates.")
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF))
    parser.add_argument("--preflight", default=str(DEFAULT_PREFLIGHT))
    parser.add_argument("--authority-bars-config", default=str(DEFAULT_BARS))
    parser.add_argument("--daily-basic-config", default=str(DEFAULT_DAILY_BASIC))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--startup-gate-packet", default="data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json")
    parser.add_argument("--data-manifest-packet", default="data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json")
    parser.add_argument(
        "--factor-batch-readiness-gate-packet",
        default="data/reports/factor_batch_readiness_gate/factor_batch_readiness_gate.json",
    )
    parser.add_argument("--allow-review-required-data-manifest", action="store_true")
    parser.add_argument("--feature-window-start", default="2024-10-01")
    parser.add_argument("--final-holdout-touched", action="store_true")
    args = parser.parse_args()
    try:
        packet = run_cn_stock_batch12_oos_validation_from_files(
            handoff=Path(args.handoff),
            preflight=Path(args.preflight),
            authority_bars_config=Path(args.authority_bars_config),
            daily_basic_config=Path(args.daily_basic_config),
            output_dir=Path(args.output_dir),
            data_root=Path(args.data_root),
            startup_gate_packet=Path(args.startup_gate_packet) if args.startup_gate_packet else None,
            data_manifest_packet=Path(args.data_manifest_packet) if args.data_manifest_packet else None,
            factor_batch_readiness_gate_packet=(
                Path(args.factor_batch_readiness_gate_packet) if args.factor_batch_readiness_gate_packet else None
            ),
            allow_review_required_data_manifest=args.allow_review_required_data_manifest,
            final_holdout_touched=args.final_holdout_touched,
            feature_window_start=args.feature_window_start,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(
        json.dumps(
            {
                "status": packet["status"],
                "validation_window": packet["validation_window"],
                "summary": packet["summary"],
                "output_dir": packet["output_dir"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _enforce_cn_stock_batch12_oos_inputs(
    *,
    startup_gate_packet: str | Path | None,
    data_manifest_packet: str | Path | None,
    factor_batch_readiness_gate_packet: str | Path | None,
    data_root: Path,
    allow_review_required_data_manifest: bool,
) -> None:
    validate_cleared_startup_gate_packet(
        startup_gate_packet,
        context="CN batch12 OOS validation",
    )
    validate_cn_stock_data_manifest_packet(
        data_manifest_packet,
        expected_source_root=data_root,
        allow_review_required=allow_review_required_data_manifest,
        context="CN batch12 OOS validation",
    )
    validate_factor_batch_readiness_gate_packet(
        factor_batch_readiness_gate_packet,
        context="CN batch12 OOS validation",
    )


if __name__ == "__main__":
    main()
