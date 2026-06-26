# CN Stock Round230 Liquidity Shock Recovery Preregistration

- Date: 2026-06-24
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Scope: CN A-share stock cross-sectional factor mining
- Family: `liquidity_shock_recovery`
- Status: research screen allowed; portfolio grid and promotion blocked

## Why This Family

Round229 public anomaly residual ensemble showed attractive raw IC, but produced zero residual research leads after industry/style exposure checks. The main blocker was high size/liquidity/volatility exposure, so Round230 rotates away instead of tuning weights or running a portfolio grid.

This family uses public OHLCV-only liquidity impact ideas:

- Amihud-style price impact / illiquidity
- volume shock normalization
- price-impact absorption after short selloffs
- range shock recovery
- downside volatility and tradable liquidity resilience

It deliberately avoids:

- Tushare moneyflow endpoints
- supertrend continuation
- public anomaly/value/lowvol ensemble reuse
- short-window parameter mining
- raw TopN promotion

## Pre-Registered Candidates

| Factor | Mechanism |
|---|---|
| `amihud_shock_reversal_recovery_20_5` | Short selloff plus recent Amihud impact shock, requiring current impact absorption. |
| `volume_shock_absorption_reversal_20_5` | Short selloff plus abnormal recent volume, penalizing current one-day impact pressure. |
| `range_shock_liquidity_recovery_20_10` | Ten-day drawdown plus range shock, requiring liquidity stability and penalizing persistent high range. |
| `downside_liquidity_resilience_20` | Stable liquidity and lower downside volatility after shocks. |
| `liquidity_recovery_quality_composite_20` | Fixed equal-weight composite of the four liquidity-recovery components. |

## Gate Evidence

- Startup gate: `data/reports/factor_mining_startup_gate_round230_liquidity_shock_recovery_20260624`
  - status: cleared
  - next direction before rotation: `round230_rotate_after_public_anomaly_residual_ensemble_failure`
- Family rotation decision: `data/reports/cn_stock_family_rotation_decision_round230_liquidity_shock_recovery_20260624`
  - selected family: `liquidity_shock_recovery`
  - families reviewed: 7
  - hibernated families: 5
  - data-gap families: 1
  - portfolio grid allowed: false
  - promotion allowed: false
- Candidate plan gate: `data/reports/factor_mining_candidate_plan_gate_round230_liquidity_shock_recovery_20260624`
  - status: research_ready
  - candidates: 5
  - complete control areas: 8 / 8
  - research screen allowed: true
  - portfolio grid allowed: false
  - promotion allowed: false

## Required Next Gate

Run a long-cycle sharded residual IC prescreen across 2015-01-01 through 2025-12-31. A candidate can only advance if it survives:

- raw IC sanity
- industry-neutral IC
- size/liquidity/vol/momentum residual IC
- yearly instability checks
- multiple-testing accounting
- reference/exposure dedup if residual leads exist

Zero residual leads means this family rotates after the next review instead of receiving parameter expansion.
