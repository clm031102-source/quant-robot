# CN Stock Round149-151 Three-Round Review

Date: 2026-06-23

Machine/task: office_desktop / factor_validation

Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`

Scope: CN A-share stock cross-sectional alpha research only.

## Rounds Reviewed

Round149: lottery/MAX-effect extreme-upside reversal preregistration.

- Candidates: 6
- Purpose: rotate away from rejected event-dividend continuation and test a public MAX-effect / lottery-demand anomaly.
- Portfolio permission: 0
- Promotion permission: 0
- Decision: successful preregistration only.

Round150: lottery/MAX-effect long-cycle prescreen.

- Assets: 5,707
- Daily bar rows: 10,785,537
- Factor rows: 60,706,799
- Aligned factor-label rows: 120,521,482
- Factor x horizon tests: 12
- FDR-significant tests: 12
- Neutral-gate pass tests: 10
- Research leads: 0
- Promotion candidates: 0
- Decision: hibernate lottery/MAX-effect as a standalone long alpha.

Round151: PIT profitability event/revision preregistration.

- PIT fina_indicator rows: 4,328
- Assets: 100
- Candidate count: 10
- Active candidates: 7
- Frozen endpoint-dependent candidates: 3
- Candidate-plan control areas complete: 8 / 8
- Portfolio permission: 0
- Promotion permission: 0
- Decision: proceed to PIT matrix/label smoke only.

## Audit

The Round149 direction choice was reasonable because it used a public anomaly instead of continuing a failed same-family sweep. The important result came in Round150: the MAX-effect family had statistically visible IC, but it failed the translation from ranking signal to tradable long-side evidence. The correct action was to stop tuning that family.

The Round151 direction change was also reasonable. It moved to a different economic mechanism: earnings information timing and PIT financial revisions. It also incorporated the missing process controls from the latest review: A-share tradeability, financial availability timing, industry/style neutralization, ETF scope separation, portfolio construction, strict statistics, China market regime, and event contamination.

The most important workflow improvement is the candidate-plan gate change. Frozen candidates can now stay in the preregistration report without blocking the whole round, but they are not active for research and cannot enter portfolio or promotion paths. This prevents two bad behaviors at once:

- silently mining endpoint-dependent candidates without endpoint evidence;
- throwing away an otherwise useful active subset because frozen future candidates are documented.

## Rejected Or Hibernated Directions

Reject or hibernate:

- lottery/MAX-effect direct long alpha after Round150;
- positive RankIC rows with negative or nonmonotonic top-minus-bottom translation;
- upper-shadow spread-only promotion when raw IC and size/liquidity-neutral checks fail;
- forecast/express profitability candidates before endpoint coverage proof;
- Round96 static profitability-quality factor names under new labels;
- any portfolio grid before Round152 matrix/label smoke.

## What Improved

The process now has a stronger pre-mining gate:

1. Candidate families must declare the eight optimization control areas before factor generation.
2. Candidate plans distinguish active candidates from frozen candidates.
3. Portfolio and promotion remain false until downstream IC, neutralization, cost/capacity, walk-forward, and long-cycle gates clear.
4. The next round is fixed before return evidence is viewed, which reduces ad hoc parameter tuning.

## Remaining Risks

Round151 is still based on the first 100-symbol financial shard. That is enough for preregistration and coverage smoke, not enough for a profitability claim.

The current active candidates use `fina_indicator` fields only. Forecast and express endpoints are frozen. If the project wants to exploit forecast/express events, it needs sharded endpoint ingestion and coverage diagnostics first.

The next Round152 must prove strict `ann_date` alignment and label coverage before any IC calculation. If the PIT matrix smoke fails, profitability event/revision mining should pause for ingestion/schema repair rather than move to portfolio tests.

## Decision

Proceed to:

`round152_pit_profitability_event_revision_matrix_and_label_smoke`

Do not run portfolio grids, Sharpe screens, profit-rate tables, or win-rate tables until the Round152 PIT matrix/label smoke clears.
