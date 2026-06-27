# CN Stock Round392 - ADX Dragon-Hot Self-Risk Overlay

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Round392 tested whether a point-in-time self-risk budget improves the Dragon-Hot and ADX-on-Dragon event lanes.

The self-risk rules only use prior closed strategy event returns, so they are suitable as simulation risk-budget observations if later replay checks pass.

## Output

- Overlay: `data/reports/round392_24h_profit_sprint_adx_dragon_self_risk_20260627`
- OOS: `data/reports/round392_24h_profit_sprint_adx_dragon_self_risk_oos_20260627`
- Block audit: `data/reports/round392_24h_profit_sprint_adx_dragon_self_risk_block_audit_20260627`
- Beta audit: `data/reports/round392_24h_profit_sprint_adx_dragon_self_risk_beta_audit_20260627`

## Main Comparison

| Candidate | Ann | Total | Sharpe | Overlap Sharpe | Max DD | Worst Year |
|---|---:|---:|---:|---:|---:|---|
| Dragon-Hot 100 | 6.45% | 1.8120 | 0.987 | 0.5324 | -28.57% | -19.30% |
| Dragon-Hot roll21 neg half | 6.71% | 1.9310 | 1.173 | 0.6172 | -15.46% | -10.27% |
| ADX-on-Dragon 100 | 6.44% | 1.8082 | 1.097 | 0.5936 | -24.12% | -15.36% |
| ADX-on-Dragon roll21 neg half | 6.58% | 1.8705 | 1.281 | 0.6730 | -13.02% | -8.00% |
| ADX-on-Dragon roll21 -2% cash | 6.23% | 1.7200 | 1.200 | 0.6289 | -12.20% | -3.18% |

OOS split:

| Candidate | Mean OOS Ann | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| Dragon-Hot 100 | 8.02% | 0.8693 | -23.68% | 90.0% |
| Dragon-Hot roll21 neg half | 7.20% | 0.8536 | -12.75% | 90.0% |
| ADX-on-Dragon 100 | 8.04% | 0.9612 | -19.42% | 90.0% |
| ADX-on-Dragon roll21 neg half | 7.15% | 0.9262 | -11.42% | 90.0% |

ZZ500 beta audit:

| Candidate | Beta | R2 | Hedged Ann | Hedged Overlap | Hedged DD |
|---|---:|---:|---:|---:|---:|
| Dragon-Hot roll21 neg half | 0.0333 | 0.2348 | 6.68% | 0.9786 | -9.49% |
| ADX-on-Dragon roll21 neg half | 0.0294 | 0.2290 | 6.54% | 1.0388 | -8.98% |
| ADX-on-Dragon roll21 -2% cash | 0.0271 | 0.1892 | 6.20% | 0.9146 | -11.51% |

## Decision

Self-risk overlay is more useful than adding another stock-selection factor name.

`roll21_sum_neg_half` remains the best simple risk-budget rule for drawdown control. It reduces OOS drawdown sharply while preserving a reasonable full-sample return. The ADX version further improves risk metrics but gives up some OOS return.

## Process Lesson

The highest-value work at this point is not expanding more public indicator windows. It is packaging a small number of primary lanes with point-in-time risk-budget controls, then enforcing cost, beta, block, OOS, and coverage gates.
