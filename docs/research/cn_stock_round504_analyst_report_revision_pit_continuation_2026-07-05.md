# CN Stock Round504 Analyst Report Revision PIT Continuation

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continue the Round467 analyst-report-revision PIT source after the provider limit reset. This is research-to-review only. No broker connection, no live account reads, no order placement, and no automatic live trading.

## Round Objective

This round followed the project loop:

1. Analyze current project state.
2. Choose the most useful next objective.
3. Execute only the allowed path.
4. Record evidence and next direction.

The selected objective was to resume the Round467 Tushare `report_rc` source construction by caching February 2024 and rerunning the frozen PIT prescreen with January plus February report roots.

## Startup Evidence

Fresh 2026-07-05 gates:

- Quant PM startup gate: `status=ready`, no blockers.
- Primary market: `CN_ETF`.
- CN stock work: factor-batch branch, scoped separately from the primary ETF line.
- CN stock factor-mining startup gate: `status=cleared`, no blockers.
- CN stock data manifest: no blockers, `status=review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Review Agent Feedback

Two read-only review agents were used as a baseline for the continuous loop.

Quant PM view:

- Best next action is to resume the Round467 analyst-report-revision PIT source after the provider limit resets.
- Do not treat Round503 self-risk overlay evidence as an independent alpha.
- Do not tune `q20`, `m175`, range-contraction, or `ps_ttm` thresholds.
- Do not use direct anonymous daily-basic alpha factory until the method contract and round-state validator agree.

New-user view:

- The index needed a current-state update because older branch-cleanup language was easy to misread.
- The project needed a one-page next-step checklist with exact commands, success signs, stop points, and safety boundaries.
- The safety line should be prominent: research-to-paper only; no broker, account, order, or live-trading access.

## Source Cache

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-02-01 --end-date 2024-02-29 --output-dir data\reports\round504_analyst_report_revision_cache_202402_20260705 --processed-output-dir data\processed\round504_analyst_report_revision_cache_202402_20260705 --window-frequency MS --request-sleep-seconds 0 --max-rows-per-window 5000
```

Result:

- Windows: 1
- Fetched windows: 1
- Failed windows: 0
- Rate-limited windows: 0
- Rows: 1,744
- Assets: 902
- Min report date: 2024-02-16
- Max report date: 2024-02-29
- Processed output: `data/processed/round504_analyst_report_revision_cache_202402_20260705`

Generated data stays out of Git.

## Frozen PIT Prescreen

Command:

```powershell
.\.venv\Scripts\python.exe scripts\run_analyst_report_revision_prescreen.py --report-root data\processed\round463_analyst_report_revision_source_smoke_20260704 --report-root data\processed\round504_analyst_report_revision_cache_202402_20260705 --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round504_analyst_report_revision_prescreen_202401_202402_20260705 --analysis-start-date 2024-01-01 --analysis-end-date 2024-04-30 --horizons 5,20 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 1 --min-industries 2 --min-assets-per-industry 2 --min-signal-date-amount 10000000
```

Result:

- Stage: `analyst_report_revision_pit_prescreen`
- Final holdout included: false
- Report rows: 3,498
- Report assets: 1,317
- Min report date: 2024-01-25
- Max report date: 2024-02-29
- Min signal date: 2024-01-26
- Max signal date: 2024-03-01
- Candidates: 4
- Tests: 8
- Factor rows: 6,882
- Aligned rows: 13,764
- IC observations per test: 14
- Multiple-testing lead count: 5
- Neutral-gate pass count: 4
- Research lead count: 0
- Promotion-allowed candidates: 0
- Next direction: `rotate_or_cache_more_analyst_report_history_after_zero_prescreen_leads`

Top short-window diagnostics:

| Candidate | Horizon | Mean IC | ICIR | IC t-stat | Positive IC rate | Quantile spread | Research lead |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `analyst_np_revision_90` | 5 | 0.10024513625752637 | 1.0607971970865206 | 3.9691396683478724 | 0.9285714285714286 | 0.019267660208860803 | false |
| `analyst_eps_revision_90` | 5 | 0.0965548271209604 | 1.1603474324497258 | 4.341622541849693 | 0.8571428571428571 | 0.016480062078286326 | false |
| `analyst_eps_revision_90` | 20 | 0.08937436298092054 | 0.6501332850738102 | 2.432576008484031 | 0.7857142857142857 | 0.019216016237331702 | false |
| `analyst_np_revision_90` | 20 | 0.08914440572692325 | 0.6358836909723388 | 2.3792589094557295 | 0.7857142857142857 | 0.025529561757046498 | false |

Why no research lead:

- `ic_year_coverage_below_gate` blocks the otherwise strong short-window signals.
- Portfolio and promotion gates are still intentionally disabled.
- Final holdout remains sealed.

## Decision

The source construction improved from one month to two months and produced promising short-window IC diagnostics, but it did not create a research lead because year coverage is still insufficient.

This is a useful result:

- It proves the provider limit reset and February source cache can be collected.
- It confirms the frozen PIT prescreen can consume multiple report roots.
- It gives a clear next action without tuning formulas.

Next action:

- Cache the next monthly `report_rc` window after provider quota allows it.
- Rerun the same frozen prescreen with all accumulated report roots.
- Stop or rotate if enough PIT history still fails year coverage, neutral, cost, capacity, or regime gates.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
- Do not use 2026 final holdout for this source-smoke work.
