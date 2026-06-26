# CN Stock Capacity-Safe Trend Accumulation Preregistration Round104 - 2026-06-22

## Executive Summary

Round104 executed the required family rotation after Round103 found the Bollinger low-volatility reversal lead to be highly redundant.

Result:

- Stage: `capacity_safe_trend_accumulation_preregistration`
- Candidate count: 10
- Unique candidate names: 10
- Blockers: 0
- Portfolio-backtest-allowed candidates: 0
- Promotion-allowed candidates: 0
- Next required gate: `alphalens_style_ic_quantile_turnover_prescreen`
- Next direction: `round105_capacity_safe_trend_accumulation_prescreen`

No factor is promoted. This is a preregistration round only.

## Rotation Context

Round104 explicitly rotates away from:

- Bollinger reversal
- RSI reversal
- Donchian pullback
- range-contraction low-volatility reversal
- low-volatility reversal blends

Reason:

- Round103 showed the only Round102 lead had high redundancy inside that cluster.
- Continuing to tune that family would be compute waste and a multiple-testing risk.

## Candidate List

| Factor | Family | Windows | Required fields | Public references |
|---|---|---|---|---|
| `volume_weighted_momentum_quality_20` | volume-confirmed trend | 20 | adj_close, amount | qlib, Alphalens, VectorBT |
| `amount_accumulation_breakout_20_60` | amount accumulation | 20, 60 | adj_close, high, low, amount | VectorBT, Alphalens, PyFolio |
| `money_pressure_efficiency_20` | money pressure | 20 | adj_close, amount | WorldQuant 101 Alphas, Alphalens, qlib |
| `relative_amount_trend_confirmed_momentum_20_60` | amount-confirmed momentum | 20, 60 | adj_close, amount | qlib, Alphalens, WorldQuant 101 Alphas |
| `obv_proxy_trend_quality_20` | OBV proxy | 20 | adj_close, amount | VectorBT, Alphalens, PyFolio |
| `high_volume_breakout_quality_20` | breakout quality | 20 | adj_close, high, amount | VectorBT, Alphalens, qlib |
| `liquidity_qualified_relative_strength_60` | liquid relative strength | 20, 60 | adj_close, amount | qlib, Alphalens, PyFolio |
| `price_path_efficiency_amount_confirmed_20` | trend efficiency | 20, 60 | adj_close, amount | Alphalens, qlib, VectorBT |
| `accumulation_distribution_proxy_20` | accumulation/distribution | 20 | adj_close, high, low, amount | VectorBT, Alphalens, WorldQuant 101 Alphas |
| `turnover_expansion_momentum_10_40` | turnover expansion | 10, 20, 40 | adj_close, amount | Alphalens, qlib, PyFolio |

## Method Discipline

Round104 follows the same process guardrails:

- public formula ideas are hypotheses, not evidence;
- every candidate must pass long-cycle IC, quantile, turnover, and capacity prescreen before portfolio construction;
- no 2026 final holdout is touched;
- cost, capacity, extreme-trade, and execution gates remain hard blockers;
- drawdown tolerance near 30% is soft only after return quality and tradability survive.

## Next Direction

Round105 should build the trend/accumulation factor matrix and run the same 2015-2025 Alphalens-style prescreen used in Round102.

Do not run a portfolio grid until the prescreen identifies a non-redundant statistical lead.

Generated files were written under:

```text
data/reports/capacity_safe_trend_accumulation_preregistration_round104_20260622/
```

Generated `data/reports` outputs stay out of Git by policy.
