# CN Stock PIT Profitability Event Revision Preregistration Round151

Date: 2026-06-23

Machine/task: office_desktop / factor_validation

Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`

Scope: CN A-share stock cross-sectional alpha research only.

## Why This Round Exists

Round150 rejected the lottery/MAX-effect family as a standalone long alpha. The family had measurable RankIC, but it did not translate into a clean monotonic long-side portfolio candidate.

Round151 rotates to a different economic source: point-in-time profitability information timing. This is deliberately not a repeat of the rejected Round96 static profitability-quality line. The new hypotheses use announcement timing, revisions, surprises, and cash-quality confirmation.

## What Ran

Output directory:

`data/reports/profitability_event_revision_preregistration_round151_20260623`

Entry point:

`python scripts\run_profitability_event_revision_preregistration.py --input-root data\processed\tushare_fina_indicator_shard1_full100_backfill_round95_20260622 --output-dir data\reports\profitability_event_revision_preregistration_round151_20260623 --min-assets 80 --min-passed-candidates 6`

Candidate-plan gate:

`python scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan data\reports\profitability_event_revision_preregistration_round151_20260623\profitability_event_revision_preregistration.json --gate-stage discovery --output-dir data\reports\factor_mining_candidate_plan_gate_round151_20260623`

## Data And Gate Results

| Item | Value |
|---|---:|
| PIT fina_indicator rows | 4,328 |
| Assets | 100 |
| Ann date range | 2015-04-15 to 2026-04-30 |
| Report period range | 2015-03-31 to 2025-12-31 |
| Duplicate financial keys | 0 |
| Missing PIT date rows | 0 |
| `ann_date < end_date` rows | 0 |
| Candidate count | 10 |
| Active candidate count | 7 |
| Frozen endpoint-dependent count | 3 |
| Candidate-plan control areas complete | 8 / 8 |
| Portfolio grid allowed | 0 |
| Promotion allowed | 0 |

The candidate-plan gate cleared discovery for the active subset only. It still blocks portfolio grids and promotion.

## Active Candidates

| Factor | Family | Coverage | Eligible assets | Status |
|---|---|---:|---:|---|
| `pit_fina_netprofit_yoy_revision_1q` | fina_revision_event | 97.69% | 100 | active |
| `pit_fina_revenue_profit_revision_spread_1q` | fina_revision_event | 97.69% | 100 | active |
| `pit_fina_margin_revision_yoy_4q` | margin_revision | 90.73% | 100 | active |
| `pit_fina_roe_revision_persistence_4q` | profitability_persistence_revision | 89.86% | 100 | active |
| `pit_fina_cash_profit_revision_4q` | cash_quality_surprise | 90.76% | 100 | active |
| `pit_fina_cash_earnings_confirmation_1q` | cash_quality_surprise | 100.00% | 100 | active |
| `pit_fina_quality_surprise_blend_1q` | revision_confirmation_blend | 96.77% | 100 | active |

## Frozen Candidates

These were logged for future endpoint work, but they are not active for Round152 until endpoint evidence exists:

- `pit_forecast_profit_revision_event_1q`
- `pit_express_profit_surprise_event_1q`
- `pit_forecast_express_quality_confirmation_1q`

## Optimization Controls Now Enforced

The Round151 candidate plan declares all eight required control areas before factor generation:

- A-share tradeability: limit up/down, suspension, ST, listing age, delisting risk, board permission.
- PIT financial timing: announcement/effective date lag, revision handling, release lag, no period-end-only signals.
- Industry/style separation: industry, size, value/low-vol/momentum/liquidity decomposition, residual factor matrix.
- ETF boundary: stock scope confirmed and ETF rotation evidence kept separate.
- Portfolio construction: risk budget, volatility budget, industry weights, turnover, stop/de-risk rules.
- Strict statistics: Deflated Sharpe, purged CPCV, White Reality Check or FDR, parameter sensitivity, cumulative multiple testing.
- China regime: policy liquidity, credit cycle, northbound/margin/turnover temperature, index state, signal-window regime coverage.
- Event controls: earnings, dividend/ex-rights, buyback/holder/unlock, index rebalance, event contamination audit.

## Decision

Round151 is successful as preregistration and process optimization, not as profitability evidence.

Allowed:

- Proceed to `round152_pit_profitability_event_revision_matrix_and_label_smoke`.
- Build PIT factor matrices for the seven active candidates only.
- Verify factor-value availability strictly after `ann_date`.

Blocked:

- No Sharpe, return, win-rate, or profit claim from Round151.
- No portfolio grid.
- No promotion or paper-ready claim.
- No use of forecast/express candidates until endpoint availability is proven.
- No revival of Round96 static profitability-quality names.

Next direction:

`round152_pit_profitability_event_revision_matrix_and_label_smoke`
