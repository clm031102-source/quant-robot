import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.factor_mining_candidate_plan_gate import build_factor_mining_candidate_plan_gate
from quant_robot.ops.profitability_event_revision_preregistration import (
    build_profitability_event_revision_preregistration,
    default_profitability_event_revision_candidate_specs,
    write_profitability_event_revision_preregistration,
)
from quant_robot.storage.dataset_store import DatasetStore


class ProfitabilityEventRevisionPreregistrationTests(unittest.TestCase):
    def test_preregisters_pit_revision_candidates_without_portfolio_permission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fina_indicator_inputs(root, _financial_rows())

            result = build_profitability_event_revision_preregistration(
                input_root=root,
                endpoint_probe_results={
                    "forecast": {
                        "ok": True,
                        "rows": 120,
                        "columns": ["ann_date", "end_date", "p_change_min", "p_change_max"],
                    },
                    "express": {
                        "ok": True,
                        "rows": 120,
                        "columns": ["ann_date", "end_date", "yoy_net_profit", "diluted_roe"],
                    },
                },
                min_assets=3,
                min_passed_candidates=6,
                min_families=3,
            )

        self.assertEqual(result["stage"], "profitability_event_revision_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["candidate_count"], 10)
        self.assertGreaterEqual(result["summary"]["coverage_passed_candidates"], 6)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertIn("research_control_plan", result)
        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("pit_fina_netprofit_yoy_revision_1q", names)
        self.assertIn("pit_forecast_profit_revision_event_1q", names)
        self.assertNotIn("fina_roe_level", names)
        plan_gate = build_factor_mining_candidate_plan_gate(result, gate_stage="discovery")
        self.assertTrue(plan_gate["decision"]["candidate_plan_gate_cleared"])
        self.assertFalse(plan_gate["decision"]["portfolio_grid_allowed"])

    def test_blocks_endpoint_candidates_without_endpoint_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fina_indicator_inputs(root, _financial_rows())

            result = build_profitability_event_revision_preregistration(
                input_root=root,
                endpoint_probe_results={},
                min_assets=3,
                min_passed_candidates=6,
                min_families=3,
            )

        candidates = {candidate["factor_name"]: candidate for candidate in result["candidates"]}
        self.assertEqual(
            candidates["pit_forecast_profit_revision_event_1q"]["registration_status"],
            "blocked_by_endpoint_availability",
        )
        self.assertEqual(
            candidates["pit_express_profit_surprise_event_1q"]["registration_status"],
            "blocked_by_endpoint_availability",
        )
        self.assertTrue(result["summary"]["passes"])

    def test_blocks_duplicate_or_round96_static_candidate_names(self) -> None:
        specs = list(default_profitability_event_revision_candidate_specs())
        specs = [specs[0], specs[0]]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fina_indicator_inputs(root, _financial_rows())
            result = build_profitability_event_revision_preregistration(
                input_root=root,
                candidate_specs=specs,
                min_assets=3,
                min_passed_candidates=1,
            )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("duplicate_candidate_names", result["summary"]["blockers"])

    def test_blocks_rejected_static_profitability_names(self) -> None:
        spec = default_profitability_event_revision_candidate_specs()[0]
        invalid = {
            **spec.__dict__,
            "factor_name": "fina_roe_level",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fina_indicator_inputs(root, _financial_rows())
            result = build_profitability_event_revision_preregistration(
                input_root=root,
                candidate_specs=[invalid],
                min_assets=3,
                min_passed_candidates=1,
            )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("round96_static_profitability_name_reused", result["summary"]["blockers"])

    def test_write_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output = Path(tmp) / "output"
            _write_fina_indicator_inputs(root, _financial_rows())
            result = build_profitability_event_revision_preregistration(
                input_root=root,
                min_assets=3,
                min_passed_candidates=6,
            )

            write_profitability_event_revision_preregistration(output, result)

            self.assertTrue((output / "profitability_event_revision_preregistration.json").exists())
            self.assertTrue((output / "profitability_event_revision_preregistration.md").exists())
            self.assertTrue((output / "profitability_event_revision_candidates.csv").exists())


def _financial_rows() -> pd.DataFrame:
    rows = []
    periods = pd.period_range("2022Q1", "2024Q4", freq="Q")
    for asset_idx in range(3):
        asset_id = f"CN_XSHE_{asset_idx:06d}"
        for period_idx, period in enumerate(periods):
            end_date = period.end_time.normalize()
            ann_date = end_date + pd.Timedelta(days=30 + asset_idx)
            rows.append(
                {
                    "date": ann_date,
                    "asset_id": asset_id,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "source": "tushare_fina_indicator",
                    "ann_date": ann_date,
                    "end_date": end_date,
                    "roe": 8.0 + asset_idx + period_idx * 0.2,
                    "roa": 3.0 + asset_idx + period_idx * 0.1,
                    "grossprofit_margin": 20.0 + period_idx,
                    "netprofit_margin": 6.0 + period_idx * 0.5,
                    "netprofit_yoy": 5.0 + period_idx * 1.2,
                    "or_yoy": 4.0 + period_idx * 0.8,
                    "ocfps": 1.0 + period_idx * 0.1,
                    "cfps": 1.2 + period_idx * 0.1,
                }
            )
    return pd.DataFrame(rows)


def _write_fina_indicator_inputs(root: Path, frame: pd.DataFrame) -> None:
    DatasetStore(root).write_frame(
        frame,
        "processed/fina_indicator_inputs",
        {"frequency": "1q", "market": "CN", "year": "2024"},
    )


if __name__ == "__main__":
    unittest.main()
