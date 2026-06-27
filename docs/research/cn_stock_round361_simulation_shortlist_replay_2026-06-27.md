# CN Stock Round361 - Simulation Shortlist Replay

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round361 adds a repeatable evidence replay check for the simulation shortlist.

The new checker reads each candidate's configured event-return source, recomputes full-sample return metrics, and compares them with the evidence stored in:

`configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json`

Reusable entrypoint:

`scripts/run_simulation_shortlist_replay.py`

Unit test:

`tests/unit/test_simulation_shortlist_replay.py`

Output:

`data/reports/round361_24h_profit_sprint_simulation_shortlist_replay_20260627`

## Bug Found And Fixed

The first replay caught a real inconsistency in `safer_defensive_zz500`.

Root cause:

- the Round345 safer event file contains both `period_return` and `overlay_return`;
- `period_return` is the pre-regime base stream;
- `overlay_return` is the final stream after the CSI500 regime overlay;
- the config evidence for `safer_defensive_zz500` corresponds to `overlay_return`.

Fix:

- set `safer_defensive_zz500.event_return_source.return_column` to `overlay_return`;
- rerun Round356 and Round357 block audits using the corrected final stream;
- update the affected docs and config values.

## Replay Result

After the fix:

| Candidate | Source Column | Replay Status |
|---|---|---|
| `primary_high_return` | `period_return` | passed |
| `primary_balanced_zz500_75` | `period_return` | passed |
| `primary_defensive_zz500` | `period_return` | passed |
| `safer_defensive_zz500` | `overlay_return` | passed |
| `primary_ps_filtered_defensive_zz500` | `period_return_variant` | passed |

Replay summary:

- candidates: 5;
- replayed candidates: 5;
- blocked candidates: 0;
- blockers: none;
- metric tolerance: 0.005.

## Corrected Safer Defensive Metrics

Using final `overlay_return`:

- total return: +114.76%;
- annualized return: +4.73%;
- Sharpe: 0.996;
- overlap Sharpe: 0.534;
- max drawdown: -14.94%;
- leave-one-year minimum annualized return: +2.52%;
- top three months log-return share: 48.26%;
- worst year: 2018 at -9.04%.

## Direction Decision

The replay checker should be mandatory before any simulation shortlist is handed off.

Current retained lanes remain:

- `primary_high_return`;
- `primary_balanced_zz500_75`;
- `primary_defensive_zz500`;
- `primary_ps_filtered_defensive_zz500`.

`safer_defensive_zz500` remains a reference lane, not a primary lane.
