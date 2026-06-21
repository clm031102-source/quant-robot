# CN Stock Three-Round Review Round94-96 - 2026-06-22

## Executive Summary

Rounds 94-96 corrected the CN stock profitability-quality path. The work moved from financial data smoke to 100-symbol PIT financial coverage and then to 14 pre-registered profitability-quality candidates.

No profitable factor was found or promoted. The useful result is that the project now has a repeatable path for real Tushare financial factors instead of continuing to overwork weak moneyflow/public-technical directions.

## Round Outcomes

| Round | Direction | Main Evidence | Decision |
|---:|---|---|---|
| 94 | First10 `fina_indicator` shard smoke | 440 requests, 429 processed rows, duplicate rows fixed to 0, PIT-ready 452/452 | data path accepted |
| 95 | Full100 shard backfill | 4,400 requests, 4,328 processed rows, duplicate rows 0, PIT-ready 4,412/4,412 | full shard accepted |
| 96 | Profitability-quality preregistration | 14 candidates, 14 coverage-passed, 0 PIT/data blockers | candidates accepted for matrix smoke |

## What Improved

- The research scope is now CN A-share stock factors, not ETF rotation evidence.
- True financial `fina_indicator` inputs are available with `ann_date` and `end_date`.
- Same-key financial row restatement duplicates are deduplicated.
- Shard-based backfill is resumable and budgeted.
- Candidate definitions are now pre-registered before testing.
- Coverage, PIT, duplicate, and single-shard promotion gates are written into the project.

## What Is Still Not Proven

- No IC, RankIC, Sharpe, profit rate, win rate, drawdown, or turnover result exists for the 14 candidates.
- Single-shard evidence is not broad-market evidence.
- The 100 symbols are an early shard and may have universe-order bias.
- Survivorship handling is still only as good as the available local universe.
- The next factor-matrix smoke can detect alignment mistakes but cannot promote anything.

## Direction Adjustment

Continue the profitability-quality family, but only through the next disciplined step:

```text
round97_profitability_quality_factor_matrix_smoke_and_label_alignment
```

Do not jump to promotion, full-universe backtest, or parameter tuning. The next round must prove that financial factor values are aligned by announcement date and that future-return labels begin after signal availability.

## Stop-Loss Rule

If Round97 finds label leakage, poor factor-matrix coverage, or inability to align prices/returns with `ann_date`, stop the profitability-quality line and repair the data/model layer before further mining.
