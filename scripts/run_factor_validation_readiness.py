from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.cn_trading_calendar import validate_cn_trading_calendar_artifact  # noqa: E402
from quant_robot.ops.cn_stock_data_manifest import validate_cn_stock_data_manifest_packet  # noqa: E402
from quant_robot.ops.factor_mining_startup import validate_cleared_startup_gate_packet  # noqa: E402
from quant_robot.ops.factor_validation_readiness import (  # noqa: E402
    build_factor_validation_readiness,
    write_factor_validation_readiness,
)
from quant_robot.validation.walk_forward import load_walk_forward_config  # noqa: E402


DEFAULT_CONFIG = Path("configs/walk_forward_tushare_moneyflow_residual_regime.json")
DEFAULT_DATA_ROOT = Path("configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json")
DEFAULT_STARTUP_GATE = Path("data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json")
DEFAULT_DATA_MANIFEST = Path(
    "data/reports/cn_stock_data_manifest_tushare_moneyflow_residual_regime/cn_stock_data_manifest.json"
)
DEFAULT_CALENDAR_DIR = Path("data/processed/trading_calendars/cn_tushare_2015_2025")
DEFAULT_OUTPUT_DIR = Path("data/reports/factor_validation_readiness_tushare_moneyflow_residual_regime")


def run_factor_validation_readiness(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    source: str = "authority-bars",
    data_root: str | Path = DEFAULT_DATA_ROOT,
    startup_gate_path: str | Path = DEFAULT_STARTUP_GATE,
    data_manifest_path: str | Path = DEFAULT_DATA_MANIFEST,
    calendar_path: str | Path = DEFAULT_CALENDAR_DIR / "cn_trading_calendar.csv",
    calendar_manifest_path: str | Path = DEFAULT_CALENDAR_DIR / "cn_trading_calendar_manifest.json",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    config_file = Path(config_path)
    data_path = Path(data_root)
    startup_path = Path(startup_gate_path)
    manifest_path = Path(data_manifest_path)
    config = load_walk_forward_config(config_file)
    moneyflow_root = config.experiment_grid.moneyflow_input_root
    if moneyflow_root is None:
        raise ValueError("Factor validation config requires a moneyflow authority root")
    startup = validate_cleared_startup_gate_packet(startup_path, context="CN stock factor validation readiness")
    data_manifest = validate_cn_stock_data_manifest_packet(
        manifest_path,
        expected_source_root=data_path,
        expected_moneyflow_source_root=moneyflow_root,
        allow_review_required=True,
        verify_source_fingerprint=True,
        context="CN stock factor validation readiness",
    )
    calendar_manifest = validate_cn_trading_calendar_artifact(calendar_path, calendar_manifest_path)
    packet = build_factor_validation_readiness(
        config_path=config_file,
        source=source,
        data_root=data_path,
        startup_gate_packet=startup,
        startup_gate_path=startup_path,
        data_manifest_packet=data_manifest,
        data_manifest_path=manifest_path,
        calendar_manifest=calendar_manifest,
        calendar_path=calendar_path,
        calendar_manifest_path=calendar_manifest_path,
    )
    write_factor_validation_readiness(output_dir, packet)
    if packet["status"] != "ready":
        raise RuntimeError(
            "Factor validation readiness is blocked: " + ", ".join(packet["decision"]["blockers"])
        )
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the frozen CN stock factor-validation readiness packet.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--source", choices=["authority-bars"], default="authority-bars")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--startup-gate-packet", default=str(DEFAULT_STARTUP_GATE))
    parser.add_argument("--data-manifest-packet", default=str(DEFAULT_DATA_MANIFEST))
    parser.add_argument("--calendar-path", default=str(DEFAULT_CALENDAR_DIR / "cn_trading_calendar.csv"))
    parser.add_argument(
        "--calendar-manifest-path",
        default=str(DEFAULT_CALENDAR_DIR / "cn_trading_calendar_manifest.json"),
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    try:
        packet = run_factor_validation_readiness(
            config_path=Path(args.config),
            source=args.source,
            data_root=Path(args.data_root),
            startup_gate_path=Path(args.startup_gate_packet),
            data_manifest_path=Path(args.data_manifest_packet),
            calendar_path=Path(args.calendar_path),
            calendar_manifest_path=Path(args.calendar_manifest_path),
            output_dir=Path(args.output_dir),
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(
        json.dumps(
            {
                "status": packet["status"],
                "summary": packet["summary"],
                "decision": packet["decision"],
                "safety": packet["safety"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
