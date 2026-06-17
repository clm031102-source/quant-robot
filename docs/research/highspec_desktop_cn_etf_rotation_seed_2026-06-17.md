# Highspec Desktop CN ETF Rotation Seed - 2026-06-17

Machine: `highspec_desktop`
Task: `factor_batch`
Branch: `codex/factor-batch-cn-etf-20260617`

## Startup And Data Gate

- Quant PM startup gate: ready.
- Research-family scheduler: ready, primary market `CN_ETF`, direct `CN` stock moneyflow remains `auxiliary_only`.
- Tushare CN_ETF bars: 2,987,045 rows, 2,665 assets, 2005-01-04 to 2026-06-16.
- Rotation membership: 2,987,045 point-in-time rows, 619,524 member rows, 1,049 member assets.
- Data-quality audit: 16,522 missing date rows across 1,154 assets, 0 zero-volume rows. The readiness gate treats these as an explicit warning for full-history listed-fund data, not as a silent pass.
- Auxiliary Tushare permissions: `etf_share_size` and `fund_portfolio` are unavailable for the current token, so share/size pressure and holdings-based moneyflow baskets are not primary runnable families yet.

## Config Fix

The full-history Tushare CN_ETF walk-forward config used `CN_ETF_XSHG_510300` as benchmark, but that ETF starts on 2012-05-28 in the local data. Early full-history folds therefore failed with `Benchmark asset is not present in bars`.

The Tushare full-history rotation benchmark was changed to `CN_ETF_XSHG_510050`, which is present from 2005-02-23 through 2026-06-16.

## Seed Walk-Forward

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_walk_forward.py --config configs\walk_forward_tushare_cn_etf_rotation_seed_20260617.json --source processed-bars --data-root data\processed\tushare_etf_full --allow-no-accepted
```

Seed families:

- Price/trend/reversal: `momentum_60`, `reversal_20`, `risk_adjusted_momentum_60`
- Liquidity/capacity: `liquidity_60`
- Volatility/regime: `volatility_60`

Controls:

- Execution lag: T+1
- Cost: 10 bps grid cost, 2 bps commission, 3 bps slippage, 5 bps market impact
- Capacity: 5% max participation, 1,000,000 portfolio value
- Rotation membership: required
- Walk-forward: 4 rolling folds, 756 train days, 252 test days, 1,260 day step
- Multiple testing: alpha 0.01

Result:

- Cases: 5
- Accepted: 0
- Rejected: 5
- Folds: 4

Interpretation:

- Early folds were too sparse for the current top2/rebalance10/min20-trade gate: fold 1 had 4 OOS trades per case, fold 2 had 14.
- Fold 3 rejected on OOS Sharpe and/or relative return.
- Fold 4 had accepted single-fold rows for liquidity, reversal, risk-adjusted momentum, and volatility, but this is not enough. The promotion-style requirement is at least 3 accepted folds plus adjusted IC significance.
- All five aggregate rows failed adjusted IC significance after multiple-testing correction.

Conclusion: this seed does not promote any factor. The useful finding is structural: simple price/liquidity/volatility representatives show a recent-period spark but do not survive full-history rolling stability, early-universe sparsity, and IC-significance gates.

## Defensive Seed Walk-Forward

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_walk_forward.py --config configs\walk_forward_tushare_cn_etf_defensive_seed_20260617.json --source processed-bars --data-root data\processed\tushare_etf_full --allow-no-accepted
```

Seed families:

- Volatility/drawdown state: `low_volatility_60`, `low_downside_volatility_60`, `drawdown_resilience_60`
- Liquidity/capacity: `liquidity_resilience_60`, `amount_stability_60`

Result:

- Cases: 5
- Accepted: 0
- Rejected: 5
- Folds: 4

Top aggregate rows:

- `drawdown_resilience_60`: rejected. Mean OOS Sharpe 0.7901, relative return 0.1628, max drawdown -0.0429, capacity-limited trades 3, but 0 accepted folds and adjusted IC p-value 1.0.
- `amount_stability_60`: rejected. Mean OOS Sharpe 1.1063, relative return 0.1428, max drawdown -0.0692, capacity-limited trades 0, but only 1 accepted fold and adjusted IC p-value 1.0.
- `liquidity_resilience_60`: rejected. Mean OOS Sharpe 0.1813, relative return 0.1596, max drawdown -0.0158, capacity-limited trades 3, but only 1 accepted fold and adjusted IC p-value 1.0.
- `low_volatility_60` and `low_downside_volatility_60`: rejected with very weak aggregate Sharpe despite shallow drawdowns.

Conclusion: the defensive factors improve drawdown/capacity optics in places but do not pass full-history stability or IC gates. Keep `drawdown_resilience_60` and `amount_stability_60` as ingredients for a future composite, not as standalone signals.

## Next Batch

Do not rescue these seeds by widening topN, lowering costs, or cherry-picking the 2023-2024 fold. The next batch should be structurally different:

- Add ETF-age and tradable-universe maturity controls to separate "too few live ETF members" from true factor failure.
- Try composite features that combine defensive state with price confirmation instead of using defensive state as a standalone rank.
- Keep `CN` stock moneyflow out of primary selection; only revisit it as ETF-level breadth or theme diffusion after holdings/theme mapping is available.

Research remains paper-only: no broker connection, no account reads, no order placement, no live trading.
