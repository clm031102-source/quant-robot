import unittest

import pandas as pd

from quant_robot.research.cross_sectional_capacity import summarize_top_quantile_capacity


class CrossSectionalCapacityTests(unittest.TestCase):
    def test_summarizes_top_quantile_adv_and_participation(self) -> None:
        factors, labels, adv20 = _frames(default_adv20=20_000_000.0)

        rows = summarize_top_quantile_capacity(
            factors,
            labels,
            adv20,
            candidate_names=("candidate",),
            horizons=(5,),
            min_cross_section=10,
            portfolio_value_cny=1_000_000.0,
            position_count=10,
            max_one_way_participation_rate=0.01,
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["top_quantile_asset_observations"], 6)
        self.assertEqual(row["top_quantile_adv20_observations"], 6)
        self.assertEqual(row["top_quantile_adv20_coverage_rate"], 1.0)
        self.assertEqual(row["top_quantile_adv20_p10_cny"], 20_000_000.0)
        self.assertAlmostEqual(row["p10_one_way_participation_rate"], 0.005)

    def test_missing_capacity_evidence_is_retained_as_zero_coverage(self) -> None:
        factors, labels, _ = _frames(default_adv20=20_000_000.0)
        adv20 = pd.DataFrame(columns=["date", "asset_id", "market", "adv20"])

        rows = summarize_top_quantile_capacity(
            factors,
            labels,
            adv20,
            candidate_names=("candidate",),
            horizons=(5,),
            min_cross_section=10,
            portfolio_value_cny=1_000_000.0,
            position_count=10,
            max_one_way_participation_rate=0.01,
        )

        row = rows[0]
        self.assertEqual(row["top_quantile_asset_observations"], 6)
        self.assertEqual(row["top_quantile_adv20_observations"], 0)
        self.assertEqual(row["top_quantile_adv20_coverage_rate"], 0.0)
        self.assertIsNone(row["top_quantile_adv20_p10_cny"])
        self.assertIsNone(row["p10_one_way_participation_rate"])

    def test_rejects_duplicate_factor_rows(self) -> None:
        factors, labels, adv20 = _frames(default_adv20=20_000_000.0)
        factors = pd.concat([factors, factors.iloc[[0]]], ignore_index=True)

        with self.assertRaisesRegex(ValueError, "duplicate factor rows"):
            summarize_top_quantile_capacity(
                factors,
                labels,
                adv20,
                candidate_names=("candidate",),
                horizons=(5,),
                min_cross_section=10,
                portfolio_value_cny=1_000_000.0,
                position_count=10,
                max_one_way_participation_rate=0.01,
            )


def _frames(*, default_adv20: float) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    factor_rows = []
    label_rows = []
    adv_rows = []
    for signal_date in pd.bdate_range("2024-01-02", periods=3):
        for asset_index in range(10):
            asset_id = f"CN_ETF_XSHG_{510000 + asset_index}"
            factor_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN_ETF",
                    "factor_name": "candidate",
                    "factor_value": float(asset_index),
                }
            )
            label_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN_ETF",
                    "horizon": 5,
                    "forward_return": asset_index / 10_000.0,
                }
            )
            adv_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN_ETF",
                    "adv20": default_adv20,
                }
            )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(adv_rows)


if __name__ == "__main__":
    unittest.main()
