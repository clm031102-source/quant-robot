import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_tushare_alpha_factory import run_alpha_factory_cli


class TushareAlphaFactoryCliTests(unittest.TestCase):
    def test_cli_helper_runs_fixture_alpha_factory_and_writes_leaderboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factor_root = root / "factor_inputs"
            output_dir = root / "factory"
            _write_daily_basic_factor_inputs(factor_root, load_demo_market_bars())

            result = run_alpha_factory_cli(
                source="fixture",
                data_root=root,
                market="CN",
                factor_input_root=factor_root,
                output_dir=output_dir,
                top_n=1,
                cost_bps=5.0,
                execution_lag=1,
                alpha=0.05,
            )

            self.assertGreater(result["summary"]["hypothesis_count"], 0)
            self.assertTrue((output_dir / "candidate_leaderboard.csv").exists())

    def test_cli_helper_runs_fixture_moneyflow_alpha_factory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            moneyflow_root = root / "moneyflow_inputs"
            output_dir = root / "factory"
            _write_moneyflow_inputs(moneyflow_root, load_demo_market_bars())

            result = run_alpha_factory_cli(
                source="fixture",
                data_root=root,
                market="CN",
                factor_input_root=None,
                moneyflow_input_root=moneyflow_root,
                factor_source="tushare_moneyflow",
                output_dir=output_dir,
                top_n=1,
                cost_bps=5.0,
                execution_lag=1,
                alpha=0.05,
            )

            self.assertGreater(result["summary"]["hypothesis_count"], 0)
            self.assertTrue((output_dir / "candidate_leaderboard.csv").exists())

    def test_cli_helper_runs_fixture_moneyflow_technical_combo_alpha_factory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            moneyflow_root = root / "moneyflow_inputs"
            output_dir = root / "factory"
            _write_moneyflow_inputs(moneyflow_root, load_demo_market_bars())

            result = run_alpha_factory_cli(
                source="fixture",
                data_root=root,
                market="CN",
                factor_input_root=None,
                moneyflow_input_root=moneyflow_root,
                factor_source="moneyflow_technical_combo",
                output_dir=output_dir,
                top_n=1,
                cost_bps=5.0,
                execution_lag=1,
                alpha=0.05,
            )

            self.assertGreater(result["summary"]["hypothesis_count"], 0)
            self.assertTrue((output_dir / "candidate_leaderboard.csv").exists())

    def test_cli_helper_passes_capacity_and_cost_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factor_root = root / "factor_inputs"
            output_dir = root / "factory"
            _write_daily_basic_factor_inputs(factor_root, load_demo_market_bars())

            result = run_alpha_factory_cli(
                source="fixture",
                data_root=root,
                market="CN",
                factor_input_root=factor_root,
                output_dir=output_dir,
                top_n=1,
                cost_bps=5.0,
                execution_lag=1,
                alpha=0.05,
                min_trades=2,
                portfolio_value=500000.0,
                market_impact_bps=10.0,
                max_participation_rate=0.05,
                min_ic_observations=3,
                min_long_short_observations=4,
                require_capacity_controls=False,
            )

            self.assertEqual(result["config"]["min_trades"], 2)
            self.assertEqual(result["config"]["min_ic_observations"], 3)
            self.assertEqual(result["config"]["min_long_short_observations"], 4)
            self.assertAlmostEqual(result["config"]["portfolio_value"], 500000.0)
            self.assertAlmostEqual(result["config"]["market_impact_bps"], 10.0)
            self.assertAlmostEqual(result["config"]["max_participation_rate"], 0.05)
            self.assertFalse(result["config"]["require_capacity_controls"])

    def test_script_entrypoint_bootstraps_project_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factor_root = root / "factor_inputs"
            output_dir = root / "factory"
            _write_daily_basic_factor_inputs(factor_root, load_demo_market_bars())
            env = dict(os.environ)
            env["PYTHONPATH"] = "src"

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_tushare_alpha_factory.py",
                    "--source",
                    "fixture",
                    "--data-root",
                    str(root),
                    "--market",
                    "CN",
                    "--factor-input-root",
                    str(factor_root),
                    "--output-dir",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("summary", result.stdout)


def _write_daily_basic_factor_inputs(root: Path, bars: pd.DataFrame) -> None:
    rows = []
    for index, row in bars[bars["market"] == "CN"].reset_index(drop=True).iterrows():
        rows.append(
            {
                "date": row["date"],
                "asset_id": row["asset_id"],
                "symbol": row["symbol"],
                "market": "CN",
                "source": "tushare",
                "turnover_rate": 1.0 + index * 0.01,
                "turnover_rate_f": 1.1 + index * 0.01,
                "volume_ratio": 0.9 + index * 0.01,
                "pe_ttm": 8.0 + index * 0.1,
                "pb": 1.5 + index * 0.1,
                "ps_ttm": 2.0 + index * 0.1,
                "dv_ttm": 3.0,
                "total_mv": 120000.0 + index * 100.0,
                "circ_mv": 90000.0 + index * 100.0,
            }
        )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/factor_inputs",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


def _write_moneyflow_inputs(root: Path, bars: pd.DataFrame) -> None:
    rows = []
    for index, row in bars[bars["market"] == "CN"].reset_index(drop=True).iterrows():
        scale = 1.0 + index * 0.01
        rows.append(
            {
                "date": row["date"],
                "asset_id": row["asset_id"],
                "symbol": row["symbol"],
                "market": "CN",
                "source": "tushare_moneyflow",
                "buy_sm_amount": 100.0 * scale,
                "sell_sm_amount": 80.0 * scale,
                "buy_md_amount": 300.0 * scale,
                "sell_md_amount": 250.0 * scale,
                "buy_lg_amount": 500.0 * scale,
                "sell_lg_amount": 450.0 * scale,
                "buy_elg_amount": 700.0 * scale,
                "sell_elg_amount": 650.0 * scale,
                "net_mf_amount": 120.0 + index,
            }
        )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/moneyflow_inputs",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


if __name__ == "__main__":
    unittest.main()
