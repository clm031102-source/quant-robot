# CN Stock Round376-378 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: three-round review for the 24h CN stock profit-factor sprint. Research-to-review only; no broker, account, order, or live-trading access.

## Rounds Audited

| Round | Focus | Outcome |
|---:|---|---|
| 376 | Event-calendar rule diagnosis | Frozen Round338/Round339 low10 event stream is exact; Round367 generated stream has calendar drift |
| 377 | Raw-generation handoff policy | Added config and code gates to prevent blocked generated streams from entering simulation |
| 378 | Three-round review | Continue simulation handoff with frozen event sources; treat raw generation as a separate blocked engineering track |

## Main Evidence

Round338 reference versus Round339 official wrapper base:

- common dates: 834;
- missing dates: 0;
- extra dates: 0;
- max absolute return difference: 0;
- signal/entry-date mismatches: 0.

Round338 reference versus Round367 generated:

- common dates: 736;
- missing generated dates: 98;
- extra generated dates: 132;
- common-date return differences above 1 bp: 218;
- max absolute common-date return difference: 0.5741%;
- common-date return correlation: 0.9994.

## Decision

Do not spend the next mining cycle trying to force the generated stream into the simulation shortlist.

The right split is:

- simulation handoff track: keep using frozen, replay-validated event files for the five current candidates;
- raw-generation engineering track: recover/rebuild trade-level evidence and make the generated stream pass event-calendar parity before it can replace frozen event files;
- alpha-mining track: resume searching for independent factor families instead of over-optimizing the same low-turnover replacement family.

## Process Upgrade

`scripts/check_simulation_shortlist_config.py` now blocks configs that lack a raw-generation policy or that point a simulation candidate at a blocked generated event source.

This directly addresses the workflow risk found in Round373-376: a generated stream that is economically close but not event-calendar identical must not silently become production evidence.

## Next Direction

Return to factor discovery, but keep the stronger handoff discipline:

1. new factors can be mined as research leads;
2. any candidate moving toward simulation must have frozen event-source replay, event-schema replay, block audit, OOS split, cost stress, and raw-generation status declared;
3. raw-generated event streams cannot replace frozen events without passing the parity gate.
