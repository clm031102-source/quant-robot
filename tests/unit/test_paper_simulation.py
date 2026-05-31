import unittest
from unittest.mock import patch

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.paper.simulator import PaperSimulationConfig, run_paper_simulation


class PaperSimulationTests(unittest.TestCase):
    def test_paper_simulation_creates_research_only_intents_and_next_bar_fills(self):
        config = PaperSimulationConfig(
            market="CN",
            factor_name="momentum_2",
            factor_windows=(2,),
            top_n=1,
            start_date="2024-01-04",
            end_date="2024-01-10",
            initial_cash=100000.0,
            commission_bps=5.0,
            slippage_bps=10.0,
        )

        result = run_paper_simulation(load_demo_market_bars(), config)

        self.assertGreater(len(result["intents"]), 0)
        self.assertGreater(len(result["fills"]), 0)
        self.assertTrue(all(row["executable"] is False for row in result["intents"]))
        self.assertTrue(all(row["fill_type"] == "simulated" for row in result["fills"]))
        first_intent = result["intents"][0]
        first_fill = result["fills"][0]
        self.assertGreater(pd.to_datetime(first_fill["execution_date"]), pd.to_datetime(first_intent["signal_date"]))
        self.assertIsNone(first_intent["broker_order_id"])

    def test_paper_simulation_tracks_cash_positions_and_equity(self):
        config = PaperSimulationConfig(
            market="ALL",
            factor_name="momentum_2",
            factor_windows=(2,),
            top_n=2,
            start_date="2024-01-04",
            end_date="2024-01-12",
            initial_cash=50000.0,
            max_asset_weight=0.35,
            min_cash_weight=0.10,
        )

        result = run_paper_simulation(load_demo_market_bars(), config)

        self.assertEqual(result["data_mode"], "fixture")
        self.assertGreater(len(result["equity_curve"]), 0)
        self.assertGreater(len(result["positions"]), 0)
        self.assertGreater(result["metrics"]["ending_equity"], 0.0)
        self.assertGreaterEqual(result["metrics"]["ending_cash"], 0.0)
        self.assertLessEqual(max(row["target_weight"] for row in result["snapshots"]), 0.70)

    def test_paper_simulation_runs_for_cn_etf_market(self):
        config = PaperSimulationConfig(
            market="CN_ETF",
            factor_name="momentum_2",
            factor_windows=(2,),
            top_n=2,
            start_date="2024-01-04",
            end_date="2024-01-12",
            initial_cash=100000.0,
            max_asset_weight=0.4,
            min_cash_weight=0.1,
        )

        result = run_paper_simulation(load_demo_market_bars(), config)

        self.assertGreater(len(result["fills"]), 0)
        self.assertTrue(all(row["market"] == "CN_ETF" for row in result["fills"]))

    def test_cn_etf_fills_respect_100_share_lots(self):
        config = PaperSimulationConfig(
            market="CN_ETF",
            factor_name="momentum_2",
            factor_windows=(2,),
            top_n=2,
            start_date="2024-01-04",
            end_date="2024-01-12",
            initial_cash=100000.0,
            max_asset_weight=0.4,
            min_cash_weight=0.1,
        )

        result = run_paper_simulation(load_demo_market_bars(), config)

        self.assertGreater(len(result["fills"]), 0)
        self.assertTrue(all(row["lot_size"] == 100.0 for row in result["fills"]))
        self.assertTrue(all(row["quantity"] % 100 == 0 for row in result["fills"]))

    def test_paper_simulation_rejects_real_account_like_position_columns(self):
        config = PaperSimulationConfig(market="CN", factor_name="momentum_2", factor_windows=(2,), top_n=1)
        positions = pd.DataFrame({"asset_id": ["CN_XSHG_600519"], "quantity": [1.0], "account_id": ["real"]})

        with self.assertRaisesRegex(ValueError, "real account or broker columns"):
            run_paper_simulation(load_demo_market_bars(), config, initial_positions=positions)

    def test_paper_simulation_computes_factors_once_for_signal_loop(self):
        config = PaperSimulationConfig(market="CN_ETF", factor_name="momentum_2", factor_windows=(2,), top_n=1)

        with patch("quant_robot.paper.simulator.compute_basic_factors", wraps=compute_basic_factors) as wrapped:
            run_paper_simulation(load_demo_market_bars(), config)

        self.assertEqual(wrapped.call_count, 1)

    def test_paper_simulation_can_sample_rebalance_dates(self):
        daily = run_paper_simulation(
            load_demo_market_bars(),
            PaperSimulationConfig(market="CN_ETF", factor_name="momentum_2", factor_windows=(2,), top_n=1, rebalance_interval=1),
        )
        sampled = run_paper_simulation(
            load_demo_market_bars(),
            PaperSimulationConfig(market="CN_ETF", factor_name="momentum_2", factor_windows=(2,), top_n=1, rebalance_interval=3),
        )

        self.assertEqual(sampled["request"]["rebalance_interval"], 3)
        self.assertAlmostEqual(sampled["request"]["periods_per_year"], 252 / 3)
        self.assertLess(len(sampled["snapshots"]), len(daily["snapshots"]))

    def test_paper_simulation_does_not_fill_assets_without_execution_day_bar(self):
        result = run_paper_simulation(
            _bars_with_cn_closed_on_execution_date(),
            PaperSimulationConfig(
                market="ALL",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=2,
                start_date="2024-01-05",
                end_date="2024-01-06",
                initial_cash=100000.0,
            ),
        )

        self.assertTrue(result["fills"])
        self.assertFalse(
            any(row["market"] == "CN" and row["execution_date"] == "2024-01-06" for row in result["fills"])
        )

    def test_paper_simulation_total_return_uses_starting_equity(self):
        result = run_paper_simulation(
            load_demo_market_bars(),
            PaperSimulationConfig(
                market="CN_ETF",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=1,
                start_date="2024-01-04",
                end_date="2024-01-10",
                initial_cash=100000.0,
            ),
        )

        self.assertEqual(result["metrics"]["starting_equity"], 100000.0)
        self.assertAlmostEqual(result["metrics"]["total_return"], result["metrics"]["cash_return"])

    def test_paper_simulation_drawdown_guard_blocks_new_buys(self):
        result = run_paper_simulation(
            load_demo_market_bars(),
            PaperSimulationConfig(
                market="CN_ETF",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=1,
                start_date="2024-01-04",
                end_date="2024-01-12",
                initial_cash=100000.0,
                commission_bps=50.0,
                slippage_bps=50.0,
                max_asset_weight=1.0,
                min_cash_weight=0.0,
                max_drawdown_guard=0.0001,
                guard_cooldown_periods=5,
            ),
        )

        self.assertGreater(len(result["guard_events"]), 0)
        self.assertGreater(result["metrics"]["guard_event_count"], 0)
        self.assertTrue(any(event["event_type"] == "drawdown_guard_triggered" for event in result["guard_events"]))
        self.assertTrue(any(event.get("blocked_buy_intents", 0) > 0 for event in result["guard_events"]))


def _bars_with_cn_closed_on_execution_date() -> pd.DataFrame:
    rows = []
    for date, price in zip(pd.date_range("2024-01-01", "2024-01-05").date, [10.0, 10.2, 10.5, 10.8, 11.2], strict=True):
        rows.append(_bar("CN_XSHG_600519", "600519.SH", "CN", "XSHG", "Asia/Shanghai", date, price))
    for date, price in zip(
        pd.date_range("2024-01-01", "2024-01-06").date,
        [30000.0, 30200.0, 30500.0, 30900.0, 31200.0, 31600.0],
        strict=True,
    ):
        rows.append(_bar("CRYPTO_BINANCE_BTC_USDT", "BTC/USDT", "CRYPTO", "BINANCE", "UTC", date, price))
    return pd.DataFrame(rows)


def _bar(asset_id: str, symbol: str, market: str, exchange: str, timezone: str, date: object, price: float) -> dict[str, object]:
    timestamp = pd.Timestamp(date).tz_localize("UTC")
    return {
        "asset_id": asset_id,
        "symbol": symbol,
        "market": market,
        "exchange": exchange,
        "asset_type": "crypto_spot" if market == "CRYPTO" else "stock",
        "timestamp": timestamp,
        "date": date,
        "timezone": timezone,
        "calendar": "24/7" if market == "CRYPTO" else exchange,
        "frequency": "1d",
        "open": price,
        "high": price * 1.01,
        "low": price * 0.99,
        "close": price,
        "adj_close": price,
        "volume": 1000.0,
        "amount": price * 1000.0,
        "vwap": price,
        "currency": "USDT" if market == "CRYPTO" else "CNY",
        "source": "fixture",
        "adjusted": True,
        "ingested_at": pd.Timestamp("2024-01-01", tz="UTC"),
    }


if __name__ == "__main__":
    unittest.main()
