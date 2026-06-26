# Round199 Eight-Control Gate Optimization Design

## Goal

Turn the eight user-requested research weaknesses into repeatable CN stock factor-mining gates before new profitability mining resumes.

## Scope

This design covers the CN stock factor-mining startup, quality, and candidate-plan gates. It does not implement new factor formulas, portfolio optimizers, live trading, broker access, or ETF rotation research.

## Approach

The project already contains Round142 quality gates, Round150 candidate-plan gates, and Round195/198 control closeout work. The safest optimization is to harden those existing gates instead of creating a separate process.

The gate now treats every new candidate plan as incomplete unless its promotion policy explicitly covers:

- same-parameter full-sample and long-cycle replay;
- rolling walk-forward validation;
- realistic cost and capacity checks;
- market-regime coverage;
- no-lookahead and point-in-time availability audit;
- overfit and multiple-testing control;
- overlap-adjusted statistics;
- parameter sensitivity heatmap;
- read-once final holdout policy;
- tradeability and survivorship-bias audit;
- industry/style neutralization;
- source-performance evidence from a public method, literature reference, market mechanism, endpoint feature, or failure-review thesis.

## Data Flow

1. A preregistration JSON enters `factor_mining_candidate_plan_gate`.
2. The gate reads declared controls from `research_control_plan`.
3. It reads promotion requirements from `promotion_policy`.
4. Discovery can proceed only when candidate identity, hypothesis source, economic rationale, declared controls, and promotion-policy requirements are complete.
5. Portfolio and promotion remain blocked until quality-gate controls are implemented and walk-forward evidence exists.

## Failure Modes

The gate blocks anonymous formulas, short-sample-only evidence, future-leaking financial factors, raw TopN-only promotion plans, and candidates that lack neutralization, regime, cost, capacity, multiple-testing, or final-holdout requirements.

## Testing

Add unit tests that prove:

- the default candidate plan includes the stricter promotion requirements;
- removing no-lookahead, final holdout, neutralization, or source evidence keys blocks the gate;
- rendered markdown exposes the stricter promotion policy so humans can audit it before mining.

## Commit Policy

Commits and pushes are not allowed in this task unless the user later explicitly permits them.
