# CN Stock Round215 Fina Indicator Stratified Shard1 First10 Smoke

- Date: 2026-06-24
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock profitability-quality data readiness, not ETF rotation
- Stage: real Tushare data smoke and PIT readiness only

## Objective

Round215 tested whether the new Round214 stratified financial shard plan can produce clean point-in-time `fina_indicator` data before spending a full 4,400-request shard budget.

This round did not create or promote any alpha factor.

## Command

```powershell
python scripts\run_fina_indicator_shard_backfill_smoke.py --shard-plan-json data\reports\fina_indicator_stratified_symbol_shard_plan_round214_20260624\fina_indicator_symbol_shard_plan.json --shard-id 1 --max-symbols 10 --batch-size 20 --max-requests 440 --output-dir data\processed\round215_fina_indicator_stratified_shard1_first10_20260624 --pit-readiness-output-dir data\reports\round215_tushare_financial_pit_readiness_stratified_shard1_first10_20260624
```

## Result

- Selected symbols: 10
- Periods: 44
- Requests: 440
- Processed rows: 440
- Empty requests: 0
- Skipped requests: 0
- Assets: 10
- Duplicate rows: 0
- Missing asset_id rows: 0
- PIT readiness: passed
- Financial-like datasets scanned: 452
- PIT-ready datasets: 452

Selected symbols:

- `000066.SZ`
- `300029.SZ`
- `000519.SZ`
- `000538.SZ`
- `002329.SZ`
- `000676.SZ`
- `000906.SZ`
- `000407.SZ`
- `601318.SH`
- `000020.SZ`

Quality notes:

- `grossprofit_margin` missing rows: 44
- `roa` missing rows: 44
- `roe` missing rows: 4
- `ann_date` range: 2015-04-24 to 2026-04-30
- report period range: 2015-03-31 to 2025-12-31

## Interpretation

The stratified financial data path is live and clean at first10 scale. This is useful because Round95's code-ordered full100 shard failed to produce profitability-quality IC leads; Round215 shows a more representative sample can be fetched with complete request success and PIT readiness.

This is not profitability evidence. It is permission to consider a full stratified shard1 backfill, followed by coverage and controlled IC checks. Any profitability-quality formula tuning remains blocked until the expanded stratified data passes PIT, coverage, factor-matrix, label-alignment, and multiple-testing gates.

## Decision

- New factors: 0
- Research leads: 0
- Promotion candidates: 0
- Data path: accepted for expansion
- Next action: three-round review for Round213-215 before spending a full stratified 4,400-request shard.

## Artifacts

- Data root: `data/processed/round215_fina_indicator_stratified_shard1_first10_20260624`
- PIT readiness report: `data/reports/round215_tushare_financial_pit_readiness_stratified_shard1_first10_20260624`

Generated data remains out of Git.
