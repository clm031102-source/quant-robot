# CN Stock Round426-428 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Executive Decision

Rounds 426-428 did not produce a new promoted factor. They did produce a useful direction change:

- do not revive old failed leads;
- do not keep mutating correlated Dragon-Hot/Alpha101/Qlib variants;
- do not upgrade public technical cohort overlays in the current harness;
- downgrade the Round425 default from clean default to conditional default because of extreme-trade stress.

The next highest-value work is entry-known extreme-risk repair. The current best candidate remains the benchmark, but it is not clean enough to hand to simulation without either repair or explicit tail-risk acceptance.

## Round Summary

| Round | Work | Result | Decision |
|---|---|---|---|
| 426 | Old-lead salvage and rotation audit | Daily-basic free-float supply quality and older low-turnover/liquidity references were not worth reviving; Alpha101/Qlib/Dragon-Hot variants were highly redundant | No older lead upgraded |
| 427 | Public technical cohort screen | RSRS, Bollinger, RSI, Donchian, and MACD cohort overlays trailed the Round425 default; SuperTrend/smart-money style sources were coverage-blocked in the current table | No public technical candidate upgraded |
| 428 | Default cohort trade-level extreme audit | 190 active `abs(gross_return) > 50%` trades contributed about 25% of total return; removing them as a diagnostic haircut cut return quality sharply and breached drawdown/concentration stress | Default downgraded to conditional |

## What Worked

The process improved in three ways:

1. Direction rotation happened. Round427 directly tested public technical ideas instead of only funding-flow or Alpha101 micro-variants.
2. Promotion discipline tightened. Round428 caught a risk that ordinary full-sample/OOS/beta metrics missed.
3. Causality discipline stayed intact. Realized gross-return filters were explicitly banned as deployable rules because they use future information.

## What Failed

The current search still has no newly promoted independent factor family.

Specific failures:

- Old factor families did not survive prior dedup, residual, or holdout audits.
- Public technical overlays did not beat the existing cohort default after full-sample, OOS, and beta checks.
- The strongest candidate's headline return is partly tied to rare extreme winners, especially around 2015.

## Current Candidate Status

The best ordinary-metric candidate remains:

`paper_ready_cohort_dragon_hot_alpha101_openclose_entry_timed_vt08_max100_self_roll21_x08`

Status after this review:

`conditional_default_pending_extreme_risk_repair`

It should be treated as:

- a benchmark for new research;
- a conditional simulation lane if the user accepts high tail dependence;
- not a clean default until an entry-known repair survives.

## Next Work Plan

Round430 should not run another broad blind factor grid. It should inspect the 190 active extreme trades and compare them against normal active trades using only entry-known fields.

Priority entry-known dimensions:

- board and exchange eligibility;
- listing age and recent IPO status;
- entry-day price-limit or suspension/ST/delist constraints;
- entry amount, volume, turnover, and participation;
- industry and concept crowding;
- Dragon-Tiger hotness source fields known before entry;
- public factor rank and tilt bucket;
- market regime before entry.

Candidate repair rules must be causal:

- board/listing-age quarantine;
- liquidity or turnover floor/ceiling known at entry;
- concentration cap by industry or event date;
- entry-time volatility or gap-risk cap;
- smaller exposure for extreme-prone sub-buckets.

Forbidden repair:

- excluding trades because realized `gross_return` later exceeded a threshold.

## Success Criteria For The Next Repair

A repair candidate is useful only if it improves tail robustness without destroying the edge:

- keeps total return positive and annualized return competitive with the default;
- keeps max drawdown near or inside -30%;
- improves overlap Sharpe or best-month concentration after the same stress audit;
- passes OOS split and beta-hedged checks;
- is fully entry-known and replayable from config.

## Updated Direction

Continue the 24h sprint, but bias work toward:

1. entry-known tail repair for the current benchmark;
2. independent event-context underreaction if the repair fails;
3. tradeability and microstructure quality families with capacity controls from the first screen;
4. coverage-gated PIT accounting quality only if announcement-date alignment is verified.

This is the right direction because simulation readiness depends more on eliminating tail/data-quality traps now than on adding another visually attractive in-sample factor.
