# CN Stock Round266-268 Three-Round Review

- Date: 2026-06-26
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock factor mining
- Safety: research-to-review only; no broker connection, account reads, order placement, or live trading

## Rounds Reviewed

| Round | Purpose | Evidence | Result |
|---:|---|---|---|
| 266 | Direction optimization gate | `docs/research/cn_stock_round266_direction_optimization_gate_2026-06-26.md` | Cleared stricter method gate; direct factor generation blocked before candidate/source proof |
| 267 | Forecast/express disagreement preregistration | `docs/research/cn_stock_round267_forecast_express_disagreement_preregistration_2026-06-26.md` | 3 candidates pre-registered; source/sample integrity gate added |
| 268 | PIT full-sample prescreen | `docs/research/cn_stock_round268_forecast_express_disagreement_pit_prescreen_2026-06-26.md` | 3 factors tested across 2015-2025; 0 research leads; 0 promotion candidates |

## What Was Useful

The useful output was process quality, not alpha:

- The candidate plan gate now requires source/sample integrity before prescreen.
- The promotion policy now requires long-sample regime coverage, future-function audit, strict statistics, sensitivity, and profit/drawdown/win-rate evidence.
- The forecast/express disagreement family was tested quickly and rejected before portfolio grids or promotion work consumed more budget.
- The implementation now has a reusable PIT event factor path for pairing two event feeds without using later information.

## Why The Factor Result Was Poor

The Round268 evidence does not support continuing this family:

- Raw disagreement and stale-correction variants had negative full-sample IC and negative Q5-Q1 spreads.
- The industry-relative variant had a small positive 20-day IC, but ICIR was only 0.094, t-stat was 0.70, Q5-Q1 was still negative, and year-positive rate was only 54.5%.
- The high industry-neutral IC did not translate into monotonic or positive return spreads. This is a classic IC-to-portfolio translation failure, not a hidden promotable alpha.
- The family had already been close to previously failed forecast/express and forecast-guidance work; the new formula was orthogonal enough to test once, but not worth parameter tuning after failure.

## Decision

Do not continue forecast/express disagreement. Hibernate the family unless a new external expectation source or materially different event source becomes available.

Blocked shortcuts:

- no forecast/express parameter tuning after Round268 zero leads;
- no portfolio grid from high industry-neutral IC alone;
- no sign flip or ranking inversion without a new preregistered economic thesis;
- no promotion or manual/live signal discussion.

## Next Direction

Round270 should rotate to a source-first audit for financial reporting timeliness and disclosure behavior:

`round270_financial_reporting_timeliness_source_audit_and_candidate_plan`

Rationale:

- It targets an information-release mechanism rather than another price/moneyflow/forecast formula.
- It directly addresses PIT timing and announcement-date realism.
- Local caches show financial PIT and financial statement shards exist, but current statement evidence appears partial; source coverage must be audited before factor generation.

Round270 may proceed only if it produces:

- endpoint/cache manifest for `ann_date`, `end_date`, `report_type`, and revision/final-release fields if available;
- full-sample coverage by year and symbol count, or a clear decision to backfill before mining;
- candidate plan with source/sample integrity controls;
- no portfolio grid, promotion, or profit claim before long-cycle PIT prescreen.
