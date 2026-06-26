# CN Stock Three-Round Review Round97-99 - 2026-06-22

## Executive Summary

Rounds 97-99 completed a disciplined profitability-quality family test:

- Round97 proved PIT factor-value and label alignment.
- Round98 ran a controlled IC screen with multiple-testing accounting.
- Round99 audited the failed family and forced rotation instead of more tuning.

No profitable factor was found. The useful result is a clean rejection: the current profitability-quality family should not consume more parameter-search budget until a new data or economic thesis is documented.

## Round Outcomes

| Round | Direction | Main Evidence | Decision |
|---:|---|---|---|
| 97 | Factor matrix and label-alignment smoke | 58,711 factor rows, 117,394 label rows, 96.89% label coverage, 0 alignment violations | IC screen allowed |
| 98 | Controlled IC screen | 14 candidates, 28 tests, 1,204 IC observations, Bonferroni 0, FDR 0 | no research lead |
| 99 | Family rejection audit | 6/6 audit requirements passed, family hibernated | rotate after Round100 sync |

## What Worked

- Real Tushare PIT financial data can now be ingested and audited.
- Announcement-date signal availability is explicit.
- Future-return labels start after signal availability.
- Multiple testing is enforced before research-lead claims.
- Failed families are now hibernated by protocol rather than extended emotionally.

## What Failed

- Profitability-quality fields did not produce statistically useful IC on the current clean shard.
- The best raw result from Round98 had p=0.1413, far above the Bonferroni threshold of 0.001786.
- No Sharpe, profit rate, or portfolio win rate should be claimed because no candidate passed the IC gate.

## Direction Adjustment

Immediate next step:

```text
round100_lightweight_stage_report_and_github_safe_sync
```

After sync, rotate to:

```text
capacity_safe_price_volume_lowvol_reversal_composite_preregistration
```

The next family must pre-register candidates first and use Alphalens-style IC, quantile, turnover, and decay checks before any portfolio grid.
