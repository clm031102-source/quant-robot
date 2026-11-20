"""Run rolling out-of-sample walk-forward validation on cached market data."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from quant_robot.config.settings import CostConfig, RiskConfig, StrategySpec, resolve_data_root
from quant_robot.storage.atomic import atomic_write_json
from quant_robot.storage.market_cache import MarketCache
from quant_robot.validation.walk_forward import run_walk_forward


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run rolling out-of-sample walk-forward validation.")
    parser.add_argument("--market", default="CN_ETF", choices=("CN_ETF", "US_ETF", "CRYPTO"))
    parser.add_argument("--train-sessions", type=int, default=None)
    parser.add_argument("--test-sessions", type=int, default=None)
    parser.add_argument("--step-sessions", type=int, default=None)
    parser.add_argument("--data-root", help="Override data directory")
    args = parser.parse_args(argv)

    data_root = Path(args.data_root) if args.data_root else resolve_data_root(ROOT)
    cache = MarketCache(data_root / "market_cache")

    if args.market == "CN_ETF":
        symbols = ["510300.SH", "510500.SH", "159915.SZ", "510880.SH", "518880.SH", "513100.SH"]
        currency, lot_size, min_trade_notional, init_cash = "CNY", 100.0, 0.0, 10000.0
        cost = CostConfig(commission_bps=1.0, minimum_commission=5.0, slippage_bps=5.0)
        defensive = None
        train_sessions = args.train_sessions or 252
        test_sessions = args.test_sessions or 126
        step_sessions = args.step_sessions or 126
        candidates = {
            "dual_mom_40_ma100": StrategySpec(kind="dual_momentum", rebalance_frequency="monthly", lookback_days=40, trend_ma_days=100, top_n=2, defensive_symbol=defensive),
            "dual_mom_60_ma120": StrategySpec(kind="dual_momentum", rebalance_frequency="monthly", lookback_days=60, trend_ma_days=120, top_n=2, defensive_symbol=defensive),
            "risk_parity_trend": StrategySpec(kind="risk_parity_trend", rebalance_frequency="monthly", rebalance_band=0.06, vol_lookback_days=60, trend_ma_days=120, defensive_symbol=defensive),
            "fixed_equal_band8": StrategySpec(kind="fixed_allocation", rebalance_frequency="quarterly", rebalance_band=0.08),
            "passive_drift": StrategySpec(kind="passive_drift", rebalance_frequency="never", rebalance_band=0.0),
        }
        risk = RiskConfig(max_drawdown_halt=0.35, cooldown_sessions=5)
    elif args.market == "US_ETF":
        symbols = ["SPYM", "EFA", "IEF", "GLDM"]
        currency, lot_size, min_trade_notional, init_cash = "USD", 1.0, 0.0, 1000.0
        cost = CostConfig(commission_bps=0.0, minimum_commission=1.0, slippage_bps=10.0)
        defensive = "IEF"
        train_sessions = args.train_sessions or 252
        test_sessions = args.test_sessions or 126
        step_sessions = args.step_sessions or 126
        candidates = {
            "dual_mom_40_ma100": StrategySpec(kind="dual_momentum", rebalance_frequency="monthly", lookback_days=40, trend_ma_days=100, top_n=2, defensive_symbol=defensive),
            "dual_mom_60_ma120": StrategySpec(kind="dual_momentum", rebalance_frequency="monthly", lookback_days=60, trend_ma_days=120, top_n=2, defensive_symbol=defensive),
            "risk_parity_trend": StrategySpec(kind="risk_parity_trend", rebalance_frequency="monthly", rebalance_band=0.06, vol_lookback_days=60, trend_ma_days=120, defensive_symbol=defensive),
            "fixed_equal_band8": StrategySpec(kind="fixed_allocation", rebalance_frequency="quarterly", rebalance_band=0.08),
            "passive_drift": StrategySpec(kind="passive_drift", rebalance_frequency="never", rebalance_band=0.0),
        }
        risk = RiskConfig(max_drawdown_halt=0.35, cooldown_sessions=5)
    else:
        symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"]
        currency, lot_size, min_trade_notional, init_cash = "USD", 0.0001, 10.0, 1000.0
        cost = CostConfig(commission_bps=10.0, minimum_commission=0.0, slippage_bps=10.0)
        train_sessions = args.train_sessions or 365
        test_sessions = args.test_sessions or 180
        step_sessions = args.step_sessions or 180
        candidates = {
            "crypto_trend_vol_35": StrategySpec(
                kind="crypto_trend_vol",
                rebalance_frequency="weekly",
                rebalance_band=0.06,
                lookback_days=40,
                trend_ma_days=60,
                vol_lookback_days=30,
                target_volatility=0.35,
                top_n=2,
            ),
            "crypto_trend_vol_50": StrategySpec(
                kind="crypto_trend_vol",
                rebalance_frequency="weekly",
                rebalance_band=0.06,
                lookback_days=30,
                trend_ma_days=50,
                vol_lookback_days=30,
                target_volatility=0.50,
                top_n=2,
            ),
            "crypto_dual_mom_40_60": StrategySpec(
                kind="dual_momentum",
                rebalance_frequency="weekly",
                rebalance_band=0.08,
                lookback_days=40,
                trend_ma_days=60,
                top_n=2,
                defensive_symbol=None,
            ),
            "crypto_rp_trend_60": StrategySpec(
                kind="risk_parity_trend",
                rebalance_frequency="weekly",
                rebalance_band=0.08,
                vol_lookback_days=30,
                trend_ma_days=60,
                defensive_symbol=None,
            ),
            "crypto_passive_drift": StrategySpec(kind="passive_drift", rebalance_frequency="never", rebalance_band=0.0),
        }
        risk = RiskConfig(max_drawdown_halt=0.45, cooldown_sessions=7)

    bars = cache.load_universe(args.market, symbols)
    if bars.empty:
        raise SystemExit(f"No cached bars for {args.market}. Run scripts/run_update_data.py first.")

    result = run_walk_forward(
        bars,
        market=args.market,
        currency=currency,
        symbols=symbols,
        candidates=candidates,
        cost=cost,
        risk=risk,
        initial_cash=init_cash,
        lot_size=lot_size,
        min_trade_notional=min_trade_notional,
        train_sessions=train_sessions,
        test_sessions=test_sessions,
        step_sessions=step_sessions,
    )
    out_file = data_root / "reports" / "walk_forward" / f"{args.market.lower()}_walk_forward.json"
    atomic_write_json(out_file, result.to_dict())
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
