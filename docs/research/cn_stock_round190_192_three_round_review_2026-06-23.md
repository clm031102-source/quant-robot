# CN Stock Round190-192 Three-Round Review

- Date: 2026-06-23
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN stock cross-sectional factor infrastructure and factor prescreening, not ETF rotation
- Review trigger: three completed rounds since Round187-189 review

## Rounds Reviewed

- Round190: 2024-07 external-feed monthly shard and coverage audit.
- Round191: Northbound holding and northbound-flow interaction IC/quantile/turnover prescreen.
- Round192: Margin-credit financing crowding/exhaustion IC/quantile/turnover prescreen.

## Evidence Summary

Round190:

- `external_margin_detail`: 85,836 new shard rows; all six external-feed seeds became matrix-ready.
- HK hold coverage passed: 40 observation dates, 134,461 rows, 3,980 symbols, 1-day median gap.
- LPR remained blocked: 340 complete SHIBOR rows but 0 non-null LPR rows.
- This was readiness evidence only, not alpha evidence.

Round191:

- Tested two preregistered northbound seeds over 2,260,686 factor rows and 2,121,490 aligned labels.
- Both tests were FDR-significant but in the wrong or weak direction.
- `northbound_hold_ratio_accumulation_20`: IC -0.0081, ICIR -0.174, IC positive rate 43.7%, monotonicity 0.300.
- `northbound_hold_accumulation_flow_regime_20`: IC -0.0055, ICIR -0.117, IC positive rate 44.9%, monotonicity 0.300.
- Decision: reject positive northbound accumulation direct-rank line; 0 research leads, 0 promotion candidates.

Round192:

- Tested two preregistered margin-credit seeds over 2,435,482 factor rows and 2,277,034 aligned labels.
- Both tests were FDR-significant and positive.
- `margin_balance_crowding_reversal_20`: IC 0.0555, ICIR 0.962, IC positive rate 83.8%, Q5-Q1 0.0244, monotonicity 0.300, turnover 18.9%.
- `margin_financing_acceleration_exhaustion_20`: IC 0.0341, ICIR 0.472, IC positive rate 66.5%, Q5-Q1 0.1824, monotonicity 0.600, turnover 28.5%.
- Decision: 2 statistical audit candidates, but 0 strict research leads because quantile monotonicity failed; 0 promotion candidates.

## Direction Audit

The direction correction worked. After the northbound direct-rank line failed, the workflow rotated to a preregistered margin-credit crowding/reversal family instead of continuing to mine the same weak direction. This is aligned with the user's requirement to avoid endless single-family lock-in.

The process also improved compared with earlier blind searches:

- All external-feed joins use `available_date`.
- Same-day raw external-feed observations are rejected.
- The test uses full available long-cycle bars through 2025-12-31 while excluding 2026 final holdout.
- Multiple testing is counted across factor x horizon tests.
- Portfolio grids are blocked until prescreen, dedup, neutralization, cost/capacity, regime, and holdout gates clear.

## What Is Promising

The margin-credit family has the strongest external-feed statistical evidence so far in this block. Both IC levels are economically visible, especially `margin_balance_crowding_reversal_20` with IC 0.0555 and ICIR 0.962 over 334 IC dates. The result is not a tradable strategy yet, but it is worth a focused audit.

## What Is Still Weak

The quantile shape is not clean. Monotonicity of 0.300 and 0.600 implies the factor may be tail-driven, sector-driven, liquidity-driven, or dominated by a specific crowding bucket. A direct top-N long-only conversion would be premature.

## Decision

- Continue the margin-credit family for one controlled audit round.
- Next round: Round193 external margin-credit reference dedup, industry/size/liquidity neutral IC, and quantile-shape audit.
- Do not run portfolio grid yet.
- Keep positive northbound accumulation hibernated unless a new negative northbound crowding/reversal hypothesis is separately preregistered before testing.
- Keep LPR-dependent macro factors blocked until non-missing LPR coverage is repaired.
