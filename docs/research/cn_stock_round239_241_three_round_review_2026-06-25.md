# CN Stock Rounds239-241 Three-Round Review

Date: 2026-06-25

## Scope

This review covers three accounting-quality work units:

- Round239: raw accounting-quality residual IC shape prescreen on 115 symbols.
- Round240: repaired accounting-quality candidate prescreen on 115 symbols.
- Round241: final shard6 five-symbol expansion and full 120-symbol gate replay.

This is research-only. No broker connection, no account reads, no order placement, and no live trading.

## Round Outcomes

| Round | Work | Sample | Result |
|---|---|---:|---|
| 239 | Raw statement-accounting formulas | 115 symbols | 5 candidates, 10 tests, 0 FDR, 0 neutral-gate pass, 0 research leads |
| 240 | Repaired industry-relative and residualized composites | 115 symbols | 3 candidates, 6 tests, 0 FDR, 0 neutral-gate pass, 0 research leads |
| 241 | Completed shard6 and replayed raw/repaired gates | 120 symbols | raw 0 leads, repaired 0 leads, no portfolio conversion |

## What Improved

The process improved in three concrete ways:

- The project did not tune around a failed family. After raw formulas failed, only one economically motivated repair pass was allowed.
- The repair pass used industry-relative and size/liquidity residual logic, so the failure is more informative than a raw formula failure.
- Round241 expanded the PIT statement sample before judging whether the weak result was only a small-sample artifact.

## Key Evidence

Round239 best raw row:

- `low_asset_growth_quality_raw`, H5 IC 0.0454, ICIR 0.249, t-stat 1.36, FDR false, research lead false.

Round240 best repaired row:

- `aq_repaired_industry_relative_cash_accrual_quality`, H5 IC 0.0291, ICIR 0.328, t-stat 1.67, FDR false, research lead false.

Round241 best rows after 120-symbol replay:

- `low_asset_growth_quality_raw`, H5 IC 0.0428, ICIR 0.246, t-stat 1.37, FDR false, research lead false.
- `aq_repaired_industry_relative_cash_accrual_quality`, H5 IC 0.0294, ICIR 0.351, t-stat 1.95, FDR false, research lead false.

## Failure Pattern

The same blocker appears across all three rounds: weak IC stability and weak statistical significance after multiple-testing control. The better-looking rows do not survive the gates that matter before portfolio construction:

- FDR remains false.
- ICIR stays below 0.5.
- Top-minus-bottom shape is weak or unstable.
- Size and liquidity neutral gates fail.
- No candidate reaches research-lead status.

This is not a drawdown-tolerance issue. The user can accept drawdown near 30% when return quality is strong, but these candidates never reached the stage where drawdown should be evaluated.

## Direction Decision

Do not run portfolio grids for the Round239-241 raw or repaired accounting-quality factors.

Allowed next direction:

1. Continue PIT statement sample expansion in small endpoint-budgeted slices if the goal is to give this public accounting-quality family more statistical power.
2. Use the same gates after each expansion: formula smoke, matrix-label smoke, residual IC, FDR, neutralization, and no final-holdout tuning.
3. If the next expanded replay still has zero leads, rotate within accounting quality to a different economic substructure: revision surprise, abnormal accrual change, or post-announcement drift.

Blocked next direction:

- no raw/repaired parameter tuning;
- no TopN portfolio conversion;
- no Sharpe/annual-return/win-rate claim;
- no final-holdout access;
- no live or paper promotion.

## Governance Check

The three-round review cadence is satisfied for Rounds239-241. The next three-round review is due after Round244 unless a hard blocker appears earlier.
