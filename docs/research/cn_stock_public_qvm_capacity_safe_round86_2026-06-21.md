# CN Stock Public QVM Capacity-Safe Replay Round86 - 2026-06-21

## Purpose

Round86 tested a small pre-registered public anomaly family after Round85 hibernated the raw low-turnover line.

Scope:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks only
- Factor source: `daily_basic_public_quality_value_momentum`
- Config: `configs/experiment_grid_cn_stock_public_qvm_capacity_safe_round86_20260621.json`
- Output: `data/reports/experiment_grid_cn_stock_public_qvm_capacity_safe_round86_20260621`

Research only. No broker connection, no account reads, no order placement, and no live-trading action.

## What Was Built

Round86 added a reusable public quality/value/momentum factor source:

- `public_qvm_value_momentum_lowvol_20`
- `public_qvm_dividend_quality_momentum_20`
- `public_qvm_value_reversal_quality_20`
- `public_qvm_lowbeta_value_momentum_20`

Design constraints:

- only same-day or trailing bars and daily-basic inputs;
- trade next period through `execution_lag=1`;
- cross-sectional tradeability gate before size-bucket ranking;
- size-bucket percentile ranks to reduce small-cap dominance;
- no raw low-turnover primary return engine.

The source was added with TDD and wired into both the single research pipeline and experiment-grid precompute path.

## Command

```powershell
python scripts\run_experiment_grid.py --config configs\experiment_grid_cn_stock_public_qvm_capacity_safe_round86_20260621.json --source authority-processed-bars --data-root configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --authority-bars-config configs\cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --data-manifest-packet data\reports\cn_stock_data_manifest_round83_daily_basic\cn_stock_data_manifest.json --allow-review-required-data-manifest
```

Startup gate status:

- `startup_gate_cleared`: true
- blockers: none
- next direction before run: `round86_capacity_safe_public_quality_value_momentum_composite`

Runtime evidence:

- bars loaded: 8,416,451
- precomputed factor rows: 33,665,804
- cases: 4
- completed: 4
- failed: 0
- no trades: 0

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

## Round86 Results

| Factor | Total Return | Annual Return | Sharpe | Overlap Sharpe | Max DD | Win Rate | Relative Return | RankIC | RankIC t | Tail RankIC t | Calendar-Limited | Capacity-Limited | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `public_qvm_value_reversal_quality_20` | +91.21% | 3.71% | 0.419 | 0.226 | -47.71% | 51.11% | -2282.54% | 0.0724 | 9.43 | 1.40 | 204 | 0 | rejected |
| `public_qvm_lowbeta_value_momentum_20` | +74.10% | 3.07% | 0.363 | 0.197 | -49.79% | 50.49% | -2299.65% | 0.0693 | 8.93 | 1.81 | 201 | 0 | rejected |
| `public_qvm_dividend_quality_momentum_20` | +30.10% | 1.43% | 0.198 | 0.104 | -58.05% | 49.04% | -2343.64% | 0.0324 | 4.26 | 1.99 | 193 | 0 | rejected |
| `public_qvm_value_momentum_lowvol_20` | +24.11% | 1.18% | 0.169 | 0.090 | -60.22% | 49.89% | -2349.63% | 0.0321 | 4.34 | 1.69 | 210 | 0 | rejected |

## Interpretation

This batch improved one thing compared with the raw low-turnover line: capacity.

- Capacity-limited trades: 0 for all four candidates.
- Max participation rate: about 0.1503% ADV, well below the 1% gate.
- No extreme-trade-return flag.

But the factors are still not usable as direct long-only Top100 signals:

- all four underperformed the equal-weight CN stock benchmark by more than 22x total return;
- overlap-adjusted Sharpe stayed below 0.23;
- max drawdown ranged from -47.71% to -60.22%;
- every candidate still had 193-210 calendar-limited skipped trades;
- tail RankIC did not become robust enough to support promotion.

The best evidence is ranking evidence, not portfolio evidence:

- `public_qvm_value_reversal_quality_20` RankIC 0.0724, t=9.43;
- `public_qvm_lowbeta_value_momentum_20` RankIC 0.0693, t=8.93;
- their long-short spreads were positive, but long-only TopN did not convert.

## Decision

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Research leads carried forward: 2 diagnostic leads
  - `public_qvm_value_reversal_quality_20`
  - `public_qvm_lowbeta_value_momentum_20`

Do not continue with:

- QVM direct long-only TopN promotion;
- QVM weight tuning;
- QVM more-window expansion;
- treating capacity cleanliness alone as profitability evidence.

## Next Direction

Round87 should be a translation-layer audit, not another direct TopN sweep:

`round87_public_qvm_bottom_exclusion_costed_walk_forward`

Minimum design:

- freeze the two Round86 leads;
- use them only as bottom-tail exclusion filters or overlay filters;
- run costed long-cycle replay first;
- if long-cycle replay is weak, hibernate public QVM immediately;
- only walk forward if absolute risk and overlap Sharpe improve materially.
