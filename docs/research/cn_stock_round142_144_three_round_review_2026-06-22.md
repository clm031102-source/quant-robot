# CN Stock Rounds 142-144 Three-Round Review

## Scope

This review covers the optimization work before resuming CN stock factor mining:

- Round142: factor-mining quality gate.
- Round143: A-share tradeability gate.
- Round144: strict statistical reality-check gate.

No live trading, broker connection, account read, or order placement was performed.

## Direction Audit

The direction was correct. These rounds did not try to mine more formulas; they reduced the probability of wasting future mining cycles on false positives. The work directly addressed the user's audit items:

- A-share real execution constraints.
- Strict statistical checks beyond point Sharpe.
- Repeatable startup gating before every mining run.
- Explicit separation between research candidates and promotable/paper-ready signals.

This was not a profitability discovery round. New factor count from these three rounds is zero by design.

## Round142 Result

Round142 created the reusable CN stock factor-mining quality gate:

- 8 control areas.
- 32 required controls.
- Startup gate can clear when all controls are at least classified.
- Promotion gate stays blocked until controls are fully implemented or explicitly not applicable.
- Integrated into the CN stock startup gate.

Key outcome:

- Future mining must acknowledge missing/partial controls before starting.
- Promotion cannot happen just because a leaderboard has high return or high Sharpe.

## Round143 Result

Round143 created the A-share tradeability gate:

- ST filter.
- New-listing age filter.
- Board permission filter for BSE/STAR/ChiNext.
- OHLCV proxy filters for limit-up/limit-down and suspension-like rows.
- Inactive/delist metadata handling when available.

Sample audit on one local 2023 CN bars shard:

- Rows: 628,167
- Assets: 5,351
- Board-permission blocked rows: 249,488
- New-listing flagged rows: 13,470
- ST flagged rows: 27,816
- Limit-up-like rows: 4,739
- Limit-down-like rows: 1,073
- Fully tradeable rows: 352,677

Key outcome:

- A large share of raw A-share rows cannot be treated as freely executable.
- The gate is executable, but limit/suspension/delist remain partial until official point-in-time feeds are added.

## Round144 Result

Round144 created the strict statistical reality-check layer:

- Probabilistic Sharpe.
- Conservative Deflated Sharpe approximation.
- Benjamini-Hochberg FDR accounting.
- Purged CPCV split planner with optional embargo.
- Parameter sensitivity heatmap.
- CLI artifacts for leaderboards and fold-level tables.

Quality gate status after Round144:

- Total controls: 32
- Implemented: 8
- Partial: 11
- Planned: 13
- Missing: 0
- Startup gate: cleared
- Promotion gate: blocked

Reality-check examples:

- Round126 turnover repair: DSR/FDR passed, but promotion remains false because severe drawdown, extreme-trade contamination, calendar-holding constraints, and weak absolute overlap Sharpe still block it.
- Round141 clean walk-forward: DSR/FDR passed and CPCV split accounting is executable, but it still moves only to the next audit layer, not promotion.

## What Improved

- The process is now more resistant to short-window and parameter-search illusions.
- The office desktop has a reusable startup/quality gate before mining.
- A-share execution constraints are no longer just a narrative requirement.
- Statistical checks are no longer scattered across ad hoc reports.
- Future reports can separate "statistically interesting" from "tradable/promotable".

## What Is Still Weak

- Financial PIT timing is only partial; revision handling is still planned.
- Industry/style decomposition exists in selected audits but is not universal.
- Portfolio construction is still too close to TopN; risk budget, volatility targeting, industry constraints, and stop/de-risk rules are not implemented as a reusable gate.
- China regime controls are incomplete.
- Event-factor controls are still planned.
- Official suspension/limit/delist feeds are still needed to replace OHLCV proxies.
- Full White Reality Check/bootstrap is not yet implemented; FDR satisfies the current OR-control but is not a complete substitute.

## Decision

Resume factor mining only under the updated startup and quality gates. Do not promote any factor unless it survives the full chain:

1. Long-cycle same-parameter replay.
2. Tradeability gate.
3. Cost/capacity/turnover gate.
4. Strict-statistics reality check.
5. Parameter sensitivity.
6. Industry/style decomposition.
7. China regime coverage.
8. Event contamination audit.
9. Final holdout or paper gate.

Next best optimization target before or alongside mining:

- Financial PIT/event timing for daily-basic and financial factors.
- Reusable portfolio-construction gate beyond raw TopN.
- China regime pack with policy/liquidity/credit/flow/index-location states.

## Bottom Line

Rounds 142-144 produced no new profitable factor, and that is acceptable. Their value is process quality: future mining is now much less likely to waste compute on impossible-to-trade, statistically fragile, or promotion-ineligible candidates.
