# CN Stock Round449 Trade Group And Entry Execution Risk Audit

Date: 2026-06-27

Scope: audit the frozen Round339 `replace_drop_turnover_f_low10_vol_target_6_lb84`
trade tape for group concentration, entry/exit tradeability loss, and entry-known
attribute cash projections. This is a diagnostic audit only; the 2026 final
holdout remains sealed.

## Inputs

- Trades: `data/reports/round338_24h_profit_sprint_turnover_low_replacement_filters_quarantine_corrected_20260627/replace_drop_turnover_f_low10_trades_with_tradeability.parquet`
- Return template: `data/reports/round339_24h_profit_sprint_replacement_filters_voltarget_wrappers_20260627/replace_drop_turnover_f_low10_vol_target_6_lb84_exit_date_returns.csv`
- Group contribution output: `data/reports/round449_24h_profit_sprint_trade_group_contribution_20260627`
- Exposure audit output: `data/reports/round449_24h_profit_sprint_trade_exposure_audit_20260627`
- Attribute projection output: `data/reports/round449_24h_profit_sprint_trade_attribute_projection_20260627`
- Incremental robustness output: `data/reports/round449_24h_profit_sprint_trade_attribute_incremental_robustness_20260627`
- Block audit output: `data/reports/round449_24h_profit_sprint_trade_attribute_block_audit_20260627`

## Baseline

`replace_drop_turnover_f_low10_vol_target_6_lb84`:

- Annualized return: 6.352%
- Total return: +177.08%
- Sharpe: 0.960
- Overlap-adjusted Sharpe: 0.517
- Max drawdown: -28.88%
- Period win rate: 41.13%

## Group And Exposure Findings

Total trade rows: 26,450. Total contribution audited on
`entry_cash_proxy_weighted_return`: 0.9482.

The most important structural risk is not industry. Industry concentration did
not breach the audit thresholds: average HHI was 0.070 and p95 top-weight share
was 0.36. The real concentration is board/exchange/connect-tag exposure:

- Stock-market blockers: top-weight-share p95 too high, average HHI too high,
  and single-group absolute return share too high.
- Exchange blockers: top-weight-share p95 too high, average HHI too high, and
  single-group absolute return share too high.
- `is_hs` blockers: top-weight-share p95 too high, average HHI too high, and
  single-group absolute return share too high.

Contribution is dominated by main-board/XSHG/HS-H style exposure:

- Main board contributes about 97.93% of total contribution.
- XSHG contributes about 79.03% of absolute return contribution.
- HS-H contributes about 66.96% of absolute return contribution.

This is a simulation disclosure and risk-budget item, not a reason to blindly
filter away SZSE or non-HS names. Direct `XSHE`, `non_xshg`, and `non_hs`
cash projections all reduced total and annualized return.

Entry and exit limit-down states are economically important:

- Entry `limit_down_like;limit_down_official` contribution: -0.04199 from 178
  trades.
- Exit `limit_down_like;limit_down_official` contribution: -0.04592 from 193
  trades.
- Exit `limit_up_like;limit_up_official` contribution is positive, so the
  symmetric "cash all limit states" shortcut is not supported.

## Attribute Projection Results

Projection results cash selected trades in the frozen official-template return
series. They are not final simulation evidence.

Clean entry-known execution candidate:

- `cash_entry_limit_down`
- Condition: `entry_blocked_reasons == limit_down_like;limit_down_official`
- Annualized return: 6.626%
- Total return: +189.11%
- Overlap-adjusted Sharpe: 0.547
- Max drawdown: -28.87%
- Delta annualized return: +0.274%
- Delta total return: +12.03%
- Delta overlap Sharpe: +0.030
- Delta max drawdown: +0.01%
- CPCV annualized-win rate: 70.83%
- Bootstrap annualized-win rate: 74.80%
- Year win rate: 45.45%

Diagnostic-only future-information candidate:

- `cash_exit_limit_down_diag`
- Delta annualized return: +0.289%
- Delta total return: +12.73%
- Delta overlap Sharpe: +0.036
- Delta max drawdown: +0.81%
- It uses exit-time information and cannot be an entry factor.

Full-sample industry blacklist diagnostic:

- Worst-10 industry cash projection delta annualized return: +0.443%
- Delta total return: +19.73%
- Delta overlap Sharpe: +0.063
- Delta max drawdown: +2.07%
- CPCV annualized-win rate: 94.17%
- Bootstrap annualized-win rate: 97.10%
- Bootstrap strict-pass rate: 85.40%
- Year win rate: 63.64%

Despite strong numbers, the industry blacklist was selected from the same
full-sample contribution table. It is a data-snooping candidate, not a
promotable factor. It must be rebuilt from an external/economic hypothesis and
pre-registered before any simulation discussion.

Rejected or diagnostic-only projections:

- `metadata_missing`: lower return than baseline.
- `non_hs`: lower annualized and total return.
- `xshe`: lower annualized and total return.
- `non_xshg`: lower annualized and total return.
- `exit_limit_down_diag`: future/exit-time information only.

## Decision

Round449 promotes 0 new independent alpha factors.

Keep `entry_limit_down` as an execution-layer observation only. It is
entry-known and economically plausible, but the year win rate is weak and the
current result is still a projection. The only acceptable next step is a formal
cohort-entry rebuild where limit-down entry treatment is part of the event
generator before vol/self-risk and cost processing.

Keep the industry blacklist as a diagnostic warning only. Do not add it to the
paper-simulation handoff, do not tune industry lists, and do not call it alpha
until it is justified ex ante and rebuilt formally.

Next direction: either formalize the entry-limit-down execution rule at
cohort-entry granularity, or rotate to a genuinely new point-in-time data
source. Do not continue valuation/industry threshold widening.

Safety: research-to-review only. No broker access, no account reads, no orders,
and no live trading.
