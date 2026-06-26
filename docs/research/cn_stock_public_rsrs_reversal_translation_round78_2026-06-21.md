# CN Stock Public RSRS Reversal Translation Round 78 - 2026-06-21

## Purpose

Round77 found that raw public RSRS factors were not tradable as direct long-only TopN stock signals. The only useful direction was the flipped signal:

`rsrs_reversal_18_60`

Round78 tested whether that signal has a better translation layer before any further RSRS window expansion. The question was deliberately narrow:

- Is the signal only a weak TopN long-only result?
- Is it industry exposure?
- Does industry-neutral selection improve it?
- Is it more useful as a bottom-quantile exclusion / risk filter?

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.

## Setup

- Market: CN stocks, not ETF rotation.
- Sample: 2015-01-05 to 2025-12-31.
- Factor: `rsrs_reversal_18_60`.
- Horizon: 20 trading days.
- Execution lag: 1.
- Rebalance interval: 10.
- Costed portfolio assumptions: 10 bps cost, 20 bps market impact, max participation 1% ADV, portfolio value 1,000,000, target gross exposure 0.6.
- Config: `configs/experiment_grid_cn_stock_public_rsrs_reversal_translation_round78_20260621.json`.

## Audit Outputs

- IC-to-portfolio gap: `data/reports/ic_portfolio_gap_public_rsrs_round78_20260621`.
- Industry-neutral IC: `data/reports/industry_neutral_ic_public_rsrs_reversal_round78_20260621`.
- Industry-neutral TopN portfolio: `data/reports/industry_neutral_portfolio_public_rsrs_reversal_round78_20260621`.
- Bottom-exclusion overlay: `data/reports/bottom_exclusion_overlay_public_rsrs_reversal_round78_20260621`.

## Results

### IC-to-Portfolio Gap

The Round77 grid had 8 cases. The gap audit found:

- Strong RankIC cases: 6.
- IC-to-portfolio gap cases: 6.
- Exclusion-signal cases: 2.
- Capacity-limited cases: 8.
- Promotable long-only cases: 0.

The best raw long-only RSRS reversal cases were still rejected:

| Case | Total Return | Annual Return | Sharpe | Overlap Sharpe | Win Rate | Max DD | RankIC | RankIC t | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `CN_rsrs_reversal_18_60_top50_cost10_reb10` | 67.28% | 2.24% | 0.293 | 0.201 | 48.55% | -44.82% | 0.0214 | 4.77 | rejected |
| `CN_rsrs_reversal_18_60_top100_cost10_reb10` | 72.07% | 1.79% | 0.272 | 0.191 | 50.19% | -40.92% | 0.0214 | 4.77 | rejected |

Main blocker: significant IC did not translate into a strong, capacity-clean, benchmark-competitive long-only portfolio.

### Industry-Neutral IC

Industry-neutral IC strengthened the signal instead of destroying it:

| Factor | Classification | Overall RankIC | Overall t | Neutral RankIC | Neutral t | Industry RankIC | Industry t | Retention |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `rsrs_reversal_18_60` | industry_neutral_signal | 0.0214 | 15.97 | 0.0253 | 24.00 | 0.0225 | 7.42 | 1.18 |

This is the best statistical result of Round78. It says the signal is not merely industry exposure. However, it is still only signal evidence, not trading evidence.

Metadata note: 297,044 factor rows had missing industry labels, so industry metadata coverage still needs repair before any promotion claim.

### Industry-Neutral TopN Portfolio

Industry-neutral selection improved the top50 portfolio but still failed the promotion gate.

| Case | Total Return | Annual Return | Sharpe | Overlap Sharpe | Win Rate | Max DD | Relative Return | Capacity-Limited Trades | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `top50_industry_neutral` | 80.75% | 2.61% | 0.352 | 0.241 | 50.09% | -40.43% | -22.93 | 69 | rejected |
| `top100_industry_neutral` | 59.28% | 1.56% | 0.256 | 0.182 | 50.53% | -40.80% | -23.14 | 77 | rejected |

Positive evidence:

- Top50 total return improved from 67.28% to 80.75%.
- Top50 overlap-adjusted Sharpe improved from 0.201 to 0.241.
- Win rate improved to about 50%.

Blocking evidence:

- Both cases remained far below the full-market benchmark curve.
- Both cases still had capacity-limited trades.
- Drawdown stayed around -40%.
- Overlap-adjusted Sharpe remained far below the research candidate threshold.

### Bottom-Exclusion Overlay

This is the strongest practical lead from Round78, but it is diagnostic only.

| Factor | Classification | Mean Full Return | Mean Kept Return | Mean Bottom Return | Overlay Excess | Overlay t | Positive Overlay Rate | Kept Compounded | Full Compounded | Bottom Compounded |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `rsrs_reversal_18_60` | bottom_exclusion_candidate | 0.9175% | 1.0210% | 0.5030% | 0.1035% | 5.39 | 66.28% | 362.69% | 257.62% | 24.21% |

Interpretation:

- The factor looks more useful for removing the weakest bottom quantile than for direct TopN buying.
- The bottom group badly lagged the full universe, while the kept universe improved.
- The overlay t-stat is strong enough to justify one more costed portfolio conversion round.

Limit:

- This audit does not yet include full portfolio transaction costs, turnover, capacity stress, and walk-forward promotion gates for the exclusion portfolio. It cannot be promoted by itself.

## Decision

Promotable profitable factors: 0.

Paper-ready factors: 0.

Research leads: 1.

- `rsrs_reversal_18_60` as a bottom-exclusion / risk-filter candidate.

Rejected directions:

- Promote RSRS reversal as direct long-only TopN.
- Promote industry-neutral TopN after Round78.
- Expand RSRS windows before a costed exclusion portfolio test.
- Treat the diagnostic bottom-exclusion overlay as promotion evidence.

## Next Direction

Round79 should run:

`public_rsrs_bottom_exclusion_costed_walk_forward`

Required checks:

- costed bottom-exclusion portfolio;
- walk-forward fold stability;
- capacity-safe universe gate;
- drawdown and overlap-adjusted Sharpe gates;
- no new RSRS parameter tuning until the frozen `rsrs_reversal_18_60` exclusion version is accepted or rejected.
