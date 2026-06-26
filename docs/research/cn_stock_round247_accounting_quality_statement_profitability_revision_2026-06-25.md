# CN Stock Round247 Accounting Quality Statement Profitability Revision

Date: 2026-06-25
Machine: office_desktop
Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
Task: factor_validation

## Objective

Round247 followed the Round246 rejection and tested a small realized-statement profitability revision family instead of continuing cash-conversion or event-reaction tuning.

The goal was to check whether year-over-year profitability acceleration has predictive power when it is:

- confirmed by operating cashflow; or
- penalized for aggressive asset expansion.

This is still a residual IC and neutralization prescreen only. It is not a Sharpe, annual return, win-rate, drawdown, portfolio, paper, or live-trading claim.

## Candidates

| Factor | Formula | Intuition |
|---|---|---|
| `aq_profitability_revision_cash_confirmed` | `delta_4q(netprofit / total_assets) + delta_4q(n_cashflow_act / total_assets)` | Profit acceleration should be more credible when operating cashflow accelerates too. |
| `aq_profitability_revision_asset_disciplined` | `delta_4q(netprofit / total_assets) - abs(pct_change_4q(total_assets))` | Profit acceleration should be more credible when it is not bought through aggressive balance-sheet expansion. |

## PIT Controls

- `signal_date` is the first trade date strictly after `ann_date`.
- Same-day announcement trading remains blocked.
- Label entry is after the factor date through `execution_lag=1`.
- Final holdout remains excluded.
- Multiple testing is counted across `2 factors x 2 horizons = 4 tests`.

## Run

Output:

```text
data/reports/round247_accounting_quality_statement_profitability_revision_residual_ic_130_symbol_20260625
```

Command source:

- Reused the 56 statement roots recorded by the Round246 report.
- Bar roots:
  - `data/processed/cn_stock_long_history_2015_202306`
  - `data/processed/office_desktop_20260616_combined_research`
- Daily-basic roots:
  - `data/processed/cn_stock_long_history_2015_202306`
  - `data/processed/office_desktop_20260617_daily_basic_factor_inputs`
- Stock basic: `data/processed/cn_stock_metadata`

CLI mode:

```text
--factor-mode statement_profitability_revision
```

## Data Coverage

- Bar assets: 130
- Bar rows: 332,562
- Bar window: 2015-01-05 to 2025-12-31
- Signal window: 2016-04-20 to 2025-11-11
- Label max date: 2025-12-23
- Factor rows: 9,651
- Label rows: 661,614
- Aligned rows: 19,302
- Candidate count: 2
- Tests: 4

## Results

| Factor | H | IC | ICIR | t | p | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | LiqNeuIC | FDR | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `aq_profitability_revision_cash_confirmed` | 5 | -0.0483 | -0.332 | -1.91 | 0.0563 | 30.3% | -0.0053 | -0.1491 | -0.0458 | -0.0428 | no | no |
| `aq_profitability_revision_asset_disciplined` | 5 | -0.0402 | -0.263 | -1.53 | 0.1249 | 32.4% | 0.0004 | 0.1500 | -0.0433 | -0.0347 | no | no |
| `aq_profitability_revision_cash_confirmed` | 20 | -0.0241 | -0.195 | -1.12 | 0.2615 | 42.4% | -0.0035 | -0.1080 | -0.0140 | -0.0175 | no | no |
| `aq_profitability_revision_asset_disciplined` | 20 | -0.0073 | -0.042 | -0.24 | 0.8065 | 47.1% | -0.0024 | -0.1815 | -0.0092 | -0.0019 | no | no |

Summary:

- Multiple-testing leads: 0
- Neutral-gate passes: 0
- Research leads: 0
- Promotion allowed candidates: 0
- Walk-forward allowed candidates: 0

## Decision

Rejected.

Both factors are negative or near zero on raw IC, fail FDR, fail neutral gates, and have weak or negative quantile shape. The `cash_confirmed` candidate is actively wrong in this sample at both horizons. The `asset_disciplined` variant has a positive 5-day industry-neutral IC, but size and liquidity neutral ICs are negative and the raw IC is negative.

## Interpretation

This result is useful because it prevents another expensive tuning loop. Realized statement profitability acceleration, as currently constructed from net profit, operating cashflow, and total assets, is not enough. The signal likely needs information that is closer to true surprise or forecast revision:

- analyst forecast revision or consensus surprise;
- explicit earnings preview or guidance-like event context;
- industry-relative profitability surprise rather than absolute realized acceleration;
- management action or event tags around buybacks, dividends, pledges, unlocks, or ownership changes;
- a larger statement universe before revisiting weak watchlist accounting clues.

## Next Direction

`round248_rotate_to_external_revision_or_nonfinancial_event_context`

Do not keep mutating the same realized statement formula family. The correct next step is a family rotation toward actual expectation-revision/event information or nonfinancial event context, while preserving the same gates: PIT timing, long-cycle residual IC, neutralization, multiple-testing accounting, no portfolio grid before a real lead, and no final-holdout read.
