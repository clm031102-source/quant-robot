import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.factors.tushare_moneyflow import compute_moneyflow_factors
from quant_robot.paper.simulator import PaperSimulationConfig, run_paper_simulation, write_paper_simulation_artifacts
from quant_robot.storage.dataset_store import DatasetStore


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

    def test_paper_simulation_uses_tushare_daily_basic_factor_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            factor_root = Path(tmp) / "factor_inputs"
            _write_daily_basic_factor_inputs(factor_root, load_demo_market_bars())
            config = PaperSimulationConfig(
                market="CN",
                factor_source="tushare_daily_basic",
                factor_input_root=factor_root,
                factor_name="total_mv_log",
                factor_windows=(1,),
                top_n=1,
                start_date="2024-01-04",
                end_date="2024-01-10",
                initial_cash=100000.0,
                max_asset_weight=0.4,
                min_cash_weight=0.1,
            )

            result = run_paper_simulation(load_demo_market_bars(), config)

        self.assertEqual(result["request"]["factor_source"], "tushare_daily_basic")
        self.assertGreater(len(result["intents"]), 0)
        self.assertGreater(len(result["fills"]), 0)
        self.assertTrue(all(row["market"] == "CN" for row in result["fills"]))

    def test_paper_simulation_uses_tushare_moneyflow_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            moneyflow_root = Path(tmp) / "moneyflow_inputs"
            _write_moneyflow_inputs(moneyflow_root, load_demo_market_bars())
            config = PaperSimulationConfig(
                market="CN",
                factor_source="tushare_moneyflow",
                moneyflow_input_root=moneyflow_root,
                factor_name="net_mf_amount_ratio",
                factor_windows=(1,),
                top_n=1,
                start_date="2024-01-04",
                end_date="2024-01-10",
                initial_cash=100000.0,
                max_asset_weight=0.4,
                min_cash_weight=0.1,
            )

            result = run_paper_simulation(load_demo_market_bars(), config)

        self.assertEqual(result["request"]["factor_source"], "tushare_moneyflow")
        self.assertEqual(result["request"]["moneyflow_input_root"], str(moneyflow_root))
        self.assertGreater(len(result["intents"]), 0)
        self.assertGreater(len(result["fills"]), 0)
        self.assertTrue(all(row["market"] == "CN" for row in result["fills"]))

    def test_tushare_moneyflow_inputs_are_filtered_to_requested_window_before_factor_compute(self):
        with tempfile.TemporaryDirectory() as tmp:
            moneyflow_root = Path(tmp) / "moneyflow_inputs"
            _write_moneyflow_inputs(moneyflow_root, load_demo_market_bars())
            config = PaperSimulationConfig(
                market="CN",
                factor_source="tushare_moneyflow",
                moneyflow_input_root=moneyflow_root,
                factor_name="net_mf_amount_ratio",
                factor_windows=(1,),
                top_n=1,
                start_date="2024-01-05",
                end_date="2024-01-08",
                initial_cash=100000.0,
            )

            with patch("quant_robot.paper.simulator.compute_moneyflow_factors", wraps=compute_moneyflow_factors) as wrapped:
                run_paper_simulation(load_demo_market_bars(), config)

            inputs = wrapped.call_args.args[0]

        input_dates = pd.to_datetime(inputs["date"]).dt.date
        self.assertGreater(len(inputs), 0)
        self.assertGreaterEqual(input_dates.min(), pd.Timestamp("2024-01-05").date())
        self.assertLessEqual(input_dates.max(), pd.Timestamp("2024-01-08").date())

    def test_paper_simulation_artifacts_serialize_path_request_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factor_root = root / "factor_inputs"
            _write_daily_basic_factor_inputs(factor_root, load_demo_market_bars())
            result = run_paper_simulation(
                load_demo_market_bars(),
                PaperSimulationConfig(
                    market="CN",
                    factor_source="tushare_daily_basic",
                    factor_input_root=factor_root,
                    factor_name="total_mv_log",
                    factor_windows=(1,),
                    top_n=1,
                    start_date="2024-01-04",
                    end_date="2024-01-10",
                    initial_cash=100000.0,
                    max_asset_weight=0.4,
                    min_cash_weight=0.1,
                ),
            )

            write_paper_simulation_artifacts(result, root / "paper")

            manifest = json.loads((root / "paper" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["request"]["factor_input_root"], str(factor_root))

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

    def test_paper_simulation_blocks_fills_on_suspended_or_limit_locked_bars(self):
        bars = _bars_with_execution_constraints()

        result = run_paper_simulation(
            bars,
            PaperSimulationConfig(
                market="CN_ETF",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=2,
                start_date="2024-01-04",
                end_date="2024-01-05",
                initial_cash=100000.0,
                max_asset_weight=0.5,
            ),
        )

        blocked_reasons = {event["reason"] for event in result["execution_events"]}
        filled_assets = {row["asset_id"] for row in result["fills"]}
        self.assertIn("suspended", blocked_reasons)
        self.assertIn("limit_up_buy_blocked", blocked_reasons)
        self.assertNotIn("CN_ETF_XSHG_510300", filled_assets)
        self.assertNotIn("CN_ETF_XSHE_159915", filled_assets)

    def test_paper_simulation_records_capacity_and_market_impact_evidence(self):
        result = run_paper_simulation(
            load_demo_market_bars(),
            PaperSimulationConfig(
                market="CN_ETF",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=1,
                start_date="2024-01-04",
                end_date="2024-01-08",
                initial_cash=100000.0,
                max_asset_weight=1.0,
                min_cash_weight=0.0,
                market_impact_bps=10.0,
                max_participation_rate=0.10,
            ),
        )

        self.assertGreater(len(result["fills"]), 0)
        self.assertTrue(any(row["capacity_limited"] for row in result["fills"]))
        self.assertTrue(any(row["market_impact_fee"] > 0.0 for row in result["fills"]))
        self.assertGreater(result["metrics"]["capacity_limited_fills"], 0)
        self.assertGreater(result["metrics"]["max_participation_rate"], 0.10)


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


def _bars_with_execution_constraints() -> pd.DataFrame:
    rows = []
    prices_by_asset = {
        "CN_ETF_XSHG_510300": ("510300.SH", "XSHG", [4.0, 4.1, 4.2, 4.4, 4.5, 4.6]),
        "CN_ETF_XSHE_159915": ("159915.SZ", "XSHE", [2.0, 2.1, 2.2, 2.4, 2.5, 2.6]),
    }
    for asset_id, (symbol, exchange, prices) in prices_by_asset.items():
        for date, price in zip(pd.date_range("2024-01-01", "2024-01-06").date, prices, strict=True):
            row = _bar(asset_id, symbol, "CN_ETF", exchange, "Asia/Shanghai", date, price)
            row["asset_type"] = "etf"
            row["suspended"] = asset_id == "CN_ETF_XSHG_510300" and str(date) == "2024-01-05"
            row["limit_up"] = asset_id == "CN_ETF_XSHE_159915" and str(date) == "2024-01-05"
            row["limit_down"] = False
            rows.append(row)
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


def _write_daily_basic_factor_inputs(root: Path, bars: pd.DataFrame) -> None:
    rows = []
    for index, row in bars[bars["market"] == "CN"].reset_index(drop=True).iterrows():
        rows.append(
            {
                "date": row["date"],
                "asset_id": row["asset_id"],
                "symbol": row["symbol"],
                "market": "CN",
                "source": "tushare",
                "turnover_rate": 1.0 + index * 0.01,
                "turnover_rate_f": 1.1 + index * 0.01,
                "volume_ratio": 0.9 + index * 0.01,
                "pe_ttm": 8.0 + index * 0.1,
                "pb": 1.5 + index * 0.1,
                "ps_ttm": 2.0 + index * 0.1,
                "dv_ttm": 3.0,
                "total_mv": 120000.0 + index * 1000.0,
                "circ_mv": 90000.0 + index * 1000.0,
            }
        )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/factor_inputs",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


def _write_moneyflow_inputs(root: Path, bars: pd.DataFrame) -> None:
    rows = []
    for index, row in bars[bars["market"] == "CN"].reset_index(drop=True).iterrows():
        scale = 1.0 + index * 0.01
        rows.append(
            {
                "date": row["date"],
                "asset_id": row["asset_id"],
                "symbol": row["symbol"],
                "market": "CN",
                "source": "tushare_moneyflow",
                "buy_sm_amount": 100.0 * scale,
                "sell_sm_amount": 80.0 * scale,
                "buy_md_amount": 300.0 * scale,
                "sell_md_amount": 250.0 * scale,
                "buy_lg_amount": 500.0 * scale,
                "sell_lg_amount": 450.0 * scale,
                "buy_elg_amount": 700.0 * scale,
                "sell_elg_amount": 650.0 * scale,
                "net_mf_amount": 120.0 + index,
            }
        )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/moneyflow_inputs",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


if __name__ == "__main__":
    unittest.main()
