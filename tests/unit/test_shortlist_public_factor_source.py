from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

import quant_robot.ops.shortlist_public_factor_source as source_module
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

    def test_supports_capacity_safe_price_volume_factor_values(self) -> None:
        dates = pd.date_range("2024-01-01", periods=80, freq="D")
        frames = []
        for index in range(8):
            asset_id = f"CN_XSHE_00010{index}"
            rows = []
            for day, trade_date in enumerate(dates):
                reversal = -0.05 * (day % 6) if index % 2 else 0.04 * (day % 5)
                drift = day * (0.01 + index * 0.002)
                close = 12.0 + index * 0.8 + drift + reversal
                high = close * (1.01 + (index % 3) * 0.002)
                low = close * (0.99 - (index % 2) * 0.002)
                amount = 20_000_000.0 + index * 1_000_000.0 + (day % 7) * 100_000.0
                rows.append(
                    {
                        "date": trade_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "open": close * 0.998,
                        "high": high,
                        "low": low,
                        "close": close,
                        "adj_close": close,
                        "volume": amount / close,
                        "amount": amount,
                    }
                )
            frames.append(pd.DataFrame(rows))
        bars = pd.concat(frames, ignore_index=True)
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000100"],
                "signal_date": ["2024-03-20"],
            }
        )

        result = build_shortlist_public_factor_source(
            trades_source=trades,
            bars_source=bars,
            factor_names=("range_contraction_lowvol_reversal_20",),
        )

        values = result["factor_values"]
        self.assertEqual(result["summary"]["target_pair_count"], 1)
        self.assertEqual(result["coverage_rows"][0]["public_factor_name"], "range_contraction_lowvol_reversal_20")
        self.assertEqual(values["public_factor_family"].tolist(), ["capacity_safe_price_volume"])
        self.assertEqual(values["asset_id"].tolist(), ["CN_XSHE_000100"])
        self.assertTrue(values["factor_value"].notna().all())

    def test_family_outputs_are_narrowed_before_cross_family_concat(self) -> None:
        bars = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01"]),
                "asset_id": ["CN_XSHE_000001"],
                "market": ["CN"],
                "adj_close": [10.0],
                "high": [10.5],
                "low": [9.5],
                "amount": [20_000_000.0],
            }
        )
        trades = pd.DataFrame({"asset_id": ["CN_XSHE_000001"], "signal_date": ["2024-01-01"]})

        def wide_builder(input_bars: pd.DataFrame, factor_names: tuple[str, ...] | None) -> pd.DataFrame:
            return pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-01"]),
                    "asset_id": ["CN_XSHE_000001"],
                    "market": ["CN"],
                    "factor_name": ["wide_factor"],
                    "factor_value": [1.0],
                    "temporary_feature_blob": [object()],
                }
            )

        original_concat = pd.concat

        def assert_narrow_concat(objs, *args, **kwargs):
            frames = list(objs)
            for frame in frames:
                self.assertNotIn("temporary_feature_blob", frame.columns)
            return original_concat(frames, *args, **kwargs)

        with patch.object(
            source_module,
            "FACTOR_FAMILIES",
            (("wide_family", ("wide_factor",), wide_builder),),
        ), patch.object(source_module.pd, "concat", side_effect=assert_narrow_concat):
            result = build_shortlist_public_factor_source(
                trades_source=trades,
                bars_source=bars,
                factor_names=("wide_factor",),
            )

        self.assertEqual(result["summary"]["factor_value_rows"], 1)

    def test_family_outputs_are_targeted_before_cross_family_concat(self) -> None:
        bars = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002", "CN_XSHE_000003"],
                "market": ["CN", "CN", "CN"],
                "adj_close": [10.0, 11.0, 12.0],
                "high": [10.5, 11.5, 12.5],
                "low": [9.5, 10.5, 11.5],
                "amount": [20_000_000.0, 21_000_000.0, 22_000_000.0],
            }
        )
        trades = pd.DataFrame({"asset_id": ["CN_XSHE_000001"], "signal_date": ["2024-01-01"]})

        def full_universe_builder(input_bars: pd.DataFrame, factor_names: tuple[str, ...] | None) -> pd.DataFrame:
            return pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                    "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002", "CN_XSHE_000003"],
                    "market": ["CN", "CN", "CN"],
                    "factor_name": ["targeted_factor", "targeted_factor", "targeted_factor"],
                    "factor_value": [1.0, 2.0, 3.0],
                }
            )

        original_concat = pd.concat

        def assert_target_only_concat(objs, *args, **kwargs):
            frames = list(objs)
            for frame in frames:
                if {"date", "asset_id", "factor_value"}.issubset(frame.columns):
                    self.assertEqual(pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d").unique().tolist(), ["2024-01-01"])
                    self.assertEqual(frame["asset_id"].unique().tolist(), ["CN_XSHE_000001"])
            return original_concat(frames, *args, **kwargs)

        with patch.object(
            source_module,
            "FACTOR_FAMILIES",
            (("full_universe_family", ("targeted_factor",), full_universe_builder),),
        ), patch.object(source_module.pd, "concat", side_effect=assert_target_only_concat):
            result = build_shortlist_public_factor_source(
                trades_source=trades,
                bars_source=bars,
                factor_names=("targeted_factor",),
            )

        values = result["factor_values"]
        self.assertEqual(values["factor_value"].tolist(), [1.0])

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
