from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.shortlist_public_factor_source import (
    build_shortlist_public_factor_source,
    write_shortlist_public_factor_source,
)


class ShortlistPublicFactorSourceTest(unittest.TestCase):
    def test_builds_target_pair_public_factor_values_from_full_bars(self) -> None:
        dates = pd.date_range("2024-01-01", periods=24, freq="D")
        bars = pd.concat(
            [
                pd.DataFrame(
                    {
                        "date": dates,
                        "asset_id": asset_id,
                        "market": "CN",
                        "adj_close": [10.0 + offset + i * step for i in range(len(dates))],
                        "high": [10.5 + offset + i * step for i in range(len(dates))],
                        "low": [9.5 + offset + i * step for i in range(len(dates))],
                        "amount": [20_000_000.0 + i * 10_000.0 for i in range(len(dates))],
                    }
                )
                for asset_id, offset, step in (
                    ("CN_XSHE_000001", 0.0, 0.10),
                    ("CN_XSHE_000002", 1.0, -0.02),
                )
            ],
            ignore_index=True,
        )
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "signal_date": ["2024-01-24"],
            }
        )

        result = build_shortlist_public_factor_source(
            trades_source=trades,
            bars_source=bars,
            factor_names=("rsi_reversal_14",),
        )

        values = result["factor_values"]
        self.assertEqual(result["summary"]["target_pair_count"], 1)
        self.assertEqual(result["coverage_rows"][0]["public_factor_name"], "rsi_reversal_14")
        self.assertEqual(values["public_factor_name"].tolist(), ["rsi_reversal_14"])
        self.assertEqual(values["asset_id"].tolist(), ["CN_XSHE_000001"])
        self.assertTrue(values["factor_value"].notna().all())

    def test_supports_public_alpha101_qlib_factor_values(self) -> None:
        dates = pd.date_range("2024-01-01", periods=80, freq="D")
        frames = []
        for index in range(8):
            rows = []
            asset_id = f"CN_XSHE_00000{index + 1}"
            for day, trade_date in enumerate(dates):
                wave = ((day % (index + 3)) - ((index + 2) / 2.0)) * (0.03 + index * 0.004)
                drift = day * (0.035 + index * 0.003) if index % 2 == 0 else -day * (0.012 + index * 0.001)
                close = 10.0 + index * 1.2 + drift + wave
                open_price = close * (1.0 + (((day + index) % 5) - 2) * 0.002)
                high = max(open_price, close) * 1.015
                low = min(open_price, close) * 0.985
                volume = 1_000_000.0 + index * 40_000.0 + (day % 11) * (5_000.0 + index * 300.0)
                rows.append(
                    {
                        "date": trade_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "open": open_price,
                        "high": high,
                        "low": low,
                        "close": close,
                        "adj_close": close,
                        "volume": volume,
                        "amount": volume * close,
                    }
                )
            frames.append(pd.DataFrame(rows))
        bars = pd.concat(frames, ignore_index=True)
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "signal_date": ["2024-03-20"],
            }
        )

        result = build_shortlist_public_factor_source(
            trades_source=trades,
            bars_source=bars,
            factor_names=("qlib_alpha158_return_std_position_blend_20",),
        )

        values = result["factor_values"]
        self.assertEqual(result["summary"]["target_pair_count"], 1)
        self.assertEqual(
            result["coverage_rows"][0]["public_factor_name"],
            "qlib_alpha158_return_std_position_blend_20",
        )
        self.assertEqual(values["public_factor_name"].tolist(), ["qlib_alpha158_return_std_position_blend_20"])
        self.assertEqual(values["asset_id"].tolist(), ["CN_XSHE_000001"])
        self.assertTrue(values["factor_value"].notna().all())

    def test_writer_exports_value_source_and_coverage(self) -> None:
        dates = pd.date_range("2024-01-01", periods=24, freq="D")
        bars = pd.DataFrame(
            {
                "date": dates,
                "asset_id": "CN_XSHE_000001",
                "market": "CN",
                "adj_close": [10.0 + i * 0.1 for i in range(len(dates))],
                "high": [10.5 + i * 0.1 for i in range(len(dates))],
                "low": [9.5 + i * 0.1 for i in range(len(dates))],
                "amount": [20_000_000.0 for _ in dates],
            }
        )
        trades = pd.DataFrame({"asset_id": ["CN_XSHE_000001"], "signal_date": ["2024-01-24"]})
        result = build_shortlist_public_factor_source(
            trades_source=trades,
            bars_source=bars,
            factor_names=("rsi_reversal_14",),
        )

        with TemporaryDirectory() as tmp:
            write_shortlist_public_factor_source(tmp, result)

            self.assertTrue((Path(tmp) / "shortlist_public_factor_source.json").exists())
            self.assertTrue((Path(tmp) / "shortlist_public_factor_source_coverage.csv").exists())
            self.assertTrue((Path(tmp) / "public_factor_values_for_shortlist.parquet").exists())


if __name__ == "__main__":
    unittest.main()
