# CN Stock Round370-372 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: mandatory three-round review inside the 24h profit-factor sprint.

## Rounds Reviewed

| Round | Work | Main Result | Decision |
|---:|---|---|---|
| 370 | Applied frozen ZZ500 120-day momentum risk-off overlay to mainboard pre-rank variants | `mainboard_prerank_vt6_zz500_mult_0.50` reached 6.54% annualized return with about -29.86% drawdown | Continue to robustness checks |
| 371 | Block, fixed OOS, and 30bps cost checks | New lead survives but does not beat existing shortlist on combined risk-adjusted evidence | Keep as research lead only |
| 372 | Three-round audit | Mainboard pre-rank plus ZZ500 is useful but not superior | Do not promote; rotate direction |

## What Was Learned

The mainboard pre-rank problem was not hopeless. Adding the already-used ZZ500 risk-off overlay can convert it from a -40% drawdown line into a near-30% drawdown line.

Best version:

`replace_drop_turnover_f_low10_mainboard_prerank + vol_target_6_lb84 + zz500_mom120_neg_half`

Key numbers:

- full-sample total return: +167.84%;
- annualized return: 6.54%;
- Sharpe: 0.958;
- overlap Sharpe: 0.477;
- max drawdown: about -30.06% in block-audit compounding;
- mean OOS annualized return: 6.59%;
- worst OOS drawdown: -15.30%;
- 30bps stress with vt6: annualized 5.43%, max drawdown -31.83%.

## Why It Is Not Promoted

The existing shortlist remains cleaner:

| Candidate | Full Ann. | Full Overlap | Full DD | Mean OOS Ann. | Worst OOS DD | Interpretation |
|---|---:|---:|---:|---:|---:|---|
| `primary_high_return` | 6.35% | 0.517 | -28.88% | 7.33% | -21.20% | better return engine |
| `mainboard_vt6_zz500_half` | 6.54% | 0.477 | -30.06% | 6.59% | -15.30% | useful but not dominant |
| `primary_defensive_zz500` | 5.62% | 0.536 | -20.38% | 5.62% | -11.74% | better defensive lane |

The new lead is not bad; it is squeezed between two existing choices:

- not as clean as `primary_high_return` for return;
- not as safe as `primary_defensive_zz500` for drawdown/cost robustness;
- adds extra implementation complexity from mainboard pre-ranking.

## Process Decision

Stop this branch of work here unless a future simulation explicitly needs a mainboard-only operational variant.

Do not tune:

- extra board filters;
- more ZZ500 multipliers;
- more vol-target lookbacks;
- entry-date limit-status replacement.

The next work should rotate to a more independent source of edge:

1. raw-data-to-event generation replay for current shortlist, to prepare for simulation handoff;
2. industry/breadth or macro-regime translation independent of low-turnover;
3. PIT financial or event-timing factors only if coverage/announcement-lag gates pass.

## Candidate Registry Decision

`mainboard_prerank_vt6_zz500_half` may be recorded as a research lead, but it should not be a simulation candidate in `configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json`.

The simulation shortlist remains unchanged after Rounds370-372.
