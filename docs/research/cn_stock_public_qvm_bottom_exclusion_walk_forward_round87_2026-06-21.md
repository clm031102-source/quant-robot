# CN Stock Public QVM Bottom-Exclusion Walk-Forward Round87 - 2026-06-21

## Purpose

Round87 froze the two Round86 public QVM diagnostic leads and tested whether they could work as bottom-tail exclusion filters after costs, market impact, liquidity, and rolling out-of-sample validation.

Scope:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks only
- Factor source: `daily_basic_public_quality_value_momentum`
- Config: `configs/experiment_grid_cn_stock_public_qvm_bottom_exclusion_round87_20260621.json`
- Output: `data/reports/bottom_exclusion_walk_forward_public_qvm_round87_20260621`

Research only. No broker connection, no account reads, no order placement, and no live-trading action.

## Preregistered Leads

Only two Round86 leads were tested:

- `public_qvm_value_reversal_quality_20`
- `public_qvm_lowbeta_value_momentum_20`

No QVM weights, factor windows, bottom quantiles, exposure levels, or thresholds were tuned in this round.

## Command

```powershell
python scripts\run_bottom_exclusion_walk_forward.py --grid-config configs\experiment_grid_cn_stock_public_qvm_bottom_exclusion_round87_20260621.json --source authority-processed-bars --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --output-dir data\reports\bottom_exclusion_walk_forward_public_qvm_round87_20260621 --rolling-train-days 756 --rolling-test-days 252 --rolling-step-days 252 --min-accepted-folds 2 --bottom-quantile 0.2 --rebalance-interval 10 --holding-period 20 --cost-bps 10 --market-impact-bps 20 --max-participation-rate 0.01 --min-entry-amount 10000000 --portfolio-value 1000000 --target-gross-exposure 0.6 --min-positive-relative-fold-rate 0.6 --min-test-overlap-adjusted-sharpe 0.5 --max-test-drawdown-limit 0.5
```

Startup gate status:

- `startup_gate_cleared`: true
- blockers: none
- next direction before run: `round87_public_qvm_bottom_exclusion_costed_walk_forward`

## Validation Settings

| Setting | Value |
|---|---:|
| Rolling train days | 756 |
| Rolling test days | 252 |
| Rolling step days | 252 |
| Folds | 7 |
| Min accepted folds | 2 |
| Bottom exclusion quantile | 20% |
| Forward horizon | 20 bars |
| Rebalance interval | 10 bars |
| Cost | 10 bps |
| Market impact | 20 bps |
| Max participation | 1% ADV |
| Min entry amount | 10,000,000 |
| Portfolio value | 1,000,000 |
| Target gross exposure | 0.6 |
| Min positive relative fold rate | 60% |
| Min test overlap-adjusted Sharpe | 0.5 |
| Max test drawdown limit | 50% |

## Round87 Results

| Factor | Status | Accepted Folds | Mean Test Total | Mean Test Relative | Mean Test Overlap Sharpe | Worst Test DD | Mean Test Win Rate | Avg Holdings | Test Capacity-Limited |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `public_qvm_value_reversal_quality_20` | rejected | 0/7 | +0.50% | +1.07% | -0.0734 | -18.67% | 46.44% | 1291.3 | 0 |
| `public_qvm_lowbeta_value_momentum_20` | rejected | 0/7 | +0.13% | +0.69% | -0.0807 | -18.96% | 46.55% | 1291.3 | 0 |

Rejection reasons for both:

- `test_not_costed_risk_filter_candidate`
- `test_overlap_adjusted_sharpe_below_min`
- `accepted_folds_below_min`

Strict split:

- Status: pass
- Violations: 0

## Fold Detail

### `public_qvm_value_reversal_quality_20`

| Fold | Test Window | Test Total | Test Relative | Test Overlap Sharpe | Test DD | Test Win Rate | Capacity-Limited |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | 2018-02-05 to 2019-02-22 | -15.55% | +0.76% | -0.7988 | -18.67% | 25.32% | 0 |
| 2 | 2019-02-25 to 2020-03-06 | +2.76% | -1.25% | +0.1534 | -10.99% | 40.40% | 0 |
| 3 | 2020-03-09 to 2021-03-19 | +9.73% | +1.72% | +0.3780 | -7.19% | 54.70% | 0 |
| 4 | 2021-03-22 to 2022-04-01 | +5.18% | +1.81% | +0.3208 | -6.17% | 56.52% | 0 |
| 5 | 2022-04-06 to 2023-04-17 | +4.61% | +0.80% | +0.2854 | -6.22% | 55.45% | 0 |
| 6 | 2023-04-18 to 2024-05-13 | -13.74% | +2.74% | -1.1472 | -16.11% | 40.00% | 0 |
| 7 | 2024-05-14 to 2025-05-28 | +10.53% | +0.89% | +0.2945 | -8.47% | 52.69% | 0 |

### `public_qvm_lowbeta_value_momentum_20`

| Fold | Test Window | Test Total | Test Relative | Test Overlap Sharpe | Test DD | Test Win Rate | Capacity-Limited |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | 2018-02-05 to 2019-02-22 | -15.86% | +0.44% | -0.7870 | -18.96% | 24.69% | 0 |
| 2 | 2019-02-25 to 2020-03-06 | +2.78% | -1.23% | +0.1574 | -10.88% | 42.42% | 0 |
| 3 | 2020-03-09 to 2021-03-19 | +8.95% | +0.94% | +0.3506 | -7.05% | 54.70% | 0 |
| 4 | 2021-03-22 to 2022-04-01 | +5.34% | +1.97% | +0.3261 | -6.14% | 58.62% | 0 |
| 5 | 2022-04-06 to 2023-04-17 | +3.95% | +0.14% | +0.2437 | -6.40% | 52.48% | 0 |
| 6 | 2023-04-18 to 2024-05-13 | -13.94% | +2.53% | -1.1368 | -16.25% | 40.23% | 0 |
| 7 | 2024-05-14 to 2025-05-28 | +9.70% | +0.06% | +0.2810 | -8.52% | 52.69% | 0 |

## Interpretation

Positive evidence:

- Both signals produced slightly positive mean test relative return.
- Both signals stayed capacity-clean with 0 test capacity-limited trades.
- Strict train/test split passed with 0 violations.
- Absolute drawdown stayed within the broad 50% test limit.

Blocking evidence:

- Accepted folds were 0/7 for both factors.
- Mean test overlap-adjusted Sharpe was negative for both factors.
- The risk-filter classification never reached `costed_risk_filter_candidate`.
- Test win rate was below 47% on average.
- Two difficult windows, 2018-2019 and 2023-2024, had materially negative absolute returns and strongly negative overlap-adjusted Sharpe.

The small positive relative return means QVM has some weak loser-avoidance information, but not enough to create a robust costed bottom-exclusion portfolio.

## Decision

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- QVM continuation candidates: 0

Hibernate as promotion paths:

- QVM direct long-only TopN;
- QVM weight/window tuning;
- QVM bottom-exclusion walk-forward;
- treating positive relative return without positive overlap-adjusted Sharpe as useful alpha.

## Next Direction

Round88 should rotate away from QVM and stop using daily-basic valuation/liquidity proxies as a substitute for true profitability factors.

Next registered direction:

`round88_tushare_financial_profitability_quality_pit_readiness_audit`

Why:

- The user asked for profitable factors, and the project has mostly exhausted price-volume, low-turnover, public trend, RSRS, SuperTrend, and QVM proxy lines without a deployable result.
- QVM was capacity-clean but not profitable enough, which suggests the missing ingredient is not another QVM weight but better economic data.
- The next high-ROI check is whether local Tushare financial indicator data can support point-in-time profitability/quality factors such as ROE, ROA, gross margin, net profit growth, operating cash flow quality, accruals, and earnings revision proxies.

Round88 constraints:

- first audit availability and announcement-date / report-date fields;
- require point-in-time lag discipline before any financial factor backtest;
- pre-register a small set of profitability-quality factors only if the data is usable;
- if financial data is missing or not point-in-time safe, record the data gap instead of inventing more proxy factors.
