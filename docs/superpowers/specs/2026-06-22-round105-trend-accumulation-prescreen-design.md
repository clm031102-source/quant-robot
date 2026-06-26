# Round105 Trend Accumulation Prescreen Design

## Context

Round104 pre-registered ten CN stock trend, breakout, OBV-style, and amount accumulation candidates after the Round103 audit found the Bollinger/RSI/Donchian/low-volatility reversal lead to be highly redundant. Round105 must not convert those candidates into a portfolio grid yet. It must first run the same long-cycle Alphalens-style IC, quintile, turnover, multiple-testing, and capacity prescreen used in Round102 so results stay comparable across families.

## Requirements

- Scope remains CN stock cross-sectional factor mining on office desktop data.
- The final 2026 holdout remains excluded unless explicitly enabled.
- Use the Round104 pre-registered factor names exactly.
- Compute signals from adjusted close, high, low, and amount only.
- Apply the same capacity-safe signal-date filters as Round102: amount and ADV20 above the minimum floor, plus an extreme one-day return exclusion.
- Report IC, ICIR, IC t-stat, p-value, FDR/Bonferroni flags, quintile spread, monotonicity, top-quantile turnover, coverage, and blockers.
- This stage can only create research leads. Promotion and portfolio backtests remain blocked until deduplication and later walk-forward/cost/capacity/regime gates.

## Architecture

Reuse the Round102 bars loader, label generator, summary function, CSV/JSON rendering helpers, and promotion policy where possible. Add a new focused module that only builds the trend/amount accumulation factor matrix, passes it into the shared summary function, then rewrites stage names and file names for Round105. This avoids diverging evaluation logic and keeps any comparison between Round102 and Round105 clean.

## Factor Feature Set

The feature matrix will compute per-asset rolling primitives, then cross-sectionally z-score them by date:

- `volume_weighted_return_20`
- `return_efficiency_20`
- `price_breakout_20`
- `amount_trend_20_60`
- `money_pressure_20`
- `skip5_momentum_20`
- `obv_slope_20`
- `momentum_20`
- `momentum_60`
- `close_to_20d_high`
- `amount_zscore_20`
- `amount_percentile_60`
- `accumulation_distribution_20`
- `amount_expansion_10_40`
- `log_adv20`

The ten candidate formulas follow the Round104 registration weights exactly enough for a controlled prescreen. Any candidate that fails should rotate family or proceed to dedup only if it clears the statistical lead gate; it should not receive parameter tuning in the same family.

## Testing

Add unit tests for:

- Factor matrix generation produces all ten Round104 names and excludes the old low-volatility reversal cluster names.
- Capacity filters keep signal rows above the minimum amount floor.
- Build flow excludes 2026 holdout data and blocks promotion.
- CLI writes JSON, Markdown, results CSV, and IC observation CSV.

Tests must be written and run before implementation to preserve the TDD proof.

## Self-Review

- No placeholders remain.
- Scope is one implementation unit: Round105 prescreen.
- No portfolio optimization, live boundary, broker path, or holdout tuning is included.
- The design uses existing project interfaces instead of inventing a second evaluator.
