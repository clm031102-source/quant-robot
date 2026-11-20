from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from quant_robot.assets.universe import resolve_asset
from quant_robot.backtest.simulator import run_portfolio_backtest
from quant_robot.config.settings import (
    CostConfig,
    PortfolioSpec,
    RiskConfig,
    StrategySpec,
    find_repo_root,
)
from quant_robot.data.updater import update_universe_cache
from quant_robot.gui.app import create_server
from quant_robot.paper.ledger import PaperLedger
from quant_robot.storage.market_cache import MarketCache
from quant_robot.strategies.builtins import compute_target_weights


def _make_crypto_bull_bear_bars(n_days: int = 260) -> pd.DataFrame:
    """Create 365-day synthetic crypto bars: 150-day uptrend followed by a 110-day bear market."""
    dates = pd.date_range("2025-01-01", periods=n_days, freq="D")
    rng = np.random.default_rng(123)
    rows = []
    specs = [
        ("BTC-USD", 60000.0, 0.0035, -0.0060, 0.015),
        ("ETH-USD", 2500.0, 0.0040, -0.0075, 0.028),
        ("SOL-USD", 120.0, 0.0050, -0.0090, 0.040),
        ("BNB-USD", 550.0, 0.0025, -0.0050, 0.018),
    ]
    for sym, start_px, bull_mu, bear_mu, vol in specs:
        rets = np.concatenate(
            [
                rng.normal(bull_mu, vol, size=150),
                rng.normal(bear_mu, vol, size=n_days - 150),
            ]
        )
        px = start_px * np.cumprod(1.0 + rets)
        for i, dt in enumerate(dates):
            c = float(px[i])
            o = float(px[i - 1]) if i > 0 else c
            rows.append(
                {
                    "date": dt.date(),
                    "symbol": sym,
                    "market": "CRYPTO",
                    "open": round(o, 4),
                    "high": round(max(o, c) * 1.01, 4),
                    "low": round(min(o, c) * 0.99, 4),
                    "close": round(c, 4),
                    "adj_close": round(c, 4),
                    "volume": 100000.0,
                    "amount": c * 100000.0,
                    "source": "mock",
                }
            )
    return pd.DataFrame(rows)


class CryptoQuantTests(unittest.TestCase):
    def test_resolve_crypto_asset_metadata(self) -> None:
        asset = resolve_asset("BTC-USD", "CRYPTO")
        self.assertEqual(asset.market, "CRYPTO")
        self.assertEqual(asset.currency, "USD")
        self.assertAlmostEqual(asset.lot_size, 0.0001)
        self.assertEqual(asset.calendar, "24/7")
        self.assertEqual(asset.timezone, "UTC")

    def test_crypto_trend_vol_bull_allocation_and_bear_cash_defense(self) -> None:
        bars = _make_crypto_bull_bear_bars(260)
        adj_pivot = bars.pivot_table(index="date", columns="symbol", values="adj_close").sort_index()
        spec = StrategySpec(
            kind="crypto_trend_vol",
            rebalance_frequency="weekly",
            lookback_days=40,
            trend_ma_days=60,
            vol_lookback_days=30,
            target_volatility=0.35,
            top_n=2,
        )
        symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"]
        risk = RiskConfig(max_single_weight=0.60)

        # Mid-bull market (day 130): should hold active positive weights capped <= 1.0
        bull_weights, bull_meta = compute_target_weights(
            adj_pivot.iloc[:130], symbols, spec, risk, periods_per_year=365.0
        )
        self.assertGreater(len(bull_weights), 0)
        self.assertLessEqual(len(bull_weights), 2)
        self.assertLessEqual(sum(bull_weights.values()), 1.0 + 1e-9)
        self.assertEqual(bull_meta["regime"], "trending")

        # Deep bear market (day 250): all coins below 60-day SMA -> 100% USD cash defense
        bear_weights, bear_meta = compute_target_weights(
            adj_pivot.iloc[:250], symbols, spec, risk, periods_per_year=365.0
        )
        self.assertEqual(bear_weights, {})
        self.assertEqual(bear_meta["regime"], "defensive_cash")

    def test_fractional_crypto_backtest_protects_drawdown_in_bear_market(self) -> None:
        bars = _make_crypto_bull_bear_bars(260)
        symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"]
        spec = StrategySpec(
            kind="crypto_trend_vol",
            rebalance_frequency="weekly",
            rebalance_band=0.06,
            lookback_days=40,
            trend_ma_days=60,
            vol_lookback_days=30,
            target_volatility=0.35,
            top_n=2,
        )
        report = run_portfolio_backtest(
            bars,
            name="Crypto Trend Vol Test",
            market="CRYPTO",
            currency="USD",
            symbols=symbols,
            strategy=spec,
            cost=CostConfig(commission_bps=10.0, minimum_commission=0.0, slippage_bps=10.0),
            risk=RiskConfig(max_drawdown_halt=0.40, cooldown_sessions=7, max_single_weight=0.60),
            initial_cash=1000.0,
            lot_size=0.0001,
            min_trade_notional=10.0,
            start_date="2025-03-05",
        )
        self.assertGreater(report.metrics["trade_count"], 0)
        self.assertGreater(report.metrics["final_nav"], 0.0)
        # Confirm fractional quantities were actually executed (e.g., < 1 BTC for $1,000 capital)
        btc_trades = report.trades[report.trades["symbol"] == "BTC-USD"]
        if not btc_trades.empty:
            self.assertTrue((btc_trades["quantity"] < 1.0).all())
            self.assertTrue((btc_trades["quantity"] >= 0.0001).all())
        # Trend + vol targeting must suffer smaller drawdown than buy-and-hold in the 110-day crash
        # (max_drawdown is negative, so closer to 0 = smaller drawdown)
        self.assertLess(
            abs(report.metrics["max_drawdown"]),
            abs(report.benchmark_metrics["max_drawdown"]),
        )

    def test_crypto_paper_ledger_fractional_positions_and_dashboard_api(self) -> None:
        bars = _make_crypto_bull_bear_bars(160)
        all_dates = sorted(bars["date"].unique())
        start_d = all_dates[90].isoformat()
        spec = PortfolioSpec(
            portfolio_id="test_crypto_1k",
            name="Test Crypto 1k",
            market="CRYPTO",
            currency="USD",
            symbols=["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"],
            lot_size=0.0001,
            min_trade_notional=10.0,
            initial_cash=1000.0,
            start_date=start_d,
            cost=CostConfig(commission_bps=10.0, minimum_commission=0.0, slippage_bps=10.0),
            risk=RiskConfig(max_drawdown_halt=0.40, cooldown_sessions=7, max_single_weight=0.60),
            strategy=StrategySpec(
                kind="crypto_trend_vol",
                rebalance_frequency="weekly",
                rebalance_band=0.06,
                lookback_days=40,
                trend_ma_days=60,
                vol_lookback_days=30,
                target_volatility=0.35,
                top_n=2,
            ),
        )

        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "data"
            cache = MarketCache(data_root / "market_cache")
            for sym in spec.symbols:
                cache.upsert_symbol("CRYPTO", sym, bars[bars["symbol"] == sym])

            ledger = PaperLedger(spec, data_root / "paper")
            r1 = ledger.sync_bars(bars[bars["date"] <= all_dates[105]])
            self.assertEqual(r1["new_days"], 16)
            self.assertGreater(r1["state"]["trade_count"], 0)
            self.assertGreater(len(r1["state"]["positions"]), 0)
            # Idempotent re-run
            r1_dup = ledger.sync_bars(bars[bars["date"] <= all_dates[105]])
            self.assertEqual(r1_dup["new_days"], 0)

            # Verify Dashboard /api/backtest/run works end-to-end for CRYPTO
            server = create_server(host="127.0.0.1", port=0, repo_root=find_repo_root(), data_root=data_root)
            port = server.server_address[1]
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            try:
                bt_req = Request(
                    f"http://127.0.0.1:{port}/api/backtest/run",
                    data=json.dumps(
                        {
                            "market": "CRYPTO",
                            "symbols": "BTC-USD,ETH-USD,SOL-USD,BNB-USD",
                            "strategy_kind": "crypto_trend_vol",
                            "rebalance_frequency": "weekly",
                            "initial_cash": 1000,
                            "lot_size": 0.0001,
                            "min_trade_notional": 10.0,
                            "commission_bps": 10.0,
                            "minimum_commission": 0.0,
                            "slippage_bps": 10.0,
                            "lookback_days": 40,
                            "trend_ma_days": 60,
                            "target_volatility": 0.35,
                            "start_date": all_dates[70].isoformat(),
                        }
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(bt_req) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                    self.assertIn("<svg", payload["svg"])
                    self.assertEqual(payload["summary"]["market"], "CRYPTO")
                    self.assertEqual(payload["summary"]["currency"], "USD")
                    self.assertGreater(payload["summary"]["metrics"]["final_nav"], 0.0)
            finally:
                server.shutdown()
                server.server_close()

    def test_updater_never_truncates_history_on_crypto_or_later_default_start(self) -> None:
        bars = _make_crypto_bull_bear_bars(160)
        btc = bars[bars["symbol"] == "BTC-USD"].copy()
        with tempfile.TemporaryDirectory() as tmp:
            cache = MarketCache(Path(tmp) / "cache")
            cache.upsert_symbol("CRYPTO", "BTC-USD", btc)
            # Simulate incremental update with a LATER default_start AND a live price tweak on the last day
            tail = btc.tail(5).copy()
            tail.loc[tail.index[-1], "close"] *= 1.03
            tail.loc[tail.index[-1], "adj_close"] *= 1.03

            def fake_fetch(market: str, symbol: str, *, start_date: str, end_date: str) -> pd.DataFrame:
                return tail[tail["date"] >= pd.to_datetime(start_date).date()]

            rep = update_universe_cache(
                cache,
                "CRYPTO",
                ["BTC-USD"],
                default_start="2025-05-01",
                end_date=str(btc["date"].max()),
                fetcher=fake_fetch,
            )
            self.assertEqual(rep["error_count"], 0)
            self.assertEqual(rep["symbols"][0]["total_rows"], 160)
            self.assertEqual(rep["symbols"][0]["first_date"], "2025-01-01")


if __name__ == "__main__":
    unittest.main()
