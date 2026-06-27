# CN Stock Round440 Anti-SuperTrend Formal Rebuild Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round438 showed a defensive projection lead from `cash_public_anti_supertrend_top10`. Round440 tests whether that defensive value survives the same formal cohort-entry rebuild used for the default delayed-exit candidate.

## Formal Rebuild

Command output:

- `data/reports/round440_24h_profit_sprint_delayed_exit_anti_supertrend_cash_formal_rebuild_20260627`

Construction:

- trade source: `data/reports/round432_24h_profit_sprint_delayed_exit_return_repair_20260627/delayed_exit_trade_rows.csv`;
- return column: `delayed_exit_weighted_return`;
- exit date column: `delayed_exit_date`;
- Dragon-Tiger cash filter: `dragon_hot_chase_20d`;
- public factor: `supertrend_volume_confirmed_10_3_20`;
- side: top 10%;
- multiplier: 0.00x, meaning the flagged public-factor trades are cashed;
- entry-timed vol target: 8%, 84-event lookback, max exposure 1.00;
- entry-timed self-risk: prior 21 closed events below 0 gets 0.80x exposure.

Coverage:

- candidate-universe trades: 26,090;
- factor-matched trades: 4,278;
- missing factor share: 83.60%;
- public-cashed trades: 725.

## Result

The formal rebuild failed. The defensive projection did not survive cohort-entry reconstruction.

| Candidate | Annualized | Total Return | Sharpe | Overlap Sharpe | Max DD | Win Rate | Leave-One-Year Min Ann. | Best 3M Log Share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `base` | 6.663% | 218.46% | 0.968 | 0.496 | -26.21% | 41.33% | 5.001% | 45.72% |
| `formal_anti_supertrend_cash` | 5.768% | 173.74% | 0.904 | 0.468 | -27.54% | 41.22% | 4.289% | 47.26% |

## OOS And Beta

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Strict OOS Pass | Worst OOS DD | Beta-Hedged Ann. | Beta-Hedged Overlap | Beta-Hedged DD | Alpha t-stat |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `base` | 10.043% | 0.831 | 90.00% | -19.30% | 7.502% | 0.797 | -12.67% | 4.40 |
| `formal_anti_supertrend_cash` | 8.906% | 0.810 | 76.67% | -18.05% | 6.479% | 0.763 | -11.48% | 4.11 |

The cash overlay reduces worst OOS drawdown and beta-hedged drawdown, but the cost is too high:

- annualized return drops by about 0.90 percentage points;
- total return drops by about 44.72 percentage points;
- overlap Sharpe weakens;
- OOS strict pass rate falls from 90.00% to 76.67%;
- the factor has 83.60% missing coverage in the selected-trade universe.

## Decision

Reject `round440_delayed_exit_anti_supertrend_top10_cash` as a paper-simulation candidate.

This also rejects the current public-technical overlay line as a useful route for the 24h sprint. RSRS z and anti-supertrend both looked better in projection than in formal reconstruction.

Next direction:

- rotate away from public technical overlays;
- prioritize event-context underreaction, tradeability/liquidity microstructure, or daily-basic non-price quality only if point-in-time and coverage gates are already available;
- keep the delayed-exit baseline as the active default.
