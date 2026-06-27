from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from quant_robot.ops.shortlist_price_volume_entry_filter import (
    build_price_volume_entry_filter_audit,
    write_price_volume_entry_filter_audit,
)


class ShortlistPriceVolumeEntryFilterTest(unittest.TestCase):
    def test_projects_flagged_price_volume_trade_onto_official_template(self) -> None:
        template = pd.DataFrame(
            {
                "date": ["2024-03-01", "2024-03-08"],
                "period_return": [0.01, 0.02],
            }
        )
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                "signal_date": ["2024-02-20", "2024-02-20"],
                "exit_date": ["2024-03-01", "2024-03-08"],
                "entry_cash_proxy_weighted_return": [-0.03, 0.02],
            }
        )
        bars = _bars()

        audit = build_price_volume_entry_filter_audit(
            template_period_returns=template,
            trades_source=trades,
            bars_source=bars,
            candidates=("pv_overheat_volume_climax_20d",),
            periods_per_year=52.0,
            holding_period=4,
        )

        row = audit["rows"][0]
        self.assertEqual(row["flagged_trade_count"], 1)
        self.assertEqual(row["matched_flagged_trade_count"], 1)
        self.assertAlmostEqual(row["matched_flagged_contribution"], -0.03)
        period_rows = audit["period_return_frames"]["cash_pv_overheat_volume_climax_20d"]
        self.assertAlmostEqual(period_rows[0]["period_return"], 0.04)
        self.assertEqual(audit["feature_summary"]["missing_feature_trade_count"], 0)

    def test_writer_exports_audit_and_period_returns(self) -> None:
        template = pd.DataFrame({"date": ["2024-03-01"], "period_return": [0.01]})
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "signal_date": ["2024-02-20"],
                "exit_date": ["2024-03-01"],
                "entry_cash_proxy_weighted_return": [-0.03],
            }
        )
        audit = build_price_volume_entry_filter_audit(
            template_period_returns=template,
            trades_source=trades,
            bars_source=_bars(asset_count=1),
            candidates=("pv_overheat_volume_climax_20d",),
            periods_per_year=52.0,
            holding_period=4,
        )

        with TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_price_volume_entry_filter_audit(output, audit)

            self.assertTrue((output / "price_volume_entry_filter_audit.json").exists())
            self.assertTrue((output / "price_volume_entry_filter_rows.csv").exists())
            self.assertTrue((output / "cash_pv_overheat_volume_climax_20d_official_template_period_returns.csv").exists())


def _bars(asset_count: int = 2) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-01", "2024-02-20")
    rows = []
    for index in range(asset_count):
        asset_id = f"CN_XSHE_00000{index + 1}"
        for i, date in enumerate(dates):
            if index == 0:
                close = 10.0 + i * 0.14 + (0.30 if i % 2 == 0 else -0.30)
                amount = 100.0 if i < len(dates) - 5 else 300.0
            else:
                close = 10.0 - i * 0.01
                amount = 100.0
            rows.append(
                {
                    "date": date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": close,
                    "high": close * 1.03,
                    "low": close * 0.97,
                    "amount": amount,
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
