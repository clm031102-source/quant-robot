from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from quant_robot.audit.project_audit import collect_project_audit
from quant_robot.config.settings import CostConfig, PortfolioSpec, PortfoliosConfig, RiskConfig, StrategySpec, find_repo_root
from quant_robot.gui.app import create_server
from quant_robot.paper.ledger import PaperLedger
from quant_robot.paper.runner import run_daily_paper_update
from quant_robot.storage.market_cache import MarketCache


def _make_us_bars(n_days: int = 80) -> pd.DataFrame:
    dates = pd.bdate_range("2026-08-03", periods=n_days)
    rng = np.random.default_rng(7)
    rows = []
    for sym, base in (("SPYM", 80.0), ("EFA", 95.0), ("IEF", 90.0), ("GLDM", 78.0)):
        px = base * np.cumprod(1.0 + rng.normal(0.0005, 0.008, size=n_days))
        for i, dt in enumerate(dates):
            c = float(px[i])
            o = float(px[i - 1]) if i > 0 else c
            rows.append(
                {
                    "date": dt.date(),
                    "symbol": sym,
                    "market": "US_ETF",
                    "open": round(o, 4),
                    "high": round(max(o, c) * 1.005, 4),
                    "low": round(min(o, c) * 0.995, 4),
                    "close": round(c, 4),
                    "adj_close": round(c, 4),
                    "volume": 200000.0,
                    "amount": c * 200000.0,
                    "source": "mock",
                }
            )
    return pd.DataFrame(rows)


class PaperAndDashboardTests(unittest.TestCase):
    def test_paper_ledger_idempotent_and_auto_backfills_missed_days(self) -> None:
        bars = _make_us_bars(80)
        all_dates = sorted(bars["date"].unique())
        start_d = all_dates[50].isoformat()
        spec = PortfolioSpec(
            portfolio_id="test_us_1k",
            name="Test US 1k",
            market="US_ETF",
            currency="USD",
            symbols=["SPYM", "EFA", "IEF", "GLDM"],
            lot_size=1,
            initial_cash=1000.0,
            start_date=start_d,
            cost=CostConfig(commission_bps=0.0, minimum_commission=1.0, slippage_bps=10.0),
            risk=RiskConfig(max_drawdown_halt=0.35, cooldown_sessions=5),
            strategy=StrategySpec(kind="fixed_allocation", rebalance_frequency="monthly", rebalance_band=0.04),
        )

        with tempfile.TemporaryDirectory() as tmp:
            ledger = PaperLedger(spec, tmp)
            # Day 1 only
            day1_bars = bars[bars["date"] <= all_dates[50]]
            r1 = ledger.sync_bars(day1_bars)
            self.assertEqual(r1["new_days"], 1)

            # Re-running same day must be a clean idempotent no-op
            r1_dup = ledger.sync_bars(day1_bars)
            self.assertEqual(r1_dup["new_days"], 0)
            self.assertEqual(r1_dup["status"], "up_to_date")

            # Simulate PC off for 10 days -> passing all bars up to day 60 must seamlessly backfill all 10 missed sessions!
            day11_bars = bars[bars["date"] <= all_dates[60]]
            r2 = ledger.sync_bars(day11_bars)
            self.assertEqual(r2["new_days"], 10)
            self.assertEqual(r2["state"]["days_recorded"], 11)
            # Initial entry trades executed on Day 2 open
            self.assertGreater(r2["state"]["trade_count"], 0)
            self.assertGreater(len(r2["state"]["positions"]), 0)

    def test_runner_and_dashboard_http_endpoints(self) -> None:
        bars = _make_us_bars(80)
        all_dates = sorted(bars["date"].unique())
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "data"
            cache = MarketCache(data_root / "market_cache")
            for sym in ("SPYM", "EFA", "IEF", "GLDM"):
                cache.upsert_symbol("US_ETF", sym, bars[bars["symbol"] == sym])

            cfg = PortfoliosConfig(
                portfolios=[
                    PortfolioSpec(
                        portfolio_id="demo_us",
                        name="Demo US",
                        market="US_ETF",
                        currency="USD",
                        symbols=["SPYM", "EFA", "IEF", "GLDM"],
                        lot_size=1,
                        initial_cash=1000.0,
                        start_date=all_dates[55].isoformat(),
                        cost=CostConfig(commission_bps=0.0, minimum_commission=1.0, slippage_bps=10.0),
                        risk=RiskConfig(max_drawdown_halt=0.35, cooldown_sessions=5),
                        strategy=StrategySpec(kind="fixed_allocation", rebalance_frequency="monthly", rebalance_band=0.04),
                    )
                ]
            )
            overview = run_daily_paper_update(config=cfg, data_root=data_root, skip_fetch=True)
            self.assertEqual(len(overview["portfolios"]), 1)
            self.assertGreater(overview["portfolios"][0]["days_recorded"], 10)

            server = create_server(host="127.0.0.1", port=0, repo_root=find_repo_root(), data_root=data_root)
            port = server.server_address[1]
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            try:
                base = f"http://127.0.0.1:{port}"
                with urlopen(f"{base}/") as resp:
                    self.assertEqual(resp.status, 200)
                    self.assertIn("Quant Robot", resp.read().decode("utf-8"))

                with urlopen(f"{base}/api/overview") as resp:
                    ov = json.loads(resp.read().decode("utf-8"))
                    self.assertFalse(ov["live_trading_allowed"])
                    self.assertEqual(ov["portfolios"][0]["portfolio_id"], "demo_us")

                with urlopen(f"{base}/api/portfolio/demo_us") as resp:
                    det = json.loads(resp.read().decode("utf-8"))
                    self.assertGreater(len(det["equity"]), 10)

                bt_req = Request(
                    f"{base}/api/backtest/run",
                    data=json.dumps(
                        {
                            "market": "US_ETF",
                            "symbols": ["SPYM", "EFA", "IEF", "GLDM"],
                            "strategy_kind": "passive_drift",
                            "rebalance_frequency": "never",
                            "initial_cash": 1000,
                            "minimum_commission": 1.0,
                        }
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(bt_req) as resp:
                    bt = json.loads(resp.read().decode("utf-8"))
                    self.assertIn("<svg", bt["svg"])
                    self.assertGreater(bt["summary"]["metrics"]["final_nav"], 0)
            finally:
                server.shutdown()
                server.server_close()

    def test_project_safety_and_maintainability_audit_passes(self) -> None:
        audit = collect_project_audit(find_repo_root())
        self.assertTrue(audit["summary"]["passes"], msg=json.dumps(audit, indent=2))
        self.assertFalse(audit["summary"]["live_trading_allowed"])
        self.assertEqual(audit["summary"]["oversized_count"], 0)


if __name__ == "__main__":
    unittest.main()
