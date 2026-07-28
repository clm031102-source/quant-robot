import unittest

import numpy as np
import pandas as pd

from quant_robot.factors.etf_residual_margin_financing_growth import (
    DIRECT_EXPOSURE_NAMES,
    FACTOR_NAME,
    compute_etf_residual_margin_financing_growth,
)


class EtfResidualMarginFinancingGrowthTests(unittest.TestCase):
    def test_factor_is_point_in_time_and_materialises_exposures(self):
        bars, margin, eligible = _inputs()
        result = compute_etf_residual_margin_financing_growth(
            bars,
            margin,
            eligible_keys=eligible,
            min_cross_section=8,
        )

        finite = result.factors["factor_value"].dropna()
        self.assertGreater(len(finite), 0)
        self.assertEqual(set(result.factors["factor_name"]), {FACTOR_NAME})
        self.assertEqual(
            set(result.direct_exposures["factor_name"]),
            set(DIRECT_EXPOSURE_NAMES),
        )
        self.assertTrue(
            pd.to_datetime(result.diagnostics["date"])
            .ge(pd.to_datetime(result.diagnostics["source_date"]))
            .all()
        )

    def test_same_day_source_availability_is_rejected(self):
        bars, margin, eligible = _inputs()
        margin["available_date"] = margin["date"]
        with self.assertRaisesRegex(ValueError, "available_date"):
            compute_etf_residual_margin_financing_growth(
                bars,
                margin,
                eligible_keys=eligible,
                min_cross_section=8,
            )

    def test_missing_exact_source_session_lag_does_not_bridge_gap(self):
        bars, margin, eligible = _inputs()
        missing = margin[
            ~(
                (margin["symbol"] == "510000.SH")
                & (pd.to_datetime(margin["date"]) == pd.Timestamp("2024-02-01"))
            )
        ]
        result = compute_etf_residual_margin_financing_growth(
            bars,
            missing,
            eligible_keys=eligible,
            min_cross_section=8,
        )
        target = result.diagnostics[
            (result.diagnostics["asset_id"] == "CN_ETF_510000.SH")
            & (pd.to_datetime(result.diagnostics["source_date"]) == pd.Timestamp("2024-02-29"))
        ]
        self.assertEqual(len(target), 1)
        self.assertTrue(target["raw_margin_growth_20"].isna().all())


def _inputs():
    dates = pd.bdate_range("2024-01-02", periods=85)
    assets = [f"{510000 + index:06d}.SH" for index in range(12)]
    bar_rows = []
    margin_rows = []
    for day_index, date in enumerate(dates):
        for asset_index, symbol in enumerate(assets):
            bar_rows.append(
                {
                    "date": date,
                    "asset_id": f"CN_ETF_{symbol}",
                    "symbol": symbol,
                    "market": "CN_ETF",
                    "adj_close": 1.0 + 0.001 * day_index + 0.0002 * asset_index,
                    "amount": 10_000_000.0 + asset_index * 100_000.0,
                }
            )
            if day_index < len(dates) - 1:
                margin_rows.append(
                    {
                        "date": date,
                        "available_date": dates[day_index + 1],
                        "asset_id": f"CN_ETF_{symbol}",
                        "symbol": symbol,
                        "market": "CN_ETF",
                        "source": "tushare_margin_detail",
                        "rzye": np.exp(8.0 + 0.01 * asset_index + 0.0005 * day_index * asset_index),
                    }
                )
    bars = pd.DataFrame(bar_rows)
    margin = pd.DataFrame(margin_rows)
    eligible = bars[["date", "asset_id", "market"]].copy()
    return bars, margin, eligible


if __name__ == "__main__":
    unittest.main()
