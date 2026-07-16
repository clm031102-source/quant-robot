import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_cn_etf_peer_relative_value_metadata_readiness import (
    STAGE,
    run_cn_etf_peer_relative_value_metadata_readiness_cli,
)


class RunCnEtfPeerRelativeValueMetadataReadinessTests(unittest.TestCase):
    def test_cli_runs_frozen_metadata_audit_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "processed"
            output_dir = root / "report"
            store = DatasetStore(data_root)
            bars = pd.DataFrame(
                [
                    {"asset_id": "CN_ETF_A", "date": "2024-01-02", "close": 1.0},
                    {"asset_id": "CN_ETF_B", "date": "2024-01-02", "close": 1.1},
                ]
            )
            store.write_frame(
                bars,
                "processed/bars",
                {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
            )
            store.write_frame(
                pd.DataFrame(
                    [
                        {
                            "symbol": "510300.SH",
                            "name": "沪深300ETF",
                            "market": "E",
                            "is_etf": True,
                            "fund_type": "股票型",
                            "type": "ETF",
                            "list_date": "2012-05-28",
                            "delist_date": None,
                        }
                    ]
                ),
                "metadata/tushare_fund_basic",
                {"market": "E", "snapshot": "2026-06-21"},
            )
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(_config(data_root, output_dir), ensure_ascii=False),
                encoding="utf-8",
            )

            result = run_cn_etf_peer_relative_value_metadata_readiness_cli(config_path=config_path)

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["configuration"]["stage"], STAGE)
            self.assertEqual(len(result["configuration"]["sha256"]), 64)
            self.assertTrue(Path(result["artifacts"]["json"]).exists())
            self.assertTrue(Path(result["artifacts"]["markdown"]).exists())
            self.assertIn("official_peer_identifier_missing", result["gate"]["blockers"])

    def test_cli_rejects_analysis_window_that_reads_final_holdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = _config(root / "processed", root / "report")
            payload["analysis_end_date"] = "2026-01-02"
            config_path = root / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "sealed final holdout"):
                run_cn_etf_peer_relative_value_metadata_readiness_cli(config_path=config_path)

    def test_cli_rejects_enabled_execution_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = _config(root / "processed", root / "report")
            payload["prescreen_execution_allowed"] = True
            config_path = root / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must be false"):
                run_cn_etf_peer_relative_value_metadata_readiness_cli(config_path=config_path)


def _config(data_root: Path, output_dir: Path) -> dict:
    return {
        "stage": STAGE,
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_peer_relative_value",
        "audit_scope": "point_in_time_official_peer_mapping",
        "data_root": str(data_root),
        "peer_mapping_path": None,
        "analysis_start_date": "2024-01-02",
        "analysis_end_date": "2024-01-03",
        "final_holdout_start": "2026-01-01",
        "thresholds": {
            "min_peer_group_size": 2,
            "min_qualifying_assets_per_date": 30,
            "min_qualifying_date_coverage": 0.8,
        },
        "output_dir": str(output_dir),
        "name_only_mapping_allowed": False,
        "prescreen_execution_allowed": False,
        "portfolio_grid_allowed": False,
        "walk_forward_allowed": False,
        "paper_signal_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "live_trading_allowed": False,
    }


if __name__ == "__main__":
    unittest.main()
