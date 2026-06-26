# CN Stock PIT Profitability Event Revision Matrix Label Smoke Round152

Date: 2026-06-23

Machine/task: office_desktop / factor_validation

Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`

Scope: CN A-share stock cross-sectional alpha research only.

## What Ran

Round152 tested whether the seven active Round151 PIT profitability event/revision candidates can be converted into factor values and safely joined to forward-return labels.

Output directory:

`data/reports/profitability_event_revision_matrix_label_smoke_round152_20260623`

Entry point:

`python scripts\run_profitability_event_revision_matrix_label_smoke.py --financial-root data\processed\tushare_fina_indicator_shard1_full100_backfill_round95_20260622 --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --preregistration-json data\reports\profitability_event_revision_preregistration_round151_20260623\profitability_event_revision_preregistration.json --candidate-plan-gate-json data\reports\factor_mining_candidate_plan_gate_round151_20260623\factor_mining_candidate_plan_gate.json --output-dir data\reports\profitability_event_revision_matrix_label_smoke_round152_20260623 --horizon 5 --horizon 20 --execution-lag 1 --min-label-coverage 0.6`

## Results

| Metric | Value |
|---|---:|
| Active candidates | 7 |
| Frozen endpoint-dependent candidates | 3 |
| Unknown active candidates | 0 |
| PIT financial rows | 4,328 |
| Financial assets | 100 |
| Bar rows | 266,894 |
| Bar assets | 100 |
| Factor value rows | 28,680 |
| Forward-label rows | 531,088 |
| Factor-label aligned rows | 57,360 |
| Label coverage | 100.00% |
| Alignment violations | 0 |
| Horizons | 5, 20 |
| Execution lag | 1 |
| Promotion allowed | 0 |
| Portfolio allowed | 0 |

## Candidate Coverage

| Factor | Factor rows | Label rows | Coverage | Violations |
|---|---:|---:|---:|---:|
| `pit_fina_cash_earnings_confirmation_1q` | 4,325 | 8,650 | 100.00% | 0 |
| `pit_fina_cash_profit_revision_4q` | 3,927 | 7,854 | 100.00% | 0 |
| `pit_fina_margin_revision_yoy_4q` | 3,925 | 7,850 | 100.00% | 0 |
| `pit_fina_netprofit_yoy_revision_1q` | 4,227 | 8,454 | 100.00% | 0 |
| `pit_fina_quality_surprise_blend_1q` | 4,180 | 8,360 | 100.00% | 0 |
| `pit_fina_revenue_profit_revision_spread_1q` | 4,227 | 8,454 | 100.00% | 0 |
| `pit_fina_roe_revision_persistence_4q` | 3,869 | 7,738 | 100.00% | 0 |

## Interpretation

Round152 passed. This means the seven active PIT profitability revision candidates are technically safe to send into a controlled IC/neutral prescreen.

This does not mean any candidate is profitable. Round152 did not compute IC, Sharpe, total return, profit rate, win rate, drawdown, or portfolio results.

The important evidence is alignment:

- signal date is the first tradable bar strictly after `ann_date`;
- same-day announcement trading is disallowed;
- label entry date is strictly after signal date;
- no active formula is unknown;
- frozen forecast/express candidates remain inactive.

## Decision

Proceed to:

`round153_pit_profitability_event_revision_controlled_ic_neutral_prescreen`

Round153 must include:

- mean Spearman IC, ICIR, t-stat, p-value, and FDR across 7 factors x 2 horizons;
- minimum cross-section checks by signal date;
- quantile spread and monotonicity;
- industry-neutral IC;
- size/liquidity-neutral IC where data exists;
- reference de-dup against the rejected Round96 static profitability-quality family;
- portfolio and promotion still blocked until a later walk-forward/cost/capacity/regime gate.
