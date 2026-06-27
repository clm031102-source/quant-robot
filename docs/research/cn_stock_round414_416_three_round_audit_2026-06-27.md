# CN Stock Rounds 414-416 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Executive Decision

Rounds 414-416 changed the priority from "find another similar high-return stream" to "make the best candidate actually simulatable."

The main discovery is structural: the old best Round407 stream is a strong research observation, but not a clean paper-simulation handoff because its controls were keyed by exit/event dates. Round416 repaired that by rebuilding the candidate with entry-timed controls.

## Round Summary

| Round | Work | Result | Decision |
|---|---|---|---|
| 414 | Independent-source triage | No fast independent source had enough evidence to justify a new grid before paper-readiness work | Do not burn cycles on weak new source families |
| 415 | Signal reconstruction audit | Round407 event returns reconcile almost exactly, but paper readiness fails | Treat Round407 as research observation only |
| 416 | Entry-timed overlay rebuild | Paper-ready candidate passes full-sample, OOS, block, and beta audits | Add entry-timed candidate to simulation shortlist |

## Key Evidence

Round415 reconstruction:

- candidate: `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21`
- max absolute return reconciliation difference: `2.8275992658421956e-16`
- paper-ready: false
- blockers:
  - `exit_timed_exposure_requires_entry_timed_rebuild`
  - `event_decision_date_collapses_multiple_trade_decisions`
  - `trade_pairs_missing_event_exposure`

Round416 entry-timed candidate:

- candidate: `paper_ready_dragon_hot_alpha101_openclose_entry_timed_vt6_self_roll21`
- total return: +143.58%
- annualized return: 5.53%
- Sharpe: 0.933
- overlap Sharpe: 0.487
- max drawdown: -21.54%
- mean OOS annualized return: 5.32%
- OOS strict pass rate: 76.67%
- beta-hedged annualized return: 5.49%
- beta-hedged max drawdown: -11.10%
- paper-ready: true

## What Went Right

- The process caught a real handoff risk before simulated paper trading.
- The repair was implemented as reusable code and tested.
- The new candidate preserves the Dragon-Hot plus Alpha101 idea while removing the exit-timed exposure dependency.

## What Still Needs Work

- The paper-ready version gives up about 2 percentage points of annualized return versus the old exit-timed observation.
- Win rate remains around 40.65%, so return distribution and sizing still matter more than hit rate.
- The best-month log share is 49.84%, which passes the current gate but still shows meaningful concentration.
- The candidate should be cost-stressed again in the final paper-simulation adapter if the simulator uses a different turnover/accounting model.

## Process Rule Going Forward

No candidate should be promoted to paper simulation unless its selection, exposure, volatility target, self-risk guard, and regime/capacity filters can be computed using information available before the entry decision.

Exit-timed streams may remain useful for research diagnosis, but they cannot be treated as tradable candidates without an entry-timed rebuild.
