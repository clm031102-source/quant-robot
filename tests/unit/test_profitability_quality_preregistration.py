import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.profitability_quality_preregistration import (
    build_profitability_quality_preregistration,
)
from quant_robot.storage.dataset_store import DatasetStore


class ProfitabilityQualityPreregistrationTests(unittest.TestCase):
    def test_preregisters_profitability_quality_candidates_with_coverage_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fina_indicator_inputs(root, _clean_financial_rows())

            result = build_profitability_quality_preregistration(
                input_root=root,
                min_assets=2,
                min_passed_candidates=8,
            )

            self.assertEqual(result["stage"], "profitability_quality_factor_preregistration")
            self.assertTrue(result["summary"]["passes"])
            self.assertGreaterEqual(result["summary"]["candidate_count"], 12)
            self.assertGreaterEqual(result["summary"]["coverage_passed_candidates"], 8)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertFalse(result["promotion_policy"]["backtest_allowed_from_single_shard"])
            self.assertFalse(result["live_boundary_allowed"])

            candidates = {candidate["name"]: candidate for candidate in result["candidates"]}
            self.assertIn("fina_roe_level", candidates)
            self.assertIn("fina_profit_growth_quality_spread", candidates)
            self.assertIn("fina_roe_persistence_4q", candidates)
            self.assertEqual(candidates["fina_roe_level"]["registration_status"], "pre_registered")
            self.assertTrue(candidates["fina_roe_level"]["coverage"]["passes"])
            self.assertTrue(candidates["fina_profit_growth_quality_spread"]["coverage"]["passes"])

    def test_blocks_preregistration_when_pit_or_field_coverage_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame = _clean_financial_rows()
            frame.loc[0, "ann_date"] = frame.loc[0, "end_date"] - pd.Timedelta(days=1)
            frame.loc[:, "roa"] = float("nan")
            _write_fina_indicator_inputs(root, frame)

            result = build_profitability_quality_preregistration(
                input_root=root,
                min_assets=2,
                min_passed_candidates=8,
            )

            self.assertFalse(result["summary"]["passes"])
            self.assertIn("ann_date_before_report_period", result["summary"]["blockers"])
            candidates = {candidate["name"]: candidate for candidate in result["candidates"]}
            self.assertFalse(candidates["fina_roa_level"]["coverage"]["passes"])
            self.assertEqual(candidates["fina_roa_level"]["registration_status"], "blocked_by_coverage")


def _clean_financial_rows() -> pd.DataFrame:
    rows = []
    symbols = ["000001.SZ", "000002.SZ"]
    periods = pd.period_range("2023Q1", "2024Q4", freq="Q")
    for symbol_index, symbol in enumerate(symbols):
        asset_id = f"CN_XSHE_{symbol.split('.')[0]}"
        for period_index, period in enumerate(periods):
            end_date = period.end_time.normalize()
            ann_date = end_date + pd.Timedelta(days=30 + symbol_index)
            rows.append(
                {
                    "date": ann_date,
                    "asset_id": asset_id,
                    "symbol": symbol,
                    "market": "CN",
                    "source": "tushare_fina_indicator",
                    "ingested_at": pd.Timestamp("2026-06-22T00:00:00Z"),
                    "ann_date": ann_date,
                    "end_date": end_date,
                    "roe": 10 + period_index + symbol_index,
                    "roa": 4 + period_index / 10 + symbol_index,
                    "grossprofit_margin": 25 + period_index,
                    "netprofit_margin": 8 + period_index / 2,
                    "netprofit_yoy": 12 + period_index,
                    "or_yoy": 7 + period_index / 2,
                    "ocfps": 1.2 + period_index / 10,
                    "cfps": 1.6 + period_index / 10,
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
