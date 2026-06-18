# Highspec Desktop Factor Mining - Liquidity-Gated Moneyflow Candidates

## Scope

- Machine role: `highspec_desktop`.
- Branch: `codex/factor-batch-alpha-mining-20260616`.
- Task type: `factor_batch`.
- Research boundary: research-to-paper only. No broker connection, no live account reads, no order placement, and no automatic live trading.
- Data policy: raw data, processed data, generated reports, logs, and local credentials remain out of Git.

## Motivation

The latest absorbed office-desktop audits rejected simple inversions, percentile targeting, wider raw top-N portfolios, longer holding periods, and standalone amount gates. The useful next direction was to combine liquidity controls with a new score shape before selection.

This branch pre-registers liquidity-gated moneyflow candidates that can be tested by the existing strict walk-forward framework:

- `large_resid_liquidity_gate_20`: residualize large-order net inflow against same-day Amihud-style illiquidity, then keep only the more liquid half of the cross-section.
- `mf_low_minus_volatility_liquidity_gate_20`: combine low net moneyflow with a volatility penalty, but use a separate 20-day liquidity gate before ranking.
- `large_plus_risk_momentum_liquidity_gate_10`: combine large-order net inflow with risk-adjusted momentum, but use a separate 10-day liquidity gate before ranking.

## Implementation Notes

`ComboFactorSpec` now supports `liquidity_gate_factor`, so a factor can use one technical component for scoring and another technical component for the liquidity gate. Existing combo factors keep their previous behavior.

Tushare daily-basic and moneyflow factor builders now normalize string dates to `datetime.date` before emitting factor frames. This keeps loaded CSV/parquet factor inputs aligned with bar dates and prevents backtest comparisons between strings and date objects.

## Validation Plan

Run the strict desktop validation profile when local processed CN bars and moneyflow inputs are available:

```powershell
$env:PYTHONPATH='src'
python scripts\run_checks.py --profile desktop-validation --execute
```

The direct candidate validation entry point remains:

```powershell
$env:PYTHONPATH='src'
python scripts\run_walk_forward.py --config configs\walk_forward_tushare_moneyflow_technical_combo.json --source processed-bars --data-root data\processed --allow-no-accepted
```

Any accepted result still requires data-quality, capacity, drawdown, monotonicity/tail-dependence, and promotion-gate review before moving beyond research observation.
