from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.shortlist_exposure_audit import (
    build_shortlist_exposure_audit,
    write_shortlist_exposure_audit,
)


class ShortlistExposureAuditTest(unittest.TestCase):
    def test_missing_group_weight_share_blocks_candidate(self) -> None:
        trades = pd.DataFrame(
            {
                "signal_date": ["2021-01-01", "2021-01-01", "2021-01-08"],
                "asset_id": ["a", "b", "c"],
                "target_weight": [0.4, 0.4, 0.2],
                "entry_cash_proxy_weighted_return": [0.01, 0.02, -0.005],
                "industry": ["Bank", None, None],
                "stock_market": ["Main", "Main", None],
            }
        )

        audit = build_shortlist_exposure_audit(
            trades,
            group_columns=("industry", "stock_market"),
            max_missing_weight_share=0.15,
        )

        self.assertEqual(audit["summary"]["event_count"], 2)
        self.assertIn("missing_industry_weight_share_too_high", audit["blockers"])
        self.assertIn("missing_stock_market_weight_share_too_high", audit["blockers"])

    def test_top_group_concentration_blocks_candidate(self) -> None:
        trades = pd.DataFrame(
            {
                "signal_date": ["2021-01-01"] * 4 + ["2021-01-08"] * 4,
                "asset_id": [f"a{i}" for i in range(8)],
                "target_weight": [0.7, 0.1, 0.1, 0.1, 0.8, 0.1, 0.05, 0.05],
                "entry_cash_proxy_weighted_return": [0.01] * 8,
                "industry": ["Bank", "Auto", "Retail", "Tech", "Bank", "Auto", "Retail", "Tech"],
                "stock_market": ["Main"] * 8,
            }
        )

        audit = build_shortlist_exposure_audit(
            trades,
            group_columns=("industry",),
            max_top_weight_share_p95=0.60,
        )

        self.assertIn("industry_top_weight_share_p95_too_high", audit["blockers"])
        industry_summary = audit["dimension_summaries"]["industry"]
        self.assertGreater(industry_summary["p95_top_weight_share"], 0.60)

    def test_write_audit_outputs_json_and_csvs(self) -> None:
        trades = pd.DataFrame(
            {
                "signal_date": ["2021-01-01", "2021-01-01"],
                "asset_id": ["a", "b"],
                "target_weight": [0.5, 0.5],
                "entry_cash_proxy_weighted_return": [0.01, 0.02],
                "industry": ["Bank", "Auto"],
            }
        )

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = build_shortlist_exposure_audit(trades, group_columns=("industry",))
            write_shortlist_exposure_audit(root / "out", audit)

            self.assertTrue((root / "out" / "shortlist_exposure_audit.json").exists())
            self.assertTrue((root / "out" / "shortlist_exposure_dimension_rows.csv").exists())
            self.assertTrue((root / "out" / "shortlist_exposure_event_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
