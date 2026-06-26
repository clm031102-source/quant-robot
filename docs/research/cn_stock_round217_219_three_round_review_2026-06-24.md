# CN Stock Round217-219 Three-Round Review

Date: 2026-06-24

Scope: CN A-share stock cross-sectional alpha research. This is not ETF rotation, not live trading, and not a promotion memo.

## Executive Decision

Rounds 217-219 completed one required three-round review block:

- Round217 tested PIT profitability-quality candidates and found 0 FDR leads.
- Round218 converted the recent audit problems into a stricter repeatable startup gate.
- Round219 rotated to a public trend-strength-state family, implemented six candidates, and ran a full 2015-2025 residual/redundancy prescreen; it found 0 residual research leads.

Decision:

- Direct profitability-quality formula tuning stays hibernated.
- Public trend-strength-state, including ADX/KAMA/Aroon/WilliamsR composites, is hibernated.
- No Round217-219 factor is promotable.
- No Round217-219 factor is allowed into a TopN portfolio grid.
- Round220 should rotate to a new orthogonal family: `industry_leader_lag_residual_diffusion`.

## Round Results

| Round | Direction | Candidates / Tests | Main Result | Decision |
|---:|---|---:|---|---|
| 217 | PIT profitability-quality stratified shard | 14 candidates, 28 controlled IC tests | 0 Bonferroni-significant tests, 0 FDR-significant tests, 0 research leads | hibernate direct profitability-quality tuning |
| 218 | Method/startup-gate optimization | process round | Added repeatable controls for A-share trading rules, financial PIT timing, industry/style neutralization, ETF boundary, portfolio metric pack, strict statistics, China regime, and events | required before further mining |
| 219 | Public trend-strength-state residual family | 6 candidates, 6 long-cycle residual tests | 0 residual research leads, 0 portfolio preflight candidates, 0 promotions | hibernate ADX/KAMA/Aroon/WilliamsR trend-strength family |

## Failure Histogram

Observed blockers:

- `no_fdr_significant_ic`: Round217, 28 tests, 0 FDR leads.
- `raw_or_neutral_ic_not_enough`: Round219 had raw/industry-neutral IC pockets, but residual IC collapsed below gate.
- `residual_mean_ic_below_threshold`: Round219 6/6 candidates.
- `residual_yearly_ic_instability`: Round219 6/6 candidates.
- `style_exposure_high`: Round219 5/6 candidates had high size/liquidity/volatility exposure.
- `portfolio_grid_blocked_before_residual_gate`: all three rounds.

## What Actually Improved

The useful work was process and evidence discipline, not profitable factors:

- The project stopped interpreting short-window or raw IC as profit evidence.
- The startup gate now requires the user-specified control suite before factor mining.
- Round219 proved that public indicator families must survive residual/de-dup gates before any portfolio metrics are computed.
- The Round219 long-cycle run used 5,707 assets, 10,785,537 bar rows, 47,693,243 factor rows, and 45,952,010 residual rows.

## Engineering Audit

Round219 exposed a real efficiency issue:

- Full-window residual prescreen succeeded, but process memory peaked above 30GB.
- Recomputing long-cycle factor, reference, exposure, and label matrices for each family is too expensive for sustained mining.
- Next engineering improvement should add reusable factor/reference/exposure matrix caching or yearly shard aggregation before more heavy prescreens.

This does not justify returning to short samples. It means full-sample rigor stays, while computation must be made cheaper.

## Direction Adjustment

The next family must satisfy all of the following:

- Orthogonal to direct profitability-quality, valuation reversion, northbound/margin credit, calendar seasonality, RSRS/SuperTrend/Donchian, and Round219 trend-strength.
- Uses existing long-cycle CN stock OHLCV, amount, and stock_basic industry metadata.
- Starts from a known public anomaly or market mechanism.
- Blocks portfolio grids before residual IC, reference de-duplication, capacity, and regime gates.

Selected next direction:

`round220_industry_leader_lag_residual_preregistration`

Selected family:

`industry_leader_lag_residual_diffusion`

Rationale:

Public slow-information-diffusion and industry-momentum literature suggests liquid industry leaders may incorporate information first, while same-industry laggards adjust more slowly. The Round220 version is not plain industry relative strength and not the old industry-breadth bridge. It must use frozen liquid-leader definitions, lagged information only, own-stock momentum/reversal reference de-duplication, and industry/style residual checks before any portfolio conversion.

## Round220 Stop-Loss Rules

Round220 must stop or rotate if any of these occur:

- Candidate construction becomes plain industry strength or same-day industry return.
- Residual IC collapses after own momentum/reversal, industry, size, liquidity, and volatility controls.
- Leader-laggard candidates are highly correlated with public momentum/reversal references.
- Capacity depends on illiquid laggards or microcap tails.
- Full-window matrix generation again becomes the bottleneck without adding cache/shard reuse.

## Safety

Research-to-review only. No broker connection, no live account reads, no order placement, and no automatic live trading.
