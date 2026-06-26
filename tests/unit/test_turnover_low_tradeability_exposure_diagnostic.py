import unittest

import pandas as pd

from quant_robot.ops.turnover_low_tradeability_exposure_diagnostic import (
    attach_tradeability_and_exposures,
    summarize_turnover_low_tradeability_exposure,
)


class TurnoverLowTradeabilityExposureDiagnosticTests(unittest.TestCase):
    def test_attach_tradeability_and_exposures_marks_blocked_roundtrip(self) -> None:
        trades = _trades()
        attached = attach_tradeability_and_exposures(
            trades,
            daily_basic=_daily_basic(),
            metadata=_metadata(),
            tradeability_masks=_masks(),
        )

        blocked = attached[attached["asset_id"] == "CN_TEST_B"].iloc[0]
        allowed = attached[attached["asset_id"] == "CN_TEST_A"].iloc[0]

        self.assertTrue(bool(allowed["fully_tradeable_roundtrip"]))
        self.assertFalse(bool(blocked["entry_allowed"]))
        self.assertFalse(bool(blocked["fully_tradeable_roundtrip"]))
        self.assertEqual(blocked["industry"], "Software")
        self.assertEqual(float(blocked["roundtrip_cash_proxy_weighted_return"]), 0.0)

    def test_summary_reports_tradeability_cash_proxy_and_reasons(self) -> None:
        attached = attach_tradeability_and_exposures(
            _trades(),
            daily_basic=_daily_basic(),
            metadata=_metadata(),
            tradeability_masks=_masks(),
        )

        result = summarize_turnover_low_tradeability_exposure(
            attached,
            base_metrics={"total_return": 0.1, "sharpe": 1.0},
            periods_per_year=252.0,
            holding_period=5,
            extreme_trade_abs_return=0.5,
        )

        self.assertEqual(result["summary"]["roundtrip_blocked_trade_rows"], 1)
        self.assertAlmostEqual(result["summary"]["roundtrip_blocked_trade_rate"], 0.5)
        self.assertIn("limit_up_official", result["blocked_reasons_top"])
        self.assertIn("roundtrip_cash_proxy", result["tradeability_metrics"])
        self.assertEqual(len(result["period_returns"]), 1)
        self.assertEqual(result["period_returns"][0]["signal_date"], "2024-01-02")
        self.assertEqual(result["period_returns"][0]["entry_date"], "2024-01-03")
        self.assertEqual(result["period_returns"][0]["date"], "2024-01-08")
        self.assertIn("entry_cash_proxy_return", result["period_returns"][0])
        self.assertIn("circ_mv", result["bucket_summaries"])
        self.assertEqual(result["industry_contribution"]["worst"][0]["industry"], "Software")


def _trades() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "signal_date": "2024-01-02",
                "entry_date": "2024-01-03",
                "exit_date": "2024-01-08",
                "asset_id": "CN_TEST_A",
                "market": "CN",
                "target_weight": 0.5,
                "target_notional": 500_000.0,
                "entry_amount": 50_000_000.0,
                "participation_rate": 0.01,
                "capacity_limited": False,
                "cost_rate": 0.001,
                "gross_return": 0.10,
                "net_return": 0.099,
                "weighted_return": 0.0495,
            },
            {
                "signal_date": "2024-01-02",
                "entry_date": "2024-01-03",
                "exit_date": "2024-01-08",
                "asset_id": "CN_TEST_B",
                "market": "CN",
                "target_weight": 0.5,
                "target_notional": 500_000.0,
                "entry_amount": 50_000_000.0,
                "participation_rate": 0.01,
                "capacity_limited": False,
                "cost_rate": 0.001,
                "gross_return": -0.20,
                "net_return": -0.201,
                "weighted_return": -0.1005,
            },
        ]
    )


def _daily_basic() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": "2024-01-02",
                "asset_id": "CN_TEST_A",
                "market": "CN",
                "turnover_rate": 0.1,
                "turnover_rate_f": 0.2,
                "volume_ratio": 0.8,
                "pe_ttm": 10.0,
                "pb": 1.0,
                "ps_ttm": 2.0,
                "dv_ttm": 1.5,
                "total_mv": 1_000_000.0,
                "circ_mv": 800_000.0,
            },
            {
                "date": "2024-01-02",
                "asset_id": "CN_TEST_B",
                "market": "CN",
                "turnover_rate": 0.2,
                "turnover_rate_f": 0.4,
                "volume_ratio": 1.1,
                "pe_ttm": 20.0,
                "pb": 2.0,
                "ps_ttm": 4.0,
                "dv_ttm": 0.5,
                "total_mv": 2_000_000.0,
                "circ_mv": 1_600_000.0,
            },
        ]
    )


def _metadata() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"asset_id": "CN_TEST_A", "industry": "Utility", "stock_market": "Main"},
            {"asset_id": "CN_TEST_B", "industry": "Software", "stock_market": "Main"},
        ]
    )


def _masks() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": "2024-01-03",
                "asset_id": "CN_TEST_A",
                "entry_tradeable": True,
                "exit_tradeable": True,
                "can_buy": True,
                "can_sell": True,
                "blocked_reasons": "",
            },
            {
                "date": "2024-01-08",
                "asset_id": "CN_TEST_A",
                "entry_tradeable": True,
                "exit_tradeable": True,
                "can_buy": True,
                "can_sell": True,
                "blocked_reasons": "",
            },
            {
                "date": "2024-01-03",
                "asset_id": "CN_TEST_B",
                "entry_tradeable": False,
                "exit_tradeable": True,
                "can_buy": False,
                "can_sell": True,
                "blocked_reasons": "limit_up_official",
            },
            {
                "date": "2024-01-08",
                "asset_id": "CN_TEST_B",
                "entry_tradeable": True,
                "exit_tradeable": True,
                "can_buy": True,
                "can_sell": True,
                "blocked_reasons": "",
            },
        ]
    )


if __name__ == "__main__":
    unittest.main()
