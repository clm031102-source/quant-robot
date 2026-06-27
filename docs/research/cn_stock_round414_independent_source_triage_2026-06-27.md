# CN Stock Round414 - Independent Source Triage

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round414 checked whether the next mining round should rotate into an independent source family after Round411-413 showed the current shortlist is dominated by a correlated Alpha101/Qlib/Dragon-Hot cluster.

This was a triage round, not a portfolio grid.

## Sources Reviewed

### Financial Reporting Timeliness

Latest durable evidence: Round302.

- aggregate rows: 84,499
- unique symbols: 394
- required unique symbols before candidate generation: 1,000
- candidate generation: blocked

Decision: do not generate financial-reporting timeliness factors yet. Coverage is only 39.4% of the source gate.

### Forecast / Express Events

Reviewed completed rounds:

- Round255 express profit surprise
- Round256 forecast guidance uncertainty
- Round267 preregistered forecast/express disagreement
- Round268 disagreement PIT prescreen

Coverage is broad, but the tested hypotheses failed IC strength, yearly stability, quantile shape, or multiple-testing gates.

Decision: keep forecast/express hibernated unless a genuinely new orthogonal hypothesis is introduced.

### Official Tradeability Event State

Reviewed Round260.

- candidates: 7
- horizon tests: 14
- residual research leads: 0
- portfolio preflight candidates: 0

Decision: use official tradeability as an execution/control layer, not a standalone alpha source.

### Share Unlock / Pledge Supply Events

Reviewed Round251.

The unlock-pressure diagnostic had strong IC in only 3 calendar years. Pledge-relief had broad coverage but wrong sign and weak size-neutral translation.

Decision: no direct ranking or portfolio grid. Possible future use only as a risk-exclusion or industry-level supply-pressure state after a new plan.

### Event Contextual Underreaction

Reviewed Rounds248-250.

Round248 produced attractive IC leads, but Round249/250 showed the holder-number leads were redundant and residual variance collapsed. `event_repurchase_quiet_volume_20` kept partial residual IC but failed yearly stability.

The current output does not preserve reusable factor rows for shortlist-entry projection, so converting it into a current-candidate filter would require recomputing the event matrix.

Decision: do not spend the 24h sprint recomputing this family unless the project explicitly chooses event-filter engineering over simulation preparation.

## Decision

Do not start a new independent-source mining grid immediately.

The fastest path to a useful 24h outcome is now:

1. carry the best current candidate into a pre-paper simulation readiness pack;
2. keep independent-source families hibernated unless they pass coverage and residual gates;
3. only re-enter event/context sources with a specific, cached, PIT-safe filter hypothesis.

## Next Direction

Round415 should prepare the current best candidate for the simulated paper stage:

- verify event stream schema and metrics one more time;
- define the paper-risk profile around the user's drawdown tolerance;
- create or adapt a local paper-simulation manifest for the selected CN stock candidate;
- keep live/broker/account/order boundaries closed.
