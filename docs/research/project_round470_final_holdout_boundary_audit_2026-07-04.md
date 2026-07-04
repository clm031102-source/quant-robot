# Project Round470 Final-Holdout Boundary Audit

Date: 2026-07-04

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-execution-aware-round465-20260704`

Scope: clarify whether any historical or current CN stock lane can be treated as final-holdout-passed while organizing the active cloud branches. This is a research-to-paper audit only; it does not open a broker, account, order, or live-trading path.

## Progress Snapshot

Estimated project completion after this audit: 94%.

This round did not clear a promotion blocker. It reduced ambiguity around the most dangerous remaining interpretation error: treating an aggregate walk-forward pass as a final-holdout pass.

## Commands

Final-holdout readiness audit, using the existing Round145 report only:

```powershell
.\.venv\Scripts\python.exe scripts\run_final_holdout_readiness_audit.py --report-path data\reports\daily_basic_free_float_supply_quality_final_holdout_with_2026_daily_basic_round145_20260622\daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward.json --output-dir data\reports\round470_final_holdout_readiness_audit_20260704
```

Final-holdout result audit, using the same existing Round145 report only:

```powershell
.\.venv\Scripts\python.exe scripts\run_final_holdout_result_audit.py --report-path data\reports\daily_basic_free_float_supply_quality_final_holdout_with_2026_daily_basic_round145_20260622\daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward.json --output-dir data\reports\round470_final_holdout_result_audit_20260704
```

No new final-holdout data window was opened for the current Round464/Round465/Round467 lanes.

## Historical Round145 Readiness

The existing Round145 `daily_basic_free_float_supply_quality` report truly touched the final holdout:

| Item | Value |
| --- | --- |
| Final holdout requested | true |
| Final holdout start | 2026-01-01 |
| Max bar date | 2026-06-15 |
| Max signal date | 2026-05-28 |
| Bars cover holdout | true |
| Signals cover holdout | true |
| Holdout fold rows | 6 |
| Aggregate accepted candidates before holdout-result audit | 6 |
| Final holdout actually read | true |

Readiness decision:

| Item | Value |
| --- | --- |
| Final holdout actual read | true |
| Promotion allowed by readiness audit | false |
| Next direction from readiness audit | `run_paper_gate_or_holdout_result_review` |

Readiness is necessary evidence, not a promotion decision.

## Historical Round145 Result

The paired result audit confirms the historical candidate family failed the read-once final holdout:

| Item | Value |
| --- | ---: |
| Aggregate accepted cases | 6 |
| Holdout case count | 6 |
| Holdout fold rows | 6 |
| Holdout passed cases | 0 |
| Best holdout total return | -0.5949% |
| Best holdout overlap-adjusted Sharpe | -5.6965 |
| Max holdout extreme trade count | 1 |

Decision:

| Item | Value |
| --- | --- |
| Paper gate allowed | false |
| Promotion allowed | false |
| Blocker | `no_case_passed_final_holdout_fold` |
| Next direction | `hibernate_or_rotate_after_final_holdout_failure` |

This means the historical Round145 family remains useful as process evidence, not as a paper or promotion candidate.

## Current Branch Boundary

Current active CN stock topic branches should be interpreted as follows:

| Branch / Round | Status |
| --- | --- |
| Round464 benchmark-relative residual moneyflow | rejected validation evidence; no accepted cases |
| Round465 fixed self-risk overlay | blocked review evidence; does not replace the existing Round462 paper lane |
| Round467 analyst-report retry | source-cache retry blocked by provider limit; no factor evidence added |
| Round468 paper ops guardrail/runbook | paper-only operational readiness; live cycle false |
| Round469 readiness blocker audit | completion blockers quantified; manual/live review still blocked by design |
| Round470 final-holdout boundary audit | historical holdout failure revalidated; no current lane may claim final-holdout passage |

## Decision

Do not claim any CN stock factor is final-holdout-passed or promotion-ready.

Allowed next actions:

- laptop integrates the two active topic branches into `main` in review order, then uses safe branch cleanup;
- assigned paper/ETF workstation reruns post-refresh replay/profile observation before recomputing observation sufficiency;
- office desktop continues only non-hibernated PIT-source work, such as the analyst-report source retry after the `report_rc` provider limit resets;
- new candidate work must use a different economic thesis or pre-registered risk-construction idea, not q20/`ps_gt10` threshold tuning or benchmark-relative moneyflow parameter expansion.

Blocked:

- paper gate for Round145 historical `daily_basic_free_float_supply_quality`;
- promotion or final-holdout claim for Round464/Round465/Round467 current lanes;
- live review enablement from office desktop;
- broker connection, account reads, order placement, or automatic live trading.
