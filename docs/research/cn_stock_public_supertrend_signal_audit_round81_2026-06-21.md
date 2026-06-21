# CN Stock Public SuperTrend Signal Audit Round81 - 2026-06-21

## Purpose

Round81 tested the pre-registered public SuperTrend/ATR-style family after the RSRS line was hibernated at the Round80 sync boundary.

This was a signal-direction and translation audit, not a promotion grid. The scope stayed CN A-share stock cross-sectional factor research, not CN ETF rotation and not live trading.

Safety boundary:

- research-to-review only;
- no broker connection;
- no live account read;
- no order placement;
- no automatic live trading.

## Setup

Config:

- `configs/experiment_grid_cn_stock_public_supertrend_round81_20260621.json`

Data and execution:

- Market: CN stocks.
- Period: 2015-01-05 through 2025-12-31.
- Factor source: `public_trend_volume`.
- Horizon: 20 trading days.
- Execution lag: 1.
- Rebalance interval: 10.
- Diagnostic portfolio: top100 only.
- Cost: 10 bps.
- Market impact: 20 bps.
- Portfolio value: 1,000,000.
- Target gross exposure: 0.6.
- Max participation: 1% ADV.
- Precomputed factor matrix reuse: enabled.

Pre-registered factors:

- `supertrend_volume_confirmed_10_3_20`
- `anti_supertrend_volume_confirmed_10_3_20`
- `supertrend_volume_capacity_strict_10_3_20`

## Direct Grid Result

Output:

- `data/reports/experiment_grid_cn_stock_public_supertrend_round81_20260621`

All 3 cases completed. All 3 were rejected.

| Factor | Total Return | Sharpe | Overlap Adj Sharpe | Max DD | Win Rate | RankIC | RankIC t | Tail RankIC | Capacity Limited Trades | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `supertrend_volume_confirmed_10_3_20` | -65.67% | -0.4707 | -0.3203 | -80.81% | 43.05% | -0.0659 | -9.28 | -0.0976 | 3 | rejected |
| `anti_supertrend_volume_confirmed_10_3_20` | -12.42% | -0.0269 | -0.0178 | -62.34% | 46.24% | 0.0659 | 9.28 | -0.0114 | 3 | rejected |
| `supertrend_volume_capacity_strict_10_3_20` | 0.56% | 0.0416 | 0.0281 | -47.75% | 43.76% | -0.0160 | -1.53 | -0.0151 | 0 | rejected |

Interpretation:

- Raw SuperTrend is materially wrong-way in this CN stock universe.
- The inverse side has strong positive RankIC, but direct TopN conversion still fails.
- Capacity-strict SuperTrend removes the capacity issue but does not create enough return or IC.
- No direct long-only SuperTrend row is promotable.

## IC-to-Portfolio Gap Audit

Output:

- `data/reports/ic_portfolio_gap_public_supertrend_round81_20260621`

Summary:

- Cases: 3.
- Strong RankIC cases: 2.
- IC-to-portfolio gap cases: 2.
- Exclusion signal cases: 1.
- Capacity-limited cases: 2.
- Promotable long-only cases: 0.

Translation status:

- `capacity_blocked`: 2.
- `weak_or_unproven_signal`: 1.

Recommended next actions from the audit:

- `bottom_quantile_exclusion_overlay`
- `stock_to_etf_breadth_bridge`
- `beta_sector_size_diagnostic`
- `stop_raw_formula_topn_sweeps`
- `capacity_filter_or_liquidity_gate`

Interpretation:

- `anti_supertrend_volume_confirmed_10_3_20` is not a buy-list factor.
- It is a possible exclusion or risk-filter lead because the rank signal is real but the long-only portfolio cannot monetize it.

## Industry-Neutral IC Audit

Output:

- `data/reports/industry_neutral_ic_public_supertrend_round81_20260621`

Summary:

- Factors: 3.
- Date-factor rows: 7,938.
- Industry-neutral signal factors: 2.
- Industry-exposure dominated factors: 1.
- Weak or unproven factors: 0.
- Missing industry rows: 80,639.

| Factor | Classification | Overall RankIC | Overall t | Neutral RankIC | Neutral t | Industry RankIC | Industry t | Retention |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `anti_supertrend_volume_confirmed_10_3_20` | industry-neutral signal | 0.0594 | 27.35 | 0.0888 | 46.29 | 0.0605 | 15.84 | 1.50 |
| `supertrend_volume_capacity_strict_10_3_20` | industry-neutral signal | -0.0223 | -6.91 | 0.0641 | 19.76 | -0.0249 | -4.38 | 2.88 |
| `supertrend_volume_confirmed_10_3_20` | industry-exposure dominated | -0.0594 | -27.35 | 0.0040 | 2.16 | -0.0605 | -15.84 | 0.07 |

Interpretation:

- The anti-SuperTrend signal is not merely an industry exposure artifact.
- The raw SuperTrend side is largely industry-exposure dominated and should not be promoted or expanded.
- Metadata coverage gaps remain a promotion blocker.

## Bottom-Exclusion Overlay Audit

Output:

- `data/reports/bottom_exclusion_overlay_public_supertrend_round81_20260621`

Summary:

- Factors: 3.
- Date-factor rows: 795.
- Bottom-exclusion candidate factors: 1.
- Weak or unproven exclusion factors: 2.
- Diagnostic only: true.

| Factor | Classification | Dates | Full Mean | Kept Mean | Bottom Mean | Overlay Excess | Overlay t | Positive Rate | Kept Compounded | Full Compounded | Bottom Compounded |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `anti_supertrend_volume_confirmed_10_3_20` | bottom-exclusion candidate | 265 | -0.2901% | -0.0153% | -1.4222% | 0.2749% | 7.00 | 68.82% | -62.65% | -82.43% | -99.33% |
| `supertrend_volume_capacity_strict_10_3_20` | weak or unproven | 265 | 0.2300% | 0.1900% | 0.4200% | -0.0400% | -0.81 | 48.66% | -20.73% | -9.66% | not promoted |
| `supertrend_volume_confirmed_10_3_20` | weak or unproven | 265 | -0.2900% | -0.4300% | 0.2800% | -0.1400% | -3.69 | 40.68% | -88.16% | -82.43% | not promoted |

Interpretation:

- `anti_supertrend_volume_confirmed_10_3_20` has the only coherent Round81 signal.
- The signal is bottom-tail avoidance, not top-tail buying.
- The kept universe is still negative on a compounded basis, so this is not promotion evidence.

## Decision

Round81 promotable profitable factors: 0.

Round81 paper-ready factors: 0.

Round81 manual/live usable factors: 0.

Direct long-only continuation candidates: 0.

Research leads:

- `anti_supertrend_volume_confirmed_10_3_20` as a bottom-exclusion risk-filter lead only.

Hibernate immediately:

- raw `supertrend_volume_confirmed_10_3_20` direct TopN;
- raw SuperTrend parameter expansion;
- capacity-strict raw SuperTrend direct TopN;
- anti-SuperTrend direct TopN promotion;
- any SuperTrend promotion claim before a costed walk-forward exclusion test.

## Next Direction

Round82 should run only:

`round82_public_supertrend_bottom_exclusion_costed_walk_forward`

Required constraints:

- use only `anti_supertrend_volume_confirmed_10_3_20`;
- keep factor parameters frozen;
- test bottom 20% exclusion as a risk filter;
- use rolling train/test walk-forward;
- include 10 bps cost, 20 bps market impact, 1% ADV capacity, and strict date separation;
- require overlap-adjusted Sharpe, drawdown, fold stability, and zero capacity blockers before any promotion discussion.

If Round82 fails the costed walk-forward gate, the SuperTrend line should be hibernated rather than tuned.

## Verification Evidence

Round81 generated these completed local reports:

- direct grid leaderboard: 3 completed cases, 0 failed cases, 0 no-trade cases;
- IC-to-portfolio gap audit;
- industry-neutral IC audit;
- bottom-exclusion overlay audit.

Generated data reports remain local under `data/reports/` and are not Git sync artifacts.
