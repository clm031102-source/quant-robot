import unittest

import pandas as pd

from quant_robot.factors.official_tradeability_events import (
    OFFICIAL_TRADEABILITY_EVENT_FACTOR_NAMES,
    compute_official_tradeability_event_factors,
)


class OfficialTradeabilityEventFactorTests(unittest.TestCase):
    def test_computes_official_tradeability_event_candidates_from_masks(self) -> None:
        assets = [f"CN_XSHG_{idx:06d}" for idx in range(6)]
        dates = list(pd.date_range("2024-01-02", periods=4, freq="B"))
        bars = pd.DataFrame(
            {
                "date": [date for date in dates for _ in assets],
                "asset_id": assets * len(dates),
                "market": ["CN"] * len(assets) * len(dates),
                "amount": [50_000_000.0] * len(assets) * len(dates),
            }
        )
        masks = bars[["date", "asset_id", "market"]].copy()
        masks["fully_tradeable"] = True
        masks["limit_up_official"] = False
        masks["limit_down_official"] = False
        masks["suspended_official"] = False
        masks["st_flag_official"] = False
        masks.loc[(masks["asset_id"] == assets[0]) & (masks["date"] == dates[0]), "limit_down_official"] = True
        masks.loc[(masks["asset_id"] == assets[1]) & (masks["date"].isin(dates[:2])), "limit_up_official"] = True
        masks.loc[(masks["asset_id"] == assets[2]) & (masks["date"] == dates[1]), "suspended_official"] = True
        masks.loc[(masks["asset_id"] == assets[3]) & (masks["date"] == dates[2]), "st_flag_official"] = True
        masks.loc[masks["suspended_official"], "fully_tradeable"] = False

        result = compute_official_tradeability_event_factors(bars, masks)

        self.assertEqual(set(result["factor_name"].unique()), set(OFFICIAL_TRADEABILITY_EVENT_FACTOR_NAMES))
        self.assertEqual(result["market"].unique().tolist(), ["CN"])
        self.assertGreater(result["factor_value"].notna().sum(), 0)
        self.assertIn("official_tradeability_cleanliness_20", set(result["factor_name"]))

    def test_unknown_factor_name_is_rejected(self) -> None:
        bars = pd.DataFrame(
            {"date": [pd.Timestamp("2024-01-02")], "asset_id": ["CN_XSHG_600000"], "market": ["CN"], "amount": [1.0]}
        )
        masks = pd.DataFrame({"date": [pd.Timestamp("2024-01-02")], "asset_id": ["CN_XSHG_600000"], "market": ["CN"]})
        with self.assertRaises(ValueError):
            compute_official_tradeability_event_factors(bars, masks, factor_names=("unknown_factor",))


if __name__ == "__main__":
    unittest.main()
