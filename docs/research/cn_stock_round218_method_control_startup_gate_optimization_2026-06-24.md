# CN Stock Round218 Method Control Startup Gate Optimization

Round218 is a process-optimization round, not a factor discovery round. It turns the
latest audit issues into repeatable startup-gate controls before resuming CN stock
factor mining.

## Why This Was Needed

Recent work found no promotable alpha after many rounds. The main failure pattern was
not a lack of parameter grids; it was weak research control:

- short-window evidence was too easy to overread;
- IC-only rows were not enough to justify portfolio grids;
- direct same-family tuning continued after repeated zero-lead outcomes;
- financial factors needed stricter point-in-time availability checks;
- public indicators needed stronger economic-source registration and dedup/exposure checks;
- portfolio results needed a full metric pack instead of headline return only.

Round217 confirmed this again: 14 profitability-quality candidates and 28 controlled IC
tests produced 0 FDR-significant tests and 0 research leads. The correct action is to
rotate family and strengthen the pre-run gate.

## Implemented Startup-Gate Controls

The startup gate now requires a method-control suite covering:

- A-share microstructure filters: limit-up/down, suspension, ST, new listings, delisting,
  and BSE/STAR/ChiNext board-permission state.
- Financial PIT availability: announcement date, revision announcement, available date,
  signal date, raw date, and signal-lag checks.
- Industry/style neutral combinations: industry, size, value, low-volatility, momentum,
  liquidity, residual factor matrix, and residual IC.
- CN ETF signal boundary: stock mining cannot be treated as ETF rotation evidence; ETF
  rotation needs a dedicated signal pack such as ETF flow, discount/premium, volume shock,
  industry ETF relative strength, and macro/rate/commodity/currency context.
- Portfolio construction metric pack: total return, annual return, profit rate, Sharpe,
  cost-adjusted Sharpe, max drawdown, win rate, turnover, and capacity usage.
- Strict statistics: Deflated Sharpe, CPCV or purged cross-validation, White Reality Check
  or FDR, parameter sensitivity heatmap, overlap-adjusted statistics, and final holdout
  status.
- China regime context: policy/liquidity state, credit cycle, northbound/margin/turnover
  temperature, index-location state, and signal-window allowed/blocked date counts.
- Event factors: forecast, dividend/ex-right, buyback, holder change, lockup unlock, and
  index-rebalance events with available/effective dates and contamination audits.

## Code And Config Changes

- Added method-optimization design and confirmation items to the startup protocol.
- Added validation so stale startup packets missing these controls are rejected.
- Expanded the pre-mining control contract outputs for trading rules, financial timing,
  portfolio metrics, statistics, China regime, and events.
- Updated the CN stock startup config source audit to this Round218 method-control
  optimization report, with Round217 as the latest zero-lead evidence source.
- Set the next direction to `round218_family_rotation_after_profitability_quality_stratified_failure`.
- Added rejected directions blocking profitability-quality tuning, portfolio grids, and
  retroactive inverse-direction mining after reading negative IC.

## Decision

- New factors mined in this round: 0
- New useful factors: 0
- Promotable factors: 0
- Useful artifact: startup-gate method-control optimization
- Next allowed work: family rotation, then only pre-registered candidates with public,
  literature, endpoint, or market-mechanism source evidence.
