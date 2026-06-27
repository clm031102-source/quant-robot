# CN Stock Round356 - Shortlist Block Dependence Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round356 adds a reusable pre-simulation audit for return concentration.

The question is simple:

Can the current shortlist survive if a strong calendar block is removed, or is it mostly one lucky year/month?

Output:

`data/reports/round356_24h_profit_sprint_shortlist_block_dependence_audit_20260627`

Reusable entrypoint:

`scripts/run_shortlist_return_block_audit.py`

Unit test:

`tests/unit/test_shortlist_return_block_audit.py`

## Inputs

The audit used the five current simulation shortlist event-return streams:

| Candidate | Source |
|---|---|
| `primary_high_return` | `round351` `primary_low10_vol6_zz500_mult_1.00_cost10_events.csv` |
| `primary_balanced_zz500_75` | `round351` `primary_low10_vol6_zz500_mult_0.75_cost10_events.csv` |
| `primary_defensive_zz500` | `round351` `primary_low10_vol6_zz500_mult_0.50_cost10_events.csv` |
| `safer_defensive_zz500` | `round345` `safer_cash_bottom20_vol5_zz500_mom120_neg_half_events.csv` |
| `primary_ps_filtered_defensive_zz500` | `round354` `cash_ps_high20_selected_riskoff_0.50_cost10_events.csv` |

For `primary_ps_filtered_defensive_zz500`, the audit auto-selected `period_return_variant` because that is the filtered/costed return stream.

## Gate Settings

- Periods per year: 50.4.
- Holding period: 20.
- Leave-one-year annualized return floor: greater than 0.
- Leave-one-year overlap Sharpe floor: greater than or equal to 0.
- Top three months log-return concentration blocker: greater than 70% of total log return.
- 2026 final holdout: still sealed.

## Results

| Candidate | Total | Ann. | Overlap Sharpe | Max DD | Min Ann. After Removing One Year | Min Overlap After Removing One Year | Best 3 Months Log Share | Worst Removed Year | Blockers |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `primary_high_return` | +177.08% | +6.35% | 0.517 | -28.88% | +3.76% | 0.386 | 46.38% | 2015 | none |
| `primary_balanced_zz500_75` | +161.99% | +5.99% | 0.530 | -24.74% | +3.41% | 0.411 | 45.84% | 2015 | none |
| `primary_defensive_zz500` | +147.29% | +5.62% | 0.536 | -20.38% | +3.05% | 0.435 | 46.66% | 2015 | none |
| `safer_defensive_zz500` | +137.10% | +5.36% | 0.533 | -21.98% | +3.16% | 0.414 | 46.22% | 2015 | none |
| `primary_ps_filtered_defensive_zz500` | +119.29% | +4.86% | 0.573 | -15.90% | +2.74% | 0.492 | 43.75% | 2015 | none |

## Interpretation

The shortlist is not a single-year artifact under this audit.

All five candidates remain positive after deleting the most important year. The weakest leave-one-year result is still positive:

- `primary_ps_filtered_defensive_zz500`: +2.74% annualized after the worst year removal.
- `primary_defensive_zz500`: +3.05%.
- `primary_balanced_zz500_75`: +3.41%.
- `primary_high_return`: +3.76%.

2015 is clearly the largest contribution year and the most sensitive removed block. This is a real risk flag, but not a rejection by itself because every candidate remains positive without it.

The worst year remains 2018 for all candidates:

- high-return default: -19.68%;
- balanced 75%: -15.79%;
- defensive 50%: -11.73%;
- safer defensive: -15.74%;
- PS-filter defensive: -9.24%.

The PS-filter defensive lane has the best concentration profile and overlap Sharpe, but lower total return. It remains a defensive observation lane, not the main return engine.

## Direction Decision

Keep all five shortlist lanes for now.

Updated confidence:

- `primary_high_return`: still best for return-seeking simulation, but its 2015 dependence and -28.88% max drawdown must be visible.
- `primary_balanced_zz500_75`: remains a useful middle lane.
- `primary_defensive_zz500`: remains the best default if robustness matters.
- `safer_defensive_zz500`: useful as a conservative benchmark, but not as the main candidate.
- `primary_ps_filtered_defensive_zz500`: useful as a low-drawdown, low-concentration comparison lane.

Next work should test whether this family survives stricter construction changes, especially holding/rebalance/TopN sensitivity or implementation mapping into a repeatable simulation entrypoint.
