# CN Stock Round426 Old-Lead Salvage And Rotation Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed for the active 24h sprint.

## Purpose

Round426 is a stop-loss audit before opening another mining grid. The goal is to decide whether any older research lead deserves 24h sprint compute, and to prevent the process from drifting back into highly correlated tweaks after Round425 already produced a cohort-entry-timed paper-simulation handoff.

## Current Paper-Simulation Baseline

Round425 remains the active handoff pack:

| Role | Candidate | Annualized | Sharpe | Overlap Sharpe | Max DD | OOS Strict Pass |
|---|---|---:|---:|---:|---:|---:|
| default 10 bps | `paper_ready_cohort_dragon_hot_alpha101_openclose_entry_timed_vt08_max100_self_roll21_x08` | 5.76% | 0.863 | 0.466 | -29.18% | 90.00% |
| heavy-cost 20 bps | `cost20_cohort_openclose_vt07_max1p0_sr21_x0p8` | 5.05% | 0.788 | 0.423 | -29.96% | 90.00% |
| stress fallback 30 bps | `cost30_cohort_openclose_vt07_max0p85_sr21_x0p8` | 4.23% | 0.727 | 0.387 | -28.89% | 76.67% |

This is not a high-Sharpe discovery. It is the best currently reconstructed candidate that satisfies the paper-simulation causality rule: controls are available at entry decision time and event rows preserve entry/exit cohort timing.

## Salvage Review

### Daily-Basic Free-Float Supply Quality

Historical evidence:

- Round141 clean walk-forward produced 6 aggregate-accepted rows, but only 3 folds and a best compounded test total return of 1.89%.
- Round141 fold acceptance was only 2/3 for each row; the rejected fold failed overlap-adjusted Sharpe.
- Round145 later performed a true 2026 final-holdout audit on the frozen family and all 6 aggregate-accepted rows failed the final holdout fold.
- Round145 holdout returns were negative after cost, with negative annualized return, negative Sharpe, negative overlap-adjusted Sharpe, 40% win rate, and an extreme-trade blocker.

Decision:

Do not spend this 24h sprint reviving `daily_basic_free_float_supply_quality`. It is a useful method lesson, not a current simulation candidate. The issue is not drawdown tolerance; the read-once holdout did not earn money.

### Alpha101/Qlib/Dragon-Hot Variants

Historical evidence:

- Round413 blend search found the best blend was 100% the current top Alpha101 self-risk candidate; blends added complexity without improving the objective.
- Round418 public-factor grid found top open-close, vwap, and intraday variants had pairwise event-return correlations above 0.9997.
- Round421 corrected the stronger aggregate Round419 stream by preserving entry/exit cohorts, lowering return but making the result paper-simulation causal.
- Round424 already searched 180 heavier-cost cohort risk-budget variants and kept the best 10/20/30 bps lanes.

Decision:

Do not continue micro-optimizing this family unless a new test changes the cohort-entry-timed handoff directly and materially. Correlated variants count as implementation noise, not new profitable factors.

### Older Price-Volume, Low-Turnover, And Residual Liquidity Leads

Historical evidence:

- Public price-volume and Alpha101 standalone rounds repeatedly found IC or return sparks, but most were redundant with low-volatility, reversal, or liquidity exposure.
- Low-turnover repair variants produced useful research observations, but earlier cost/capacity work showed sensitivity and capacity limits.
- Residual liquidity/market-regime candidates had occasional single-fold wins, but aggregate walk-forward and promotion gates blocked them.

Decision:

Keep these families as reference controls only. They can be used for redundancy checks, neutralization, and risk-budget baselines, but not as the next primary mining direction.

## Round426 Decision

No older lead is upgraded into the active paper-simulation shortlist.

The next mining round should rotate away from the current highly correlated event-risk plus public Alpha101 lane and test a genuinely independent family with explicit economic rationale. Candidate directions:

1. Event-timed underreaction or overreaction using point-in-time public events, where event availability is auditable before entry.
2. Tradeability/liquidity microstructure quality that is not just raw low turnover and includes capacity from the start.
3. Financial reporting timeliness or accounting-quality sources only if source coverage is broad enough before IC screening.
4. Public technical indicators such as SuperTrend, smart-money pressure, range contraction, or trend exhaustion only when pre-registered as entry-time rules and validated against the current cohort handoff.

## Process Rule Added

Before opening a new factor grid during this 24h sprint:

- check whether the family has already failed a final-holdout, capacity, causality, or redundancy gate;
- require a different economic thesis from the current Dragon-Hot/Alpha101 handoff;
- run long-cycle non-holdout evidence before any paper-ready label;
- keep 2026 final holdout sealed unless explicitly running the final paper gate;
- compare any survivor to the Round425 cohort handoff, not to stale aggregate event streams.

## Next Direction

Round427 should start an independent family screen. Priority goes to public technical/event rules that can be computed at entry time from existing cached sources and evaluated quickly under long-cycle costed OOS gates.
