# CN Stock Public QVM Capacity-Safe Preregistration Round86 - 2026-06-21

## Scope

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks only
- Not scope: CN ETF rotation, live trading, broker/account/order actions

Round86 follows the Round85 decision to hibernate raw low-turnover direct TopN work. The new family is a small, public-anomaly composite line instead of another liquidity-only sweep.

## Hypothesis

Public factor literature repeatedly motivates value, quality/low-volatility, and momentum as simple, economically interpretable anomalies. The Round86 test asks whether a capacity-safe blend of those effects can produce a cleaner CN stock long-only portfolio than the low-turnover line.

This is not a promotion claim. It is a frozen long-cycle replay before any walk-forward validation.

## Pre-Registered Candidates

| Factor | Economic Thesis | Main Components | Direction |
|---|---|---|---|
| `public_qvm_value_momentum_lowvol_20` | Cheap stocks with positive medium-term trend and low realized downside risk may have better risk-adjusted continuation. | PB/PE/PS inverse, 20-bar momentum, skip-5 momentum, downside/realized vol, liquidity quality | higher is better |
| `public_qvm_dividend_quality_momentum_20` | Dividend/value names with quality and non-fragile momentum may avoid distressed cheap traps. | dividend yield, value, low-vol quality, momentum | higher is better |
| `public_qvm_value_reversal_quality_20` | Cheap names after short-term pullback can work only when low-tail quality is acceptable. | value, 5-bar reversal, low-vol/efficiency quality | higher is better |
| `public_qvm_lowbeta_value_momentum_20` | Low-volatility value with moderate trend is a capacity-friendlier public anomaly blend. | value, momentum, realized vol, high-low range | higher is better |

## Built-In Candidate Gates

Each factor:

- uses only same-day or trailing bars and daily-basic inputs;
- trades next period through `execution_lag=1`;
- applies a cross-sectional tradeability gate before size-bucket ranking;
- ranks within market/date size buckets to reduce small-cap dominance;
- does not include raw low-turnover as a primary return engine.

## Replay Settings

| Setting | Value |
|---|---:|
| Period | 2015-01-05 to 2025-12-31 |
| TopN | 100 |
| Cost | 10 bps |
| Market impact | 20 bps |
| Max participation | 1% ADV |
| Signal-date amount gate | 10,000,000 |
| Max calendar holding | 60 days |
| Forward horizon | 20 bars |
| Rebalance interval | 5 bars |
| Factor matrix reuse | enabled |

## Promotion Rules

A candidate cannot advance unless it survives:

- positive total and relative return after costs and impact;
- acceptable drawdown under the configured decision gate;
- no capacity-limited or calendar-limited trades;
- overlap-aware Sharpe, tail IC, and RankIC review;
- later walk-forward validation if long-cycle replay is good enough.

## Command

```powershell
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_stock_public_qvm_capacity_safe_round86_20260621.json --source authority-processed-bars --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --data-manifest-packet data\reports\cn_stock_data_manifest_round83_daily_basic\cn_stock_data_manifest.json --allow-review-required-data-manifest
```
