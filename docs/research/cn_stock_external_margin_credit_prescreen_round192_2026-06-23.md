# CN Stock External Margin Credit Prescreen Round192

## Scope

- Machine role: office_desktop
- Task type: factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Market/universe: CN stock cross-sectional alpha, not CN ETF rotation
- Stage: external-feed IC/quantile/turnover prescreen only
- Live boundary: no broker, account, order, or automatic live-trading access

## Command

```powershell
python scripts\run_external_feed_margin_credit_prescreen.py --output-dir data\reports\round192_external_margin_credit_prescreen_20260623 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 20 --execution-lag 1 --lookback 20 --min-cross-section 30 --min-ic-observations 20 --min-signal-date-amount 10000000
```

## Data Window

- Bars: 10,785,537 rows, 5,707 assets, 2015-01-05 to 2025-12-31.
- Margin detail: 1,414,557 rows, 4,660 assets, raw dates 2024-07-01 to 2025-12-31.
- Margin signal rows: 2,435,482 factor rows, 3,815 factor assets.
- Label alignment: 2,277,034 rows.
- IC observation dates: 334 dates per seed.
- Final holdout: excluded. 2026 remains read-once final holdout.
- PIT rule: external feeds join only when `available_date <= signal_date`; raw feed date must be before signal date.

## Results

| Factor | Horizon | IC obs | Mean RankIC | ICIR | t-stat | IC positive rate | Q5-Q1 | Monotonicity | Top turnover | FDR | Research lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| margin_balance_crowding_reversal_20 | 20 | 334 | 0.0555 | 0.962 | 17.58 | 83.8% | 0.0244 | 0.300 | 18.9% | yes | no |
| margin_financing_acceleration_exhaustion_20 | 20 | 334 | 0.0341 | 0.472 | 8.63 | 66.5% | 0.1824 | 0.600 | 28.5% | yes | no |

## Interpretation

Round192 is the first external-feed factor screen in this block that shows a meaningful positive statistical signal. Both preregistered margin-credit reversal seeds pass FDR and have positive IC, positive IC rate, positive Q5-Q1 spread, and acceptable top-quantile turnover.

They still do not qualify for direct promotion. The blocking issue is quantile monotonicity: `margin_balance_crowding_reversal_20` has monotonicity 0.300 and `margin_financing_acceleration_exhaustion_20` has monotonicity 0.600, below the 0.700 prescreen gate. This means the signal may be concentrated in tails or contaminated by size/liquidity/industry exposure rather than a clean linear cross-sectional ranking edge.

## Decision

- Research leads under the strict prescreen gate: 0.
- Statistical audit candidates: 2.
- Promotion candidates: 0.
- Portfolio backtest permission: 0.
- Do not expand TopN/cost grids from this result alone.
- Next direction: Round193 external margin-credit reference dedup, industry/size/liquidity neutral IC, and quantile-shape audit.

## Remaining Blockers

- No industry/style-neutral residual review yet.
- No redundancy/dedup against existing liquidity, low-volatility, turnover, and price-volume references.
- Quantile monotonicity is below gate.
- No cost/capacity walk-forward or China regime stress audit.
- No final-holdout clearance.
