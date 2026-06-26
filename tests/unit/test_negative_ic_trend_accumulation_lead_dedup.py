import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.ops.negative_ic_trend_accumulation_lead_dedup import (
    DEFAULT_LEAD_FACTOR_NAME,
    build_negative_ic_trend_accumulation_lead_dedup,
    summarize_negative_ic_trend_accumulation_lead_dedup,
)


def _synthetic_bars(days: int = 110, assets: int = 42, *, include_holdout: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=10))
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        price = 8.0 + asset_idx * 0.05
        for day_idx, signal_date in enumerate(dates):
            trend = (asset_idx % 7) * 0.0005
            cycle = ((day_idx % 17) - 8) * 0.0008
            price = max(1.0, price * (1.0 + trend + cycle))
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.012,
                    "low": price * 0.988,
                    "amount": 18_000_000 + asset_idx * 120_000 + (day_idx % 7) * 90_000,
                }
            )
    return pd.DataFrame(rows)


def _factor_row(date: pd.Timestamp, asset_idx: int, factor_name: str, value: float, family: str) -> dict:
    return {
        "date": date,
        "asset_id": f"{asset_idx:06d}.SZ",
        "market": "CN",
        "factor_name": factor_name,
        "factor_value": value,
        "amount": 20_000_000.0 + asset_idx * 10_000,
        "adv20_amount": 21_000_000.0 + asset_idx * 10_000,
        "reference_family": family,
    }


class NegativeIcTrendAccumulationLeadDedupTests(unittest.TestCase):
    def test_summarizes_hard_blocking_and_source_lineage_redundancy(self) -> None:
        rows = []
        for signal_date in pd.bdate_range("2025-01-02", periods=6):
            for asset_idx in range(40):
                lead = float(asset_idx)
                rows.append(_factor_row(signal_date, asset_idx, "lead", lead, "negative_ic_trend_accumulation_same_family"))
                rows.append(_factor_row(signal_date, asset_idx, "hard_duplicate", lead * 2.0, "capacity_safe_price_volume"))
                rows.append(
                    _factor_row(signal_date, asset_idx, "source_inverse", -lead, "positive_trend_accumulation_source")
                )
                rows.append(
                    _factor_row(
                        signal_date,
                        asset_idx,
                        "unique_reference",
                        float((asset_idx * 7) % 40),
                        "capacity_safe_price_volume",
                    )
                )

        result = summarize_negative_ic_trend_accumulation_lead_dedup(
            pd.DataFrame(rows),
            lead_factor_name="lead",
            lead_horizon=20,
            prescreen_report={"results": [{"factor_name": "lead", "horizon": 20, "research_lead": True}]},
            min_cross_section=20,
        )

        self.assertEqual(result["stage"], "negative_ic_trend_accumulation_lead_dedup")
        self.assertEqual(result["summary"]["compared_candidate_count"], 3)
        self.assertEqual(result["summary"]["hard_blocking_redundant_count"], 1)
        self.assertEqual(result["summary"]["source_lineage_redundant_count"], 1)
        self.assertIn("lead_highly_redundant_with_hard_blocking_reference", result["gate"]["blockers"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        classes = {(row["reference_family"], row["factor_name"]): row for row in result["correlations"]}
        self.assertTrue(classes[("capacity_safe_price_volume", "hard_duplicate")]["hard_blocking_redundancy"])
        self.assertFalse(classes[("positive_trend_accumulation_source", "source_inverse")]["hard_blocking_redundancy"])

    def test_build_confirms_prescreen_lead_excludes_holdout_and_audits_capacity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            bars = _synthetic_bars(include_holdout=True)
            store = DatasetStore(root)
            store.write_frame(
                bars[bars["date"].dt.year == 2025],
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                bars[bars["date"].dt.year == 2026],
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2026"},
            )
            prescreen_report = {
                "results": [
                    {
                        "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                        "horizon": 20,
                        "research_lead": True,
                        "blockers": ["promotion_requires_later_walk_forward_cost_capacity_regime_gates"],
                    }
                ]
            }

            result = build_negative_ic_trend_accumulation_lead_dedup(
                bars_roots=[root],
                prescreen_report=prescreen_report,
                analysis_end_date="2025-12-31",
                sample_every_n_dates=2,
                min_cross_section=20,
            )

        self.assertTrue(result["lead_evidence"]["prescreen_research_lead"])
        self.assertEqual(result["lead_evidence"]["lead_factor_name"], DEFAULT_LEAD_FACTOR_NAME)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertGreater(result["capacity_audit"]["top_quantile_rows"], 0)
        self.assertIn("extreme_abs_return_095_rate", result["capacity_audit"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertIn(result["next_direction"], set(result["gate"]["allowed_next_directions"]))

    def test_missing_prescreen_lead_blocks_bridge(self) -> None:
        rows = []
        for signal_date in pd.bdate_range("2025-01-02", periods=4):
            for asset_idx in range(30):
                rows.append(_factor_row(signal_date, asset_idx, "lead", float(asset_idx), "negative_ic_trend_accumulation_same_family"))
                rows.append(_factor_row(signal_date, asset_idx, "other", float((asset_idx * 3) % 30), "capacity_safe_price_volume"))

        result = summarize_negative_ic_trend_accumulation_lead_dedup(
            pd.DataFrame(rows),
            lead_factor_name="lead",
            prescreen_report={"results": [{"factor_name": "lead", "horizon": 20, "research_lead": False}]},
            min_cross_section=20,
        )

        self.assertIn("prescreen_lead_not_confirmed", result["gate"]["blockers"])
        self.assertEqual(result["next_direction"], "round109_family_rotation_after_round108_dedup_failure")


if __name__ == "__main__":
    unittest.main()
