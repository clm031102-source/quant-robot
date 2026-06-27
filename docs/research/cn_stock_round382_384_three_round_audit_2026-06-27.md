# CN Stock Round382-384 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## What Was Tested

| Round | Work | Result |
|---:|---|---|
| 382 | Naive Dragon-Tiger cash-filter quickcheck | Positive research lead, blocked by calendar parity |
| 383 | Official 834-date template projection | Calendar-safe positive increment |
| 384 | `vol_target_6_lb84` + ZZ500 wrapper comparison | Positive increment survives current simulation wrappers |

## Key Finding

`dragon_hot_chase_20d` is the first useful event-risk overlay from this block.

It does not replace the low-turnover factor family. It improves the current family by cashing selected trades that recently had high-attention Dragon-Tiger net-buy/chase behavior.

## Why Round382 Was Not Enough

Round382 used naive exit-date aggregation:

- generated dates: 872;
- official reference dates: 834;
- missing dates: 93;
- extra dates: 131;
- calendar parity: blocked.

That made the attractive Round382 numbers insufficient for simulation handoff.

## What Changed In Round383

Round383 projected flagged trade contribution onto the frozen official template.

Best official-template candidate:

| Candidate | Total | Ann. | Overlap | Max DD | Unmatched Abs Contribution |
|---|---:|---:|---:|---:|---:|
| `cash_dragon_hot_chase_20d` | +159.79% | 5.94% | 0.454 | -32.87% | 0.00033 |
| official base | +150.65% | 5.71% | 0.428 | -35.29% | n/a |

OOS also improved:

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD |
|---|---:|---:|---:|
| `cash_dragon_hot_chase_20d` | 9.06% | 0.898 | -23.68% |
| official base | 8.90% | 0.875 | -24.00% |

## What Changed In Round384

Round384 tested the Dragon-Tiger overlay inside the current simulation wrapper stack.

| Lane | Full Ann. | Full Overlap | Full DD | OOS Ann. | OOS Overlap | OOS Worst DD |
|---|---:|---:|---:|---:|---:|---:|
| `dragon_hot_100` | 6.45% | 0.532 | -28.57% | 8.02% | 0.869 | -23.68% |
| `primary_100` | 6.35% | 0.517 | -28.88% | 7.86% | 0.845 | -24.00% |
| `dragon_hot_075` | 6.07% | 0.546 | -24.43% | 7.11% | 0.854 | -19.24% |
| `primary_075` | 5.99% | 0.530 | -24.74% | 6.95% | 0.828 | -19.55% |
| `dragon_hot_050` | 5.68% | 0.552 | -20.07% | 6.20% | 0.849 | -14.57% |
| `primary_050` | 5.62% | 0.536 | -20.38% | 6.05% | 0.824 | -14.87% |

Beta audit did not show increased benchmark dependence. ZZ500 R2 stayed essentially unchanged, and beta-hedged overlap improved slightly in all three multiplier lanes.

## Decision

Add a new simulation observation lane:

`primary_low10_vol6 + dragon_hot_chase_20d cash filter + ZZ500 risk-off multiplier`

Preferred observation:

- `dragon_hot_100` for return-seeking simulation, because drawdown remains below 30%;
- `dragon_hot_050` for conservative simulation, because it improves the defensive lane without increasing drawdown.

Do not yet make it the default. The incremental edge is small. It should enter simulation as an observation lane, then be monitored for whether it improves live-like replay and paper-trading behavior.

## Process Lessons

1. Naive event aggregation is not acceptable evidence.
2. Every event-risk filter must pass official-template projection or event-calendar parity.
3. A useful overlay should be tested inside the actual wrapper stack, not only on the unwrapped base.
4. The project now has a reusable official-template cash-filter audit tool for future event filters.

## Next Direction

Continue factor mining, but rotate away from pure low-turnover tuning after this useful overlay is recorded.

Next high-value families:

- public technical indicators with clear market microstructure intuition, such as SuperTrend/ATR trend exhaustion and VWAP/volume-price divergence;
- event filters with official-template projection, such as pledge/unlock/buyback if data coverage is sufficient;
- ETF-aware regime overlays that use the purchased ETF data more directly.
