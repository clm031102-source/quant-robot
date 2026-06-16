# Laptop Factor Framework Progress - 2026-06-16

## Scope

- Machine role: `laptop`.
- Branch: `codex/factor-liquidity-residual-framework`.
- Task type: `architecture_ops` / `factor_review`.
- Boundary: research-to-paper only. No broker connection, no live account reads, no order placement, and no automatic live trading.

## Reason For This Step

The office desktop audits rejected wider raw top-N moneyflow and technical searches. The useful conclusion was not another promoted factor; it was a narrower next hypothesis: moneyflow signals need explicit liquidity control before selection.

This branch therefore adds pre-registered framework candidates rather than reporting alpha:

- `large_resid_liquidity_20`: cross-sectionally residualizes large-order net inflow against `liquidity_20`, reducing direct Amihud-style liquidity exposure.
- `large_liquidity_gate_20`: keeps large-order net inflow only in the more liquid half of each date/market cross-section.

## Validation Expectations

These candidates should be treated as strict-validation inputs only. A future data-pipeline workstation run should still require:

- walk-forward validation;
- positive adjusted IC after multiple-testing correction;
- long-short and quantile-spread review;
- realistic cost and capacity checks;
- split-window robustness;
- data-quality inspection for stale prices, missing dates, extreme returns, and adjusted-close jumps.

The config `configs/walk_forward_tushare_moneyflow_technical_combo.json` now includes both candidates for the next heavier validation pass.

Recommended validation command on `highspec_desktop` or `office_desktop`:

```powershell
python scripts\run_walk_forward.py --config configs\walk_forward_tushare_moneyflow_technical_combo.json --source processed-bars --data-root data\processed --allow-no-accepted
```

The `--allow-no-accepted` flag is intentional for strict factor review. It keeps the command successful when the grid completes and every candidate is rejected, because a full rejection set is still useful research evidence. Grid failures, missing train/test results, and unsafe data or sync paths remain blockers.

The latest office attribution also adds a review warning: `large_minus_liquidity_20` failed through a severe 2024H1 drawdown and hump-shaped quantiles rather than a pure capacity problem, while `mf_low_minus_volatility_20` was both capacity-constrained and non-monotonic. The next run should inspect quantile shape and mid-quantile/tail behavior before treating any liquidity-controlled variant as robust.
