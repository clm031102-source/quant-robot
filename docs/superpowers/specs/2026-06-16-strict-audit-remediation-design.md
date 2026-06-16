# Strict Audit Remediation Design

## Context

The strict audit found no live-trading boundary violation, but it found several
research-readiness gaps that can make local evidence look stronger than it is.
This design keeps the project research-to-paper only and turns the audit
findings into executable checks.

## Scope

In scope:

- Make `scripts/run_checks.py` run child Python commands against this worktree's
  `src` package, even when the parent interpreter is not the project virtualenv.
- Make walk-forward validation reject candidates that fail adjusted IC
  significance after multiple-testing correction.
- Add explicit Alpha Factory gates for minimum trades, minimum IC observations,
  minimum long-short observations, and strict capacity-cost controls.
- Prevent tiny or degenerate IC samples from reporting statistical significance.
- Update lightweight docs for the safer commands and stricter research policy.

Out of scope:

- Broker adapters, account reads, order placement, or live trading.
- New provider downloads or committing generated data.
- Rebuilding local raw or processed data artifacts.

## Design

`run_checks.py` will construct a child environment with `src` and the repository
root prepended to `PYTHONPATH`, then run all check steps from the project root.
It will also expose small helper functions that tests can verify directly.

Walk-forward validation already calculates Bonferroni-adjusted IC evidence. The
fix is to apply that evidence before ranking and to rewrite any accepted row
that fails the adjusted p-value gate into a rejected row with an explicit
`adjusted_ic_significance_not_passed` reason.

Alpha Factory will keep smoke runs possible, but only through explicit low
thresholds. Defaults will move toward research-grade gates: at least 30 trades,
at least 20 IC observations, at least 20 long-short observations, nonzero market
impact, and an explicit participation cap. Candidate rejection reasons will name
each failed gate.

The IC summary will stop reporting significance from tiny samples. Any sample
with fewer than a configured minimum number of IC observations, or zero
cross-period variance, will be marked insufficient rather than significant.

## Validation

Required local validation:

- Targeted unit tests for each changed behavior.
- `.\.venv\Scripts\python.exe -m unittest discover -s tests`
- `.\.venv\Scripts\python.exe -m compileall -q src scripts tests`
- `.\.venv\Scripts\python.exe scripts\run_project_audit.py --json`
- `.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop --execute`

The full profile remains a desktop/heavier-machine check unless it is split or
given longer runtime control.
