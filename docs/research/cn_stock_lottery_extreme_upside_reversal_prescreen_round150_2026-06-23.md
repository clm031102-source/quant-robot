# CN Stock Lottery Extreme Upside Reversal Prescreen Round150

Date: 2026-06-23

Machine/task: office_desktop / factor_validation

Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`

Scope: CN A-share stock cross-sectional alpha research only.

## What Ran

Round150 replayed the six Round149 lottery-demand / MAX-effect candidates across the long CN stock sample before any portfolio conversion.

Output directory:

`data/reports/lottery_extreme_upside_reversal_prescreen_round150_20260623`

Entry point:

`python scripts\run_lottery_extreme_upside_reversal_prescreen.py --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --execution-lag 1`

The run used:

- long-cycle bars from 2015-01-05 through 2025-12-31;
- 5,707 A-share assets;
- 10,785,537 daily bar rows;
- 60,706,799 factor rows;
- 21,417,227 forward-return label rows;
- 120,521,482 aligned factor-label rows;
- horizon 5 and horizon 20, both with one-bar execution lag;
- final 2026 holdout excluded.

## Gate Results

| Metric | Value |
|---|---:|
| Candidates | 6 |
| Factor x horizon tests | 12 |
| FDR-significant tests | 12 |
| Neutral-gate pass tests | 10 |
| Public-reference de-dup pass tests | 12 |
| Research leads | 0 |
| Promotion candidates | 0 |

This is a useful rejection, not a failed run. The public MAX-effect family has measurable long-cycle RankIC, but it did not produce a clean tradable long-side research lead after quantile-shape and neutralization checks.

## Top Evidence

| Factor | Horizon | IC | ICIR | IC t | IC>0 | Q5-Q1 | Industry-neutral IC | Size-neutral IC | Max ref corr | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `lottery_gapless_max_reversal_20` | 20 | 0.0499 | 0.349 | 17.94 | 65.5% | -0.0446 | 0.5820 | 0.0587 | 0.749 | no |
| `lottery_gapless_max_reversal_20` | 5 | 0.0424 | 0.327 | 16.84 | 63.8% | -0.0109 | 0.5834 | 0.0485 | 0.749 | no |
| `lottery_climax_volume_reversal_20` | 20 | 0.0416 | 0.319 | 16.43 | 65.0% | -0.0370 | 0.5807 | 0.0607 | 0.843 | no |
| `lottery_climax_volume_reversal_20` | 5 | 0.0411 | 0.346 | 17.84 | 65.4% | -0.0155 | 0.5850 | 0.0538 | 0.843 | no |
| `lottery_max_return_reversal_20` | 20 | 0.0353 | 0.234 | 12.02 | 61.1% | -0.0446 | 0.5753 | 0.0554 | 0.751 | no |
| `lottery_upper_shadow_reversal_20` | 20 | -0.0819 | -0.586 | -30.15 | 29.3% | 0.0933 | 0.4974 | -0.0015 | 0.322 | no |

## Why Nothing Is Usable Yet

The strongest positive-IC candidates fail the portfolio-translation shape:

- `lottery_gapless_max_reversal_20`, `lottery_climax_volume_reversal_20`, and `lottery_max_return_reversal_20` have positive RankIC, but top-minus-bottom return spread is negative and quantile monotonicity is weak or reversed.
- That means the signal can rank the cross-section statistically, but the high-score bucket is not a clean long portfolio. A direct TopN or top-quantile portfolio from these scores would be methodologically unsafe.

The apparent upper-shadow payoff is not a clean alpha:

- `lottery_upper_shadow_reversal_20` has positive Q5-Q1 spread, but raw RankIC is strongly negative and the size/liquidity-neutral IC gate fails.
- It cannot be promoted by pointing to the spread alone; this is exactly the IC-to-portfolio gap the new workflow is meant to catch.

The family is not simply rejected because it duplicates public references:

- all 12 tests passed the public-reference correlation cap of 0.85;
- the problem is weaker: the signals do not translate into stable, monotonic, neutral long-side portfolio evidence.

## Decision

Do not continue tuning the lottery/MAX-effect family as a standalone long alpha after Round150.

Allowed future use:

- keep the evidence as a possible exclusion/risk overlay only if a separate profitable base signal exists;
- require a new preregistration if this family is revisited as a short-side, bottom-exclusion, or execution-aware overlay.

Blocked:

- no portfolio grid from these six candidates;
- no formula tuning after seeing these results;
- no direct TopN, top-quantile, or high-return claim from the positive RankIC rows;
- no promotion or paper-ready claim.

## Next Direction

Rotate away from lottery/MAX-effect.

Recommended Round151 direction:

`round151_rotate_to_pit_profitability_event_revision_preregistration`

Reason:

- The lottery family produced evidence but no usable lead.
- The project now has stricter startup and candidate-plan controls, so the next efficient use of compute is a new PIT-aware family rather than more parameter searching inside this failed family.
- The next family should prioritize information timing, financial/event availability, neutralization, and pre-registered economic rationale before any return or Sharpe screen.
