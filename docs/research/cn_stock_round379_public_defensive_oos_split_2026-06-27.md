# CN Stock Round379 - Public Defensive Filter OOS Split

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Why This Round

Round364 found public indicators can be useful as selected-basket defensive filters on the primary low-turnover replacement candidate. Round365 only ran OOS splits for the best ADX filter.

Round379 retests the saved non-ADX defensive event files against ADX and the existing shortlist references using a reusable rolling OOS split audit.

## Reusable Tool Added

- `src/quant_robot/ops/shortlist_oos_split_audit.py`
- `scripts/run_shortlist_oos_split_audit.py`
- `tests/unit/test_shortlist_oos_split_audit.py`

This tool compares event-return sources across fixed rolling test windows and reports mean/min OOS annualized return, overlap Sharpe, drawdown, and pass rates.

## Output

`data/reports/round379_24h_profit_sprint_public_defensive_oos_split_20260627`

Candidates:

- `primary_defensive_zz500_50`;
- `ps_filtered_zz500_50`;
- `adx_filter_zz500_50`;
- `kama_filter_zz500_50`;
- `choppy_filter_zz500_50`;
- `williams_filter_zz500_50`.

## OOS Results

| Candidate | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|---:|
| `adx_filter_zz500_50` | 6.02% | -4.81% | 0.896 | -11.97% | 90.00% |
| `kama_filter_zz500_50` | 5.69% | -4.92% | 0.890 | -12.25% | 90.00% |
| `williams_filter_zz500_50` | 5.30% | -4.60% | 0.864 | -11.72% | 90.00% |
| `ps_filtered_zz500_50` | 5.01% | -4.87% | 0.862 | -12.02% | 90.00% |
| `choppy_filter_zz500_50` | 5.69% | -4.33% | 0.846 | -10.98% | 90.00% |
| `primary_defensive_zz500_50` | 6.05% | -6.22% | 0.824 | -14.87% | 90.00% |

The split count is 30 per candidate under the reusable tool's 2/3/4/5-year train-span and 1-year fixed test-window grid.

## Interpretation

The public defensive filters improve OOS drawdown and OOS overlap versus the plain `primary_defensive_zz500_50`, but they still give up return.

Best trade-off:

- `adx_filter_zz500_50` remains the best public defensive research lead;
- `kama_filter_zz500_50` is close enough to keep as a second defensive lead;
- `choppy_filter_zz500_50` has the best worst OOS drawdown, but weaker overlap and return.

## Decision

Do not add a new public defensive filter to the simulation shortlist.

Keep:

- `primary_defensive_zz500_50` as the current defensive simulation lane;
- `adx_filter_zz500_50` and `kama_filter_zz500_50` as research leads for future drawdown-prioritized variants.

This round improves process quality by adding a reusable OOS split audit, not by adding a new tradable factor.
