# CN Stock Round420 - Simulation Shortlist With Aggressive Entry-Timed Candidate

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round420 reruns the formal simulation shortlist replay and ranking after adding the Round419 aggressive entry-timed candidate.

## Replay Result

- configured candidates: 16
- replayed candidates: 16
- blocked candidates: 0
- status: passed

## Ranking Result

- eligible unique candidates: 7
- near-duplicate return streams: 9
- hard blocked candidates: 0

Top unique candidates:

| Rank | Candidate | Role | Total Return | Ann. Return | Sharpe | Overlap Sharpe | Max DD | Mean OOS Ann. | Strict OOS Pass |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21` | best research observation | +232.15% | 7.52% | 1.229 | 0.645 | -16.45% | 8.05% | 90.00% |
| 2 | `paper_ready_aggressive_dragon_hot_alpha101_openclose_entry_timed_vt10_max115_self_roll42_x08` | aggressive paper-simulation candidate | +206.28% | 7.00% | 0.929 | 0.512 | -29.19% | 9.61% | 90.00% |
| 3 | `primary_balanced_dragon_hot_chase_alpha101_openclose_top10_cash_zz500075` | balanced observation | +166.31% | 6.10% | 1.124 | 0.607 | -22.07% | 7.10% | 90.00% |
| 4 | `primary_high_return_dragon_hot_chase_adx_fullsource_roll42` | defensive public-indicator observation | +184.00% | 6.51% | 1.174 | 0.639 | -17.41% | 7.70% | n/a |
| 5 | `paper_ready_dragon_hot_alpha101_openclose_entry_timed_vt6_self_roll21` | conservative paper-simulation candidate | +143.58% | 5.53% | 0.933 | 0.487 | -21.54% | 5.32% | 76.67% |

## Interpretation

The old Round407 observation remains the highest-ranked research stream, but Round415 already showed it is not a clean direct handoff to paper simulation.

The Round419 aggressive entry-timed candidate is the best current paper-simulation candidate. It trades a larger drawdown for higher return while staying inside the user's -30% drawdown tolerance.

## Decision

Carry two paper-simulation candidates into the next phase:

- aggressive: `paper_ready_aggressive_dragon_hot_alpha101_openclose_entry_timed_vt10_max115_self_roll42_x08`
- conservative: `paper_ready_dragon_hot_alpha101_openclose_entry_timed_vt6_self_roll21`

Keep the Round407 exit-timed candidate as a benchmark and research target, not as a direct simulation handoff.
