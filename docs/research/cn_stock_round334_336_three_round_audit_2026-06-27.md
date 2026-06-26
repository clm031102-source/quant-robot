# CN Stock Round334-336 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Rounds Audited

| Round | Direction | Outcome |
|---:|---|---|
| 334 | Combine `cash_low_turnover_f_bottom20` with volatility-target overlays | Superseded because zero-return dates were dropped in overlay input |
| 335 | Calendar-corrected cash exclusion + volatility target | Corrected evidence; cash exclusion is useful, overlay is secondary |
| 336 | Public technical indicators as cash filters on turnover-low base | Rejected as direct filters; useful only as risk labels |

## Main Audit Finding

The main improvement in this block was not a new alpha. It was a measurement correction.

Round334 looked stronger because it annualized over 690 non-zero event dates instead of the full 834 exit-date calendar. Round335 fixed this and became the authoritative version.

## Corrected Evidence

Best corrected cash exclusion + overlay row:

`cash_low_turnover_f_bottom20 + vol_target_5_lb84`

- total return: +137.10%;
- annualized return: +5.36%;
- Sharpe: 0.984;
- overlap Sharpe: 0.533;
- max drawdown: -21.98%;
- event rows: 834.

Best corrected cross-split wrapper:

`cash_low_turnover_f_bottom20 + vol_target_4_lb168`

- mean OOS annualized return: +5.84%;
- mean OOS overlap Sharpe: 0.660;
- worst OOS drawdown: -16.13%.

## Public Indicator Result

Round336 tested 22 public indicators and 66 filter hypotheses.

Best OOS public filter:

`cash_public_bollinger_reversal_20_failure_worst_top20`

- mean OOS annualized return: +5.11%;
- mean OOS overlap Sharpe: 0.617;
- worst OOS drawdown: -15.76%.

But full-sample performance was weaker than the current `cash_low_turnover_f_bottom20` baseline:

- public filter overlap Sharpe: about 0.36;
- baseline overlap Sharpe: 0.414;
- public filter annualized return: about +3.6%;
- baseline annualized return: +4.52%.

Decision: do not promote public indicator cash filters.

## Direction Change

Do not continue direct public-indicator cash filters.

Do not tune volatility-target parameters further unless attached to a stronger base portfolio.

Next direction:

1. replacement construction instead of cash-only exclusion;
2. keep full calendar and entry-date decision alignment;
3. keep Round322/Round333 data quarantine as mandatory;
4. compare every new portfolio against both `entry_cash_no_extra_filter` and `cash_low_turnover_f_bottom20`.

## Process Rule Added

Before any future candidate is called useful, verify:

- 834-event calendar or explicitly documented event count;
- baseline reproduction against Round322/Round333;
- data quarantine parity: `CN_XBEI` excluded and extreme daily-return quarantine applied;
- 2026 holdout untouched;
- cross-split OOS and 2017-2018 regime audit included.
