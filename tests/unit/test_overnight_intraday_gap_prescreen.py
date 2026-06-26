import unittest

import pandas as pd

from quant_robot.ops.overnight_intraday_gap_prescreen import (
    compute_overnight_intraday_gap_factors,
    default_overnight_intraday_gap_candidate_specs,
    summarize_overnight_intraday_gap_prescreen,
)


def _synthetic_bars(days: int = 90, assets: int = 50) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        close = 10.0 + asset_idx * 0.05
        for day_idx, date in enumerate(dates):
            overnight = ((asset_idx % 9) - 4) * 0.001 + ((day_idx % 7) - 3) * 0.0003
            intraday = ((asset_idx % 11) - 5) * 0.0008 + ((day_idx % 5) - 2) * 0.0002
            open_price = max(1.0, close * (1.0 + overnight))
            close = max(1.0, open_price * (1.0 + intraday))
            high = max(open_price, close) * 1.01
            low = min(open_price, close) * 0.99
            amount = 20_000_000.0 + asset_idx * 120_000.0 + (day_idx % 5) * 50_000.0
            rows.append(
                {
                    "date": date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN",
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "adj_close": close,
                    "amount": amount,
                    "volume": amount / close,
                }
            )
    return pd.DataFrame(rows)


class OvernightIntradayGapPrescreenTests(unittest.TestCase):
    def test_default_specs_are_pre_registered_and_block_direct_promotion(self) -> None:
        specs = default_overnight_intraday_gap_candidate_specs()

        self.assertEqual(len(specs), 10)
        self.assertEqual(len({spec.factor_name for spec in specs}), 10)
        self.assertTrue(all(spec.family == "overnight_intraday_gap" for spec in specs))
        self.assertTrue(all(not spec.portfolio_backtest_allowed for spec in specs))
        self.assertTrue(all(not spec.promotion_allowed for spec in specs))
        self.assertTrue(all("alphalens" in spec.public_reference_tags for spec in specs))

    def test_computes_all_pre_registered_gap_factor_names_with_capacity_filter(self) -> None:
        factors = compute_overnight_intraday_gap_factors(
            _synthetic_bars(),
            min_signal_date_amount=10_000_000,
        )

        self.assertEqual(factors["factor_name"].nunique(), 10)
        self.assertIn("overnight_reversal_5", set(factors["factor_name"]))
        self.assertIn("gap_down_intraday_recovery_10", set(factors["factor_name"]))
        self.assertIn("gap_reversal_lowvol_liquid_20", set(factors["factor_name"]))
        self.assertTrue((factors["amount"] >= 10_000_000).all())
        self.assertTrue((factors["adv20_amount"] >= 10_000_000).all())

    def test_summarizer_can_flag_research_lead_but_never_promotion(self) -> None:
        dates = pd.bdate_range("2025-01-02", periods=8)
        factor_rows = []
        labels = []
        for date in dates:
            for asset_idx in range(40):
                asset_id = f"{asset_idx:06d}.SZ"
                signal = float(asset_idx)
                factor_rows.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "synthetic_gap_signal",
                        "factor_value": signal,
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0,
                    }
                )
                labels.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "horizon": 5,
                        "execution_lag": 1,
                        "forward_return": signal / 10_000.0,
                        "entry_date": date + pd.Timedelta(days=1),
                        "exit_date": date + pd.Timedelta(days=6),
                    }
                )

        result = summarize_overnight_intraday_gap_prescreen(
            pd.DataFrame(factor_rows),
            pd.DataFrame(labels),
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=4,
        )

        self.assertEqual(result["summary"]["research_lead_count"], 1)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertEqual(result["next_direction"], "round110_overnight_intraday_gap_lead_dedup")
        self.assertTrue(result["results"][0]["research_lead"])


if __name__ == "__main__":
    unittest.main()
