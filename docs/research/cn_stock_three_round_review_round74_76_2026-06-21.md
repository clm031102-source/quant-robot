# CN Stock Three-Round Review - Rounds 74-76 - 2026-06-21

## Scope

This review covers the governance checkpoint after Rounds 74, 75, and 76.

The block started from the Round73 finding that public risk-filter bridge factors had beta-adjusted residual signal but poor long-only portfolio quality. It then tested whether a simple beta-hedged spread could monetize that signal and, after rejection, rotated to a new public-method family.

## Round Summary

| Round | Direction | Result | Decision |
|---|---|---|---|
| 74 | Fixed 1.0 benchmark-hedged spread | Corrected implementation rejected all 3 spreads; best spread total -12.91%, overlap Sharpe -0.516 | no candidate |
| 75 | Cost/impact stress of the corrected spread | All 3 spreads failed harder; best spread total -53.74%, overlap Sharpe -1.701 | hibernate family |
| 76 | New public-method family registration | Added and pre-registered `public_rsrs` with 4 RSRS factors and a long-cycle grid | rotate to RSRS grid |

Promotable profitable factors: 0.

Paper-ready factors: 0.

Useful engineering outputs:

- `src/quant_robot/ops/beta_hedged_spread_audit.py`
- `scripts/run_beta_hedged_spread_audit.py`
- `tests/unit/test_beta_hedged_spread_audit.py`
- `src/quant_robot/factors/public_rsrs.py`
- `tests/unit/test_public_rsrs_factors.py`
- `configs/experiment_grid_cn_stock_public_rsrs_round76_20260621.json`

## Critical Audit Finding

Round74 initially looked positive, but that read was invalid.

Root cause:

- The first spread implementation used `selected_net - benchmark_net`.
- For a short benchmark leg, this reverses the benchmark-leg cost sign.
- Correct logic is `selected_net + (-benchmark_gross - benchmark_cost)`.

After the fix, the public risk-filter bridge spread turned negative. This is exactly the kind of issue the new three-round review rule is meant to catch early.

## Rejection Decision

Hibernate as promotion paths:

- public risk-filter bridge long-only cash overlays;
- public risk-filter bridge fixed beta-hedged spread;
- more cost or hedge-ratio tuning around the same family.

Keep as reusable diagnostics only:

- dynamic cash overlay audit;
- benchmark beta exposure audit;
- beta-hedged spread audit.

## Direction Adjustment

The project should now rotate rather than continue squeezing this family.

Round77 should run:

`configs/experiment_grid_cn_stock_public_rsrs_round76_20260621.json`

Pre-registered RSRS factors:

- `rsrs_slope_18`
- `rsrs_zscore_18_60`
- `rsrs_right_skew_18_60`
- `rsrs_reversal_18_60`

Stop-loss rule:

If the RSRS long-only grid fails, do not expand windows first. Run IC-to-portfolio and quantile-shape diagnostics to decide whether the useful side is top selection, bottom exclusion, or no signal.

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.
