# CN Stock Round214 Fina Indicator Stratified Shard Plan

- Date: 2026-06-24
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock profitability-quality data planning, not ETF rotation
- Stage: data-efficiency planning only; no Tushare API call and no alpha claim

## Objective

Round214 improves the next profitability-quality attempt before spending more Tushare request budget.

Round93 built a valid broad `fina_indicator` plan, but the shards were sorted by stock code. Round95 then tested shard 1, covering `000001.SZ` to `000516.SZ`. That was clean PIT data, but it was a narrow code-ordered sample. Since Round98 found 0 controlled IC leads on that first shard, repeating code-ordered shard fetches would be a weak use of time and request quota.

Round214 adds optional stratified shard ordering so the next financial-data pull can cover a broader cross-section of industries, exchanges, and listing cohorts.

## Implementation

Changed:

- `src/quant_robot/ops/fina_indicator_symbol_shard_plan.py`
- `scripts/run_fina_indicator_symbol_shard_plan.py`
- `tests/unit/test_fina_indicator_symbol_shard_plan.py`
- `tests/unit/test_fina_indicator_symbol_shard_plan_cli.py`

The old behavior remains the default. Stratification only activates when `--stratify-by` is passed.

New CLI pattern:

```powershell
python scripts\run_fina_indicator_symbol_shard_plan.py --stock-basic-root data\processed\cn_stock_metadata\metadata\tushare_stock_basic --start-period 2015-03-31 --end-period 2025-12-31 --symbols-per-shard 100 --max-requests-per-shard 4400 --exclude-suffixes BJ --stratify-by industry,exchange,list_year --output-dir data\reports\fina_indicator_stratified_symbol_shard_plan_round214_20260624
```

## Result

- Plan passes: true
- Non-BJ symbols: 5,208
- Excluded BJ symbols: 321
- Periods: 44
- Total planned requests: 229,152
- Shards: 53
- Requests per full shard: 4,400
- Stratification columns: industry, exchange, list_year
- Strata: 2,180

First stratified shards:

| Shard | Symbols | Requests | Industries | Exchanges | Listing years | First | Last |
|---:|---:|---:|---:|---:|---:|---|---|
| 1 | 100 | 4,400 | 100 | 2 | 19 | `000066.SZ` | `000488.SZ` |
| 2 | 100 | 4,400 | 100 | 2 | 21 | `000428.SZ` | `000738.SZ` |
| 3 | 100 | 4,400 | 100 | 2 | 22 | `300065.SZ` | `000698.SZ` |
| 4 | 100 | 4,400 | 100 | 2 | 28 | `002554.SZ` | `002318.SZ` |
| 5 | 100 | 4,400 | 100 | 2 | 26 | `000068.SZ` | `600822.SH` |

The old Round93 first shard was code-ordered:

- shard 1: `000001.SZ` to `000516.SZ`
- shard 2: `000517.SZ` to `000669.SZ`
- shard 3: `000670.SZ` to `000820.SZ`

## Interpretation

This round does not discover a factor. It improves the data acquisition strategy for true PIT profitability-quality factors.

The key value is budget efficiency. If profitability-quality is revisited, the next 4,400-request shard should be representative instead of another adjacent code segment. A stratified shard is more likely to reveal whether the prior 100-symbol failure was broad-family failure or sample-specific weakness.

## Decision

- Profitability-quality direct formula tuning remains hibernated.
- Code-ordered financial shard expansion is deprecated for research sampling.
- Use the Round214 stratified shard plan before any new `fina_indicator` backfill.
- Next round: run a small stratified shard smoke or full stratified shard 1 backfill, then PIT readiness and coverage checks, before any profitability factor prescreen.

## Verification

- `python -m unittest tests.unit.test_fina_indicator_symbol_shard_plan tests.unit.test_fina_indicator_symbol_shard_plan_cli`
- `python scripts\run_fina_indicator_symbol_shard_plan.py ... --stratify-by industry,exchange,list_year ...`
