# CN Stock Round255 Forecast/Express Event Cache And PIT Prescreen

- Date: 2026-06-25
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock factor mining
- Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Purpose

Round254 concluded that the old forecast formula should not be rerun directly. Round255 therefore optimized the workflow before more mining:

1. Build a reusable Tushare `forecast` and `express` event cache.
2. Convert cached events into point-in-time PIT signals with a strict next-trade-date rule.
3. Run the same-parameter 2015-2025 long-cycle prescreen before any portfolio grid.
4. Decide whether forecast/express deserves more budget or should rotate.

## Reusable Project Changes

- Added `src/quant_robot/data/ingest/tushare_forecast_express_events.py`.
- Added `scripts/run_tushare_forecast_express_event_cache.py`.
- Added `--event-cache-root` support to `scripts/run_event_factor_pit_ic_prescreen.py`.
- Enabled `event_express_profit_surprise_1q` in the PIT prescreen registry.
- Added unit tests for the event cache, cache CLI, express PIT factor conversion, and cached event loading.

The cache remains research data only and is written under `data/processed`, so it must not be committed.

## Cache Result

Command:

```powershell
.venv\Scripts\python.exe scripts\run_tushare_forecast_express_event_cache.py `
  --start-date 2015-01-01 `
  --end-date 2025-12-31 `
  --output-dir data\reports\round255_forecast_express_event_cache_full_2015_2025_20260625 `
  --processed-output-dir data\processed\round255_forecast_express_event_cache_20260625 `
  --execute-write-processed
```

Result:

| Feed | Rows | Assets | Event Dates | Date Range | Status |
|---|---:|---:|---:|---|---|
| forecast | 78,573 | 5,728 | 2,681 | 2015-01-01..2025-12-31 | pass |
| express | 20,304 | 4,280 | 1,441 | 2015-01-06..2025-10-22 | pass |

There were no fetch failures, duplicate key failures, or missing available-date failures. Forecast monthly range calls required an `ann_date` fallback; that fallback is now encoded in the cache tool.

## Long-Cycle PIT Prescreen

Command:

```powershell
.venv\Scripts\python.exe scripts\run_event_factor_pit_ic_prescreen.py `
  --event-cache-root data\processed\round255_forecast_express_event_cache_20260625 `
  --candidate-names event_express_profit_surprise_1q `
  --analysis-start-date 2015-01-01 `
  --analysis-end-date 2025-12-31 `
  --horizons 5,20 `
  --execution-lag 1 `
  --pit-lag-trade-days 1 `
  --min-cross-section 30 `
  --min-ic-observations 8 `
  --output-dir data\reports\round255_event_express_profit_surprise_pit_ic_prescreen_20260625
```

Data alignment:

| Metric | Value |
|---|---:|
| Bar rows | 10,785,537 |
| Bar assets | 5,707 |
| Express event rows | 20,304 |
| Express factor rows | 20,228 |
| Aligned rows | 36,841 |
| IC observation dates per horizon | 79 |

Result:

| Factor | Horizon | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | Years Positive | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| event_express_profit_surprise_1q | 5 | -0.0438 | -0.245 | -2.17 | 36.7% | -0.0087 | 0.2728 | -0.0281 | 27.3% | no |
| event_express_profit_surprise_1q | 20 | -0.0033 | -0.019 | -0.17 | 45.6% | -0.0091 | 0.2626 | 0.0297 | 27.3% | no |

Conclusion: the standalone express surprise factor is rejected. It has broad coverage, but raw IC, ICIR, quantile spread, yearly stability, and size-neutral gates do not clear.

## Diagnostic Neutralization Check

Because the raw express factor showed strong industry-neutral RankIC but poor raw IC, an in-session diagnostic tested industry-relative transforms on the same 2015-2025 data.

Best diagnostic row:

| Diagnostic Variant | Horizon | IC | ICIR | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | SizeT | Years Positive | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| event_express_profit_surprise_industry_relative_1q | 20 | 0.0095 | 0.075 | 50.7% | 0.0018 | 0.2957 | 0.0314 | 2.20 | 54.5% | no |

This is not promotable either, but it is an important process finding: express data contains within-industry information, while raw portfolio selection is polluted by industry and size/style exposure. Future event mining should start from industry-relative and size-aware formulations, not raw TopN ranking.

## Decision

- `event_express_profit_surprise_1q`: rejected as a standalone factor.
- Forecast/express cache: accepted as reusable infrastructure.
- Express path: hibernate direct standalone formulas after this batch.
- Re-entry condition: only revisit forecast/express with a new orthogonal hypothesis, such as forecast/express disagreement, industry reporting-season surprise, cash-quality confirmation, or size-aware industry-neutral construction.
- Portfolio grids remain blocked. No promotion, no live signal, no order logic.

## Next Direction

Rotate away from standalone forecast/express and mine a more orthogonal family with the improved gates:

- PIT event timing required.
- Full 2015-2025 replay required before portfolio conversion.
- Industry/style exposure report required.
- Size-neutral and industry-neutral RankIC required.
- Yearly stability required.
- Portfolio grid only after a prescreen lead survives de-dup, cost, capacity, regime, and final-holdout gates.
