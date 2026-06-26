# Round106 Negative-IC Trend Accumulation Preregistration Design

## Context

Round105 tested the Round104 higher-is-better trend and amount accumulation candidates across the 2015-2025 CN stock long cycle. The result was not a promotable positive trend family: 20 of 20 factor-horizon tests were FDR-significant, but every mean IC was negative and no candidate became a research lead. Round106 must convert that evidence into a new pre-registered hypothesis rather than treating post-hoc inversion as a discovered profitable factor.

## Goal

Pre-register a small, capacity-safe anti-overheat candidate family that tests whether crowded trend, late-stage amount expansion, and money-pressure spikes should be avoided or ranked lower in CN stock selection.

## Requirements

- Use CN stock scope only.
- Use Round105 as source evidence, but mark it as hypothesis evidence, not promotion evidence.
- Candidate names must clearly show anti/overheat avoidance semantics.
- Direction remains `higher_is_better`, where higher scores mean lower overheat or safer non-crowded accumulation.
- Do not allow portfolio backtest or promotion before Alphalens-style IC, quantile, turnover, multiple-testing, and capacity prescreen.
- Avoid same-family parameter tuning of the failed Round104 positive direction.
- Keep public-reference rationale: Alphalens/qlib screening, WorldQuant-style price-volume reversal/overreaction, vectorbt/pyfolio later risk validation.

## Candidate Shape

Round106 will pre-register eight to ten candidates:

- Inverse volume-weighted momentum quality
- Inverse money-pressure efficiency
- Inverse accumulation/distribution pressure
- Inverse turnover expansion momentum
- Inverse amount breakout
- Overheated high-volume breakout avoidance
- Non-crowded relative strength
- Anti-OBV late accumulation
- Amount exhaustion pullback candidate
- Composite overheat avoidance score

These formulas are hypotheses only. They can proceed to Round107 prescreen, but cannot be promoted or portfolio-tested from registration alone.

## Testing

Tests must prove:

- The default candidate list is unique and has at least eight candidates.
- Every candidate is CN stock, has capacity filters, public references, economic rationale, and promotion disabled.
- Names avoid implying promotion readiness.
- Build output records Round105 negative IC as source context and points next direction to Round107 prescreen.
- CLI writes JSON, Markdown, and CSV outputs.

## Self-Review

- No direct backtest or walk-forward is included.
- No 2026 holdout is touched.
- The design explicitly blocks post-hoc inversion as promotion evidence.
- The scope is one preregistration artifact plus startup-gate update and three-round audit.
