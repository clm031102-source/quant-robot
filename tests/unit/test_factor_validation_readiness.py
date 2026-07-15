import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from quant_robot.data.cn_trading_calendar import build_cn_trading_calendar, write_cn_trading_calendar
from quant_robot.ops.factor_validation_readiness import (
    build_factor_validation_readiness,
    validate_factor_validation_readiness_packet,
    write_factor_validation_readiness,
)


class FactorValidationReadinessTests(unittest.TestCase):
    def test_ready_packet_binds_config_factors_authority_data_and_calendar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _fixture(Path(tmp))
            packet = build_factor_validation_readiness(**fixture["build_args"])

            self.assertEqual(packet["status"], "ready")
            self.assertTrue(packet["decision"]["factor_validation_allowed"])
            self.assertFalse(packet["decision"]["promotion_allowed"])
            self.assertEqual(packet["config"]["factor_names"], ["large_resid_liq_vol_amt_gate_20"])
            self.assertEqual(packet["summary"]["task"], "factor_validation")
            output = fixture["root"] / "readiness"
            write_factor_validation_readiness(output, packet)

            validated = validate_factor_validation_readiness_packet(
                output / "factor_validation_readiness.json",
                expected_config_path=fixture["config_path"],
                expected_source="authority-bars",
                expected_data_root=fixture["bars_config"],
                expected_factor_names=["large_resid_liq_vol_amt_gate_20"],
            )

            self.assertEqual(validated["status"], "ready")

    def test_packet_is_blocked_for_wrong_branch_or_post_2025_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _fixture(Path(tmp))
            fixture["build_args"]["startup_gate_packet"]["summary"]["branch"] = "codex/factor-batch-cn-stock-x"
            fixture["build_args"]["data_manifest_packet"]["summary"]["date_end"] = "2026-01-02"

            packet = build_factor_validation_readiness(**fixture["build_args"])

            self.assertEqual(packet["status"], "blocked")
            self.assertIn("branch_not_factor_validation", packet["decision"]["blockers"])
            self.assertIn("final_holdout_data_present", packet["decision"]["blockers"])

    def test_validation_rejects_config_or_authority_data_changed_after_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _fixture(Path(tmp))
            output = fixture["root"] / "readiness"
            write_factor_validation_readiness(
                output,
                build_factor_validation_readiness(**fixture["build_args"]),
            )
            packet_path = output / "factor_validation_readiness.json"

            fixture["config_path"].write_text(
                fixture["config_path"].read_text(encoding="utf-8").replace("gate_20", "gate_21"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "config fingerprint mismatch"):
                validate_factor_validation_readiness_packet(
                    packet_path,
                    expected_config_path=fixture["config_path"],
                    expected_source="authority-bars",
                    expected_data_root=fixture["bars_config"],
                )

            fixture = _fixture(fixture["root"] / "second")
            output = fixture["root"] / "readiness"
            write_factor_validation_readiness(
                output,
                build_factor_validation_readiness(**fixture["build_args"]),
            )
            fixture["bar_file"].write_text("date,asset_id\n2024-01-02,B\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "authority data fingerprint mismatch"):
                validate_factor_validation_readiness_packet(
                    output / "factor_validation_readiness.json",
                    expected_config_path=fixture["config_path"],
                    expected_source="authority-bars",
                    expected_data_root=fixture["bars_config"],
                )

    def test_build_blocks_missing_authority_files_and_upstream_path_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _fixture(Path(tmp))
            fixture["bar_file"].unlink()
            fixture["build_args"]["startup_gate_path"].write_text("{}", encoding="utf-8")

            packet = build_factor_validation_readiness(**fixture["build_args"])

            self.assertEqual(packet["status"], "blocked")
            self.assertIn("authority_bars_data_missing", packet["decision"]["blockers"])
            self.assertIn("startup_packet_path_mismatch", packet["decision"]["blockers"])


def _fixture(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    bar_store = root / "bar_store"
    moneyflow_store = root / "moneyflow_store"
    bar_file = bar_store / "processed/bars/frequency=1d/market=CN/year=2024/bars.csv"
    moneyflow_file = (
        moneyflow_store / "processed/moneyflow_inputs/frequency=1d/market=CN/year=2024/moneyflow.csv"
    )
    bar_file.parent.mkdir(parents=True)
    moneyflow_file.parent.mkdir(parents=True)
    bar_file.write_text("date,asset_id\n2024-01-02,A\n", encoding="utf-8")
    moneyflow_file.write_text("date,asset_id\n2024-01-02,A\n", encoding="utf-8")
    bars_config = root / "authority_bars.json"
    moneyflow_config = root / "authority_moneyflow.json"
    bars_config.write_text(
        json.dumps({"market": "CN", "segments": [{"root": str(bar_store), "end_date": "2025-12-31"}]}),
        encoding="utf-8",
    )
    moneyflow_config.write_text(
        json.dumps({"market": "CN", "segments": [{"root": str(moneyflow_store), "end_date": "2025-12-31"}]}),
        encoding="utf-8",
    )
    config_path = root / "walk_forward.json"
    config_path.write_text(
        json.dumps(
            {
                "split_date": "2025-01-02",
                "bar_start_date": "2024-01-02",
                "bar_end_date": "2025-12-31",
                "experiment_grid": {
                    "markets": ["CN"],
                    "factor_source": "moneyflow_technical_combo",
                    "moneyflow_input_root": str(moneyflow_config),
                    "factor_names": ["large_resid_liq_vol_amt_gate_20"],
                    "factor_windows": [20],
                    "top_n_values": [5],
                    "cost_bps_values": [20],
                },
            }
        ),
        encoding="utf-8",
    )
    exchange = pd.DataFrame(
        {
            "exchange": ["SSE", "SSE"],
            "date": pd.to_datetime(["2024-01-02", "2025-12-31"]).date,
            "is_open": [1, 1],
        }
    )
    calendar, calendar_manifest = build_cn_trading_calendar(
        {"SSE": exchange, "SZSE": exchange.assign(exchange="SZSE")},
        start_date="2024-01-01",
        end_date="2025-12-31",
    )
    calendar_paths = write_cn_trading_calendar(root / "calendar", calendar, calendar_manifest)
    startup = {
        "generated_at": date.today().isoformat(),
        "status": "cleared",
        "summary": {
            "task": "factor_validation",
            "branch": "codex/factor-validation-cn-stock-evidence",
            "market": "CN",
            "asset_type": "stock",
        },
        "decision": {"startup_gate_cleared": True, "blockers": []},
        "live_boundary_allowed": False,
    }
    data_manifest = {
        "generated_at": date.today().isoformat(),
        "status": "review_required",
        "summary": {
            "source_root": str(bars_config),
            "moneyflow_source_root": str(moneyflow_config),
            "bar_rows": 10,
            "bar_symbols": 2,
            "date_start": "2024-01-02",
            "date_end": "2025-12-31",
        },
        "decision": {"data_manifest_cleared": False, "blockers": [], "warnings": ["review"]},
        "live_boundary_allowed": False,
    }
    startup_path = root / "startup.json"
    startup_path.write_text(json.dumps(startup), encoding="utf-8")
    data_manifest_path = root / "data_manifest.json"
    data_manifest_path.write_text(json.dumps(data_manifest), encoding="utf-8")
    return {
        "root": root,
        "config_path": config_path,
        "bars_config": bars_config,
        "moneyflow_config": moneyflow_config,
        "bar_file": bar_file,
        "build_args": {
            "config_path": config_path,
            "source": "authority-bars",
            "data_root": bars_config,
            "startup_gate_packet": startup,
            "startup_gate_path": startup_path,
            "data_manifest_packet": data_manifest,
            "data_manifest_path": data_manifest_path,
            "calendar_manifest": calendar_paths["manifest"],
            "calendar_path": calendar_paths["calendar_path"],
            "calendar_manifest_path": calendar_paths["manifest_path"],
        },
    }


if __name__ == "__main__":
    unittest.main()
