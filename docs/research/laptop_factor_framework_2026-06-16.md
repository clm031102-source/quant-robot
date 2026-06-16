# Laptop Factor Framework Progress - 2026-06-16

## Scope

- Machine role: `laptop`.
- Branch: `codex/factor-method-optimization-20260616`.
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

The config `configs/walk_forward_tushare_moneyflow_technical_combo.json` includes the first liquidity-control candidates for historical comparison. The stricter current default is the residual-regime validation profile, which focuses on `large_resid_liq_vol_amt_20` and `large_resid_liq_vol_amt_gate_20` across multiple pre-registered regime lookbacks.

Recommended validation command on `highspec_desktop` or `office_desktop`:

```powershell
python scripts\run_desktop_factor_validation.py
```

Allowing zero accepted candidates is intentional for strict factor review. The desktop validation script keeps the command successful when the grid completes and every candidate is rejected, because a full rejection set is still useful research evidence. Grid failures, missing train/test results, and unsafe data or sync paths remain blockers.

For the full desktop check chain, use:

```powershell
python scripts\run_checks.py --profile desktop-validation --execute
```

The desktop profile now enforces the full residual-regime chain:

- strict walk-forward validation on `configs/walk_forward_tushare_moneyflow_residual_regime.json`;
- CN data-quality audit against `data/processed` with output under `data/reports/data_quality_gap_audit_tushare_moneyflow_residual_regime`;
- market-regime coverage rebuilt from walk-forward test-fold `regime_curve.csv` files;
- residual-regime promotion gate that consumes the data-quality audit and requires the market-regime coverage pack;
- Markdown summary that cross-checks the walk-forward leaderboard against `manifest.json` and records data-quality, promotion-gate, and regime-coverage status.

This means a candidate can no longer look acceptable merely because it survived one favorable market cycle or because an old leaderboard CSV was mixed with a newer manifest.

The latest office attribution also adds a review warning: `large_minus_liquidity_20` failed through a severe 2024H1 drawdown and hump-shaped quantiles rather than a pure capacity problem, while `mf_low_minus_volatility_20` was both capacity-constrained and non-monotonic. The next run should inspect quantile shape and mid-quantile/tail behavior before treating any liquidity-controlled variant as robust.
