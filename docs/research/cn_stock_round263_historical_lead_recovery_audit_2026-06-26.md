# CN Stock Round263 Historical Lead Recovery Audit

## Scope

Round263 audited whether the best historical CN-stock factor leads should be revived before the next mining batch. This was a recovery audit only, not a new factor-mining round, not a portfolio promotion, and not a final-holdout read.

The repeatable tool is:

```powershell
python scripts\run_historical_lead_recovery_audit.py --output-dir data\reports\round263_historical_lead_recovery_audit_20260626
```

Outputs:

- `data/reports/round263_historical_lead_recovery_audit_20260626/historical_lead_recovery_audit.json`
- `data/reports/round263_historical_lead_recovery_audit_20260626/historical_lead_recovery_audit.md`
- `data/reports/round263_historical_lead_recovery_audit_20260626/historical_lead_recovery_rows.csv`

## Result

| Metric | Value |
| --- | ---: |
| Historical candidates audited | 5 |
| Recovery candidates | 0 |
| Promotion allowed candidates | 0 |
| Hard-blocked candidates | 5 |
| Portfolio conversion failures | 1 |
| Redundancy/exposure failures | 2 |
| Quantile-shape failures | 2 |
| 2015 risk candidates | 1 |

The audited historical candidates were:

| Factor | Source | Main issue |
| --- | --- | --- |
| `turnover_rate_f_low_participation_budget_100k_20` | Round126 | Costed portfolio conversion failure |
| `beta_adjusted_range_contraction_60` | Round112 | Reference redundancy, exposure, and 2015 regime failure |
| `alpha101_rank_pv_reversal_liquid_20` | Round252 | Positive IC but negative top-minus-bottom quantile spread |
| `qlib_alpha158_return_std_position_blend_20` | Round116 | Strongly redundant with low-vol/reversal/liquidity references |
| `main_force_divergence_reversal_5_20` | Round252 | Weak ICIR and weak quantile monotonicity |

## Why Round126 Failed

Round126 did not fail because raw return was low. It failed because the attractive return did not survive implementation-quality gates.

Best Round126 row:

- total return: `1094.25%`
- annualized return: `11.90%`
- Sharpe: `0.224`
- overlap-adjusted Sharpe: `0.226`
- Newey-West t-stat: `1.061`
- max drawdown: `-69.55%`
- win rate: `55.76%`
- extreme trade rate: `1.61%`
- max absolute gross trade return: `205.39`
- calendar-limited trades: `126`
- walk-forward allowed candidates: `0`

User drawdown tolerance matters, but it does not waive data quality, overlap statistics, extreme-trade, cost, capacity, or execution gates. A 30% drawdown tolerance cannot rescue a row whose best drawdown is around 70%, whose adjusted Sharpe is around 0.23, and whose trade log contains extreme single-trade returns.

The correct interpretation is therefore:

> Round126 is a costed conversion failure with a large historical return artifact, not a profitable factor waiting for promotion.

## 2015 Redundancy Risk

The 2015 warning is not just "one bad year." In A-shares it is a regime-overlap diagnostic:

- crash and rebound path dependence;
- suspension and reopening effects;
- liquidity segmentation;
- small-cap crowding;
- low-turnover and low-volatility crowding;
- limit-up/limit-down execution distortion;
- broad beta, reversal, liquidity, and volatility cluster overlap.

`beta_adjusted_range_contraction_60` showed the clearest 2015 risk:

- full-sample mean IC: `0.0559`
- ICIR: `0.3709`
- t-stat: `18.89`
- 2015 mean IC: `-0.1021`
- 2015 IC positive rate: `23.78%`
- highest reference correlation: `0.9768`
- highest exposure correlation: `0.9955`

That means the factor can look strong in the full sample while still being economically redundant. It is too close to the low-volatility, reversal, liquidity, low-turnover, and market-exposure cluster. Future factor recovery must report year/regime contribution, 2015-specific behavior, reference overlap, and style exposure before any portfolio grid.

## Decision

Historical lead recovery found no usable lead.

Next direction:

`round264_rotate_to_accessible_public_tradeable_indicator_family_with_regime_and_portfolio_gates`

Blocked re-entry:

- low-turnover repair parameter grids after Round126/Round263;
- market-residual technical range-contraction grids after 2015/redundancy failure;
- direct Alpha101 rank price-volume reversal grids after quantile-shape failure;
- Qlib Alpha158 blend grids after redundancy/exposure failure;
- direct smart-money-flow reference grids after weak ICIR and quantile-shape failure.

Required before next mining:

- use an accessible, PIT-safe, long-cycle source;
- pre-register the public indicator family before factor generation;
- separate IC/shape gates from portfolio gates;
- report 2015 regime contribution and reference overlap;
- do not claim total return without overlap Sharpe, drawdown, capacity, cost, and extreme-trade gates.
