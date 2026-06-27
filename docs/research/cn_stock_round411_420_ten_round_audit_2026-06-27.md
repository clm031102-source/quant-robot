# CN Stock Rounds 411-420 Ten-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Executive Decision

Rounds 411-420 produced a meaningful process correction and one stronger paper-ready candidate.

The most important change was not factor count. It was separating high-return research observations from signals that can actually be generated before entry time.

## What Changed

| Area | Before | After |
|---|---|---|
| Shortlist ranking | Manual comparison across many similar streams | Reusable ranker with duplicate detection |
| Self-risk streams | Some outputs replayed numerically but missed schema columns | Schema-preserving self-risk overlay |
| Best candidate handoff | Round407 looked strongest but was exit/event-timed | Round416/419 rebuild entry-timed paper candidates |
| Public-factor search | Individual public factors were checked one by one | 64 public-indicator candidates batch rebuilt with entry-timed controls |
| Risk budget | Conservative 6% vol target only | Aggressive 10% vol, max exposure 1.15 variant under -30% drawdown limit |

## Round Summary

| Rounds | Work | Outcome |
|---|---|---|
| 411-413 | Shortlist ranker, schema repair, blend audit | 14 candidates collapsed to 5 unique streams; blends did not improve |
| 414-416 | Independent-source triage, signal reconstruction, entry-timed rebuild | Found Round407 handoff issue; created conservative paper-ready entry-timed candidate |
| 417 | Full shortlist replay/ranking with entry-timed candidate | 15 candidates replayed; conservative paper-ready candidate ranked as clean handoff |
| 418 | Entry-timed public-factor grid | 64 public indicators scanned; top variants were >0.9997 correlated |
| 419 | Risk-budget sensitivity | 90 parameter combinations scanned; best aggressive paper-ready candidate found |
| 420 | Full shortlist replay/ranking with aggressive candidate | 16 candidates replayed; aggressive paper-ready candidate ranked #2 overall and #1 paper-ready |

## Best Current Candidates

| Candidate | Role | Total Return | Ann. Return | Sharpe | Overlap Sharpe | Max DD | Mean OOS Ann. | Strict OOS Pass | Paper Ready |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21` | research benchmark | +232.15% | 7.52% | 1.229 | 0.645 | -16.45% | 8.05% | 90.00% | no direct handoff |
| `paper_ready_aggressive_dragon_hot_alpha101_openclose_entry_timed_vt10_max115_self_roll42_x08` | aggressive paper candidate | +206.28% | 7.00% | 0.929 | 0.512 | -29.19% | 9.61% | 90.00% | yes |
| `paper_ready_dragon_hot_alpha101_openclose_entry_timed_vt6_self_roll21` | conservative paper candidate | +143.58% | 5.53% | 0.933 | 0.487 | -21.54% | 5.32% | 76.67% | yes |

## Useful Output

Reusable code added:

- `src/quant_robot/ops/simulation_shortlist_ranker.py`
- `src/quant_robot/ops/simulation_shortlist_signal_reconstruction.py`
- `src/quant_robot/ops/simulation_shortlist_entry_timed_overlay.py`
- `src/quant_robot/ops/simulation_shortlist_entry_timed_grid.py`

Reusable scripts added:

- `scripts/run_simulation_shortlist_ranker.py`
- `scripts/run_simulation_shortlist_signal_reconstruction.py`
- `scripts/run_simulation_shortlist_entry_timed_overlay.py`
- `scripts/run_simulation_shortlist_entry_timed_grid.py`

Test coverage added for the new ranker, reconstruction, entry-timed overlay, entry-timed grid, and CLI paths.

## Problems Found

- The old top stream was too easy to over-trust because event returns reconciled exactly, while exposure timing was still not paper-simulation safe.
- Public-indicator variants generated many names but very little independent information.
- More aggressive risk budgets can improve return, but drawdown quickly approaches the user's -30% tolerance.

## Next Direction

Next work should not keep creating highly correlated Alpha101 variants.

Priority:

1. Run paper-simulation adapter comparison for the aggressive and conservative entry-timed candidates.
2. Apply cost/accounting stress to the aggressive candidate with the simulator's exact turnover model.
3. Search for independent sources only if they can pass the same entry-timed causality gate and produce low correlation to the current Dragon-Hot/Alpha101 lane.
