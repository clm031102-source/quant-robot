# CN Stock External Northbound Prescreen Round191

## Scope

- Machine role: office_desktop
- Task type: factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Market/universe: CN stock cross-sectional alpha, not CN ETF rotation
- Stage: external-feed IC/quantile/turnover prescreen only
- Live boundary: no broker, account, order, or automatic live-trading access

## Command

```powershell
python scripts\run_external_feed_northbound_prescreen.py --output-dir data\reports\round191_external_northbound_prescreen_20260623 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 20 --execution-lag 1 --lookback 20 --min-cross-section 30 --min-ic-observations 20 --min-signal-date-amount 10000000
```

## Data Window

- Bars: 10,785,537 rows, 5,707 assets, 2015-01-05 to 2025-12-31.
- Northbound signal rows: 2,260,686 factor rows, 3,326 assets.
- Label alignment: 2,121,490 rows.
- IC observation dates: 2024-07-31 to 2025-12-02, 323 dates per seed.
- Final holdout: excluded. 2026 remains read-once final holdout.
- PIT rule: external feeds join only when `available_date <= signal_date`; raw feed date must be before signal date.

## Results

| Factor | Horizon | IC obs | Mean RankIC | ICIR | t-stat | IC positive rate | Q5-Q1 | Monotonicity | Top turnover | FDR | Research lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| northbound_hold_ratio_accumulation_20 | 20 | 323 | -0.0081 | -0.174 | -3.13 | 43.7% | 0.0306 | 0.300 | 1.8% | yes | no |
| northbound_hold_accumulation_flow_regime_20 | 20 | 323 | -0.0055 | -0.117 | -2.10 | 44.9% | 0.0312 | 0.300 | 2.5% | yes | no |

## Interpretation

Round191 is useful as a process correction, not as an alpha discovery.

Both northbound seeds are FDR-significant only because the daily IC sample is large. The actual effect is in the wrong preregistered direction and too small: absolute IC is below 0.02, ICIR is negative, positive-IC rate is below 50%, and quantile monotonicity is weak. The positive northbound-accumulation hypothesis is rejected for direct factor use.

The positive Q5-Q1 spread is not enough to rescue the signal because the rank IC and monotonicity disagree. This is exactly why the optimized workflow blocks portfolio grids before IC/quantile/turnover evidence is audited.

## Decision

- Research leads: 0.
- Promotion candidates: 0.
- Portfolio backtest permission: 0.
- Do not expand TopN, costs, or portfolio grids for the positive northbound accumulation family.
- Next direction: rotate to external margin/credit IC/quantile/turnover prescreen, or separately preregister a negative northbound crowding/reversal hypothesis before testing it. Do not flip direction retroactively inside Round191.

## Remaining Blockers

- LPR coverage remains fully blocked.
- No industry/style-neutral residual review yet for external northbound seeds.
- No redundancy/dedup against existing price-volume/liquidity/style factors.
- No cost/capacity walk-forward or China regime stress audit.
- No final-holdout clearance.
