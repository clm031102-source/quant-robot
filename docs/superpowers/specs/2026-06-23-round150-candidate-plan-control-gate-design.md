# Round150 Candidate Plan Control Gate Design

## Goal

Make every new CN stock factor family declare the controls from the user's optimization list before factor generation: A-share tradeability, point-in-time timing, industry/style neutralization, ETF scope separation, portfolio construction, strict statistics, China regime coverage, and event/event-contamination handling.

## Approach

Add a reusable candidate-plan gate after preregistration and before any IC screen, portfolio grid, or promotion review. The gate separates three states:

- `research_ready`: the plan declares all controls and may proceed to IC/neutral prescreen.
- `portfolio_preflight_ready`: reserved for later portfolio conversion after statistical and tradeability evidence.
- `promotion_ready`: requires both a complete candidate plan and a promotion-ready quality gate.

## Boundaries

The gate does not pretend planned controls are implemented. It only forces a candidate family to declare how each control will be handled and keeps portfolio/promotion blocked until actual evidence exists. This preserves the current research-to-review boundary: no broker connection, no live account reads, no orders, and no automatic trading.

## Files

- `src/quant_robot/ops/factor_mining_candidate_plan_gate.py`: reusable gate builder, writer, validator, Markdown renderer, and default CN stock control plan.
- `scripts/run_factor_mining_candidate_plan_gate.py`: CLI for validating preregistration artifacts.
- `src/quant_robot/ops/lottery_extreme_upside_reversal_preregistration.py`: adds the default control declaration to the active Round149/Round150 candidate family.
- `src/quant_robot/ops/factor_mining_startup.py`: makes the candidate plan gate part of the startup protocol before each future mining run.

## Success Criteria

- Missing control declarations block the candidate plan gate.
- The current Round149 lottery/MAX-effect preregistration clears research screening but keeps portfolio grid and promotion disabled.
- Startup gate packets include the new candidate-plan control protocol every time the CN stock mining flow starts.
