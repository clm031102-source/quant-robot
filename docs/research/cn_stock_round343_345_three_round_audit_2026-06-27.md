# CN Stock Round343-345 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Rounds Reviewed

| Round | Work | Status |
|---:|---|---|
| 343 | Strategy self-risk overlays | Completed |
| 344 | External ETF regime overlays on primary candidate | Completed |
| 345 | External ETF regime comparison across safer, primary, and aggressive candidates | Completed |

## Main Finding

External ETF regime control is more useful than strategy self-risk control.

The best current high-return default remains:

`primary_low10_vol6 baseline`

Formula:

`turnover_rate_low Top50 hold20 reb5 cost5 + replace_drop_turnover_f_low10 + entry_cash + vol_target_6_lb84`

The best current defensive variant is:

`primary_low10_vol6 + zz500_mom120_neg_half`

Formula:

`primary_low10_vol6`, with 50% exposure when `CN_ETF_XSHG_510500` 120-day momentum is negative before the strategy decision date.

## Candidate Tiers

| Tier | Candidate | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Mean OOS Ann. | Worst OOS DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| High-return default | `primary_low10_vol6 baseline` | +177.08% | +6.35% | 0.960 | 0.517 | -28.88% | +7.86% | -24.00% |
| Preferred defensive | `primary_low10_vol6 + zz500_mom120_neg_half` | +147.29% | +5.62% | 1.001 | 0.536 | -20.38% | +6.05% | -14.87% |
| Ultra-defensive reference | `safer_cash_bottom20_vol5 + zz500_mom120_neg_half` | +114.76% | +4.73% | 0.996 | 0.534 | -14.94% | +4.72% | -11.68% |

## What Changed

Before these three rounds, the main unresolved issue was whether the current lead was too exposed to 2017-2018.

After these three rounds:

- self-risk overlays can reduce drawdown, but mostly by giving up too much return;
- external ETF regime overlays explain the weak state better;
- `zz500_mom120_neg_half` is stable across safer, primary, and aggressive candidates;
- hard cash regime overlays are too defensive for the user's stated return preference.

## Rejected Directions

Do not continue near-term work on:

- `roll21_sum_m2_cash`;
- `current_dd_15_cash`;
- `combo_roll21_m2_cash_dd10_half` as default;
- `both_mom120_neg_cash` as default;
- aggressive low20/PB as default.

These are useful references, but they trade away too much return or add complexity without enough benefit.

## Direction Audit

The work is still aligned with the 24h objective.

This is no longer blind factor fishing. The current path is:

1. keep the profitable low-turnover repair signal;
2. isolate stale free-float turnover as the failure pocket;
3. use vol-target for drawdown control;
4. use CSI500 ETF trend as an external market-state defense;
5. keep a high-return and a defensive candidate for simulation instead of forcing one objective.

## Updated Next Steps

Next work should focus on confirmation, not broad random search:

1. add a formal read-once final holdout plan for 2026, but do not run it yet unless explicitly entering final validation;
2. test benchmark/beta dependence for the three candidate tiers;
3. test cost stress around 5, 10, 20, and 30 bps;
4. convert the three candidate tiers into repeatable config or runbook entries;
5. only then resume new factor-family exploration.

Current simulation shortlist:

- `primary_low10_vol6 baseline`;
- `primary_low10_vol6 + zz500_mom120_neg_half`;
- `safer_cash_bottom20_vol5 + zz500_mom120_neg_half`.
