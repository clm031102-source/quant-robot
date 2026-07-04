# CN Stock Round505 Analyst Report Revision March Extension

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continue the analyst-report-revision PIT source by adding March 2024 and rerunning the same frozen prescreen. This is research-to-review only. No broker connection, no live account reads, no order placement, and no automatic live trading.

## Round Objective

This was continuous-work loop round 2 after the Round504 review-agent baseline. The selected objective was:

- Extend the Tushare `report_rc` PIT cache from January-February to January-March 2024.
- Keep formulas, horizons, execution lag, PIT lag, and prescreen thresholds frozen.
- Stop if provider quota blocks the request.
- Do not touch final holdout, portfolio grids, or promotion gates.

No new review agents were created in this round because the objective asks for the two-agent review every ten rounds.

## Startup Evidence

Fresh 2026-07-05 gates:

- Quant PM startup gate: `status=ready`, no blockers.
- Primary market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, no blockers.
- CN stock data manifest: no blockers, `status=review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Source Cache

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-03-01 --end-date 2024-03-31 --output-dir data\reports\round505_analyst_report_revision_cache_202403_20260705 --processed-output-dir data\processed\round505_analyst_report_revision_cache_202403_20260705 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000
```

Result:

- Windows: 1
- Fetched windows: 1
- Failed windows: 0
- Rate-limited windows: 0
- Rows: 1,634
- Assets: 531
- Min report date: 2024-03-28
- Max report date: 2024-03-31
- Processed output: `data/processed/round505_analyst_report_revision_cache_202403_20260705`

Generated data stays out of Git.

## Frozen PIT Prescreen

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --report-root data\processed\round505_analyst_report_revision_cache_202403_20260705 --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round505_analyst_report_revision_prescreen_202401_202403_20260705 --analysis-start-date 2024-01-01 --analysis-end-date 2024-05-31 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

Result:

- Stage: `analyst_report_revision_pit_prescreen`
- Final holdout included: false
- Report rows: 5,132
- Report assets: 1,511
- Min report date: 2024-01-25
- Max report date: 2024-03-31
- Min signal date: 2024-01-26
- Max signal date: 2024-04-01
- Candidates: 4
- Tests: 8
- Factor rows: 9,966
- Aligned rows: 19,932
- Multiple-testing lead count: 0
- Neutral-gate pass count: 2
- Research lead count: 0
- Promotion-allowed candidates: 0
- Next direction: `rotate_or_cache_more_analyst_report_history_after_zero_prescreen_leads`

Top diagnostics after adding March:

| Candidate | Horizon | Mean IC | ICIR | IC t-stat | Positive IC rate | Quantile spread | Research lead |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `analyst_np_revision_90` | 20 | 0.07710561091491691 | 0.5640800340719271 | 2.2563201362877083 | 0.75 | 0.024707045749538196 | false |
| `analyst_eps_revision_90` | 20 | 0.07674041200653667 | 0.5697655240917351 | 2.2790620963669403 | 0.75 | 0.018980251163071046 | false |
| `analyst_np_revision_90` | 5 | 0.07007631336183154 | 0.4979692684743769 | 1.9918770738975076 | 0.875 | 0.014079717932989295 | false |
| `analyst_eps_revision_90` | 5 | 0.06588572318679375 | 0.5041600464441606 | 2.0166401857766423 | 0.8125 | 0.011681684728665766 | false |

Why no research lead:

- No candidate survived multiple-testing/FDR after adding March.
- The source still has only one-year coverage for IC-year gates.
- Promotion and portfolio conversion remain blocked until later long-cycle, cost, capacity, regime, and final-holdout gates.

## Interpretation

Round504's two-month smoke had promising short-window diagnostics, but Round505 weakened that evidence after adding March:

- Multiple-testing leads dropped from 5 to 0.
- Neutral-gate pass count dropped from 4 to 2.
- Research lead count stayed 0.

This argues against formula tuning on this partial source. The analyst-report-revision family may still deserve one more quota-aware monthly cache to test whether March is a sparse-window artifact, but it should be rotated away if broader coverage does not restore stable evidence.

## Decision

Do not promote, portfolio-grid, or tune analyst revision formulas.

Allowed next actions:

- Cache one more monthly `report_rc` window only if provider quota allows it, then rerun the same frozen prescreen.
- If the family still produces zero research leads, run a family review and rotate to a genuinely new PIT source candidate plan.
- Keep 2026 final holdout sealed.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
- Do not use 2026 final holdout for this source-smoke work.
