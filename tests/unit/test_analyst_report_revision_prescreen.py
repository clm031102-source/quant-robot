import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.analyst_report_revision_prescreen import (
    build_analyst_report_revision_prescreen,
    compute_analyst_report_revision_factors,
    write_analyst_report_revision_prescreen,
)


class AnalystReportRevisionPrescreenTests(unittest.TestCase):
    def test_compute_analyst_report_revision_factors_uses_next_trade_date(self) -> None:
        bars = _bars(days=16, assets=4)
        reports = _reports()

        factors = compute_analyst_report_revision_factors(
            reports,
            bars,
            pit_lag_trade_days=1,
            min_signal_date_amount=1.0,
        )

        self.assertEqual(
            set(factors["factor_name"]),
            {
                "analyst_target_upside_60",
                "analyst_np_revision_90",
                "analyst_eps_revision_90",
                "analyst_revision_target_composite_90",
            },
        )
        self.assertTrue((pd.to_datetime(factors["date"]) > pd.to_datetime(factors["event_date"])).all())
        self.assertTrue(factors["factor_value"].notna().all())
        self.assertTrue(factors["adv20_amount"].notna().all())

    def test_build_and_writer_keep_promotion_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars_root = root / "bars_root" / "bars"
            report_root = root / "report_root" / "processed" / "analyst_report_rc" / "year=2024"
            bars_root.mkdir(parents=True)
            report_root.mkdir(parents=True)
            _bars(days=18, assets=4).to_csv(bars_root / "part.csv", index=False)
            _reports().to_csv(report_root / "part.csv", index=False)

            result = build_analyst_report_revision_prescreen(
                report_roots=[root / "report_root"],
                bars_roots=[root / "bars_root"],
                stock_basic=_stock_basic(4),
                analysis_start_date="2024-01-01",
                analysis_end_date="2024-01-31",
                horizons=(1,),
                execution_lag=1,
                min_cross_section=4,
                min_ic_observations=1,
                min_signal_date_amount=1.0,
            )

            self.assertEqual(result["stage"], "analyst_report_revision_pit_prescreen")
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertFalse(result["live_boundary_allowed"])
            self.assertGreater(result["summary"]["factor_rows"], 0)
            write_analyst_report_revision_prescreen(root / "out", result)
            self.assertTrue((root / "out" / "analyst_report_revision_prescreen.json").exists())
            self.assertTrue((root / "out" / "analyst_report_revision_prescreen.md").exists())


def _bars(days: int, assets: int) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=days)
    rows = []
    for asset_idx in range(assets):
        price = 10.0 + asset_idx
        for day_idx, date_value in enumerate(dates):
            price *= 1.0 + (asset_idx % 2) * 0.005
            rows.append(
                {
                    "date": date_value,
                    "asset_id": f"CN_XSHE_{asset_idx:06d}",
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": 20_000_000.0 + asset_idx * 1_000_000.0 + day_idx,
                }
            )
    return pd.DataFrame(rows)


def _reports() -> pd.DataFrame:
    symbols = [f"{idx:06d}.SZ" for idx in range(4)]
    return pd.DataFrame(
        {
            "symbol": symbols * 2,
            "report_date": ["2024-01-09"] * 4 + ["2024-01-16"] * 4,
            "name": [f"Stock {idx}" for idx in range(4)] * 2,
            "org_name": ["Org"] * 8,
            "author_name": ["Analyst"] * 8,
            "report_title": [f"Report {idx}" for idx in range(8)],
            "report_type": ["company"] * 8,
            "rating": ["持有", "增持", "买入", "买入"] * 2,
            "quarter": ["2024Q1"] * 8,
            "eps": [1.0, 1.1, 1.2, 1.3, 1.1, 1.2, 1.4, 1.7],
            "np": [100.0, 110.0, 120.0, 130.0, 105.0, 120.0, 140.0, 170.0],
            "roe": [10.0, 11.0, 12.0, 13.0, 11.0, 12.0, 14.0, 17.0],
            "tp": [12.0, 14.0, 16.0, 18.0, 12.5, 15.0, 18.0, 23.0],
            "min_price": [pd.NA] * 8,
            "max_price": [pd.NA] * 8,
            "pe": [10.0] * 8,
        }
    )


def _stock_basic(assets: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "asset_id": [f"CN_XSHE_{idx:06d}" for idx in range(assets)],
            "symbol": [f"{idx:06d}.SZ" for idx in range(assets)],
            "market": ["CN"] * assets,
            "industry": ["Tech", "Tech", "Bank", "Bank"],
        }
    )


if __name__ == "__main__":
    unittest.main()
