# CN Stock Rounds263-265 Three-Round Review

Date: 2026-06-26

## Scope

This review covers the three rounds after the data-source availability reset:

- Round263: historical lead recovery audit
- Round264: public tradeable indicator composite preregistration
- Round265: public tradeable indicator composite long-cycle residual prescreen

The mandate remains CN stock cross-sectional alpha mining. CN ETF rotation is out of scope for this run.

## Round Outcomes

| Round | Action | Candidates | Result | Decision |
|---:|---|---:|---|---|
| 263 | Re-audited historical bright leads with frozen old parameters | 5 historical leads | 0 recovery candidates, 0 promotion candidates | Old high-return leads remain blocked |
| 264 | Pre-registered accessible public indicator composite candidates | 8 candidates, 4 families | Candidate plan gate cleared; 0 portfolio/promotion allowed | Allowed only Round265 residual prescreen |
| 265 | Ran 2015-2025 full-sample residual IC, quantile, turnover, 2015, reference-overlap prescreen | 8 tests | 0 residual research leads, 0 portfolio/promotion allowed | Hibernate public indicator composite and rotate |

## Best Evidence Found

Round265's best raw/neutral row was `volume_dryup_pullback_liquid_reversal_5_20`:

- Raw IC: 0.0407
- Industry-neutral IC: 0.0412
- Residual IC: 0.0172
- Residual ICIR: 0.224
- Q5-Q1 spread: 0.0074
- Top-quantile turnover: 46.6%
- 2015 IC: 0.0510
- Blocker: residual mean IC below the 0.02 gate

This is a diagnostic lead only. It is not a portfolio or promotion candidate.

Round263's most eye-catching old return row remained invalid for promotion. The Round126 costed turnover-repair path had high apparent total return, but overlap Sharpe, drawdown/extreme-trade, and walk-forward gates blocked it. Round263 found 0 recovery candidates.

## Failure Pattern

The repeated pattern is not lack of computation. It is lack of incremental, robust alpha after hard controls:

- Old high-return rows fail after overlap, drawdown, extreme-trade, and walk-forward gates.
- Public indicator composites can produce visible raw or industry-neutral IC, but the edge collapses or falls below gate after residual controls.
- 2015 can make some rows look better, but full-window residual stability does not survive.
- No candidate earned permission for a portfolio grid.

## Process Improvements Completed

- Added Round264 candidate preregistration and candidate-plan gate for public indicator composites.
- Added Round265 residual prescreen with full-window raw, industry-neutral, residual IC, quantile spread, top-quantile turnover, 2015 diagnostics, reference overlap, and style exposure checks.
- Added a Round265 bars-only loader to avoid wasting time reading non-bar processed inputs.
- Updated startup gate state so future runs must read Round265 and rotate away from this family.

## Decision

Round266 must rotate to a new orthogonal family. It must not tune:

- MFI/CMF variants
- OBV variants
- SuperTrend variants
- RSI/MACD threshold variants
- ATR/Donchian/Bollinger parameter variants from the same public indicator composite family

Round266 requires a new candidate plan gate before any factor generation or residual prescreen. Any next family must prove:

- accessible PIT-safe data source,
- long-cycle coverage,
- clear economic hypothesis,
- neutralization plan,
- portfolio/promotion blocked until after residual, walk-forward, cost/capacity, regime, and strict-statistics gates.

## Recommended Round266 Direction

Rotate to a non-price-volume and non-public-indicator family. The next candidate plan should prefer an orthogonal source such as event/expectation context with true availability dates, or another accessible data source not already hibernated by zero residual leads.

If no genuinely new source is accessible, the correct action is to improve data-source coverage and family selection tooling, not to continue formula tuning.
