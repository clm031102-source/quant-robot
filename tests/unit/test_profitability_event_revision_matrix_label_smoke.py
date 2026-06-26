import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.factor_mining_candidate_plan_gate import build_factor_mining_candidate_plan_gate, write_factor_mining_candidate_plan_gate
from quant_robot.ops.profitability_event_revision_matrix_label_smoke import (
    build_profitability_event_revision_matrix_label_smoke,
    compute_profitability_event_revision_factor_frame,
    write_profitability_event_revision_matrix_label_smoke,
)
from quant_robot.ops.profitability_event_revision_preregistration import (
    build_profitability_event_revision_preregistration,
    write_profitability_event_revision_preregistration,
)
from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_profitability_event_revision_preregistration import (
    _financial_rows,
    _write_fina_indicator_inputs,
)


class ProfitabilityEventRevisionMatrixLabelSmokeTests(unittest.TestCase):
    def test_builds_active_factor_matrix_and_labels_without_lookahead(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_dir = root / "prereg"
            gate_dir = root / "gate"
            _write_fina_indicator_inputs(financial_root, _financial_rows())
            _write_bars(bars_root, _financial_rows()["asset_id"].unique().tolist())
            prereg = build_profitability_event_revision_preregistration(
                input_root=financial_root,
                min_assets=3,
                min_passed_candidates=6,
                min_families=3,
            )
            write_profitability_event_revision_preregistration(prereg_dir, prereg)
            gate = build_factor_mining_candidate_plan_gate(prereg, gate_stage="discovery")
            write_factor_mining_candidate_plan_gate(gate_dir, gate)

            result = build_profitability_event_revision_matrix_label_smoke(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_dir / "profitability_event_revision_preregistration.json",
                candidate_plan_gate_json=gate_dir / "factor_mining_candidate_plan_gate.json",
                horizons=(5, 20),
                execution_lag=1,
                min_label_coverage=0.6,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["active_candidate_count"], 7)
            self.assertEqual(result["summary"]["frozen_candidate_count"], 3)
            self.assertEqual(result["summary"]["unknown_active_candidate_count"], 0)
            self.assertGreater(result["summary"]["factor_value_rows"], 0)
            self.assertGreater(result["summary"]["label_aligned_rows"], 0)
            self.assertEqual(result["summary"]["alignment_violation_rows"], 0)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertIn("pit_fina_netprofit_yoy_revision_1q", {row["factor_name"] for row in result["candidate_summaries"]})

    def test_signal_date_is_strictly_after_ann_date(self) -> None:
        financial = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2023-10-31"),
                    "asset_id": "CN_XSHE_000001",
                    "market": "CN",
                    "ann_date": pd.Timestamp("2023-10-31"),
                    "end_date": pd.Timestamp("2023-09-30"),
                    "netprofit_yoy": 1.0,
                },
                {
                    "date": pd.Timestamp("2024-01-02"),
                    "asset_id": "CN_XSHE_000001",
                    "market": "CN",
                    "ann_date": pd.Timestamp("2024-01-02"),
                    "end_date": pd.Timestamp("2023-12-31"),
                    "netprofit_yoy": 3.5,
                },
            ]
        )
        bars = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
                "asset_id": ["CN_XSHE_000001"] * 3,
                "market": ["CN"] * 3,
                "adj_close": [10.0, 10.1, 10.2],
            }
        )
        candidates = [{"factor_name": "pit_fina_netprofit_yoy_revision_1q", "registration_status": "pre_registered"}]

        factors = compute_profitability_event_revision_factor_frame(financial, candidates, bars)

        self.assertEqual(len(factors), 1)
        self.assertEqual(pd.Timestamp(factors.iloc[0]["ann_date"]), pd.Timestamp("2024-01-02"))
        self.assertEqual(pd.Timestamp(factors.iloc[0]["date"]), pd.Timestamp("2024-01-03"))
        self.assertGreater(pd.Timestamp(factors.iloc[0]["date"]), pd.Timestamp(factors.iloc[0]["ann_date"]))

    def test_blocks_unknown_active_formula(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_dir = root / "prereg"
            _write_fina_indicator_inputs(financial_root, _financial_rows())
            _write_bars(bars_root, _financial_rows()["asset_id"].unique().tolist())
            prereg = build_profitability_event_revision_preregistration(
                input_root=financial_root,
                min_assets=3,
                min_passed_candidates=6,
                min_families=3,
            )
            prereg["candidates"] = [
                {
                    "factor_name": "fina_roe_level",
                    "family": "rejected_static_profitability",
                    "market": "CN",
                    "asset_type": "stock",
                    "registration_status": "pre_registered",
                    "portfolio_backtest_allowed": False,
                    "promotion_allowed": False,
                }
            ]
            write_profitability_event_revision_preregistration(prereg_dir, prereg)

            result = build_profitability_event_revision_matrix_label_smoke(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_dir / "profitability_event_revision_preregistration.json",
                horizons=(5,),
                min_label_coverage=0.1,
            )

            self.assertFalse(result["summary"]["passes"])
            self.assertIn("unknown_active_candidate_formula", result["summary"]["blockers"])

    def test_blocks_when_forward_labels_are_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_dir = root / "prereg"
            _write_fina_indicator_inputs(financial_root, _financial_rows())
            _write_sparse_bars(bars_root, _financial_rows()["asset_id"].unique().tolist())
            prereg = build_profitability_event_revision_preregistration(
                input_root=financial_root,
                min_assets=3,
                min_passed_candidates=6,
                min_families=3,
            )
            write_profitability_event_revision_preregistration(prereg_dir, prereg)

            result = build_profitability_event_revision_matrix_label_smoke(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_dir / "profitability_event_revision_preregistration.json",
                horizons=(20,),
                min_label_coverage=0.6,
            )

            self.assertFalse(result["summary"]["passes"])
            self.assertIn("label_coverage_below_threshold", result["summary"]["blockers"])

    def test_write_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_dir = root / "prereg"
            output_dir = root / "output"
            _write_fina_indicator_inputs(financial_root, _financial_rows())
            _write_bars(bars_root, _financial_rows()["asset_id"].unique().tolist())
            prereg = build_profitability_event_revision_preregistration(
                input_root=financial_root,
                min_assets=3,
                min_passed_candidates=6,
                min_families=3,
            )
            write_profitability_event_revision_preregistration(prereg_dir, prereg)
            result = build_profitability_event_revision_matrix_label_smoke(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_dir / "profitability_event_revision_preregistration.json",
                horizons=(5,),
                min_label_coverage=0.6,
            )

            write_profitability_event_revision_matrix_label_smoke(output_dir, result)

            self.assertTrue((output_dir / "profitability_event_revision_matrix_label_smoke.json").exists())
            self.assertTrue((output_dir / "profitability_event_revision_matrix_label_smoke.md").exists())
            self.assertTrue((output_dir / "profitability_event_revision_matrix_candidate_summary.csv").exists())


def _write_bars(root: Path, asset_ids: list[str]) -> None:
    dates = pd.bdate_range("2022-04-01", "2025-06-30")
    rows = []
    for asset_index, asset_id in enumerate(asset_ids):
        for index, day in enumerate(dates):
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": 10.0 + asset_index + index * 0.01,
                }
            )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/bars",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


def _write_sparse_bars(root: Path, asset_ids: list[str]) -> None:
    rows = [
        {"date": pd.Timestamp("2024-01-02"), "asset_id": asset_id, "market": "CN", "adj_close": 10.0}
        for asset_id in asset_ids
    ]
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/bars",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


if __name__ == "__main__":
    unittest.main()
