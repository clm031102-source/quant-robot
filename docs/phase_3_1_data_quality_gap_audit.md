# Phase 3.1 Data Quality Gap Audit

Phase 3.1 turns CN ETF data-quality blockers into exact local missing-date evidence.

It is still research-only. It does not connect to providers, brokers, accounts, or order systems.

## What It Adds

- Gap-audit builder in `quant_robot.data.gap_audit`.
- CLI artifact generation through `scripts/run_data_quality_audit.py`.
- Core-check integration after the data catalog step.
- Evidence Refresh now starts data-quality remediation by running the gap audit before suggesting CSV refresh work.

## CLI Usage

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_quality_audit.py --data-root data\processed\etf_csv --market CN_ETF --output-dir data\reports\data_quality_gap_audit
```

Output files:

- `data_quality_gap_audit.json`
- `data_quality_gap_audit.md`
- `missing_dates.csv`
- `coverage_by_asset.csv`

## Current CN ETF Findings

The current local ETF dataset has 6 missing date rows across 4 assets:

- `CN_ETF_XSHE_159915` / `159915.SZ`: `2013-10-07`, `2021-02-08`
- `CN_ETF_XSHG_510500` / `510500.SH`: `2015-04-13`, `2015-04-14`
- `CN_ETF_XSHG_512100` / `512100.SH`: `2022-09-02`
- `CN_ETF_XSHG_512690` / `512690.SH`: `2021-05-14`

These rows explain the `missing_dates_present` blocker that appears in Promotion Ops, the Phase 2.9 review packet, and the Phase 3.0 evidence-refresh plan.

## Interpretation

The audit does not decide whether a date is a true exchange holiday, a suspended ETF day, or a missing local CSV row. It narrows the next review step to exact asset/date pairs so a human or later provider-readiness workflow can decide whether to backfill, annotate, or accept the gap.

After local data changes, rerun:

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_quality_audit.py --data-root data\processed\etf_csv --market CN_ETF --output-dir data\reports\data_quality_gap_audit
python scripts\run_promotion_ops.py --output-dir data\reports\promotion_ops
python scripts\run_promotion_review.py --output-dir data\reports\promotion_review
python scripts\run_evidence_refresh.py --output-dir data\reports\evidence_refresh
```
