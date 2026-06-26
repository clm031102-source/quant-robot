# CN Stock Round100 Lightweight Stage Report - 2026-06-22

## Executive Summary

Round100 packages the Round91-99 office desktop CN stock factor-validation work for GitHub safe sync.

This checkpoint produced no promotable profitable factor, but it did produce a stricter, repeatable research path:

- Real Tushare `fina_indicator` PIT ingestion and shard planning.
- Limited live backfill smoke before full shard backfill.
- 100-symbol clean financial shard with PIT readiness.
- Profitability-quality candidate pre-registration.
- PIT signal-date and forward-label alignment.
- Controlled IC screen with multiple-testing accounting.
- Family rejection audit that hibernates a failed family and rotates direction.

## Factor Result

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Profitability-quality research leads after multiple testing: 0
- Current family status: hibernated

## Bright Data Points

| Area | Evidence |
|---|---|
| Backfill budget | 5,208 non-BJ symbols x 44 quarters = 229,152 planned requests, 53 shards |
| Full100 shard | 4,400 requests, 4,328 final rows, 72 empty responses |
| Data quality | duplicate rows 0, missing asset id 0, PIT readiness 4,412/4,412 |
| Candidate coverage | 14/14 profitability-quality candidates coverage-passed |
| Label alignment | 58,711 factor rows, 117,394 aligned label rows, 0 alignment violations |
| Controlled IC | 28 tests, 1,204 IC observations, Bonferroni 0, FDR 0 |
| Governance | Round99 family rejection audit passed 6/6 requirements |

## Main Lesson

The project made progress, but not by finding a factor. It made progress by refusing to promote weak evidence.

The profitability-quality family had a clean data path and still failed statistically. The correct response is not more tuning; it is family hibernation, safe sync, and a new pre-registered direction.

## Sync Scope

This sync should include:

- `src/quant_robot/ops/*` additions for financial backfill, pre-registration, matrix smoke, IC screen, and family rejection audit.
- `scripts/run_*` CLI additions.
- Unit tests for the above.
- Startup gate config updates.
- Lightweight docs under `docs/`.

This sync must exclude:

- `data/raw/`
- `data/processed/`
- `data/reports/`
- Tushare token
- Broker/account/order/live trading secrets

## Next Direction After Sync

```text
capacity_safe_price_volume_lowvol_reversal_composite_preregistration
```

The next family must be pre-registered and screened with Alphalens-style IC, quantile spread, turnover, and decay diagnostics before any portfolio grid is allowed.
