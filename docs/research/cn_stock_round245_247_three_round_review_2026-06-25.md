# CN Stock Round245-247 Three-Round Review

Date: 2026-06-25
Machine: office_desktop
Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
Task: factor_validation

## Scope

This review covers the three accounting-quality statement rounds after the Round244 new-substructure failure:

- Round245: directional audit of `aq_abnormal_accrual_change_reversal`.
- Round246: post-statement cash-conversion muted-reaction drift.
- Round247: realized statement profitability revision.

All work is CN-stock cross-sectional research-to-review only. No broker connection, account read, order placement, paper-ready claim, live claim, or final-holdout read is allowed.

## Round Summary

| Round | Direction | Candidates | Tests | Best Evidence | Decision |
|---|---|---:|---:|---|---|
| 245 | Sign audit of Round244 accrual-change clue | 1 | 2 | 5d IC 0.0505, ICIR 0.399, t 2.292, FDR true, Q5-Q1 0.0082 | Watchlist only; industry-neutral t-stat 1.629 below gate |
| 246 | Cash-conversion improvement plus muted announcement reaction | 1 | 2 | 20d IC 0.0373, ICIR 0.264, IC>0 63.6% | Rejected; no FDR, negative quantile spread, industry-neutral IC negative |
| 247 | Profitability acceleration with cash confirmation or asset-discipline penalty | 2 | 4 | No positive robust evidence; best raw ICs are negative or near zero | Rejected; no FDR, no neutral gate pass, no lead |

## Hard Counts

Across Rounds 245-247:

- New factor names tested: 4
- Factor x horizon tests: 8
- Multiple-testing significant tests: 1
- Neutral-gate pass tests: 0
- Research leads: 0
- Walk-forward candidates: 0
- Paper-ready candidates: 0
- Promotable candidates: 0

## What Worked

The useful output is process and infrastructure, not alpha:

- A `new_substructure_directional_audit` mode now prevents free sign-flip promotion.
- A `statement_event_drift` mode now tests PIT announcement-reaction ideas.
- A `statement_profitability_revision` mode now tests realized profitability acceleration without mixing old raw candidates.
- All three rounds stayed on long-cycle 2015-2025 data and excluded final holdout.
- Each candidate family was small and preregistered, reducing multiple-testing waste.
- Portfolio conversion remained blocked because no residual IC lead survived.

## What Failed

The statement-accounting family did not produce a usable factor in this 130-symbol sample:

1. The only statistical bright spot was Round245 5d sign flip, but it failed the industry-neutral gate and had weak ICIR.
2. Round246 showed that "good cash conversion plus muted reaction" does not create a robust drift signal here.
3. Round247 showed realized profitability acceleration is directionally wrong or too weak without actual surprise or expectation data.
4. No round generated a neutral-gate pass, so no candidate deserves walk-forward, cost/capacity, or portfolio conversion.

## Audit Judgment

Continue mining, but stop tuning this realized statement formula line.

This is not a failure of using financial statements as a data source. It is a failure of these specific realized accounting transforms as standalone alpha. The next effort should move closer to information surprise, expectation revision, or event context.

The current evidence says:

- Do not run TopN portfolio grids for Rounds 245-247.
- Do not promote the Round245 sign flip.
- Do not invert Round247 negative results into short factors without a new preregistration.
- Do not spend another round on simple netprofit/cashflow/assets formula mutations.

## Next Plan

Round248 should rotate to one of the following families:

1. External or explicit expectation revision:
   - analyst/forecast revision if local data exists;
   - earnings preview or guidance-like proxy;
   - announcement surprise versus prior trend or industry peers.

2. Nonfinancial event context:
   - dividend or buyback event drift;
   - pledge, unlock, shareholder change, or management action;
   - event timing combined with tradeability and liquidity constraints.

3. Industry-relative surprise:
   - profitability acceleration relative to same-industry peers on the same announcement window;
   - only if preregistered as a new family and counted as new hypotheses.

## Required Gates For Round248

- Pre-register the family before computing labels.
- Keep candidate count small.
- Use PIT signal dates after the true announcement or event date.
- Use 2015-2025 long-cycle sample and exclude final holdout.
- Require residual IC, FDR, quantile shape, industry/size/liquidity neutral gates.
- Block portfolio, paper, and live claims until a real lead exists.

Next direction:

`round248_rotate_to_external_revision_or_nonfinancial_event_context`
