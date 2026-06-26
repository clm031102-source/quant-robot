# CN Stock Round187-189 Three-Round Review

- Date: 2026-06-23
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN stock cross-sectional factor infrastructure, not ETF rotation
- Review trigger: three completed rounds since Round184-186 review

## Rounds Reviewed

- Round187: 2024-10 external-feed monthly shard
- Round188: 2024-09 external-feed monthly shard
- Round189: 2024-08 external-feed monthly shard

These rounds were data-readiness and process-hardening work. They did not mine or promote profitable alpha factors.

## Evidence Summary

Round187:

- `external_margin_detail`: 59,141 rows
- `external_hk_hold`: 0 canonical CN-stock rows
- `external_hsgt_flow`: 10 rows
- `external_index_state`: 18 rows
- `external_macro_rates`: 14 rows, LPR missing
- Join smoke: 4 pass, 2 insufficient-history, 0 PIT/raw-date violations
- Matrix-ready seeds: two margin seeds, SHIBOR regime, index-state regime

Round188:

- `external_margin_detail`: 66,683 rows
- `external_hk_hold`: 3,540 canonical CN-stock rows
- `external_hsgt_flow`: 17 rows
- `external_index_state`: 19 rows
- `external_macro_rates`: 18 rows, LPR missing
- Join smoke: 4 pass, 2 insufficient-history, 0 PIT/raw-date violations
- Full-window joined rows: 3,586,126
- HK hold coverage: 6 observation dates, 20,744 rows, 3,952 symbols, median gap 92 days
- Macro coverage: 295 SHIBOR-complete rows, 0 LPR rows

Round189:

- `external_margin_detail`: 86,124 rows
- `external_hk_hold`: 40,112 canonical CN-stock rows
- `external_hsgt_flow`: 21 rows
- `external_index_state`: 22 rows
- `external_macro_rates`: 22 rows, LPR missing
- Join smoke: 4 pass, 2 insufficient-history, 0 PIT/raw-date violations
- Full-window joined rows: 3,932,590
- HK hold coverage: 18 observation dates, 60,856 rows, 3,972 symbols, median gap 1 day, max gap 92 days
- Macro coverage: 317 SHIBOR-complete rows, 0 LPR rows

## What Improved

- Long-cycle matrix readiness improved across margin, SHIBOR, and index-state seeds.
- Margin seeds advanced from 286 observation dates in Round187 to 325 observation dates in Round189.
- SHIBOR regime coverage advanced from 277 observation dates in Round187 to 317 in Round189.
- Index-state regime coverage advanced from 304 observation dates in Round187 to 345 in Round189.
- HK hold moved from effectively unusable sparse coverage to near-daily segments after adding 2024-08, but still has only 18 observation dates.
- A repeatable path-root footgun was fixed: join smoke and coverage audit now accept either the parent processed root or the `processed` child directory.

## What Did Not Improve Enough

- No profitability evidence exists from these rounds: no IC screen, no quantile monotonicity, no turnover decay, no portfolio conversion, no walk-forward acceptance.
- HK hold is still blocked by minimum observation dates. It cannot enter daily cross-sectional IC or portfolio tests yet.
- LPR remains fully missing. LPR-dependent policy-liquidity factors stay blocked.
- The join smoke implementation is still slow on full-window runs because it loops over signal dates and recomputes latest eligible observations. This is acceptable for validation but should be optimized before frequent large sweeps.

## Direction Audit

The direction was not factor overfitting; it was controlled data-readiness work for external macro, credit, northbound, and index-state context. That direction remains justified because:

- It directly addresses earlier user concerns about regime blindness, short windows, and missing China-specific context.
- It is not a blind parameter sweep.
- It has clear blockers and stop conditions.

The direction must remain bounded:

- Do not treat external feed ingestion, join smoke, or coverage audit as alpha evidence.
- Do not run HK-hold daily ranking IC until HK hold clears coverage.
- Do not run LPR factors until LPR non-missing coverage clears.
- Do not expand external-feed factor formulas before the current preregistered seeds reach long-cycle matrix readiness.

## Decision

Continue one controlled backfill round to 2024-07:

- Primary goal: continue margin, SHIBOR, and index-state long-cycle coverage.
- Secondary goal: see whether HK hold exceeds the 25-observation-date threshold.
- Blocked: LPR factors and HK-hold daily ranking factors until coverage gates pass.
- No promotion or profitability claim allowed from Round190 ingestion alone.

If Round190 still leaves HK hold below threshold or LPR at 0, keep those feeds blocked and continue only if the long-cycle backfill is still advancing matrix-ready regime coverage. If the next three rounds do not unlock a new testable seed, rotate from data backfill to a different preregistered family or to infrastructure optimization.
