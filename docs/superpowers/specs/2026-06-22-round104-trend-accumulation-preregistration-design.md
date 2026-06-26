# Round104 Trend Accumulation Preregistration Design

## Context

Round103 showed that the only Round102 lead, `bollinger_reversal_lowvol_liquid_20`, is highly redundant with the same public low-volatility reversal cluster. Continuing to tune Bollinger, RSI, Donchian, or range-contraction pullback variants would violate the three-round review stop-loss rule.

Round104 rotates to a different return engine: volume-confirmed trend and accumulation. This is still public-method inspired, but it avoids the specific low-volatility reversal cluster that Round103 rejected.

## Scope

Pre-register a new CN stock candidate family only. Do not run a portfolio grid, do not claim profitability, and do not read final 2026 holdout data.

Candidate requirements:

- 8 or more unique candidates.
- Economic rationale for every candidate.
- Public references for every candidate: qlib, Alphalens, VectorBT, PyFolio, or WorldQuant-style price-volume formula research.
- Capacity filters inherited from the existing capacity-safe preregistration policy.
- Portfolio and promotion flags false for every candidate.
- Next gate remains Alphalens-style IC, quantile, turnover, and capacity prescreen.

## Candidate Family

The candidates should focus on:

- volume-weighted momentum,
- amount accumulation,
- price path efficiency,
- breakout confirmation by turnover or amount,
- money pressure proxies from return times amount,
- liquidity-qualified relative strength.

Forbidden in this Round104 family:

- Bollinger reversal,
- RSI reversal,
- Donchian pullback,
- range contraction low-vol reversal,
- low-volatility reversal blends,
- low-turnover tails as alpha.

## Files

- Create `src/quant_robot/ops/capacity_safe_trend_accumulation_preregistration.py`
- Create `scripts/run_capacity_safe_trend_accumulation_preregistration.py`
- Create `tests/unit/test_capacity_safe_trend_accumulation_preregistration.py`
- Create `tests/unit/test_capacity_safe_trend_accumulation_preregistration_cli.py`
- Create `docs/research/cn_stock_capacity_safe_trend_accumulation_preregistration_round104_2026-06-22.md`
- Modify `configs/factor_mining_startup_cn_stock.json`
- Modify `tests/unit/test_factor_mining_startup_gate_cli.py`

## Verification

Run TDD red-green for the new preregistration op and CLI. Then run the startup gate and project audit. The next startup direction after Round104 should become:

```text
round105_capacity_safe_trend_accumulation_prescreen
```

This keeps the office desktop in continuous factor discovery while avoiding the redundant low-volatility reversal cluster.
