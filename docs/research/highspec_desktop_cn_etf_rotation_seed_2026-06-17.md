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

## Composite Seed Walk-Forward

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_walk_forward.py --config configs\walk_forward_tushare_cn_etf_composite_seed_20260617.json --source processed-bars --data-root data\processed\tushare_etf_full --allow-no-accepted
```

New factor construction:

- `trend_resilience_60`: cross-sectional rank blend of 60-day momentum, drawdown resilience, and liquidity resilience.
- `risk_confirmed_momentum_60`: rank blend of risk-adjusted momentum, drawdown resilience, and amount stability.
- `defensive_reversal_60`: rank blend of reversal, low downside volatility, and liquidity resilience.
- `liquidity_confirmed_breakout_60`: rank blend of momentum, amount stability, and liquidity resilience.

Result:

- Cases: 4
- Accepted: 0
- Rejected: 4
- Folds: 4

Top aggregate rows:

- `liquidity_confirmed_breakout_60`: rejected. Mean OOS Sharpe 2.5162, relative return 0.1763, max drawdown -0.0770, capacity-limited trades 1, but only 1 accepted fold and adjusted IC p-value 1.0.
- `trend_resilience_60`: rejected. Mean OOS Sharpe 1.0255, relative return 0.1375, max drawdown -0.0927, no capacity-limited trades, but 0 accepted folds and adjusted IC p-value 1.0.
- `risk_confirmed_momentum_60`: rejected. Mean OOS Sharpe 0.4472, relative return 0.1421, max drawdown -0.0683, capacity-limited trades 1, but 0 accepted folds and adjusted IC p-value 1.0.
- `defensive_reversal_60`: rejected. Mean OOS Sharpe -10.5622 despite shallow drawdown; only 1 accepted fold and adjusted IC p-value 1.0.

Fold diagnostics:

- Fold 1 and fold 2 were rejected for insufficient OOS trades, with 4 and 14 trades per case.
- Fold 3 completed but failed Sharpe and/or relative-return gates.
- Fold 4 accepted `liquidity_confirmed_breakout_60` and `defensive_reversal_60`, but this is a recent-period spark, not a full-history signal.

Conclusion: composite construction improved the best aggregate row relative to standalone defensive factors, but it still fails the required full-history stability and multiple-testing gates. Keep `liquidity_confirmed_breakout_60` as an observation candidate only, not as a promoted paper signal.

## Mature-Universe Diagnostic

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_walk_forward.py --config configs\walk_forward_tushare_cn_etf_composite_mature_diagnostic_20260617.json --source processed-bars --data-root data\processed\tushare_etf_full --allow-no-accepted
```

Diagnostic scope:

- Same four composite factors as the full-history composite seed.
- Explicit validation bar window: `bar_start_date = 2015-01-01`.
- This is a diagnostic slice only. It is not promotion evidence and does not replace the full-history gate.

Result:

- Cases: 4
- Accepted: 0
- Rejected: 4
- Folds: 4

Top aggregate rows:

- `trend_resilience_60`: rejected. Accepted folds 1, mean OOS Sharpe -1.1531, relative return -0.0568, max drawdown -0.1880, capacity-limited trades 2, adjusted IC p-value 1.0.
- `risk_confirmed_momentum_60`: rejected. Accepted folds 0, mean OOS Sharpe -1.4185, relative return -0.0310, max drawdown -0.0604, capacity-limited trades 1, adjusted IC p-value 1.0.
- `liquidity_confirmed_breakout_60`: rejected. Accepted folds 0, mean OOS Sharpe -1.5509, relative return -0.0743, max drawdown -0.1878, capacity-limited trades 1, adjusted IC p-value 1.0.
- `defensive_reversal_60`: rejected. Accepted folds 0, mean OOS Sharpe -4.5771, relative return -0.0557, max drawdown -0.0672, capacity-limited trades 22, adjusted IC p-value 1.0.

Interpretation: removing the early sparse ETF era did not rescue the composite factors. The full-history rejection is therefore not only an early-universe artifact; these rank blends also fail mature-window OOS Sharpe, relative-return, stability, and IC-significance checks.

## Structure-Shift Seed Walk-Forward

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_walk_forward.py --config configs\walk_forward_tushare_cn_etf_structure_shift_20260617.json --source processed-bars --data-root data\processed\tushare_etf_full --allow-no-accepted
```

New factor families:

- Cross-ETF dispersion leadership: `market_relative_strength_60`, `momentum_dispersion_breakout_60`
- Crash/recovery asymmetry: `crash_recovery_60`, `recovery_quality_60`
- Demand-pressure proxies from ETF traded amount: `demand_pressure_60`, `quiet_accumulation_60`

Result:

- Cases: 6
- Accepted: 0
- Rejected: 6
- Folds: 4

Top aggregate rows:

- `crash_recovery_60`: rejected. Accepted folds 1, mean OOS Sharpe 1.6739, relative return 0.1295, max drawdown -0.0918, capacity-limited trades 4, max participation 0.1822, adjusted IC p-value 1.0.
- `recovery_quality_60`: rejected. Accepted folds 0, mean OOS Sharpe 1.2874, relative return 0.1581, max drawdown -0.0402, capacity-limited trades 3, max participation 0.1472, adjusted IC p-value 1.0.
- `market_relative_strength_60`: rejected. Accepted folds 0, mean OOS Sharpe 1.2686, relative return 0.1262, max drawdown -0.1876, capacity-limited trades 4, max participation 0.2960, adjusted IC p-value 1.0.
- `momentum_dispersion_breakout_60`: rejected with the same top2 selections as `market_relative_strength_60`; the z-score transform was rank-equivalent for this grid.
- `demand_pressure_60`: rejected. Accepted folds 1, mean OOS Sharpe 0.4380, relative return 0.1120, max drawdown -0.0774, capacity-limited trades 7, max participation 0.5287, adjusted IC p-value 1.0.
- `quiet_accumulation_60`: rejected. Accepted folds 0, mean OOS Sharpe 0.4356, relative return 0.1173, max drawdown -0.0892, capacity-limited trades 3, max participation 4000.0, adjusted IC p-value 1.0.

Fold diagnostics:

- Fold 1 and fold 2 again failed on insufficient OOS trades, with 4 and 14 trades per case.
- Fold 3 completed but all factors failed Sharpe and/or relative-return gates.
- Fold 4 accepted only `crash_recovery_60` and `demand_pressure_60`; this is still a recent-fold spark and not enough for promotion.
- `quiet_accumulation_60` has a severe capacity warning from extreme participation in one completed fold. Treat it as a rejected demand/liquidity proxy, not as a candidate for cost tuning.

Conclusion: structurally different price/liquidity state factors improved the appearance of crash-recovery rows, but no factor passed full-history stability, adjusted IC significance, or accepted-fold requirements. Do not promote any structure-shift factor.

## Liquidity-Gated Structure Diagnostic

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_walk_forward.py --config configs\walk_forward_tushare_cn_etf_liquidity_gated_structure_20260617.json --source processed-bars --data-root data\processed\tushare_etf_full --allow-no-accepted
```

Diagnostic construction:

- `average_amount_60`: rolling average traded amount, log scaled.
- `liquid_*_60` variants: keep the source factor only when same-date ETF rolling traded amount rank and liquidity-resilience rank are both above the cross-sectional median.
- This tests whether a point-in-time liquidity gate fixes the capacity and sparse-tradability failure modes. It is not a promotion shortcut.

Result:

- Cases: 6
- Accepted: 0
- Rejected: 6
- Folds: 4

Top aggregate rows:

- `liquid_recovery_quality_60`: rejected. Accepted folds 1, mean OOS Sharpe 1.5113, relative return 0.1628, max drawdown -0.0383, capacity-limited trades 3, max participation 0.1472, adjusted IC p-value 1.0.
- `liquid_crash_recovery_60`: rejected. Accepted folds 1, mean OOS Sharpe 1.6768, relative return 0.1296, max drawdown -0.0918, capacity-limited trades 3, max participation 0.1822, adjusted IC p-value 1.0.
- `liquid_market_relative_strength_60`: rejected. Accepted folds 0, mean OOS Sharpe 1.2686, relative return 0.1262, max drawdown -0.1876, capacity-limited trades 4, max participation 0.2960, adjusted IC p-value 1.0.
- `liquid_demand_pressure_60`: rejected. Accepted folds 0, mean OOS Sharpe 0.3660, relative return 0.1109, max drawdown -0.0774, capacity-limited trades 4, max participation 0.4557, adjusted IC p-value 1.0.
- `liquid_quiet_accumulation_60`: rejected. Accepted folds 0, mean OOS Sharpe 0.4356, relative return 0.1173, max drawdown -0.0892, capacity-limited trades 3, max participation 4000.0, adjusted IC p-value 1.0.
- `average_amount_60`: rejected. Accepted folds 0, mean OOS Sharpe -9.1406, relative return 0.1491, max drawdown -0.0538, capacity-limited trades 0, max participation 0.0048, adjusted IC p-value 1.0.

Interpretation: the liquidity gate reduced some average participation optics but did not solve the tail-capacity problem. A relative median gate is too weak for ETF rotation; future capacity controls need absolute rolling amount, participation feasibility, or minimum tradable notional constraints before ranking.

## Next Batch

Do not rescue these seeds by widening topN, lowering costs, or cherry-picking the 2023-2024 fold. The next batch should address the repeated failure modes directly:

- Add ETF-age and tradable-universe maturity controls to separate "too few live ETF members" from true factor failure.
- Avoid rank-equivalent duplicates such as raw relative momentum versus its same-date z-score when the topN selection is identical.
- Replace relative liquidity gates with absolute rolling notional or ex-ante participation feasibility filters before demand-pressure proxies.
- Move toward ETF theme/industry breadth diffusion once a clean ETF theme map is available.
- Keep `CN` stock moneyflow out of primary selection; only revisit it as ETF-level breadth or theme diffusion after holdings/theme mapping is available.

Research remains paper-only: no broker connection, no account reads, no order placement, no live trading.
