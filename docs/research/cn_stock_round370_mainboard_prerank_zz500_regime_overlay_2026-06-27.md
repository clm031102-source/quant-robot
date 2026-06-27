# CN Stock Round370 - Mainboard Pre-Rank With ZZ500 Regime Overlay

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Why This Round

Round367 found that mainboard pre-rank replacement raises return but creates too much drawdown. Round368 showed volatility targeting alone cannot reduce the drawdown below the target band.

Round370 applies the already-used ZZ500 external regime overlay to this high-return line. This is not a new regime search. It reuses the same frozen ZZ500 120-day momentum risk-off signal already used in the simulation shortlist.

Regime source:

`data/reports/round351_24h_profit_sprint_zz500_75_cost_beta_quickcheck_20260627/primary_low10_vol6_zz500_mult_0.50_cost10_events.csv`

Output:

`data/reports/round370_24h_profit_sprint_mainboard_prerank_zz500_regime_overlay_20260627`

## Results

Mainboard pre-rank with vol target and ZZ500 half-risk-off:

| Candidate | Total | Ann. | Sharpe | Overlap Sharpe | Max DD | Avg Regime Guard | Risk-Off Events |
|---|---:|---:|---:|---:|---:|---:|---:|
| `mainboard_prerank_vt4_zz500_mult_0.50` | +155.84% | 6.22% | 0.996 | 0.448 | -27.09% | 77.23% | 45.54% |
| `mainboard_prerank_vt5_zz500_mult_0.50` | +161.42% | 6.37% | 0.971 | 0.448 | -29.05% | 77.23% | 45.54% |
| `mainboard_prerank_vt6_zz500_mult_0.50` | +167.84% | 6.54% | 0.958 | 0.450 | -29.86% | 77.23% | 45.54% |
| `mainboard_prerank_vt8_zz500_mult_0.50` | +182.22% | 6.90% | 0.950 | 0.458 | -31.88% | 77.23% | 45.54% |

The 0.75 multiplier is weaker on drawdown:

| Candidate | Total | Ann. | Sharpe | Overlap Sharpe | Max DD |
|---|---:|---:|---:|---:|---:|
| `vt4_zz500_mult_0.75` | +163.71% | 6.43% | 0.968 | 0.443 | -32.24% |
| `vt6_zz500_mult_0.75` | +179.62% | 6.83% | 0.929 | 0.443 | -35.53% |
| `vt8_zz500_mult_0.75` | +200.87% | 7.34% | 0.932 | 0.455 | -36.48% |

## Interpretation

This is the first mainboard-pre-rank variant that lands near the drawdown band:

- `vt6 + ZZ500 half` keeps annualized return near the existing `primary_high_return`;
- max drawdown falls from about -40.54% after vol target alone to about -29.86%;
- overlap Sharpe still trails the existing primary/defensive shortlist.

## Decision

Keep `mainboard_prerank_vt6_zz500_mult_0.50` as a research lead for Round371 robustness checks.

Do not promote yet. It still needs block-dependence, OOS, and cost stress.
