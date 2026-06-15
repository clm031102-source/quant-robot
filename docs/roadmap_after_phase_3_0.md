# Roadmap After Phase 3.0

This roadmap keeps the project pre-API and research-only while moving the current CN ETF candidate from blocked review evidence toward cleaner local operations evidence.

## Phase 3.1 Data Quality Gap Audit

Status: implemented.

Goal: turn `missing_date_rows` into exact asset/date rows.

Deliverables:

- `scripts/run_data_quality_audit.py`
- `data/reports/data_quality_gap_audit/data_quality_gap_audit.json`
- `data/reports/data_quality_gap_audit/missing_dates.csv`
- integration into `run_checks.py`

Exit condition: every data-quality blocker can be traced to exact local rows and repair commands.

## Phase 3.2 Provider Readiness Evidence Pack

Status: implemented.

Goal: turn provider readiness from a flat missing-dependency message into a durable evidence pack.

Deliverables:

- `scripts/run_provider_evidence.py`
- `data/reports/provider_evidence/provider_evidence_pack.json`
- `data/reports/provider_evidence/provider_market_matrix.csv`
- package/token/adapter readiness by provider;
- supported-market matrix;
- Markdown summary for review packets and Evidence Refresh.

Exit condition: review packets can distinguish missing optional packages, missing tokens, and unsupported providers without manual interpretation.

## Phase 3.3 Paper Observation Extension

Status: implemented.

Goal: extend local paper evidence for the canonical candidate without changing the research-only boundary.

Deliverables:

- `scripts/run_paper_observation.py`
- `data/reports/paper_observation/paper_observation_pack.json`
- observation-window summary;
- guard-event and execution-block summaries;
- per-risk-profile comparison table;
- trend of paper drawdown and Sharpe across refreshed candidates.

Exit condition: `paper_ready` means the candidate has enough local observation history for manual review discussion, not just a one-off paper run.

## Phase 3.4 Duplicate Canonical Registry

Status: implemented.

Goal: make duplicate candidate clusters explicit and stable across reruns.

Deliverables:

- `scripts/run_duplicate_registry.py`
- `data/reports/duplicate_registry/duplicate_canonical_registry.json`
- canonical candidate registry;
- duplicate member list;
- reason each duplicate is suppressed;
- Promotion Ops and Review Packet registry summary fields.

Exit condition: duplicate strategy variants cannot inflate candidate counts or look like independent edges.

## Phase 3.5 Manual Review Gate Rehearsal

Status: implemented.

Goal: rehearse the manual review gate without enabling live trading.

Deliverables:

- `scripts/run_manual_review_rehearsal.py`
- `data/reports/manual_review_rehearsal/manual_review_rehearsal.json`
- checklist of required clean states;
- blocked/ready rehearsal payload;
- dry-run gate output proving no broker/account/order boundary is crossed.

Exit condition: the project can say exactly what remains before any future API-boundary work starts.

## Phase 4.0 Pre-API Readiness Board

Status: implemented.

Goal: consolidate Phase 3 evidence into one local operational readiness board.

Deliverables:

- `scripts/run_pre_api_readiness_board.py`
- `data/reports/pre_api_readiness_board/pre_api_readiness_board.json`
- readiness item table;
- blocker register;
- next local action list;
- broker/account/order boundary status.

Exit condition: the project has one local artifact that says whether API-boundary planning is blocked, what blocks it, and which local commands should run next.

## Phase 4.1 Blocker Resolution Worklist

Status: implemented.

Goal: turn readiness-board blockers into a local action queue.

Deliverables:

- `scripts/run_blocker_worklist.py`
- `data/reports/blocker_worklist/blocker_resolution_worklist.json`
- open work item table;
- deduplicated local action queue;
- local-only and live-boundary status per worklist.

Exit condition: each readiness blocker has a concrete local work item and primary command before any external boundary work is considered.

## Phase 4.2 Data Gap Resolution Ledger

Status: implemented.

Goal: turn exact missing ETF dates into stable local resolution rows.

Deliverables:

- `scripts/run_data_gap_resolution.py`
- `data/reports/data_gap_resolution/data_gap_resolution_ledger.json`
- stable `gap_id` per missing asset/date row;
- default `needs_review` blocker state;
- optional local resolution CSV support;
- row-level recommended local commands;
- integration into `run_checks.py` after the data-quality audit.

Exit condition: each data-quality missing-date row has a traceable local resolution status before any API-boundary planning is considered.

## Phase 4.3 Data Gap Ledger Board Integration

Status: implemented.

Goal: connect the Phase 4.2 data-gap resolution ledger to the main pre-API readiness board.

Deliverables:

- `scripts/run_pre_api_readiness_board.py` default support for `data_gap_resolution_ledger.json`;
- `data_gap_resolution` readiness item;
- `data_gap_resolution_blocking_gaps` blocker;
- local action queue entry for `scripts/run_data_gap_resolution.py`;
- documentation in `docs/phase_4_3_data_gap_ledger_board_integration.md`.

Exit condition: unresolved data-gap ledger rows are visible on the same board as provider readiness, manual review, duplicate registry, and live-boundary status.

## Phase 4.4 Data Gap Resolution Template

Status: implemented.

Goal: make data-gap resolution evidence fillable from local CSV artifacts.

Deliverables:

- `gap_resolutions_template.csv`;
- `data_gap_resolution_status_options.csv`;
- template helper functions in `quant_robot.ops.data_gap_resolution`;
- documentation in `docs/phase_4_4_data_gap_resolution_template.md`.

Exit condition: each unresolved data-gap row can be reviewed by filling a generated local template and rerunning the ledger command with `--resolution-file`.

## Phase 4.5 Data Gap Resolution Validation

Status: implemented.

Goal: report invalid local data-gap resolution inputs before they affect readiness evidence.

Deliverables:

- `resolution_validation` payload in `data_gap_resolution_ledger.json`;
- `data_gap_resolution_validation.csv`;
- unknown gap ID detection;
- unsupported status detection;
- duplicate gap ID detection.

Exit condition: local resolution CSV mistakes are visible as validation rows and are not silently applied to the ledger.

## Phase 4.6 Data Gap Resolution Rehearsal

Status: implemented.

Goal: prove the local resolution pipeline with a rehearsal-only sample resolution file.

Deliverables:

- `scripts/run_data_gap_rehearsal.py`;
- `data/reports/data_gap_rehearsal/data_gap_rehearsal.json`;
- sample resolution CSV;
- rehearsed ledger rows CSV;
- before/after blocking summary;
- core-check integration after `data_gap_resolution`.

Exit condition: the project can demonstrate, without changing real evidence, how valid resolution rows reduce data-gap blockers and feed readiness projection.

## Phase 4.7 Provider Remediation Matrix

Status: implemented.

Goal: turn provider-readiness blockers into a local remediation matrix.

Deliverables:

- `scripts/run_provider_remediation.py`;
- `data/reports/provider_remediation/provider_remediation_matrix.json`;
- remediation item table;
- dependency, credential, adapter, and storage blocker counts;
- local verification commands;
- core-check integration after `provider_evidence`.

Exit condition: every provider-readiness blocker has a local remediation row before manual provider-enablement work begins.

## Phase 4.8 Provider Remediation Board Integration

Status: implemented.

Goal: connect the provider remediation matrix to the main pre-API readiness board.

Deliverables:

- `scripts/run_pre_api_readiness_board.py` default support for `provider_remediation_matrix.json`;
- `provider_remediation` readiness item;
- `provider_remediation_items_open` blocker;
- local action queue entry for `scripts/run_provider_remediation.py`;
- documentation in `docs/phase_4_8_provider_remediation_board_integration.md`.

Exit condition: open provider remediation rows are visible on the same board as data gaps, provider readiness, manual review, duplicate registry, and live-boundary status.

## Phase 4.9 Provider Remediation Review Template

Status: implemented.

Goal: make provider-remediation rows fillable as local review evidence.

Deliverables:

- `provider_remediation_review_template.csv`;
- `provider_remediation_status_options.csv`;
- pure template/status helpers in `quant_robot.ops.provider_remediation`;
- documentation in `docs/phase_4_9_provider_remediation_review_template.md`.

Exit condition: each provider remediation row can be reviewed with a generated local template before any provider-enablement or API-boundary work is considered.

## Phase 4.10 Provider Remediation Review Validation

Status: implemented.

Goal: validate filled provider-remediation review rows and apply valid local statuses to remediation evidence.

Deliverables:

- `--review-file` support in `scripts/run_provider_remediation.py`;
- `provider_remediation_validation.csv`;
- `review_validation` summary in `provider_remediation_matrix.json`;
- `blocking_remediation_items` summary count;
- readiness-board status based on blocking remediation items;
- documentation in `docs/phase_4_10_provider_remediation_review_validation.md`.

Exit condition: provider-remediation review rows can be validated and reflected in local blocking counts without deleting historical remediation evidence.

## Phase 4.11 Provider Remediation Review Rehearsal

Status: implemented.

Goal: demonstrate how validated provider-remediation review rows can reduce blockers without changing real evidence.

Deliverables:

- `scripts/run_provider_remediation_rehearsal.py`;
- `data/reports/provider_remediation_rehearsal/provider_remediation_rehearsal.json`;
- sample provider review CSV;
- rehearsed remediation item CSV;
- before/after blocking summary;
- core-check integration after `provider_remediation`.

Exit condition: the project can demonstrate, without changing real evidence, how non-blocking provider review statuses reduce provider-remediation blockers and feed readiness projection.

## Phase 4.12 Pre-API Readiness Projection Pack

Status: implemented.

Goal: consolidate current readiness evidence with rehearsal projections into one local operations artifact.

Deliverables:

- `scripts/run_readiness_projection.py`;
- `data/reports/readiness_projection/readiness_projection_pack.json`;
- current versus projected readiness item CSV;
- rehearsal delta CSV;
- residual blocker CSV;
- core-check integration after `pre_api_readiness_board`.

Exit condition: the project can show projected blocker reductions and residual blockers in one local artifact without mutating real evidence.

## Phase 4.13 Residual Blocker Focus Pack

Status: implemented.

Goal: convert projected residual blockers into a prioritized local focus pack.

Deliverables:

- `scripts/run_residual_blocker_focus.py`;
- `data/reports/residual_blocker_focus/residual_blocker_focus_pack.json`;
- residual focus item CSV;
- downstream wait CSV;
- focus-scoped local action CSV;
- core-check integration after `blocker_worklist`.

Exit condition: the project can show which residual blocker classes should be worked first, which existing work items they cover, which downstream manual-review blockers are waiting on them, and which local commands should run next.

## Phase 4.14 Residual Data Gap Review Pack

Status: implemented.

Goal: turn post-rehearsal blocking data gaps into a focused local review worksheet.

Deliverables:

- `scripts/run_residual_data_gap_review.py`;
- `data/reports/residual_data_gap_review/residual_data_gap_review_pack.json`;
- residual data-gap row CSV;
- fillable residual gap review template;
- residual gap action queue;
- core-check integration after `residual_blocker_focus`.

Exit condition: the project can isolate the data-gap rows that still block the API boundary after rehearsal and provide a ready-to-fill local resolution file for the next ledger run.

## Phase 4.15 Residual Provider Review Pack

Status: implemented.

Goal: turn post-rehearsal blocking provider-remediation items into a focused local review worksheet.

Deliverables:

- `scripts/run_residual_provider_review.py`;
- `data/reports/residual_provider_review/residual_provider_review_pack.json`;
- residual provider-remediation item CSV;
- fillable residual provider review template;
- residual provider action queue;
- core-check integration after `residual_data_gap_review`.

Exit condition: the project can isolate the provider-remediation rows that still block the API boundary after rehearsal and provide a ready-to-fill local review file for the next provider-remediation run.
