# CN Stock Factor Mining Work Report Rounds 1-97 - 2026-06-22

## Executive Summary

Current context:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Mandate: CN A-share stock cross-sectional alpha research, not ETF rotation
- Safety: research-to-review only; no broker, account, order, or live-trading actions

Headline status through Round97:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Pre-registered profitability-quality candidates: 14
- Candidates with clean label-aligned matrix smoke: 14
- Current next direction: `round98_profitability_quality_controlled_ic_screen_on_clean_shard`

Round97 did not prove profitability, but it removed a major source of false alpha: financial factors are now aligned from `ann_date` to next tradable signal date, and forward labels start after the signal date.

## Latest Round Results

| Round | Direction | Key Result | Decision |
|---:|---|---|---|
| 94 | Shard 1 first10 live smoke | 440 requests, 429 processed rows, duplicate rows 0, PIT readiness passed | data path accepted |
| 95 | Shard 1 full100 live backfill | 4,400 requests, 4,328 processed rows, duplicate rows 0, PIT readiness passed | full shard accepted |
| 96 | Profitability-quality preregistration | 14 candidates, 14 coverage-passed, 0 data/PIT blockers | candidates accepted |
| 97 | Factor matrix and label-alignment smoke | 58,711 factor rows, 117,394 label rows, 96.89% label coverage, 0 violations | IC screen allowed next |

## Current Conclusion

The corrected profitability-quality path is now ready for a controlled IC screen on the clean shard. It is still not ready for portfolio backtesting or promotion.

Next step:

```text
round98_profitability_quality_controlled_ic_screen_on_clean_shard
```
