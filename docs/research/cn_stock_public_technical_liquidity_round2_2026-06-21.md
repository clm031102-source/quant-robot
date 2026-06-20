# CN Stock Public Technical Liquidity Round 2

- Date: 2026-06-21
- Machine: office_desktop
- Task: factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Round status: round 2 of the current 3-round review cycle
- Scope: CN A-share stock cross-sectional factors, not ETF rotation

## Purpose

Round 1 showed that public mean-reversion indicators had statistically visible IC, but standalone top100 portfolios were rejected by capacity, drawdown, and extreme-return risk. Round 2 tested whether a minimal liquidity-aware composite could reduce the capacity blocker without expanding the parameter search.

## Implementation

Added `public_technical_liquidity` factor source:

- `rsi_reversal_liquid_14_20`
- `bollinger_reversal_liquid_20`

Design:

- Uses only bars: `adj_close`, `high`, `low`, and `amount`.
- Uses past-only RSI/Bollinger signals.
- Adds 20-day average traded amount rank.
- Excludes rows below the 60th percentile by 20-day traded amount.
- Excludes rows with absolute 1-day return above 50%.
- Blends 75% mean-reversion signal and 25% liquidity z-score.

## Verification

- Red-green tests passed for the factor source, research pipeline source dispatch, experiment-grid precompute, and project-audit registry.
- The implementation is bars-only and does not use moneyflow or daily-basic inputs.

## Long-Cycle Fast Diagnostic

Command:

```powershell
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_stock_public_technical_liquidity_fast_20260621.json --source authority-processed-bars --authority-bars-config configs\cn_stock_authority_bars_2015_2025.json --allow-review-required-data-manifest
```

Result summary:

| factor | annualized return | Sharpe | overlap-adjusted Sharpe | max drawdown | win rate | mean rank IC | rank IC p-value | capacity-limited trades | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `bollinger_reversal_liquid_20` | 20.97% | 0.393 | 0.211 | -83.70% | 43.70% | 0.0568 | 4.71e-23 | 10 | rejected |
| `rsi_reversal_liquid_14_20` | 18.61% | 0.348 | 0.210 | -85.01% | 43.38% | 0.0559 | 1.68e-20 | 12 | rejected |

Key changes versus Round 1:

- Capacity-limited trades fell sharply, from thousands in standalone public technical factors to 10-12.
- IC remained positive and statistically significant.
- Tail IC remained significantly negative.
- Max drawdown worsened to roughly -84% to -85%.
- Both candidates still underperformed the benchmark on relative return.

## Interpretation

Round 2 solved much of the capacity symptom but not the economic problem. The signal still buys names that can have severe downside after oversold conditions. The long-short spread is negative, which means the cross-sectional ranking is not translating into clean top-vs-bottom behavior.

No factor from Round 2 is promotable or paper-ready.

## Next Direction

Round 3 should be a tail-risk and drawdown-control round, not another mean-reversion expansion:

- Add a fast pre-walk-forward gate that rejects candidates with negative tail IC, extreme trade return flags, or max drawdown worse than 50%.
- Test downside-volatility or range-position filters as gates, not as additional ranking knobs.
- Consider reversing or neutralizing the top/bottom interpretation only if IC, long-short spread, and tail IC agree.
- Do not run the heavy walk-forward grid unless the fast long-cycle gate clears first.
