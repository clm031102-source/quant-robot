import unittest

import numpy as np
import pandas as pd

from quant_robot.factors.etf_residual_share_creation_crowding import (
    DIRECT_EXPOSURE_NAMES,
    FACTOR_NAME,
    compute_etf_residual_share_creation_crowding,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class EtfResidualShareCreationCrowdingTests(unittest.TestCase):
    def test_builds_frozen_reversal_factor_from_known_share_snapshots(self):
        bars, structure, eligible = _inputs()

        result = compute_etf_residual_share_creation_crowding(
            bars,
            structure,
            eligible_keys=eligible,
            share_lookback=20,
            short_return_window=20,
            long_return_window=60,
            volatility_window=20,
            adv_window=20,
            min_cross_section=10,
        )

        self.assertEqual(list(result.factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(result.factors["factor_name"]), {FACTOR_NAME})
        self.assertEqual(set(result.direct_exposures["factor_name"]), set(DIRECT_EXPOSURE_NAMES))
        finite = result.diagnostics.dropna(subset=["factor_value"])
        self.assertFalse(finite.empty)
        np.testing.assert_allclose(
            finite["factor_value"],
            -finite["share_creation_residual"],
            rtol=0.0,
            atol=1e-12,
        )
        most_crowded = finite.loc[finite["share_creation_residual"].idxmax()]
        self.assertGreater(most_crowded["share_creation_residual"], 0.0)
        self.assertLess(most_crowded["factor_value"], 0.0)

    def test_uses_exact_source_session_lag_and_never_same_day_share_data(self):
        bars, structure, eligible = _inputs()

        result = compute_etf_residual_share_creation_crowding(
            bars,
            structure,
            eligible_keys=eligible,
            share_lookback=20,
            short_return_window=20,
            long_return_window=60,
            volatility_window=20,
            adv_window=20,
            min_cross_section=10,
        )

        finite = result.diagnostics.dropna(subset=["raw_share_creation_20"])
        self.assertTrue((finite["known_from"] > finite["source_date"]).all())
        row = finite[
            finite["asset_id"].eq("CN_ETF_XSHG_510009")
            & finite["source_date"].eq(pd.Timestamp("2024-04-22"))
        ].iloc[0]
        expected = np.log(
            structure.loc[
                structure["asset_id"].eq("CN_ETF_XSHG_510009")
                & structure["date"].eq(pd.Timestamp("2024-04-22")),
                "total_share",
            ].iloc[0]
            / structure.loc[
                structure["asset_id"].eq("CN_ETF_XSHG_510009")
                & structure["date"].eq(pd.Timestamp("2024-03-25")),
                "total_share",
            ].iloc[0]
        )
        self.assertAlmostEqual(row["raw_share_creation_20"], expected)

    def test_rejects_non_lagged_source_rows(self):
        bars, structure, eligible = _inputs()
        structure.loc[0, "known_from"] = structure.loc[0, "date"]

        with self.assertRaisesRegex(ValueError, "known_from"):
            compute_etf_residual_share_creation_crowding(
                bars,
                structure,
                eligible_keys=eligible,
                min_cross_section=10,
            )


def _inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2024-01-02", periods=82)
    assets = [f"CN_ETF_XSHG_5100{index:02d}" for index in range(10)]
    bar_rows = []
    structure_rows = []
    for asset_index, asset_id in enumerate(assets):
        phase = asset_index * 0.37
        exchange = "SSE" if asset_index < 5 else "SZSE"
        for date_index, current in enumerate(dates):
            price = (
                1.0
                + 0.0015 * date_index
                + 0.0004 * asset_index * date_index
                + 0.012 * np.sin(date_index / (3.0 + asset_index / 10.0) + phase)
            )
            amount = 8_000_000.0 + 150_000.0 * asset_index + 10_000.0 * date_index
            bar_rows.append(
                {
                    "date": current,
                    "asset_id": asset_id,
                    "market": "CN_ETF",
                    "adj_close": price,
                    "amount": amount,
                }
            )
            if date_index < len(dates) - 1:
                flow = 0.0005 * asset_index + 0.0002 * np.cos(date_index / 5.0 + phase)
                if asset_index == 9 and date_index >= 60:
                    flow += 0.03
                total_share = 10_000_000.0 * np.exp(flow * date_index)
                structure_rows.append(
                    {
                        "date": current,
                        "known_from": dates[date_index + 1],
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "exchange": exchange,
                        "total_share": total_share,
                        "total_size": total_share * price,
                    }
                )
    bars = pd.DataFrame(bar_rows)
    structure = pd.DataFrame(structure_rows)
    eligible = bars[["date", "asset_id", "market"]].copy()
    return bars, structure, eligible


if __name__ == "__main__":
    unittest.main()
