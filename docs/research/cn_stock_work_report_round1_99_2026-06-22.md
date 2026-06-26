# CN Stock Factor Mining Work Report Rounds 1-99 - 2026-06-22

## Executive Summary

Current context:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Mandate: CN A-share stock cross-sectional alpha research, not ETF rotation
- Safety: research-to-review only; no broker, account, order, or live-trading actions

Headline status through Round99:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Profitability-quality family status: hibernated
- Immediate next direction: `round100_lightweight_stage_report_and_github_safe_sync`
- Post-sync research direction: `capacity_safe_price_volume_lowvol_reversal_composite_preregistration`

## Latest Round Results

| Round | Direction | Key Result | Decision |
|---:|---|---|---|
| 95 | Shard 1 full100 live backfill | 4,400 requests, 4,328 processed rows, duplicate rows 0, PIT-ready 4,412/4,412 | full shard accepted |
| 96 | Profitability-quality preregistration | 14 candidates, 14 coverage-passed, 0 data/PIT blockers | candidates accepted |
| 97 | Factor matrix and label-alignment smoke | 58,711 factor rows, 117,394 label rows, 96.89% label coverage, 0 violations | IC screen allowed |
| 98 | Controlled IC screen | 28 tests, 1,204 IC observations, Bonferroni 0, FDR 0 | no lead |
| 99 | Family rejection audit | 6/6 requirements passed, family hibernated | rotate after sync |

## Bright Data Points

- The financial PIT data path is now real rather than mocked or proxy-based.
- Round95 full shard quality was clean: 4,328 rows, 0 duplicates, 0 missing asset IDs, PIT-ready 4,412/4,412.
- Round96 generated 14 pre-registered profitability-quality candidates with coverage gates passed.
- Round97 produced 117,394 label-aligned rows with 0 alignment violations.
- Round98 blocked false promotion early: 0 FDR leads and 0 Bonferroni-significant results.
- Round99 made the stop-loss rule executable: no more same-family tuning after zero multiple-testing leads.

## Current Conclusion

The project did not find a profitable factor in this block. The positive outcome is process quality: failed families are now audited, recorded, and rotated.

Next required action is not another factor grid. It is Round100 packaging and GitHub safe sync, followed by a new pre-registered capacity-safe price-volume/low-volatility/reversal composite family.
