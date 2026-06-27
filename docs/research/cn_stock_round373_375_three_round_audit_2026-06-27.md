# CN Stock Round373-375 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: mandatory three-round review inside the 24h profit-factor sprint.

## Rounds Reviewed

| Round | Work | Main Result | Decision |
|---:|---|---|---|
| 373 | Raw generation parity audit | New reusable generation output does not reproduce official Round339 event stream | Need event-calendar parity gate |
| 374 | Implemented event-calendar parity gate | Gate blocks current generated stream with missing/extra dates and metric drift | Raw generation not simulation-ready |
| 375 | Review | The blocker is a process-quality win, not a candidate failure | Fix calendar parity before raw handoff |

## Why This Matters

The current simulation shortlist has good replay evidence, but replay only proves that event files match the config. It does not prove those event files can be regenerated from raw processed data.

The parity audit found a repeatability gap:

- generated period dates: 868;
- official period dates: 834;
- overlap dates: 736;
- missing generated dates: 98;
- extra generated dates: 132;
- total return drift: -6.26%;
- overlap Sharpe drift: -0.021.

The trade-level selection is close, so the problem is mostly calendar and event aggregation rather than a totally different factor.

## New Reusable Gate

`scripts/run_shortlist_event_calendar_parity.py`

This gate compares a generated event stream against a reference stream and blocks on:

- missing reference dates;
- extra generated dates;
- date-level return drift;
- full-sample metric drift.

It writes:

- `event_calendar_parity_audit.json`;
- `event_calendar_parity_rows.csv`;
- `event_calendar_parity_metric_diffs.csv`.

## Decision

Do not replace official simulation shortlist event sources with raw-generated outputs yet.

The simulation shortlist itself is unchanged. The new gate becomes a required step before raw generation can be considered equivalent to the existing evidence.

## Next Direction

Round376 should diagnose the event calendar rule:

1. compare official period rows to official trade-exit grouping;
2. identify why the official stream has 834 dates while trade exits have 872;
3. implement a template-calendar alignment mode only if it can be justified without hiding return rows;
4. keep final holdout sealed.
