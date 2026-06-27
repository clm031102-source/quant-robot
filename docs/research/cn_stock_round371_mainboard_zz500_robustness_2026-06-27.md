# CN Stock Round371 - Mainboard ZZ500 Robustness Checks

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. 2026 final holdout remains unused.

## Why This Round

Round370 produced a plausible high-return research lead:

`mainboard_prerank_vt6_zz500_mult_0.50`

Round371 checks whether it is robust enough to challenge the existing simulation shortlist.

Outputs:

- `data/reports/round371_24h_profit_sprint_mainboard_zz500_block_audit_20260627`
- `data/reports/round371_24h_profit_sprint_mainboard_zz500_oos_split_20260627`
- `data/reports/round371_24h_profit_sprint_turnover_low_mainboard_prerank_replacement_cost30_20260627`
- `data/reports/round371_24h_profit_sprint_mainboard_zz500_cost30_stress_20260627`

## Block Audit

| Candidate | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Leave-One-Year Min Ann. | Blockers |
|---|---:|---:|---:|---:|---:|---:|---|
| `mainboard_vt6_zz500_half` | +167.84% | 6.54% | 0.958 | 0.477 | -30.06% | 2.97% | none |
| `primary_high_return` | +177.08% | 6.35% | 0.960 | 0.517 | -28.88% | 3.76% | none |
| `primary_defensive_zz500` | +147.29% | 5.62% | 1.001 | 0.536 | -20.38% | 3.05% | none |
| `mainboard_vt4_zz500_half` | +155.84% | 6.22% | 0.996 | 0.476 | -27.27% | 2.40% | best-month concentration |

The lead passes loose block gates, but it remains more 2015-sensitive than the existing shortlist.

## Fixed OOS Split

No parameter selection is performed inside the split.

| Candidate | Folds | Mean OOS Ann. | Min OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|---:|---:|
| `primary_high_return` | 26 | 7.33% | -11.56% | 0.662 | -21.20% | 88.46% |
| `mainboard_vt6_zz500_half` | 26 | 6.59% | -10.40% | 0.798 | -15.30% | 88.46% |
| `primary_defensive_zz500` | 26 | 5.62% | -6.72% | 0.686 | -11.74% | 88.46% |

The new candidate sits between `primary_high_return` and `primary_defensive_zz500`:

- less mean OOS return than `primary_high_return`;
- better worst OOS drawdown than `primary_high_return`;
- worse tail than `primary_defensive_zz500`;
- stronger mean OOS overlap than both, but this needs caution because the event count differs.

## 30bps Cost Stress

The pre-rank replacement was rerun at `cost_bps=15`, equivalent to about 30 bps round trip.

After vol target and ZZ500 half overlay:

| Candidate | Total | Ann. | Sharpe | Overlap Sharpe | Max DD |
|---|---:|---:|---:|---:|---:|
| `mainboard_prerank_cost30_vt4_zz500_half` | +123.83% | 5.32% | 0.862 | 0.388 | -28.78% |
| `mainboard_prerank_cost30_vt5_zz500_half` | +125.08% | 5.35% | 0.827 | 0.382 | -30.91% |
| `mainboard_prerank_cost30_vt6_zz500_half` | +127.72% | 5.43% | 0.807 | 0.380 | -31.83% |

Cost stress does not kill the strategy, but it reduces the edge and makes `vt6` exceed the 30% drawdown band.

## Decision

Do not add `mainboard_prerank_vt6_zz500_mult_0.50` to the simulation shortlist yet.

It is a useful research lead, but the existing shortlist still has cleaner evidence:

- `primary_high_return` has higher full-sample total return and better overlap Sharpe;
- `primary_defensive_zz500` has much better drawdown and cost robustness;
- the new mainboard candidate adds implementation complexity and depends on replacing positions that were previously cash-defensive.

Status: research lead, not simulation-ready.
