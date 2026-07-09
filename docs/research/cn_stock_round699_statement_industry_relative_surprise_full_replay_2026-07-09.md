# CN Stock Round699 Statement Industry-Relative Surprise Full Replay

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round699 replayed the old Round253 `accounting_quality_industry_relative_surprise` family after the local statement source expanded from the original 130-symbol sample to the current broad statement root. This was a frozen-family coverage replay, not formula tuning.

This round did not run portfolio grids, walk-forward portfolio validation, promotion gates, sign/window tuning, mixed-window harvesting, signal generation, or 2026 final-holdout reads.

## Prior Evidence

Round253 tested this family on a 130-symbol statement sample and rejected it as underpowered with zero research leads. Because the 2026-07-08 statement backfill cleared the source gate at 1,002 unique symbols, a single frozen full-sample replay was allowed to check whether the old failure was mostly a coverage problem.

## Command

```powershell
.\.venv\Scripts\python.exe scripts\run_accounting_quality_statement_residual_ic_shape_prescreen.py --statement-root data\processed --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --daily-basic-root data\processed\cn_stock_long_history_2015_202306 --daily-basic-root data\processed\office_desktop_20260617_daily_basic_factor_inputs --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round699_statement_industry_relative_surprise_full_residual_prescreen_20260709 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 5 --horizon 20 --execution-lag 1 --min-cross-section 30 --min-ic-observations 8 --factor-mode industry_relative_surprise --allow-not-ready
```

Output:

```text
data/reports/round699_statement_industry_relative_surprise_full_residual_prescreen_20260709
```

## Summary

| Metric | Value |
| --- | ---: |
| Candidate count | 3 |
| Test count | 6 |
| Factor rows | 67,782 |
| Aligned rows | 135,564 |
| IC observations per test | 160 |
| Multiple-testing leads | 0 |
| Neutral-gate passes | 0 |
| Research leads | 0 |
| Promotion allowed candidates | 0 |
| Final holdout included | false |

Top rows:

| Factor | H | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | LiqNeuIC | Lead |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `aq_industry_relative_profitability_surprise` | 20 | -0.0129 | -0.116 | -1.47 | 43.8% | -0.0043 | 0.1685 | -0.0110 | -0.0107 | no |
| `aq_industry_relative_profitability_surprise` | 5 | -0.0085 | -0.086 | -1.09 | 46.9% | -0.0016 | 0.1554 | -0.0066 | -0.0069 | no |
| `aq_industry_relative_asset_disciplined_surprise` | 20 | -0.0057 | -0.051 | -0.64 | 43.8% | 0.0006 | 0.1554 | -0.0036 | -0.0079 | no |
| `aq_industry_relative_cash_conversion_surprise` | 5 | 0.0049 | 0.046 | 0.58 | 50.0% | -0.0010 | 0.1877 | 0.0031 | 0.0058 | no |
| `aq_industry_relative_cash_conversion_surprise` | 20 | 0.0028 | 0.027 | 0.34 | 50.0% | -0.0011 | 0.1893 | 0.0018 | 0.0018 | no |
| `aq_industry_relative_asset_disciplined_surprise` | 5 | -0.0018 | -0.016 | -0.20 | 51.2% | 0.0006 | 0.1725 | -0.0013 | -0.0054 | no |

## Decision

Rejected.

The full-sample replay did not rescue the Round253 family. The apparent positive industry-neutral IC is not enough: raw IC is negative or near zero, FDR is false for every test, ICIR is weak, top-minus-bottom quantile spread is negative or tiny, and size/liquidity neutral gates fail.

Do not continue this family through:

- formula mutations;
- sign flips;
- portfolio grids;
- walk-forward conversion;
- threshold relaxation;
- final-holdout reads.

Next action: rotate away from realized statement surprise families. The remaining high-expected-value paths are external expectation revision only when quota evidence clears, or a genuinely new nonfinancial event source with PIT source proof before any IC screen.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
