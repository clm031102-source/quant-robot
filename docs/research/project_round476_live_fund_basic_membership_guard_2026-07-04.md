# Project Round476 Live Fund-Basic Membership Guard

Date: 2026-07-04

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Scope: harden the Round475 CN ETF rotation-membership repair so live Tushare recent refreshes cannot silently fall back to the old all-membership path when `fund_basic` is unavailable.

## Progress Snapshot

Estimated project completion after this guard: 96%.

Round475 fixed the normal path: when live Tushare `fund_basic` is available, recent-refresh membership now excludes non-ETF funds such as `501222.SH`. Round476 closes the failure path: when live Tushare `fund_basic` cannot be loaded, the refresh is marked `data_quality_blocked` instead of writing a permissive rotation membership.

## Startup Context

| Item | Value |
| --- | --- |
| Machine/task | office_desktop / factor_review |
| Current branch | `codex/factor-batch-cn-stock-execution-aware-round465-20260704` |
| Quant PM gate | `ready` |
| Gate blockers | none |
| Primary market | `CN_ETF` |

The work stayed inside the research-to-paper boundary.

## Change

Changed:

- `scripts/run_recent_data_refresh.py`
- `src/quant_robot/ops/recent_data_refresh.py`
- `tests/unit/test_recent_data_refresh_cli.py`

Behavior after the guard:

| Scenario | Result |
| --- | --- |
| live `tushare` + `CN_ETF` + valid `fund_basic` | write membership with `tushare_fund_basic_fund_daily` |
| live `tushare` + `CN_ETF` + missing/empty `fund_basic` | do not write permissive membership; block refresh |
| fixture source | keep fixture fallback membership for tests |

New blocker:

```text
rotation_membership_fund_basic_missing
```

The refresh pack now carries this through `coverage` and `decision.blockers`, so downstream post-refresh replay will not run Daily Ops on an unvalidated CN ETF universe.

## Regression Evidence

New test:

```text
test_live_tushare_refresh_blocks_when_fund_basic_membership_cannot_be_validated
```

RED result before the guard:

```text
expected data_quality_blocked, got completed
```

GREEN result after the guard:

```text
1 passed
```

Related test suite after the guard:

```text
25 passed
```

Covered paths:

- `test_fund_basic_rotation_membership_excludes_lof_from_recent_refresh`
- `test_live_tushare_refresh_blocks_when_fund_basic_membership_cannot_be_validated`
- recent refresh pack construction
- Tushare CN ETF sync membership builder
- post-refresh replay
- observation sufficiency
- expanded observation replay

## Decision

This makes the CN ETF paper replay path stricter and safer. A live recent refresh must now have fund-basic validated rotation membership before it can be considered ready for downstream replay.

Remaining completion work is unchanged:

- laptop must integrate this branch into `main`;
- laptop must run safe remote topic-branch cleanup;
- repaired paper-observation sufficiency should be rerun or explicitly re-scoped after integration;
- profit-factor mining should wait until main is stable and the scheduler opens a pre-registered orthogonal direction.
