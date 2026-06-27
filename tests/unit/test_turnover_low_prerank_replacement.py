from __future__ import annotations

import unittest

import pandas as pd

from quant_robot.ops.turnover_low_prerank_replacement import (
    attach_signal_metadata,
    drop_bottom_quantile_by_date,
    filter_allowed_stock_markets,
)


class TurnoverLowPrerankReplacementTest(unittest.TestCase):
    def test_drop_bottom_quantile_by_date_removes_extreme_low_values(self) -> None:
        frame = pd.DataFrame(
            {
                "date": ["2021-01-01"] * 4,
                "asset_id": ["a", "b", "c", "d"],
                "turnover_rate_f": [0.1, 0.2, 0.3, 0.4],
            }
        )

        filtered = drop_bottom_quantile_by_date(frame, "turnover_rate_f", 0.25)

        self.assertNotIn("a", set(filtered["asset_id"]))
        self.assertEqual(set(filtered["asset_id"]), {"b", "c", "d"})

    def test_attach_signal_metadata_uses_asset_level_stock_market(self) -> None:
        factors = pd.DataFrame(
            {
                "date": ["2021-01-01", "2021-01-01"],
                "asset_id": ["a", "b"],
                "market": ["CN", "CN"],
                "factor_value": [1.0, 2.0],
            }
        )
        metadata = pd.DataFrame({"asset_id": ["a", "b"], "stock_market": ["主板", "科创板"]})

        enriched = attach_signal_metadata(factors, metadata, columns=("stock_market",))

        self.assertEqual(enriched.loc[enriched["asset_id"] == "a", "stock_market"].iloc[0], "主板")
        self.assertEqual(enriched.loc[enriched["asset_id"] == "b", "stock_market"].iloc[0], "科创板")

    def test_filter_allowed_stock_markets_excludes_growth_boards_and_unknowns(self) -> None:
        frame = pd.DataFrame(
            {
                "asset_id": ["a", "b", "c", "d"],
                "stock_market": ["主板", "科创板", "创业板", None],
            }
        )

        filtered = filter_allowed_stock_markets(frame, allowed_stock_markets=("主板",))

        self.assertEqual(list(filtered["asset_id"]), ["a"])


if __name__ == "__main__":
    unittest.main()
