import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.daily_basic_valuation_shape_exposure_audit import (
    REQUIRED_STYLE_NAMES,
    build_style_factors_from_bars_daily_basic,
    build_valuation_shape_exposure_audit,
    summarize_quantile_shape,
    write_valuation_shape_exposure_audit,
)


def _shape_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2025-01-02", periods=8)
    assets = [f"CN_XSHG_TEST{i:03d}" for i in range(30)]
    factor_rows = []
    label_rows = []
    style_rows = []
    stock_basic_rows = []
    for asset_idx, asset_id in enumerate(assets):
        stock_basic_rows.append({"asset_id": asset_id, "industry": ["bank", "tech", "consumer"][asset_idx % 3]})
    for date_idx, trade_date in enumerate(dates):
        for asset_idx, asset_id in enumerate(assets):
            signal = float(asset_idx)
            bucket = asset_idx // 6
            bucket_payoff = [0.00, 0.04, 0.03, 0.02, 0.01][bucket]
            factor_rows.append(
                {
                    "date": trade_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "daily_basic_valuation_reversion_dvratio_quality_60",
                    "factor_value": signal,
                }
            )
            label_rows.append(
                {
                    "date": trade_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 20,
                    "execution_lag": 1,
                    "forward_return": bucket_payoff + date_idx * 0.0001,
                }
            )
            for style_name, style_value in {
                "size": asset_idx,
                "value": 30 - asset_idx,
                "lowvol": asset_idx % 5,
                "momentum": (asset_idx + date_idx) % 7,
                "liquidity": asset_idx % 11,
            }.items():
                style_rows.append(
                    {
                        "date": trade_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "style_name": style_name,
                        "style_value": float(style_value),
                    }
                )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(stock_basic_rows), pd.DataFrame(style_rows)


class DailyBasicValuationShapeExposureAuditTests(unittest.TestCase):
    def test_build_style_factors_from_bars_and_daily_basic_outputs_required_styles(self) -> None:
        dates = pd.bdate_range("2025-01-02", periods=30)
        bars = []
        daily_basic = []
        for asset_idx in range(8):
            asset_id = f"CN_XSHG_TEST{asset_idx:03d}"
            price = 10.0 + asset_idx
            for date_idx, trade_date in enumerate(dates):
                price *= 1.0 + 0.001 * ((date_idx % 5) - 2)
                bars.append(
                    {
                        "date": trade_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "adj_close": price,
                        "amount": 20_000_000 + asset_idx * 1_000_000,
                    }
                )
                daily_basic.append(
                    {
                        "date": trade_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "pb": 1.0 + asset_idx * 0.1,
                        "ps_ttm": 2.0 + asset_idx * 0.2,
                        "dv_ratio": 0.5 + asset_idx * 0.01,
                        "circ_mv": 5_000_000_000 + asset_idx * 10_000_000,
                    }
                )

        styles = build_style_factors_from_bars_daily_basic(pd.DataFrame(bars), pd.DataFrame(daily_basic))

        self.assertEqual(set(styles["style_name"].unique()), set(REQUIRED_STYLE_NAMES))
        self.assertGreater(len(styles), 0)
        self.assertFalse(styles["style_value"].isna().all())

    def test_quantile_shape_flags_nonmonotonic_top_bucket(self) -> None:
        factors, labels, _, _ = _shape_frames()

        result = summarize_quantile_shape(factors, labels, min_cross_section=20, min_dates=6)

        row = result["quantile_summary"][0]
        self.assertEqual(row["best_quantile"], "q2")
        self.assertLess(row["quantile_monotonicity"], 0.70)
        self.assertFalse(row["shape_pass"])
        self.assertIn("top_quantile_not_best_bucket", row["shape_blockers"])

    def test_combined_audit_never_allows_promotion_directly(self) -> None:
        factors, labels, stock_basic, styles = _shape_frames()

        result = build_valuation_shape_exposure_audit(
            factors=factors,
            labels=labels,
            stock_basic=stock_basic,
            style_factors=styles,
            min_dates=6,
            min_cross_section=20,
            min_residual_mean_ic=0.001,
            min_residual_ic_t_stat=0.1,
        )

        self.assertEqual(result["stage"], "daily_basic_valuation_shape_exposure_audit")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed"])
        self.assertEqual(result["shape_audit"]["summary"]["shape_pass_count"], 0)

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_valuation_shape_exposure_audit(output_dir, result)
            self.assertTrue((output_dir / "daily_basic_valuation_shape_exposure_audit.json").exists())
            self.assertTrue((output_dir / "daily_basic_valuation_shape_exposure_audit.md").exists())
            self.assertTrue((output_dir / "quantile_shape_summary.csv").exists())
            self.assertTrue((output_dir / "factor_summary.csv").exists())


if __name__ == "__main__":
    unittest.main()
