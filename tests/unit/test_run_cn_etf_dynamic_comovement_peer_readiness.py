import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_cn_etf_dynamic_comovement_peer_readiness import (
    run_cn_etf_dynamic_comovement_peer_readiness_cli,
)


class RunCnEtfDynamicComovementPeerReadinessTests(unittest.TestCase):
    def test_cli_runs_frozen_source_audit_and_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "processed"
            output_dir = root / "report"
            _write_fixture_data(data_root)
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(_config(data_root, output_dir), indent=2),
                encoding="utf-8",
            )

            result = run_cn_etf_dynamic_comovement_peer_readiness_cli(
                config_path=config_path
            )

            self.assertEqual(result["stage"], "cn_etf_dynamic_comovement_peer_readiness")
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(len(result["configuration"]["sha256"]), 64)
            self.assertTrue(Path(result["artifacts"]["json"]).exists())
            self.assertTrue(Path(result["artifacts"]["mapping_csv"]).exists())
            self.assertFalse(result["factor_generation_allowed"])

    def test_cli_rejects_peer_policy_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = _config(root / "processed", root / "report")
            payload["peer_policy"]["min_correlation"] = 0.40
            config_path = root / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "frozen peer policy"):
                run_cn_etf_dynamic_comovement_peer_readiness_cli(
                    config_path=config_path
                )

    def test_cli_rejects_final_holdout_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = _config(root / "processed", root / "report")
            payload["analysis_end_date"] = "2026-01-02"
            config_path = root / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "sealed final holdout"):
                run_cn_etf_dynamic_comovement_peer_readiness_cli(
                    config_path=config_path
                )

    def test_cli_rejects_enabled_execution_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = _config(root / "processed", root / "report")
            payload["factor_generation_allowed"] = True
            config_path = root / "config.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "must be false"):
                run_cn_etf_dynamic_comovement_peer_readiness_cli(
                    config_path=config_path
                )


def _config(data_root: Path, output_dir: Path) -> dict:
    return {
        "stage": "cn_etf_dynamic_comovement_peer_readiness",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_dynamic_comovement_peer_dislocation",
        "audit_scope": "lagged_market_residual_correlation_topk_peer_source",
        "data_root": str(data_root),
        "metadata_root": None,
        "analysis_start_date": "2020-01-02",
        "analysis_end_date": "2024-06-28",
        "final_holdout_start": "2026-01-01",
        "eligibility_policy": {
            "min_prior_observations": 120,
            "liquidity_window": 20,
            "min_trailing_median_amount": 5000000.0,
            "max_stale_rate": 0.05,
            "max_abs_return": 0.20,
        },
        "peer_policy": {
            "return_window": 120,
            "min_asset_return_observations": 100,
            "market_min_cross_section": 30,
            "beta_min_observations": 80,
            "pair_min_observations": 80,
            "min_correlation": 0.50,
            "max_peers": 5,
            "min_peers": 3,
            "rebalance_months": [1, 4, 7, 10],
            "residual_volatility_window": 60,
            "momentum_window": 60,
            "short_return_window": 5,
            "liquidity_window": 20,
        },
        "thresholds": {
            "min_qualifying_assets_per_date": 30,
            "min_qualifying_date_coverage": 0.80,
            "min_comparable_assets_per_transition": 30,
            "min_median_jaccard": 0.25,
            "min_median_retention": 0.40,
            "max_complete_churn_rate": 0.40,
            "min_reciprocity_rate": 0.30,
            "max_reference_edge_overlap": 0.50,
            "min_reference_edge_coverage": 0.80,
        },
        "output_dir": str(output_dir),
        "current_name_input_allowed": False,
        "official_2026_peer_mapping_allowed": False,
        "forward_return_calculation_allowed": False,
        "factor_generation_allowed": False,
        "prescreen_execution_allowed": False,
        "portfolio_grid_allowed": False,
        "walk_forward_allowed": False,
        "paper_signal_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "live_trading_allowed": False,
    }


def _write_fixture_data(root: Path) -> None:
    dates = pd.bdate_range("2020-01-02", periods=130)
    rows = []
    lifecycle = []
    market = np.resize(np.array([0.002, -0.001, 0.0015, -0.0005, 0.0008]), len(dates) - 1)
    pattern = np.resize(np.array([0.008, -0.006, 0.004, -0.003, 0.005]), len(dates) - 1)
    for asset_index in range(31):
        symbol = f"{510000 + asset_index:06d}.SH"
        asset_id = f"CN_ETF_XSHG_{510000 + asset_index:06d}"
        sign = 1.0 if asset_index < 16 else -1.0
        returns = market + sign * pattern
        prices = np.concatenate([[100.0], 100.0 * np.cumprod(1.0 + returns)])
        lifecycle.append(
            {
                "symbol": symbol,
                "is_etf": True,
                "list_date": "2010-01-01",
                "delist_date": None,
            }
        )
        for date_index, signal_date in enumerate(dates):
            rows.append(
                {
                    "date": signal_date,
                    "timestamp": signal_date,
                    "frequency": "1d",
                    "asset_id": asset_id,
                    "symbol": symbol,
                    "market": "CN_ETF",
                    "adj_close": prices[date_index],
                    "amount": 10_000_000.0 + asset_index * 10_000.0,
                }
            )
    store = DatasetStore(root)
    store.write_frame(
        pd.DataFrame(rows),
        "processed/bars",
        {"frequency": "1d", "market": "CN_ETF", "year": "2020"},
    )
    store.write_frame(
        pd.DataFrame(lifecycle),
        "metadata/tushare_fund_basic",
        {"market": "E", "snapshot": "2026-07-16"},
    )


if __name__ == "__main__":
    unittest.main()
