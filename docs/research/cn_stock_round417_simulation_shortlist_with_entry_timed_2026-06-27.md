# CN Stock Round417 - Simulation Shortlist With Entry-Timed Candidate

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round417 reruns the formal simulation shortlist replay and ranking after adding the Round416 entry-timed paper-simulation candidate.

This separates two different concepts:

- best research observation: the higher-return Round407 exit-timed stream;
- best paper-simulation handoff candidate: the Round416 entry-timed stream with controls known before each `entry_date`.

## Commands

```powershell
python scripts\run_simulation_shortlist_replay.py --config configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json --output-dir data\reports\round417_24h_profit_sprint_simulation_shortlist_replay_with_entry_timed_20260627 --metric-tolerance 0.01
python scripts\run_simulation_shortlist_ranker.py --config configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json --output-dir data\reports\round417_24h_profit_sprint_simulation_shortlist_ranking_with_entry_timed_20260627
```

## Replay Result

- configured candidates: 15
- replayed candidates: 15
- blocked candidates: 0
- status: passed

## Ranking Result

Unique eligible candidates increase from 5 to 6. Nine candidates remain near-duplicate return streams.

| Rank | Candidate | Role | Total Return | Ann. Return | Sharpe | Overlap Sharpe | Max DD | Mean OOS Ann. | Strict OOS Pass |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21` | best research observation | +232.15% | 7.52% | 1.229 | 0.645 | -16.45% | 8.05% | 90.00% |
| 2 | `primary_high_return_dragon_hot_chase_alpha101_openclose_bottom10_tilt_m150` | aggressive observation | +216.69% | 7.21% | 1.035 | 0.558 | -29.84% | 8.82% | 90.00% |
| 3 | `primary_high_return_dragon_hot_chase_adx_fullsource_roll42` | defensive public-indicator observation | +184.00% | 6.51% | 1.174 | 0.639 | -17.41% | 7.70% | n/a |
| 4 | `paper_ready_dragon_hot_alpha101_openclose_entry_timed_vt6_self_roll21` | paper-simulation handoff | +143.58% | 5.53% | 0.933 | 0.487 | -21.54% | 5.32% | 76.67% |
| 5 | `primary_defensive_zz500` | defensive reference | +147.29% | 5.62% | 1.001 | 0.536 | -20.38% | 6.05% | n/a |
| 6 | `safer_defensive_zz500` | ultra-defensive reference | +114.76% | 4.73% | 0.996 | 0.534 | -14.94% | 4.72% | n/a |

## Interpretation

The entry-timed candidate is not the top return stream. It ranks below the exit-timed high-return observations because it removes timing assumptions that are unsafe for paper simulation.

That tradeoff is acceptable for the next project phase. A simulated paper handoff needs a signal that can be generated at decision time, not just an event-return stream that is numerically attractive after the fact.

## Decision

Use `paper_ready_dragon_hot_alpha101_openclose_entry_timed_vt6_self_roll21` as the current paper-simulation candidate for the Dragon-Hot plus Alpha101 open-close lane.

Keep `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21` as a research observation and benchmark only until an entry-timed rebuild closes its paper-readiness blockers.

Next mining work should only promote candidates that pass the same entry-timed causality gate.
