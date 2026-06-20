import unittest

import pandas as pd

from quant_robot.ops.extreme_trade_diagnostic import diagnose_extreme_trades, render_extreme_trade_markdown


class ExtremeTradeDiagnosticTests(unittest.TestCase):
    def test_diagnostic_identifies_extreme_trades_and_attaches_price_context(self):
        diagnostic = diagnose_extreme_trades(_trades(), _bars(), threshold=5.0, top_n=5)

        self.assertEqual(diagnostic["summary"]["trades"], 2)
        self.assertEqual(diagnostic["summary"]["extreme_trades"], 1)
        self.assertAlmostEqual(diagnostic["summary"]["max_abs_gross_return"], 6.0)
        row = diagnostic["extreme_trades"][0]
        self.assertEqual(row["asset_id"], "CN_XSHE_000001")
        self.assertEqual(row["symbol"], "000001.SZ")
        self.assertEqual(row["signal_date"], "2024-01-01")
        self.assertEqual(row["entry_date"], "2024-01-02")
        self.assertEqual(row["exit_date"], "2024-01-22")
        self.assertAlmostEqual(row["entry_adj_close"], 10.0)
        self.assertAlmostEqual(row["exit_adj_close"], 70.0)
        self.assertIn("abs_gross_return_above_threshold", row["reasons"])

    def test_markdown_report_summarizes_blocking_context(self):
        report = render_extreme_trade_markdown(diagnose_extreme_trades(_trades(), _bars(), threshold=5.0))

        self.assertIn("# Extreme Trade Diagnostic", report)
        self.assertIn("extreme trades: 1", report)
        self.assertIn("CN_XSHE_000001", report)


def _trades() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "signal_date": pd.Timestamp("2024-01-01").date(),
                "entry_date": pd.Timestamp("2024-01-02").date(),
                "exit_date": pd.Timestamp("2024-01-22").date(),
                "asset_id": "CN_XSHE_000001",
                "market": "CN",
                "factor_name": "value_low_turnover_low_tail_20",
                "gross_return": 6.0,
                "target_weight": 0.01,
            },
            {
                "signal_date": pd.Timestamp("2024-01-01").date(),
                "entry_date": pd.Timestamp("2024-01-02").date(),
                "exit_date": pd.Timestamp("2024-01-22").date(),
                "asset_id": "CN_XSHG_600000",
                "market": "CN",
                "factor_name": "value_low_turnover_low_tail_20",
                "gross_return": 0.10,
                "target_weight": 0.01,
            },
        ]
    )


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2024-01-02").date(),
                "asset_id": "CN_XSHE_000001",
                "symbol": "000001.SZ",
                "market": "CN",
                "adj_close": 10.0,
                "close": 10.0,
                "source": "fixture",
            },
            {
                "date": pd.Timestamp("2024-01-22").date(),
                "asset_id": "CN_XSHE_000001",
                "symbol": "000001.SZ",
                "market": "CN",
                "adj_close": 70.0,
                "close": 70.0,
                "source": "fixture",
            },
        ]
    )


if __name__ == "__main__":
    unittest.main()
