# CN Stock Round379-381 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: three-round review for the 24h CN stock profit-factor sprint. Research-to-review only; no broker, account, order, or live-trading access.

## Rounds Audited

| Round | Focus | Outcome |
|---:|---|---|
| 379 | Public defensive OOS split | ADX/KAMA remain useful defensive leads, but no new simulation candidate |
| 380 | Forecast/express selected-trade event audit | Rejected simple forecast/express cash filters |
| 381 | Dragon-Tiger selected-trade event audit | Found a new Dragon-Tiger crowding-risk research lead |

## Key Decisions

The public technical line is not dead, but it is incremental. It improves drawdown/overlap more than return and does not beat the current shortlist enough to add complexity.

The forecast/express line does not work as a simple selected-trade defensive filter. Negative events are not bad enough in the current basket; cashing them would reduce return.

The Dragon-Tiger line is the most useful new direction from these three rounds. Recent hot attention/net-buy events have negative selected-trade contribution and deserve a portfolio quickcheck.

## Direction After Audit

Continue with Dragon-Tiger as the next event-family lead, but keep the raw-generation/calendar gate:

- research lead allowed;
- simulation shortlist not allowed;
- official event-calendar reconstruction required before promotion.
