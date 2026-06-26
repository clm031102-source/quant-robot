# CN Stock Public QVM Bottom-Exclusion Preregistration Round87 - 2026-06-21

## Scope

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks only
- Not scope: CN ETF rotation, live trading, broker/account/order actions

Round87 follows the Round86 decision: the public QVM factors are not promotable as direct long-only TopN strategies, but two of them still showed positive RankIC and capacity-clean implementation.

## Frozen Leads

Only these Round86 diagnostic leads are eligible:

| Factor | Round86 Evidence | Round86 Blocker |
|---|---|---|
| `public_qvm_value_reversal_quality_20` | total return +91.21%, Sharpe 0.419, overlap Sharpe 0.226, RankIC 0.0724, IC t 9.43, capacity-limited trades 0 | drawdown -47.71%, relative return -2282.54%, calendar-limited trades 204 |
| `public_qvm_lowbeta_value_momentum_20` | total return +74.10%, Sharpe 0.363, overlap Sharpe 0.197, RankIC 0.0693, IC t 8.93, capacity-limited trades 0 | drawdown -49.79%, relative return -2299.65%, calendar-limited trades 201 |

No new QVM weights, windows, factor definitions, bottom quantiles, or exposure levels are tuned in this round.

## Hypothesis

The QVM signals may rank fragile stocks well enough to avoid bottom-tail risk even though direct long-only buying fails. Round87 therefore tests the translation-layer question:

> If the bottom 20% ranked stocks are excluded and the kept universe is held with costs and capacity controls, does the signal improve out-of-sample relative performance with acceptable risk?

This is a risk-filter validation, not a promotion grid.

## Fixed Validation Settings

| Setting | Value |
|---|---:|
| Period | 2015-01-05 to 2025-12-31 |
| Rolling train days | 756 |
| Rolling test days | 252 |
| Rolling step days | 252 |
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

## Promotion Rules

A candidate cannot advance unless:

- strict train/test split has zero violations;
- accepted folds >= 2;
- mean test relative return is positive;
- mean test overlap-adjusted Sharpe is at least 0.5;
- worst test drawdown stays within the 50% limit;
- test capacity-limited trades are zero;
- result is positive after cost and market-impact assumptions.

Failure means QVM is hibernated as an immediate promotion path and the next round rotates away from QVM.

## Command

```powershell
python scripts\run_bottom_exclusion_walk_forward.py `
  --grid-config configs\experiment_grid_cn_stock_public_qvm_bottom_exclusion_round87_20260621.json `
  --source authority-processed-bars `
  --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json `
  --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json `
  --output-dir data\reports\bottom_exclusion_walk_forward_public_qvm_round87_20260621 `
  --rolling-train-days 756 `
  --rolling-test-days 252 `
  --rolling-step-days 252 `
  --min-accepted-folds 2 `
  --bottom-quantile 0.2 `
  --rebalance-interval 10 `
  --holding-period 20 `
  --cost-bps 10 `
  --market-impact-bps 20 `
  --max-participation-rate 0.01 `
  --min-entry-amount 10000000 `
  --portfolio-value 1000000 `
  --target-gross-exposure 0.6 `
  --min-positive-relative-fold-rate 0.6 `
  --min-test-overlap-adjusted-sharpe 0.5 `
  --max-test-drawdown-limit 0.5
```
