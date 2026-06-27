# CN Stock Round411 - Simulation Shortlist Ranking

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round411 moved the sprint from factor discovery into simulation-readiness triage.

The goal was to stop treating all 14 configured observations as independent candidates. The new ranking pack compares the same event-return streams under a user-tolerant aggressive drawdown limit of -30%, merges OOS and beta-hedged evidence, and marks highly correlated streams as duplicates.

## Engineering Output

Added a reusable simulation shortlist ranker:

- `src/quant_robot/ops/simulation_shortlist_ranker.py`
- `scripts/run_simulation_shortlist_ranker.py`
- `tests/unit/test_simulation_shortlist_ranker.py`
- `tests/unit/test_simulation_shortlist_ranker_cli.py`

The ranker writes:

- `simulation_shortlist_ranking.json`
- `simulation_shortlist_ranking_rows.csv`
- `simulation_shortlist_return_correlations.csv`

## Round411 Outputs

- Replay: `data/reports/round411_24h_profit_sprint_simulation_shortlist_replay_20260627`
- Ranking: `data/reports/round411_24h_profit_sprint_simulation_shortlist_ranking_20260627`

## Ranking Result

| Candidate | Status | Total Return | Ann. Return | Sharpe | Overlap Sharpe | Max DD | Mean OOS Ann. | Worst OOS DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21` | best unique | +232.15% | 7.52% | 1.229 | 0.645 | -16.45% | 8.05% | -13.44% |
| `primary_high_return_dragon_hot_chase_alpha101_openclose_bottom10_tilt_m150` | aggressive unique | +216.69% | 7.21% | 1.035 | 0.558 | -29.84% | 8.82% | -24.58% |
| `primary_high_return_dragon_hot_chase_adx_fullsource_roll42` | defensive unique | +184.00% | 6.51% | 1.174 | 0.639 | -17.41% | 7.70% | -13.86% |
| `primary_defensive_zz500` | defensive reference | +147.29% | 5.62% | 1.001 | 0.536 | -20.38% | 6.05% | -14.87% |
| `safer_defensive_zz500` | ultra-defensive reference | +114.76% | 4.73% | 0.996 | 0.534 | -14.94% | 4.72% | -11.68% |

Summary:

- configured candidates: 14
- unique simulation-observation candidates under the ranker: 5
- duplicate return streams: 9
- hard blocked by the -30% user drawdown limit: 0

## Important Caveat

The initial replay audit was blocked because five self-risk event streams were missing structure columns:

- `decision_date`
- `final_exposure`
- `regime_guard_exposure`

The returns were numerically replayable, but the event schema was not simulation-ready. Round412 repairs this upstream instead of relaxing the replay check.

## Decision

Carry the top Alpha101 open-close self-risk candidate as the current best simulation observation, but treat Qlib and Dragon-Hot self-risk variants as duplicates/comparators rather than independent alphas.

Next work: repair self-risk event schema, then rerun replay/ranking before additional mining.
