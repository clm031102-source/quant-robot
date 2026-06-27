from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.simulation_shortlist_signal_reconstruction import (
    build_simulation_shortlist_signal_reconstruction,
    write_simulation_shortlist_signal_reconstruction,
)


class SimulationShortlistSignalReconstructionTest(unittest.TestCase):
    def test_reconstructs_asset_level_weights_and_reconciles_event_returns(self) -> None:
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002", "CN_XSHE_000003"],
                "signal_date": ["2024-01-01", "2024-01-01", "2024-01-01"],
                "entry_date": ["2024-01-02", "2024-01-02", "2024-01-02"],
                "exit_date": ["2024-01-10", "2024-01-10", "2024-01-10"],
                "target_weight": [0.4, 0.3, 0.3],
                "entry_cash_proxy_weighted_return": [0.04, -0.03, 0.01],
            }
        )
        dragon = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000002"],
                "date": ["2023-12-29"],
                "available_date": ["2024-01-02"],
                "top_list_event_count": [1],
                "top_list_net_amount_sum": [100.0],
                "top_list_abs_pct_change_max": [10.0],
            }
        )
        public = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-01", "2024-01-01"],
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002", "CN_XSHE_000003"],
                "public_factor_name": ["alpha"] * 3,
                "factor_value": [1.0, 0.0, 2.0],
            }
        )
        event_source = pd.DataFrame(
            {
                "date": ["2024-01-10"],
                "decision_date": ["2024-01-02"],
                "final_exposure": [0.5],
                "period_return": [0.035],
            }
        )

        result = build_simulation_shortlist_signal_reconstruction(
            trades_source=trades,
            event_source=event_source,
            dragon_tiger_source=dragon,
            public_factor_source=public,
            public_factor_name="alpha",
            public_factor_side="bottom",
            public_factor_quantile=0.5,
            public_factor_exposure_multiplier=1.5,
        )

        self.assertEqual(result["summary"]["trade_count"], 3)
        self.assertEqual(result["summary"]["dragon_cash_trade_count"], 1)
        self.assertEqual(result["summary"]["public_tilt_trade_count"], 1)
        self.assertAlmostEqual(result["summary"]["max_abs_return_reconciliation_diff"], 0.0)
        self.assertTrue(result["paper_readiness"]["paper_ready"])
        self.assertEqual(result["paper_readiness"]["blockers"], [])

        signals = pd.DataFrame(result["signal_rows"]).set_index("asset_id")
        self.assertAlmostEqual(signals.loc["CN_XSHE_000001", "pre_overlay_target_weight"], 0.6)
        self.assertAlmostEqual(signals.loc["CN_XSHE_000001", "target_weight"], 0.3)
        self.assertAlmostEqual(signals.loc["CN_XSHE_000002", "target_weight"], 0.0)
        self.assertAlmostEqual(signals.loc["CN_XSHE_000003", "target_weight"], 0.15)

    def test_reconciles_date_level_event_rows_with_multiple_trade_decisions(self) -> None:
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                "signal_date": ["2024-01-01", "2024-01-02"],
                "entry_date": ["2024-01-02", "2024-01-03"],
                "exit_date": ["2024-01-10", "2024-01-10"],
                "target_weight": [0.5, 0.5],
                "entry_cash_proxy_weighted_return": [0.01, 0.02],
            }
        )
        dragon = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_999999"],
                "date": ["2023-12-29"],
                "available_date": ["2024-01-02"],
                "top_list_event_count": [0],
                "top_list_net_amount_sum": [0.0],
                "top_list_abs_pct_change_max": [0.0],
            }
        )
        public = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-02"],
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                "public_factor_name": ["alpha", "alpha"],
                "factor_value": [1.0, 2.0],
            }
        )
        event_source = pd.DataFrame(
            {
                "date": ["2024-01-10"],
                "decision_date": ["2024-01-02"],
                "final_exposure": [1.0],
                "period_return": [0.03],
            }
        )

        result = build_simulation_shortlist_signal_reconstruction(
            trades_source=trades,
            event_source=event_source,
            dragon_tiger_source=dragon,
            public_factor_source=public,
            public_factor_name="alpha",
            public_factor_side="top",
            public_factor_quantile=0.5,
            public_factor_exposure_multiplier=1.0,
        )

        self.assertAlmostEqual(result["summary"]["max_abs_return_reconciliation_diff"], 0.0)
        self.assertEqual(result["summary"]["collapsed_event_decision_date_count"], 1)
        self.assertEqual(result["summary"]["event_decision_date_mismatch_count"], 1)
        self.assertIn(
            "event_decision_date_collapses_multiple_trade_decisions",
            result["paper_readiness"]["blockers"],
        )
        self.assertIn("event_decision_date_mismatch", result["paper_readiness"]["blockers"])

    def test_writer_exports_signal_and_reconciliation_artifacts(self) -> None:
        result = {
            "stage": "simulation_shortlist_signal_reconstruction",
            "summary": {"candidate_name": "demo"},
            "paper_readiness": {"paper_ready": False, "blockers": ["demo_blocker"]},
            "signal_rows": [{"asset_id": "CN_XSHE_000001", "target_weight": 0.1}],
            "reconciliation_rows": [
                {"date": "2024-01-10", "trade_max_decision_date": pd.NaT, "reconciliation_diff": 0.0}
            ],
        }

        with TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_simulation_shortlist_signal_reconstruction(output, result)

            self.assertTrue((output / "simulation_shortlist_signal_reconstruction.json").exists())
            self.assertTrue((output / "simulation_shortlist_signal_rows.csv").exists())
            self.assertTrue((output / "simulation_shortlist_reconciliation_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
