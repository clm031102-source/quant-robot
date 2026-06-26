# CN Stock Round270 Financial Reporting Timeliness Source Audit

- Date: 2026-06-26
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock factor mining
- Safety: research-to-review only; no broker connection, account reads, order placement, or live trading

## Purpose

Round270 tested whether the project has enough local, PIT-safe financial reporting timeliness data to mine announcement-delay or disclosure-behavior factors.

This was deliberately a source audit, not factor generation. The prior three-round review selected the direction, but required source coverage proof before candidate registration.

## Tooling Added

- Module: `src/quant_robot/ops/financial_reporting_timeliness_source_audit.py`
- CLI: `scripts/run_financial_reporting_timeliness_source_audit.py`
- Tests:
  - `tests/unit/test_financial_reporting_timeliness_source_audit.py`
  - `tests/unit/test_financial_reporting_timeliness_source_audit_cli.py`

The audit checks required fields, symbol coverage, end-year coverage, and blocks candidate generation if source coverage is too small.

## Audit Run

- Output: `data/reports/round270_financial_reporting_timeliness_source_audit_20260626`
- Window: 2015-01-01 through 2025-12-31
- Minimum required symbols: 1,000
- Minimum required end years: 8
- Sources checked: 3
- Total rows: 8,926
- Max unique symbols in any source: 100
- Source-ready count: 0
- Candidate plan allowed: false
- Next direction: `round270_financial_reporting_timeliness_backfill_or_retire_before_factor_generation`

## Source Profiles

| Source | Rows | Unique symbols | End years | Ann date range | End date range | Status |
|---|---:|---:|---:|---|---|---|
| `round202_financial_pit_signal_filtered_20260623` | 4,211 | 100 | 11 | 2015-04-15..2026-04-30 | 2015-03-31..2025-12-31 | blocked |
| `round216_financial_pit_signal_filtered_stratified_shard1_full100_20260624` | 4,277 | 100 | 11 | 2015-04-18..2026-04-29 | 2015-03-31..2025-12-31 | blocked |
| `round236_financial_statement_pilot_first2_fullcycle_20260625` | 438 | 2 | 11 | 2015-04-28..2026-04-30 | 2015-03-31..2025-12-31 | blocked |

## Decision

Do not pre-register or mine financial reporting timeliness factors from the current local cache. The date range is long enough, but the symbol coverage is far too small for a full-market CN stock factor claim.

Blocked shortcuts:

- no candidate generation from 100-stock or 2-stock samples;
- no short-sample IC screen;
- no portfolio grid;
- no claim that announcement-timing factors failed or passed, because the source did not clear coverage.

## Next Action

Round271 should either:

- backfill a full-market financial reporting timeliness source with `symbol`, `ann_date`, `end_date`, and report metadata, then rerun the same source audit; or
- retire this family and rotate to another accessible, full-sample data source.

Until one of those happens, this direction stays blocked at source gate.
