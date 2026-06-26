import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.ops.capacity_safe_price_volume_lead_dedup import (
    build_capacity_safe_price_volume_lead_dedup,
    summarize_capacity_safe_price_volume_lead_dedup,
)


def _synthetic_bars(days: int = 90, assets: int = 40, *, include_holdout: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=10))
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        price = 10.0 + asset_idx * 0.03
        for day_idx, date in enumerate(dates):
            seasonal = ((day_idx % 17) - 8) * 0.001
            drift = (asset_idx % 7) * 0.0005
            price = max(1.0, price * (1.0 + seasonal + drift))
            rows.append(
                {
                    "date": date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.015,
                    "low": price * 0.985,
                    "amount": 20_000_000 + asset_idx * 100_000 + (day_idx % 5) * 50_000,
                }
            )
    return pd.DataFrame(rows)


class CapacitySafePriceVolumeLeadDedupTests(unittest.TestCase):
    def test_summarizes_lead_correlations_and_classifies_redundancy(self) -> None:
        dates = pd.bdate_range("2025-01-02", periods=6)
        rows = []
        for date in dates:
            for asset_idx in range(40):
                asset_id = f"{asset_idx:06d}.SZ"
                lead = float(asset_idx)
                rows.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "lead",
                        "factor_value": lead,
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0,
                    }
                )
                rows.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "duplicate",
                        "factor_value": lead * 2.0,
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0,
                    }
                )
                rows.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "independent",
                        "factor_value": float((asset_idx * 7) % 40),
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0,
                    }
                )

        result = summarize_capacity_safe_price_volume_lead_dedup(
            pd.DataFrame(rows),
            lead_factor_name="lead",
            min_cross_section=20,
        )

        self.assertEqual(result["stage"], "capacity_safe_price_volume_lead_dedup")
        self.assertEqual(result["summary"]["candidate_count"], 3)
        self.assertEqual(result["summary"]["compared_candidate_count"], 2)
        self.assertEqual(result["summary"]["highly_redundant_count"], 1)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        classifications = {row["factor_name"]: row["redundancy_class"] for row in result["correlations"]}
        self.assertEqual(classifications["duplicate"], "highly_redundant")
        self.assertEqual(classifications["independent"], "unique")
        duplicate = next(row for row in result["correlations"] if row["factor_name"] == "duplicate")
        self.assertGreaterEqual(duplicate["max_abs_correlation"], 0.99)
        self.assertIn("candidate_correlation_dedup_before_portfolio_grid", result["gate"]["required_before"])

    def test_build_confirms_prescreen_lead_and_blocks_promotion(self) -> None:
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
                        "factor_name": "bollinger_reversal_lowvol_liquid_20",
                        "horizon": 20,
                        "research_lead": True,
                    }
                ],
                "summary": {"research_lead_count": 1},
            }

            result = build_capacity_safe_price_volume_lead_dedup(
                bars_roots=[root],
                prescreen_report=prescreen_report,
                analysis_end_date="2025-12-31",
                sample_every_n_dates=2,
                min_cross_section=20,
            )

        self.assertTrue(result["lead_evidence"]["prescreen_research_lead"])
        self.assertEqual(result["lead_evidence"]["lead_factor_name"], "bollinger_reversal_lowvol_liquid_20")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertIn(result["next_direction"], set(result["gate"]["allowed_next_directions"]))

    def test_prescreen_mismatch_blocks_next_portfolio_bridge(self) -> None:
        rows = []
        for date in pd.bdate_range("2025-01-02", periods=4):
            for asset_idx in range(30):
                for factor_name in ["lead", "other"]:
                    rows.append(
                        {
                            "date": date,
                            "asset_id": f"{asset_idx:06d}.SZ",
                            "market": "CN",
                            "factor_name": factor_name,
                            "factor_value": float(asset_idx),
                            "amount": 20_000_000.0,
                            "adv20_amount": 20_000_000.0,
                        }
                    )

        result = summarize_capacity_safe_price_volume_lead_dedup(
            pd.DataFrame(rows),
            lead_factor_name="lead",
            prescreen_report={"results": [{"factor_name": "lead", "horizon": 20, "research_lead": False}]},
            min_cross_section=20,
        )

        self.assertFalse(result["lead_evidence"]["prescreen_research_lead"])
        self.assertIn("prescreen_lead_not_confirmed", result["gate"]["blockers"])
        self.assertEqual(result["next_direction"], "round104_family_rotation_after_bollinger_redundancy")

    def test_prescreen_blockers_keep_list_shape(self) -> None:
        rows = []
        for date in pd.bdate_range("2025-01-02", periods=4):
            for asset_idx in range(30):
                for factor_name in ["lead", "other"]:
                    rows.append(
                        {
                            "date": date,
                            "asset_id": f"{asset_idx:06d}.SZ",
                            "market": "CN",
                            "factor_name": factor_name,
                            "factor_value": float(asset_idx),
                            "amount": 20_000_000.0,
                            "adv20_amount": 20_000_000.0,
                        }
                    )

        result = summarize_capacity_safe_price_volume_lead_dedup(
            pd.DataFrame(rows),
            lead_factor_name="lead",
            prescreen_report={
                "results": [
                    {
                        "factor_name": "lead",
                        "horizon": 20,
                        "research_lead": True,
                        "blockers": ["promotion_requires_later_walk_forward_cost_capacity_regime_gates"],
                    }
                ]
            },
            min_cross_section=20,
        )

        self.assertEqual(
            result["lead_evidence"]["prescreen_blockers"],
            ["promotion_requires_later_walk_forward_cost_capacity_regime_gates"],
        )


if __name__ == "__main__":
    unittest.main()
