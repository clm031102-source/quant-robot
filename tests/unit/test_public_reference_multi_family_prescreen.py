import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.ops.public_reference_multi_family_prescreen import (
    _market_return_by_date,
    _replace_infinite_numeric,
    build_public_reference_multi_family_prescreen,
    compute_public_reference_multi_family_factors,
    load_public_reference_multi_family_bars,
)
from quant_robot.storage.dataset_store import DatasetStore


def _synthetic_public_reference_bars(
    days: int = 140,
    assets: int = 45,
    *,
    include_holdout: bool = False,
) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=8))
    rows = []
    for asset_idx in range(assets):
        asset_id = f"CN_XSHE_{asset_idx:06d}"
        price = 8.0 + asset_idx * 0.07
        for day_idx, date in enumerate(dates):
            drift = (asset_idx % 7) * 0.00035
            wave = ((day_idx % 17) - 8) * 0.001
            open_price = max(1.0, price * (1.0 + wave * 0.25))
            close = max(1.0, open_price * (1.0 + drift + wave))
            high = max(open_price, close) * 1.014
            low = min(open_price, close) * 0.986
            volume = 900_000 + asset_idx * 12_000 + (day_idx % 9) * 4_000
            amount = volume * close
            rows.append(
                {
                    "date": date,
                    "asset_id": asset_id,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "adj_close": close,
                    "volume": volume,
                    "amount": amount,
                    "vwap": amount / volume,
                }
            )
            price = close
    return pd.DataFrame(rows)


def _synthetic_factor_inputs(bars: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row_idx, row in bars.iterrows():
        asset_number = int(str(row["asset_id"]).split("_")[-1])
        rows.append(
            {
                "date": row["date"],
                "asset_id": row["asset_id"],
                "symbol": row["symbol"],
                "market": "CN",
                "source": "synthetic",
                "turnover_rate": 0.8 + (asset_number % 9) * 0.05,
                "turnover_rate_f": 0.9 + (asset_number % 11) * 0.04,
                "pe_ttm": 8.0 + (asset_number % 17) * 0.7,
                "pb": 0.8 + (asset_number % 13) * 0.12,
                "dv_ttm": 1.0 + (asset_number % 5) * 0.2,
                "circ_mv": 800_000.0 + asset_number * 15_000.0,
            }
        )
    return pd.DataFrame(rows)


def _synthetic_moneyflow_inputs(bars: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row_idx, row in bars.iterrows():
        asset_number = int(str(row["asset_id"]).split("_")[-1])
        scale = 1.0 + (row_idx % 23) * 0.01 + (asset_number % 7) * 0.02
        rows.append(
            {
                "date": row["date"],
                "asset_id": row["asset_id"],
                "symbol": row["symbol"],
                "market": "CN",
                "source": "synthetic_moneyflow",
                "buy_lg_amount": 500.0 * scale,
                "sell_lg_amount": 450.0 * scale,
                "buy_elg_amount": 700.0 * scale,
                "sell_elg_amount": 640.0 * scale,
                "net_mf_amount": 120.0 * scale,
            }
        )
    return pd.DataFrame(rows)


class PublicReferenceMultiFamilyPrescreenTests(unittest.TestCase):
    def test_market_return_uses_time_series_asset_returns_not_same_day_cross_section(self) -> None:
        bars = pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-01-02", "2025-01-02", "2025-01-03", "2025-01-03"]),
                "asset_id": ["a", "b", "a", "b"],
                "market": ["CN", "CN", "CN", "CN"],
                "adj_close": [10.0, 20.0, 11.0, 18.0],
            }
        )

        market_return = _market_return_by_date(bars)

        self.assertAlmostEqual(market_return.loc[pd.Timestamp("2025-01-03")], 0.0)

    def test_replace_infinite_numeric_does_not_touch_identifier_columns(self) -> None:
        frame = pd.DataFrame(
            {
                "asset_id": ["a", "b"],
                "factor_value": [float("inf"), -float("inf")],
                "amount": [1.0, 2.0],
            }
        )

        clean = _replace_infinite_numeric(frame)

        self.assertEqual(clean["asset_id"].tolist(), ["a", "b"])
        self.assertTrue(clean["factor_value"].isna().all())
        self.assertEqual(clean["amount"].tolist(), [1.0, 2.0])

    def test_computes_all_round127_public_reference_candidate_factor_names(self) -> None:
        bars = _synthetic_public_reference_bars()
        factors = compute_public_reference_multi_family_factors(
            bars,
            factor_inputs=_synthetic_factor_inputs(bars),
            moneyflow_inputs=_synthetic_moneyflow_inputs(bars),
            min_signal_date_amount=1_000_000,
        )

        names = set(factors["factor_name"])
        self.assertEqual(len(names), 20)
        self.assertIn("alpha101_rank_pv_reversal_liquid_20", names)
        self.assertIn("supertrend_pullback_lowvol_liquid_10_3", names)
        self.assertIn("rsrs_residual_reversal_liquid_18", names)
        self.assertIn("smart_money_accumulation_quality_20", names)
        self.assertIn("qvm_quality_value_momentum_blend_20_60", names)
        self.assertIn("beta_neutral_momentum_residual_quality_60", names)
        self.assertTrue((factors["amount"] >= 1_000_000).all())

    def test_zero_intraday_range_does_not_break_rolling_feature_computation(self) -> None:
        bars = _synthetic_public_reference_bars()
        bars.loc[bars.index[:10], "high"] = bars.loc[bars.index[:10], "low"]

        factors = compute_public_reference_multi_family_factors(
            bars,
            factor_inputs=_synthetic_factor_inputs(bars),
            moneyflow_inputs=_synthetic_moneyflow_inputs(bars),
            min_signal_date_amount=1_000_000,
        )

        self.assertEqual(factors["factor_name"].nunique(), 20)

    def test_builds_prescreen_without_reading_final_holdout_and_without_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = _synthetic_public_reference_bars(include_holdout=True)
            store = DatasetStore(root)
            for year in sorted(bars["date"].dt.year.unique()):
                store.write_frame(
                    bars[bars["date"].dt.year == year],
                    "processed/bars",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )
                store.write_frame(
                    _synthetic_factor_inputs(bars[bars["date"].dt.year == year]),
                    "processed/factor_inputs",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )
                store.write_frame(
                    _synthetic_moneyflow_inputs(bars[bars["date"].dt.year == year]),
                    "processed/moneyflow_inputs",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )

            result = build_public_reference_multi_family_prescreen(
                bars_roots=[root],
                factor_input_root=root,
                moneyflow_input_root=root,
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=1_000_000,
            )

        self.assertEqual(result["stage"], "public_reference_multi_family_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 20)
        self.assertEqual(result["summary"]["test_count"], 20)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertTrue(result["multiple_testing_policy"]["counts_all_round127_candidates"])
        self.assertTrue(result["summary"]["streaming_factor_evaluation"])

    def test_bar_loader_skips_year_partitions_outside_requested_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for year in (2024, 2025):
                path = root / "processed" / "bars" / "frequency=1d" / "market=CN" / f"year={year}" / "part-00000.csv"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("placeholder", encoding="utf-8")

            calls: list[Path] = []

            def fake_read(file: Path) -> pd.DataFrame:
                calls.append(file)
                return pd.DataFrame(
                    {
                        "date": [pd.Timestamp("2025-01-03")],
                        "asset_id": ["CN_XSHE_000001"],
                        "symbol": ["000001.SZ"],
                        "market": ["CN"],
                        "open": [10.0],
                        "high": [10.2],
                        "low": [9.8],
                        "close": [10.1],
                        "adj_close": [10.1],
                        "volume": [1000.0],
                        "amount": [10_100.0],
                        "vwap": [10.1],
                    }
                )

            with patch("quant_robot.ops.public_reference_multi_family_prescreen._read_bars_file", side_effect=fake_read):
                bars = load_public_reference_multi_family_bars(
                    [root],
                    analysis_start_date="2025-01-01",
                    analysis_end_date="2025-01-31",
                )

        self.assertEqual(len(calls), 1)
        self.assertIn("year=2025", str(calls[0]))
        self.assertEqual(len(bars), 1)


if __name__ == "__main__":
    unittest.main()
