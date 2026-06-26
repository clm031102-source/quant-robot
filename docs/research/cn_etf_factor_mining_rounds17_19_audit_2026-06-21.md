# CN ETF Factor Mining Rounds 17-19 Audit

Date: 2026-06-21

## Scope

This audit covers the three work rounds after the Round 14-16 review:

- Round 17: CN ETF public trend-volume factor grid
- Round 18: risk overlay for the best Round 17 ETF candidate
- Round 19: walk-forward validation for the Round 18 candidate

This implements the standing rule: every 3 rounds, review the prior work and adjust direction.

## What Was Tested

Round 17 moved back toward the practical ETF-rotation objective.

Families tested:

- SuperTrend with volume confirmation
- smart-money style amount pressure
- OBV breakout
- anti / contrarian variants

Round 18 did not add a new factor. It changed only target gross exposure on the best Round 17 lead.

Round 19 froze the best Round 18 candidate and ran walk-forward validation.

## Results

| Round | New factor names | Main result | Promotable |
|---:|---:|---|---:|
| 17 | 0 | `smart_money_trend_20_top2_cost5_reb5_regime120` became a research lead, but full grid had 0 approved cases | 0 |
| 18 | 0 | 0.6 exposure version passed full-sample gate: total return 0.3553, relative return 0.0379, Sharpe 0.5739, max DD -0.1993 | 0 |
| 19 | 0 | Same candidate failed walk-forward: 0 accepted folds out of 42 | 0 |

Net outcome:

- New unique factor names: 0
- Full-sample validation candidates: 1
- Walk-forward accepted candidates: 0
- Paper/live candidates: 0

## Audit Judgment

The direction change from CN stock TopN formula mining to ETF rotation was correct.

The candidate quality was still not sufficient:

- The apparent full-sample win was not stable out of sample.
- The ETF universe was too small for robust fold-level IC inference.
- The regime filter reduced bad exposure but also created too few fold-level trades.
- Full-sample drawdown control did not translate into walk-forward profitability.

The useful lesson is procedural:

- A same-sample approval is not a success.
- Walk-forward must be the gate before calling a factor useful.
- Low trade count should block promotion even when summary returns look good.

## Why The Work Still Looked Bad

The recent factors were not bad because the code was unable to compute indicators.

They were bad because the research process kept exposing the same structural problem:

- signal IC sometimes appears,
- portfolio translation is weak,
- costs and drawdowns remove the apparent edge,
- walk-forward validation rejects the remaining candidate.

That is exactly the failure pattern expected from public technical signals when the universe is small and the parameter set is discovered from the same history.

## Direction Change

Stop:

- Mutating `smart_money_trend_20_top2_cost5_reb5_regime120` exposure again.
- Treating full-sample approval as enough evidence.
- Running small ETF grids that produce too few fold-level trades.

Continue:

- ETF rotation alignment, because it matches the project's intended practical use.
- Public, explainable indicator families, because they reduce blind search.
- Strict cost, capacity, drawdown, and walk-forward gates.

Next:

1. Audit available CN ETF data coverage and expand the ETF universe if possible.
2. Build an ETF validation preflight that rejects configs likely to produce too few OOS trades.
3. Mine broader, more liquid ETF rotation families:
   - relative strength / dual momentum,
   - volatility-adjusted momentum,
   - drawdown recovery,
   - low-volatility trend,
   - market breadth / risk-on filters,
   - trend plus crash-protection overlays.
4. For CN stock work, use stock signals as upstream theme / risk signals only when they can improve ETF allocation, not as endless TopN stock-picking variants.

## Public Method References To Keep Using

The next cycle should keep borrowing process discipline from established public quant tooling:

- Qlib-style train / test workflow and experiment tracking
- Alphalens-style IC, quantile, turnover, and factor decay checks
- Formulaic-alpha templates only when paired with economic intuition and multiple-testing discipline
- MlFinLab-style walk-forward, purging / embargo thinking, and backtest-overfitting skepticism

## Revised Plan For The Next 3 Rounds

Round 20:

- Add ETF validation preflight for minimum expected fold trades / universe size.
- Use it to prevent low-power walk-forward runs.
- After Round 20, perform the required 10-round GitHub sync because the last sync was Round 10.

Round 21:

- Mine a new ETF rotation family with clear public-market intuition, starting from relative strength plus volatility adjustment.

Round 22:

- Run full-sample and immediate walk-forward on the best Round 21 candidate, with parameters frozen before validation.

## Conclusion

Rounds 17-19 produced no promotable factor.

The best candidate was a false positive: it passed full-sample risk overlay but failed walk-forward completely.

The process is improving because weak candidates are being killed faster. The next improvement is to prevent low-trade-count ETF validations before they run and to mine families that have enough turnover and economic rationale to survive out-of-sample testing.
