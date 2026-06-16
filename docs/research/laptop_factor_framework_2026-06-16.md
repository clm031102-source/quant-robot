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
