# CN Stock Round246 Accounting Quality Statement Event Drift

Date: 2026-06-25
Machine: office_desktop
Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
Task: factor_validation

## Objective

Round246 rotated away from more raw accounting-quality formula tuning and tested a public-method-inspired post-announcement underreaction idea:

`aq_cash_conversion_muted_reaction_drift`

The candidate combines statement cash-conversion improvement with muted post-announcement price reaction. This is intended to test whether improving accounting quality that is not immediately priced can drift after the true announcement date.

## Candidate

Formula:

```text
0.5 * within-date rank(earnings_cash_conversion_improvement_yoy_raw)
+ 0.5 * within-date rank(-abs(signal_close / pre_announcement_close - 1))
```

Parameters:

- Source factor: `earnings_cash_conversion_improvement_yoy_raw`
- Event reaction: last close before `ann_date` to `signal_date` close
- Factor date: existing `signal_date`
- Horizons: 5 and 20 trading days
- Execution lag: 1
- Candidate count: 1

## PIT Controls

- `signal_date` must be strictly after `ann_date`.
- Same-day announcement trading remains blocked.
- The event reaction is only measured by the close of `signal_date`.
- Forward-return entry is after the factor date through `execution_lag=1`.
- Final holdout remains excluded.
- This is an IC shape and neutralization prescreen only, not a portfolio or profitability claim.

## Run

Output:

```text
data/reports/round246_accounting_quality_statement_event_drift_residual_ic_130_symbol_20260625
```

Data:

- Statement roots: 56 accumulated processed roots
- Bar roots:
  - `data/processed/cn_stock_long_history_2015_202306`
  - `data/processed/office_desktop_20260616_combined_research`
- Daily-basic roots:
  - `data/processed/cn_stock_long_history_2015_202306`
  - `data/processed/office_desktop_20260617_daily_basic_factor_inputs`
- Stock basic: `data/processed/cn_stock_metadata`

Command shape:

```powershell
.\.venv\Scripts\python.exe scripts\run_accounting_quality_statement_residual_ic_shape_prescreen.py `
  --statement-root <56 statement roots> `
  --bars-root data\processed\cn_stock_long_history_2015_202306 `
  --bars-root data\processed\office_desktop_20260616_combined_research `
  --stock-basic data\processed\cn_stock_metadata `
  --daily-basic-root data\processed\cn_stock_long_history_2015_202306 `
  --daily-basic-root data\processed\office_desktop_20260617_daily_basic_factor_inputs `
  --output-dir data\reports\round246_accounting_quality_statement_event_drift_residual_ic_130_symbol_20260625 `
  --factor-mode statement_event_drift `
  --horizon 5 `
  --horizon 20
```

## Data Coverage

- Bar assets: 130
- Bar rows: 332,562
- Bar window: 2015-01-05 to 2025-12-31
- Signal window: 2016-04-20 to 2025-11-11
- Label max date: 2025-12-23
- Factor rows: 4,786
- Label rows: 661,614
- Aligned rows: 9,572
- Tests: 2

## Results

| Factor | Horizon | IC | ICIR | t | p | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | LiqNeuIC | FDR | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `aq_cash_conversion_muted_reaction_drift` | 20 | 0.0373 | 0.264 | 1.52 | 0.1293 | 63.6% | -0.0002 | -0.0137 | 0.0347 | 0.0154 | no | no |
| `aq_cash_conversion_muted_reaction_drift` | 5 | -0.0196 | -0.139 | -0.80 | 0.4255 | 39.4% | -0.0059 | -0.1942 | -0.0128 | -0.0220 | no | no |

Summary:

- Multiple-testing leads: 0
- Neutral-gate passes: 0
- Research leads: 0
- Promotion allowed candidates: 0

## Decision

Rejected as a usable or promotable factor.

The 20-day IC has a weak positive sign, but it does not pass FDR, ICIR is low, the top-minus-bottom quantile spread is slightly negative, and industry-neutral IC turns negative. The 5-day horizon is directly negative. This means the construction is not finding a robust post-statement drift signal in the current 130-symbol long-cycle sample.

## Interpretation

This round improved the process even though it did not produce a profitable factor:

- It moved from repeated raw cash/accrual formula tuning into an event-context family.
- It reused public PEAD and underreaction intuition instead of blind factor mutation.
- It kept only one candidate, reducing multiple-testing pressure.
- It preserved PIT boundaries and blocked portfolio claims.
- It created a reusable `statement_event_drift` mode for future event-conditioned accounting tests.

The failure mode suggests that simple "good accounting quality plus muted total reaction" is too blunt. The next event-family attempt should not retest the same shape. More promising variants need an actual surprise or revision component, such as profitability revision acceleration, analyst/forecast update proxies, guidance-like event flags, or industry-relative earnings surprise context.

## Next Direction

`round247_accounting_quality_rotate_to_profitability_revision_or_event_context`

Recommended next step:

Test a profitability-revision or announcement-surprise family rather than another direct cash-conversion level formula. Keep the same constraints: one small preregistered candidate set, PIT announcement dates, no same-day event trading, long-cycle IC first, neutral gates before any portfolio conversion.
