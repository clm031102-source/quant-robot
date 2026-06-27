# CN Stock Round374 - Event Calendar Parity Gate

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: simulation-readiness tooling. Research-to-review only; no broker, account, order, or live-trading access.

## Why This Round

Round373 found that the reusable low-turnover generation output does not reproduce the official Round339 base event stream. Round374 turns that mismatch into a reusable gate.

Reusable files added:

- `src/quant_robot/ops/shortlist_event_calendar_parity.py`
- `scripts/run_shortlist_event_calendar_parity.py`
- `tests/unit/test_shortlist_event_calendar_parity.py`

Output:

`data/reports/round374_24h_profit_sprint_event_calendar_parity_gate_20260627`

## Command

```powershell
.venv\Scripts\python.exe scripts\run_shortlist_event_calendar_parity.py `
  --reference data\reports\round339_24h_profit_sprint_replacement_filters_voltarget_wrappers_20260627\replace_drop_turnover_f_low10_base_period_returns.csv `
  --generated data\reports\round367_24h_profit_sprint_turnover_low_mainboard_prerank_replacement_20260627\replace_drop_turnover_f_low10_entry_cash_after_period_returns.csv `
  --generated-return-column entry_cash_proxy_return `
  --output-dir data\reports\round374_24h_profit_sprint_event_calendar_parity_gate_20260627 `
  --holding-period 20 `
  --periods-per-year 50.4 `
  --metric-tolerance 0.005 `
  --date-return-tolerance 0.0001
```

## Result

Status: blocked.

| Check | Value |
|---|---:|
| reference dates | 834 |
| generated dates | 868 |
| overlap dates | 736 |
| missing generated dates | 98 |
| extra generated dates | 132 |
| date return drift count | 261 |
| max absolute date return diff | 0.574% |

Metric diffs, generated minus reference:

| Metric | Diff |
|---|---:|
| total return | -6.26% |
| annualized return | -0.38% |
| Sharpe | -0.040 |
| overlap Sharpe | -0.021 |
| max drawdown | -1.71% |
| win rate | ~0.00% |

Blockers:

- `missing_generated_dates`;
- `extra_generated_dates`;
- `date_return_drift`;
- `metric_drift:total_return`;
- `metric_drift:sharpe`;
- `metric_drift:overlap_autocorr_adjusted_sharpe`;
- `metric_drift:max_drawdown`.

## Decision

The current reusable generation path is not simulation-ready.

Before any raw-generated event stream replaces the official event files, the generator must reproduce:

1. the official event calendar;
2. the official event-date return sums;
3. full-sample metrics within tolerance;
4. structured columns needed by replay: `decision_date`, `final_exposure`, and regime fields where applicable.

This gate should be mandatory before any future simulation handoff.
