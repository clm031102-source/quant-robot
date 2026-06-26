# CN Stock Public Technical Tail-Guard Round 3

- Date: 2026-06-21
- Machine: office_desktop
- Task: factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Round status: round 3 of the current 3-round review cycle
- Scope: CN A-share stock cross-sectional factors, not ETF rotation

## Purpose

Rounds 1-2 showed that public mean-reversion indicators can produce statistically visible IC, but standalone and liquidity-aware versions still failed on drawdown, capacity, and tail IC. Round 3 tested whether explicit tail-risk filters could make the same economic idea safer before any walk-forward budget is spent.

## Implementation

Added `public_technical_tail_guard` factor source:

- `rsi_reversal_liquid_low_tail_14_20`
- `bollinger_reversal_liquid_low_tail_20`

Design:

- Uses only bars: `adj_close`, `high`, `low`, and `amount`.
- Uses past-only RSI/Bollinger mean-reversion signals.
- Requires 20-day traded amount rank at or above the median.
- Excludes rows with absolute 1-day return above 50%.
- Excludes the worst downside-volatility group.
- Excludes names too close to their 20-day rolling low to avoid falling-knife entries.
- Adds a small low-downside-volatility preference to the score.

## Verification

- Red-green tests passed for the factor source, research pipeline dispatch, experiment-grid precompute, and project-audit registry.
- The implementation is bars-only and does not use moneyflow or daily-basic inputs.

## Long-Cycle Fast Diagnostic

Command:

```powershell
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_stock_public_technical_tail_guard_fast_20260621.json --source authority-processed-bars --authority-bars-config configs\cn_stock_authority_bars_2015_2025.json --allow-review-required-data-manifest
```

Result summary:

| factor | annualized return | Sharpe | overlap-adjusted Sharpe | max drawdown | win rate | mean rank IC | rank IC p-value | tail mean IC | tail IC p-value | capacity-limited trades | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `bollinger_reversal_liquid_low_tail_20` | 23.49% | 0.408 | 0.214 | -79.45% | 44.54% | 0.0312 | 8.73e-08 | -0.0174 | 1.41e-03 | 5 | rejected |
| `rsi_reversal_liquid_low_tail_14_20` | 22.82% | 0.412 | 0.213 | -79.80% | 45.09% | 0.0317 | 2.17e-07 | -0.0222 | 4.06e-05 | 2 | rejected |

Key changes versus Round 2:

- Capacity-limited trades improved again, from 10-12 to 2-5.
- Max drawdown improved slightly, from roughly -84%/-85% to roughly -79%/-80%.
- Tail IC stayed significantly negative.
- Long-cycle fast gate still rejected both candidates.

## Interpretation

Round 3 confirmed that the public technical mean-reversion family has a persistent translation problem:

- Cross-sectional IC is positive.
- Tail IC is negative.
- The top-ranked portfolio still suffers unacceptable drawdowns.
- Capacity filters help mechanics but do not create a deployable edge.

No Round 3 factor is promotable or paper-ready.

## Decision

Do not continue expanding standalone public technical mean-reversion factors. Keep the reusable source code because it is useful as a component library, but stop treating this family as a standalone alpha direction until a different portfolio construction or orthogonal input family changes the evidence.
