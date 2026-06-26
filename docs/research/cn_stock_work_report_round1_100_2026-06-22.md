# CN Stock Factor Mining Work Report Rounds 1-100 - 2026-06-22

## Executive Summary

Round100 is the ten-round synchronization checkpoint after the Round91-99 profitability-quality data and audit block.

Status:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Profitability-quality family: hibernated
- GitHub sync cadence: due at Round100
- Next research direction after sync: `capacity_safe_price_volume_lowvol_reversal_composite_preregistration`

## What Was Accomplished In Rounds 91-100

| Round | Result |
|---:|---|
| 91 | Planned long-history Tushare `fina_indicator` backfill. |
| 92 | Ran limited 2-symbol live backfill smoke and fixed duplicate handling. |
| 93 | Built 5,208-symbol, 53-shard request plan. |
| 94 | Ran first10 shard smoke: 440 requests, 429 rows, duplicate 0 after fix. |
| 95 | Ran full100 shard: 4,400 requests, 4,328 rows, PIT-ready 4,412/4,412. |
| 96 | Pre-registered 14 profitability-quality candidates. |
| 97 | Built factor matrix and label-alignment smoke: 117,394 label rows, 0 violations. |
| 98 | Ran controlled IC screen: 28 tests, Bonferroni 0, FDR 0. |
| 99 | Rejected and hibernated profitability-quality family. |
| 100 | Packaged safe-sync report and prepared GitHub sync. |

## Conclusion

This block did not find a usable alpha. It did improve the research machine: data readiness, candidate pre-registration, PIT alignment, multiple-testing control, family stop-loss, and sync discipline are now encoded in the project.

The next profitable-factor attempt should not be another profitability-quality variant. It should rotate to a capacity-safe price-volume/low-volatility/reversal composite family, with public-reference style diagnostics before any portfolio backtest.
