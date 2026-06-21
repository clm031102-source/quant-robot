# CN Stock Factor Mining Work Report Rounds 1-98 - 2026-06-22

## Executive Summary

Current context:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Mandate: CN A-share stock cross-sectional alpha research, not ETF rotation
- Safety: research-to-review only; no broker, account, order, or live-trading actions

Headline status through Round98:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Pre-registered profitability-quality candidates: 14
- Controlled profitability-quality IC research leads: 0
- Current next direction: `round99_profitability_quality_family_rejection_and_next_family_rotation_audit`

Round98 is a clean negative result. The project now has stronger evidence that this profitability-quality family should not be promoted or tuned further on the current 100-symbol shard.

## Latest Round Results

| Round | Direction | Key Result | Decision |
|---:|---|---|---|
| 94 | Shard 1 first10 live smoke | 440 requests, 429 processed rows, duplicate rows fixed to 0, PIT-ready 452/452 | data path accepted |
| 95 | Shard 1 full100 live backfill | 4,400 requests, 4,328 processed rows, duplicate rows 0, PIT-ready 4,412/4,412 | full shard accepted |
| 96 | Profitability-quality preregistration | 14 candidates, 14 coverage-passed, 0 data/PIT blockers | candidates accepted |
| 97 | Factor matrix and label-alignment smoke | 58,711 factor rows, 117,394 label rows, 96.89% label coverage, 0 violations | IC screen allowed |
| 98 | Controlled IC screen | 28 tests, 1,204 IC observations, Bonferroni significant 0, FDR significant 0 | family has no current lead |

## Bright Data Points

- Tushare `fina_indicator` shard path is live and repeatable.
- Full100 shard quality is clean: 4,328 final rows, duplicate rows 0, missing asset id 0, PIT readiness passed.
- Financial candidate coverage is strong: all 14 profitability-quality candidates passed coverage gates.
- Label alignment is clean: 117,394 aligned label rows and 0 alignment violations in Round97.
- Round98 rejected weak results before portfolio backtesting, avoiding another false promotion path.

## Current Conclusion

The infrastructure improved more than the factors did. That is still progress: the project can now ingest real PIT financial data, pre-register financial candidates, align signals to future labels, and apply multiple-testing-aware IC screens.

But the factor result is poor:

- No Sharpe, profit rate, or win rate should be claimed for Round98 because no candidate reached the portfolio-backtest stage.
- No candidate passed a statistically credible IC screen.
- The profitability-quality line should move into rejection/rotation audit, not parameter tuning.

Next step:

```text
round99_profitability_quality_family_rejection_and_next_family_rotation_audit
```
