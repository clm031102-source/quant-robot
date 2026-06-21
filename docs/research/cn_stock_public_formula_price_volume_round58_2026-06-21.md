# CN Stock Public Formula Price-Volume Round58 Audit

Date: 2026-06-21
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock cross-sectional alpha, not ETF rotation
Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Goal

Replay the public-formula price-volume family on the 2015-2025 long-cycle CN stock authority data, then require industry-neutral IC before spending more budget on portfolio backtests.

This round was meant to correct the previous failure mode: do not keep expanding a single raw factor family after strong IC but rejected long-only results. Public indicators are hypothesis sources only; they must translate into costed, capacity-aware portfolio returns before promotion.

## Inputs

- Config: `configs/experiment_grid_cn_stock_public_formula_price_volume_round58_20260621.json`
- Factor source: `public_formula_price_volume`
- Factors tested: 8
- Period: 2015-01-05 through 2025-12-31
- Forward horizon: 20 trading days
- Execution lag: 1
- Rebalance intervals: 5 and 10
- Top N: 100
- Cost: 10 bps
- Regime lookback: 120
- Portfolio value: 1,000,000
- Max participation rate: 1%

## Industry-Neutral IC Gate

Output: `data/reports/industry_neutral_ic_audit_public_formula_price_volume_round58_20260621`

- Input rows: 66,539,560
- Date-factor rows: 21,168
- Factors classified as industry-neutral signal: 8 / 8
- Industry-exposure dominated factors: 0 / 8
- Weak or unproven factors: 0 / 8
- Missing industry rows: 1,059,978

Top neutral IC readings:

| Factor | Overall Rank IC | Overall t | Neutral Rank IC | Neutral t | Neutral retention |
|---|---:|---:|---:|---:|---:|
| `formula_volume_contraction_reversal_20` | 0.0844 | 31.68 | 0.0910 | 49.41 | 1.08 |
| `formula_pv_corr_reversal_20` | 0.0770 | 32.06 | 0.0879 | 49.86 | 1.14 |
| `formula_range_contraction_breakout_20` | 0.0639 | 16.52 | 0.0787 | 28.84 | 1.23 |
| `formula_volume_contraction_momentum_confirmed_20_60` | 0.0504 | 20.57 | 0.0739 | 37.77 | 1.47 |
| `formula_pv_corr_momentum_confirmed_20_60` | 0.0371 | 14.81 | 0.0637 | 30.61 | 1.71 |

Interpretation: this family is not industry-only noise. The IC survives industry neutralization, so the family is worth a portfolio-construction diagnostic. The missing industry metadata is still a promotion blocker and must be repaired before any promotion review.

## Industry-Neutral Portfolio Gate

Output: `data/reports/industry_neutral_portfolio_public_formula_price_volume_round58_20260621`

- Cases: 16
- Approved: 0
- Rejected: 16
- Capacity-limited cases: 10
- Best total return: 35.48%
- Best overlap-adjusted Sharpe: 0.1771
- Best relative return: -23.3827

Best case:

- Case: `CN_formula_pv_corr_reversal_20_top100_cost10_reb5_regime120_industry_neutral`
- Total return: 35.48%
- Annualized return: 2.15%
- Sharpe: 0.3134
- Overlap-adjusted Sharpe: 0.1771
- Max drawdown: -26.71%
- Win rate: 46.87%
- Relative return: -23.3827
- Capacity-limited trades: 0
- Mean rank IC: 0.0773
- Rank IC t-stat: 11.02
- Tail mean rank IC: 0.0133
- Decision: rejected, `relative_return_below_threshold`

## Decision

- Promotable factors: 0
- Paper-ready factors: 0
- Research leads: 1
- Rejected portfolio cases: 16

Research lead:

- `formula_pv_corr_reversal_20`, rebalance 5, industry-neutral top 100

Why it is a lead:

- Strong long-cycle IC.
- Strong industry-neutral IC.
- Positive absolute long-cycle portfolio return.
- No capacity-limited trades in the best case.

Why it is not useful yet:

- Relative return is deeply below the benchmark.
- Overlap-adjusted Sharpe is only 0.1771.
- Win rate is below 50%.
- Drawdown is still large at -26.71%.
- The strategy converts cross-sectional prediction into weak realized portfolio returns.

## Failure Analysis

The factor family appears to rank stocks correctly on average, but the current portfolio translation is poor. The main failure is not signal discovery; it is signal monetization:

- top-N long-only exposure is too benchmark-like and does not capture enough spread;
- rebalance/cost structure consumes weak realized edge;
- tail IC is much weaker than full-period IC;
- broad formula expansion would create multiple-testing waste;
- industry metadata gaps prevent promotion-grade review.

## Next Direction

Set the next direction to `pv_corr_reversal_cash_regime_overlay_and_streaming_cache_batch`.

Required next-round constraints:

- Work only from the cleanest Round58 lead first: `formula_pv_corr_reversal_20`.
- Do not expand the full public-formula family until the portfolio conversion problem is understood.
- Test cash/risk-off overlay and drawdown gate before changing factor parameters.
- Keep rebalance and factor parameters frozen unless a pre-registered sensitivity test is explicitly part of the batch.
- Repair or quantify industry metadata coverage before any promotion claim.
- Add or use chunked/streaming factor-matrix audit paths before another memory-heavy 66M-row neutral run.

## Project Status

This round improved process quality but did not produce a tradable factor. It narrowed the next work from blind public-indicator mining to one specific signal-translation problem: `pv_corr_reversal_20` has real ranking evidence, but the portfolio needs better risk allocation, benchmark-relative construction, or rejection after a focused conversion audit.
