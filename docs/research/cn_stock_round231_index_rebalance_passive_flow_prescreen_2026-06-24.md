# CN Stock Round231 Index Rebalance Passive Flow Prescreen - 2026-06-24

## Scope

Round231 tested the pre-registered `index_rebalance_passive_flow` family after rotating away from the failed Round230 liquidity-shock-recovery path. This was a CN stock event/supply-demand study, not ETF rotation and not a portfolio backtest.

Promotion remained blocked throughout the run. The only permitted evidence was PIT event IC plus industry/size neutralization from index-rebalance `available_date`.

## Data Coverage

- Tushare endpoint: `index_weight`.
- Indexes: `000300.SH`, `000905.SH`, `000852.SH`.
- Pull window: 2015 through 2025.
- Index-weight rows: 199,400.
- Trading-calendar rows: 2,694.
- Snapshot dates: 205.
- Event rows: 12,091.
- Added events: 4,886.
- Removed events: 4,886.
- Weight-changed events: 2,319.
- Event audit blockers: none.
- Bars used for event assets: 7,189,772 rows, 3,292 assets.
- Bar window: 2015-01-05 through 2025-12-31.

## Prescreen Summary

- Pre-registered factor names: 5.
- Factor x horizon tests: 10.
- Horizons: 5 and 20 trading days.
- Filtered constant factor-date groups: 317 groups, 5,860 rows.
- Remaining factor rows: 46,255.
- Signal window: 2015-03-02 through 2025-12-01.
- Label window: 2015-01-05 through 2025-12-23.
- Neutral-gate pass tests: 2.
- Multiple-testing research leads: 0.
- Promotion-allowed candidates: 0.
- Next direction: `round232_rotate_after_index_rebalance_passive_flow_failure`.

## Result Table

| Factor | H | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `index_rebalance_weight_down_pressure_1d` | 5 | -0.0758 | -0.420 | -2.75 | 39.5% | -0.1016 | 0.4076 | -0.0682 | no |
| `index_rebalance_weight_down_pressure_1d` | 20 | -0.0609 | -0.290 | -1.90 | 34.9% | -0.0164 | 0.4126 | -0.0626 | no |
| `index_rebalance_weight_up_pressure_1d` | 5 | -0.0521 | -0.248 | -1.53 | 42.1% | -0.0545 | 0.4149 | -0.0476 | no |
| `index_rebalance_remove_pressure_1d` | 5 | -0.0498 | -0.362 | -2.01 | 45.2% | -0.1454 | 0.4233 | -0.0406 | no |
| `index_rebalance_weight_up_pressure_1d` | 20 | -0.0478 | -0.212 | -1.31 | 42.1% | -0.0160 | 0.4020 | -0.0169 | no |
| `index_rebalance_abs_flow_pressure_1d` | 5 | 0.0260 | 0.145 | 0.95 | 55.8% | 0.0490 | 0.4065 | 0.0402 | no |
| `index_rebalance_remove_pressure_1d` | 20 | -0.0228 | -0.164 | -0.91 | 45.2% | -0.0100 | 0.4304 | -0.0444 | no |
| `index_rebalance_abs_flow_pressure_1d` | 20 | 0.0205 | 0.141 | 0.92 | 55.8% | -0.0019 | 0.3995 | 0.0494 | no |
| `index_rebalance_add_pressure_1d` | 20 | -0.0192 | -0.159 | -0.90 | 40.6% | -0.0095 | 0.4620 | 0.0132 | no |
| `index_rebalance_add_pressure_1d` | 5 | -0.0042 | -0.031 | -0.18 | 40.6% | -0.0736 | 0.4845 | -0.0128 | no |

## Interpretation

The passive-flow same-direction hypothesis did not survive. The larger raw effects were negative, weak after multiple-testing control, and generally failed size-neutral checks. The two `abs_flow` rows had small positive IC and size-neutral IC, but ICIR was too low and FDR did not pass.

The strong positive industry-neutral IC combined with negative raw or weak size-neutral IC is not promotion evidence. It is a diagnostic warning that event-date clustering, industry composition, or sparse event cohorts may dominate the signal. It requires a new pre-registered hypothesis before any contrarian or industry-relative repair can be tested.

## Decision

Round231 produced 5 new pre-registered factor names and 0 research leads. It produced no promotable factor and no portfolio candidate.

Forbidden follow-ups:

- no threshold tuning after zero leads;
- no portfolio grid after zero leads;
- no direction flip after reading the opposite-sign raw IC;
- no adding more index lists without a new orthogonal hypothesis.

Allowed follow-up:

- rotate Round232 to a different factor family, or separately pre-register a genuinely new index-rebalance contrarian/industry-relative hypothesis later.

## Evidence Files

- `data/reports/round231_index_rebalance_passive_flow_20260624/index_weight_pull_summary.json`
- `data/reports/round231_index_rebalance_passive_flow_20260624/index_rebalance_event_audit/index_rebalance_event_audit.json`
- `data/reports/round231_index_rebalance_passive_flow_20260624/round231_prescreen_input_summary.json`
- `data/reports/round231_index_rebalance_passive_flow_20260624/prescreen/index_rebalance_passive_flow_prescreen.json`
- `data/reports/round231_index_rebalance_passive_flow_20260624/prescreen/index_rebalance_passive_flow_prescreen_results.csv`
