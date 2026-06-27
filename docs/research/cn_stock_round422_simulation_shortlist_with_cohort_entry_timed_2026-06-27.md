# CN Stock Round422 - Simulation Shortlist With Cohort Entry-Timed Candidate

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round422 reruns the formal shortlist replay/ranking after adding the cohort-level paper-ready candidate from Round421 and downgrading the aggregate Round419 candidate.

## Replay Result

- configured candidates: 17
- replayed candidates: 17
- replay blockers: 0

## Ranking Result

- eligible candidates: 7
- duplicate candidates: 9
- blocked candidates: 1

The blocked candidate is the aggregate Round419 event stream:

`paper_ready_aggressive_dragon_hot_alpha101_openclose_entry_timed_vt10_max115_self_roll42_x08`

Blocker:

- `not_paper_ready`

## Top Candidates

| Rank | Candidate | Role | Total Return | Ann. Return | Sharpe | Overlap Sharpe | Max DD | Mean OOS Ann. | Paper Ready |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21` | research benchmark | +232.15% | 7.52% | 1.229 | 0.645 | -16.45% | 8.05% | not direct |
| 2 | `primary_high_return_dragon_hot_chase_alpha101_openclose_bottom10_tilt_m150` | aggregate observation | +216.69% | 7.21% | 1.035 | 0.558 | -29.84% | 8.82% | not direct |
| 3 | `paper_ready_cohort_dragon_hot_alpha101_openclose_entry_timed_vt08_max100_self_roll21_x08` | best true paper handoff | +163.48% | 5.76% | 0.863 | 0.466 | -29.18% | 8.53% | yes |
| 4 | `primary_high_return_dragon_hot_chase_adx_fullsource_roll42` | public defensive observation | +184.00% | 6.51% | 1.174 | 0.639 | -17.41% | 7.70% | not direct |
| 5 | `paper_ready_dragon_hot_alpha101_openclose_entry_timed_vt6_self_roll21` | aggregate conservative handoff | +143.58% | 5.53% | 0.933 | 0.487 | -21.54% | 5.32% | aggregate-level |

## Decision

The cohort-level candidate is now the best true paper-simulation handoff.

Do not use the aggregate Round419 aggressive stream for simulation despite its better headline return. It is useful only as a research target because it collapses multiple entry cohorts under exit-date events.
