# CN Stock Round365 Public ADX Filter OOS Split

Date: 2026-06-27

Machine/task: `office_desktop` / `factor_validation`

Safety boundary: research-to-review only; no broker connection, no account reads, no order placement, no live trading.

## Purpose

Round364 found one useful public-indicator defensive filter:

`public_adx_trend_strength_exhaustion_reversal_14_20_cash_bottom20_on_primary_low10`

Round365 compares it against the existing simulation shortlist candidates using fixed rolling OOS windows. No parameter is selected inside the split; the run only measures out-of-sample behavior for already-defined candidates.

## Method

Candidates:

- `primary_high_zz500_100`
- `primary_balanced_zz500_75`
- `primary_defensive_zz500_50`
- `ps_filtered_zz500_50`
- `adx_filter_zz500_100`
- `adx_filter_zz500_75`
- `adx_filter_zz500_50`

Split method:

- rolling test windows after fixed 2/3/4/5 year train spans;
- one-year test windows;
- 26 test folds per candidate;
- no parameter selection;
- 2026 final holdout remains untouched.

Output:

`data/reports/round365_24h_profit_sprint_public_adx_filter_oos_split_20260627`

## OOS Summary

| Candidate | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ps_filtered_zz500_50` | 4.77% | -5.29% | 0.775 | -9.22% | 73.08% |
| `primary_defensive_zz500_50` | 5.62% | -6.72% | 0.686 | -11.74% | 88.46% |
| `adx_filter_zz500_50` | 5.43% | -5.27% | 0.676 | -9.11% | 88.46% |
| `primary_balanced_zz500_75` | 6.47% | -9.16% | 0.670 | -16.59% | 73.08% |
| `primary_high_zz500_100` | 7.33% | -11.56% | 0.662 | -21.20% | 73.08% |
| `adx_filter_zz500_75` | 6.28% | -7.24% | 0.653 | -13.11% | 73.08% |
| `adx_filter_zz500_100` | 7.14% | -9.17% | 0.644 | -16.95% | 73.08% |

## Interpretation

The ADX filter is useful but not dominant.

What improved:

- `adx_filter_zz500_50` reduces worst OOS drawdown versus `primary_defensive_zz500_50`: -9.11% vs -11.74%.
- It keeps the same strict pass rate as `primary_defensive_zz500_50`: 88.46%.
- It has a milder worst OOS annualized return: -5.27% vs -6.72%.

What did not improve:

- Mean OOS annualized return is lower than the primary defensive lane: 5.43% vs 5.62%.
- Mean OOS overlap is slightly lower: 0.676 vs 0.686.
- The PS-filter lane still has the best mean OOS overlap and lowest worst OOS drawdown, but with lower mean OOS return and lower strict pass.

## Decision

Do not promote the ADX filter into the simulation shortlist yet.

Keep it as a defensive research lead:

- useful when drawdown reduction is prioritized;
- not a replacement for `primary_defensive_zz500_50`;
- not a new independent public-indicator alpha;
- not paper-ready.

Next work should not continue broad public-indicator sweeps. If this lead is revisited, the only justified checks are direct cost/beta and event-schema packaging against the current shortlist, not more indicator parameter search.
