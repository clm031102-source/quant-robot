# CN Stock Round413 - Unique Candidate Blend Search

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round413 tested whether combining the five unique Round412 simulation observations improves the pre-simulation candidate.

This is a portfolio-construction sanity check, not a new alpha discovery round. If a blend had reduced drawdown without sacrificing too much return, it could have been carried as a cleaner paper-simulation profile.

## Inputs

Five unique candidates from Round412:

- `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21`
- `primary_high_return_dragon_hot_chase_alpha101_openclose_bottom10_tilt_m150`
- `primary_high_return_dragon_hot_chase_adx_fullsource_roll42`
- `primary_defensive_zz500`
- `safer_defensive_zz500`

## Search

Output: `data/reports/round413_24h_profit_sprint_unique_candidate_blend_search_20260627`

Search grid:

- weights in 25% steps;
- 1 to 4 components per blend;
- weights sum to 100%;
- full common date range only;
- -30% max-drawdown eligibility threshold.

Results:

- tested combinations: 70
- combinations within -30% drawdown: 70
- best combination: 100% `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21`

## Top Results

| Rank | Blend | Total Return | Ann. Return | Sharpe | Overlap Sharpe | Max DD |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 100% Alpha101 open-close self-risk | +232.15% | 7.52% | 1.229 | 0.645 | -16.45% |
| 2 | 75% Alpha101 self-risk + 25% Alpha101 aggressive | +228.41% | 7.45% | 1.184 | 0.623 | -20.01% |
| 3 | 75% Alpha101 self-risk + 25% ADX self-risk | +219.52% | 7.27% | 1.224 | 0.645 | -16.66% |
| 4 | 50% Alpha101 self-risk + 50% Alpha101 aggressive | +224.59% | 7.37% | 1.136 | 0.602 | -23.42% |
| 5 | 50% Alpha101 self-risk + 25% Alpha101 aggressive + 25% ADX | +215.89% | 7.20% | 1.174 | 0.623 | -20.20% |

## Decision

Do not add a blended candidate to the shortlist.

The current best single candidate already has the best return, best score, and acceptable drawdown. Blending adds complexity without improving the objective. The only useful information is that ADX can slightly preserve overlap Sharpe, but it reduces total and annualized return.

Next direction should rotate to genuinely independent event or accounting sources rather than blend highly related strategy streams.
