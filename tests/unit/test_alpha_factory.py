import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.factors.moneyflow_technical import MONEYFLOW_TECHNICAL_COMBO_FACTOR_NAMES
from quant_robot.factors.tushare_inputs import DAILY_BASIC_FACTOR_NAMES
from quant_robot.factors.tushare_moneyflow import MONEYFLOW_FACTOR_NAMES
from quant_robot.research.alpha_factory import (
    AlphaFactoryConfig,
    _candidate_row,
    _summary,
    apply_bonferroni_correction,
    run_tushare_alpha_factory,
)
from quant_robot.storage.dataset_store import DatasetStore


class AlphaFactoryTests(unittest.TestCase):
    def test_alpha_factory_defaults_use_research_grade_candidate_gates(self):
        config = AlphaFactoryConfig()

        self.assertEqual(config.min_trades, 30)
        self.assertEqual(config.min_ic_observations, 20)
        self.assertEqual(config.min_long_short_observations, 20)
        self.assertTrue(config.require_capacity_controls)
        self.assertGreater(config.market_impact_bps, 0.0)
        self.assertIsNotNone(config.max_participation_rate)

    def test_bonferroni_correction_tracks_hypothesis_count_and_adjusted_p_value(self):
        rows = [
            {"factor_name": "a", "ic_p_value": 0.01},
            {"factor_name": "b", "ic_p_value": 0.03},
            {"factor_name": "c", "ic_p_value": 0.20},
        ]

        result = apply_bonferroni_correction(rows, alpha=0.05)

        self.assertEqual({row["hypothesis_count"] for row in result}, {3})
        self.assertAlmostEqual(result[0]["adjusted_ic_p_value"], 0.03)
        self.assertTrue(result[0]["passes_adjusted_ic_p_value"])
        self.assertFalse(result[1]["passes_adjusted_ic_p_value"])
        self.assertFalse(result[2]["passes_adjusted_ic_p_value"])

    def test_bonferroni_correction_only_allows_positive_direction_paper_candidates(self):
        rows = [
            {
                "case_id": "positive",
                "status": "completed",
                "factor_name": "low_turnover",
                "ic_p_value": 0.001,
                "significance_status": "significant_positive",
            },
            {
                "case_id": "negative",
                "status": "completed",
                "factor_name": "turnover_rate",
                "ic_p_value": 0.001,
                "significance_status": "significant_negative",
            },
        ]

        result = apply_bonferroni_correction(rows, alpha=0.05)

        by_id = {row["case_id"]: row for row in result}
        self.assertTrue(by_id["positive"]["paper_candidate_allowed"])
        self.assertFalse(by_id["negative"]["paper_candidate_allowed"])
        self.assertIn("significance_direction_not_positive", by_id["negative"]["paper_candidate_rejection_reasons"])

    def test_bonferroni_correction_blocks_capacity_limited_paper_candidates(self):
        rows = [
            {
                "case_id": "capacity_limited",
                "status": "completed",
                "factor_name": "large_order_net_amount_ratio",
                "ic_p_value": 0.001,
                "significance_status": "significant_positive",
                "capacity_limited_trades": 1,
            }
        ]

        result = apply_bonferroni_correction(rows, alpha=0.05)

        self.assertFalse(result[0]["paper_candidate_allowed"])
        self.assertIn("capacity_limited_trades_present", result[0]["paper_candidate_rejection_reasons"])

    def test_candidate_row_rejects_underpowered_samples(self):
        row = {
            "case_id": "tiny_sample",
            "status": "completed",
            "trades": 1,
            "ic_observations": 2,
            "long_short_observations": 2,
            "ic_p_value": 0.001,
            "significance_status": "significant_positive",
            "capacity_limited_trades": 0,
        }

        result = _candidate_row(row, AlphaFactoryConfig())

        self.assertIn("insufficient_trades", result["multiple_test_rejection_reasons"])
        self.assertIn("insufficient_ic_observations", result["multiple_test_rejection_reasons"])
        self.assertIn("insufficient_long_short_observations", result["multiple_test_rejection_reasons"])

    def test_candidate_row_rejects_missing_capacity_controls(self):
        row = {
            "case_id": "uncosted",
            "status": "completed",
            "trades": 30,
            "ic_observations": 20,
            "long_short_observations": 20,
            "ic_p_value": 0.001,
            "significance_status": "significant_positive",
            "capacity_limited_trades": 0,
        }
        config = AlphaFactoryConfig(
            min_trades=1,
            market_impact_bps=0.0,
            max_participation_rate=None,
        )

        result = apply_bonferroni_correction([_candidate_row(row, config)], alpha=0.05)[0]

        self.assertFalse(result["paper_candidate_allowed"])
        self.assertIn("market_impact_not_configured", result["paper_candidate_rejection_reasons"])
        self.assertIn("max_participation_rate_not_configured", result["paper_candidate_rejection_reasons"])

    def test_summary_counts_capacity_and_return_quality(self):
        leaderboard = [
            {
                "status": "completed",
                "passes_adjusted_ic_p_value": True,
                "paper_candidate_allowed": True,
                "capacity_limited_trades": 0,
                "sharpe": 1.2,
                "total_return": 0.03,
            },
            {
                "status": "completed",
                "passes_adjusted_ic_p_value": True,
                "paper_candidate_allowed": True,
                "capacity_limited_trades": 0,
                "sharpe": -0.5,
                "total_return": -0.02,
            },
            {
                "status": "completed",
                "passes_adjusted_ic_p_value": False,
                "paper_candidate_allowed": False,
                "capacity_limited_trades": 3,
                "sharpe": -1.0,
                "total_return": 0.01,
            },
        ]

        summary = _summary(leaderboard)

        self.assertEqual(summary["capacity_limited"], 1)
        self.assertEqual(summary["positive_total_return"], 2)
        self.assertEqual(summary["positive_sharpe"], 1)
        self.assertEqual(summary["paper_eligible_positive_return"], 1)
        self.assertEqual(summary["paper_eligible_negative_return"], 1)


    def test_alpha_factory_runs_pre_registered_daily_basic_family_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factor_root = root / "factor_inputs"
            output_dir = root / "factory"
            bars = load_demo_market_bars()
            _write_daily_basic_factor_inputs(factor_root, bars)

            result = run_tushare_alpha_factory(
                bars,
                AlphaFactoryConfig(
                    market="CN",
                    factor_input_root=factor_root,
                    output_dir=output_dir,
                    top_n=1,
                    cost_bps=5.0,
                    alpha=0.05,
                ),
            )

            leaderboard = result["candidate_leaderboard"]
            self.assertEqual(result["summary"]["hypothesis_count"], len(DAILY_BASIC_FACTOR_NAMES))
            self.assertEqual(len(leaderboard), len(DAILY_BASIC_FACTOR_NAMES))
            self.assertEqual({row["factor_source"] for row in leaderboard}, {"tushare_daily_basic"})
            self.assertTrue(all("adjusted_ic_p_value" in row for row in leaderboard))
            self.assertTrue(all("multiple_test_rejection_reasons" in row for row in leaderboard))
            self.assertTrue(all("paper_candidate_allowed" in row for row in leaderboard))
            self.assertTrue((output_dir / "candidate_leaderboard.csv").exists())
            self.assertTrue((output_dir / "candidate_leaderboard.json").exists())
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["summary"]["hypothesis_count"], len(DAILY_BASIC_FACTOR_NAMES))

    def test_alpha_factory_runs_pre_registered_moneyflow_family_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            moneyflow_root = root / "moneyflow_inputs"
            output_dir = root / "factory"
            bars = load_demo_market_bars()
            _write_moneyflow_inputs(moneyflow_root, bars)

            result = run_tushare_alpha_factory(
                bars,
                AlphaFactoryConfig(
                    market="CN",
                    factor_source="tushare_moneyflow",
                    moneyflow_input_root=moneyflow_root,
                    output_dir=output_dir,
                    top_n=1,
                    cost_bps=5.0,
                    alpha=0.05,
                ),
            )

            leaderboard = result["candidate_leaderboard"]
            self.assertEqual(result["summary"]["hypothesis_count"], len(MONEYFLOW_FACTOR_NAMES))
            self.assertEqual(len(leaderboard), len(MONEYFLOW_FACTOR_NAMES))
            self.assertEqual({row["factor_source"] for row in leaderboard}, {"tushare_moneyflow"})
            self.assertTrue(all("paper_candidate_allowed" in row for row in leaderboard))
            self.assertTrue((output_dir / "candidate_leaderboard.csv").exists())

    def test_alpha_factory_runs_pre_registered_moneyflow_technical_combo_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            moneyflow_root = root / "moneyflow_inputs"
            output_dir = root / "factory"
            bars = load_demo_market_bars()
            _write_moneyflow_inputs(moneyflow_root, bars)

            result = run_tushare_alpha_factory(
                bars,
                AlphaFactoryConfig(
                    market="CN",
                    factor_source="moneyflow_technical_combo",
                    moneyflow_input_root=moneyflow_root,
                    output_dir=output_dir,
                    top_n=1,
                    cost_bps=5.0,
                    alpha=0.05,
                ),
            )

            leaderboard = result["candidate_leaderboard"]
            self.assertEqual(result["summary"]["hypothesis_count"], len(MONEYFLOW_TECHNICAL_COMBO_FACTOR_NAMES))
            self.assertEqual(len(leaderboard), len(MONEYFLOW_TECHNICAL_COMBO_FACTOR_NAMES))
            self.assertEqual({row["factor_source"] for row in leaderboard}, {"moneyflow_technical_combo"})
            self.assertTrue((output_dir / "candidate_leaderboard.csv").exists())


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
