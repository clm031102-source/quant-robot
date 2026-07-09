# CN Stock Round703 Local Source Queue Audit

Date: 2026-07-09

Branch: `codex/factor-batch-cn-stock-source-readiness-round695-20260709`

Machine/task: `office_desktop` / `factor_batch`

## Scope

Round703 audited the local, no-provider factor-mining queue after Round702. The purpose was to identify whether any already cached PIT-safe source could support another honest factor batch today, given that Round701 exhausted the local `report_rc` provider request budget.

This was a source and direction audit only. It did not run provider requests, generate new factor formulas, run portfolio grids, walk-forward conversion, promotion gates, signal generation, mixed-window harvesting, or 2026 final-holdout reads.

## Current Local Constraint

Round701 postcheck blocked another analyst-report provider request with `daily_provider_request_budget_exhausted`, counted request windows `2`, remaining windows `0`.

Round702 startup/data controls were still valid for this audit:

- Quant PM startup gate: `ready`, blockers `[]`, primary market `CN_ETF`.
- CN stock factor-mining startup gate: `cleared`.
- CN stock data manifest: `review_required`, blockers `[]`, warnings `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- Worktree was clean after commit `6801b5a2`.

## Local Processed Source Scan

Relevant recent processed source roots found locally:

| Source root | Status |
| --- | --- |
| `round701_analyst_report_revision_cache_202406_20260709` | active source accumulation, no conversion |
| `round700_analyst_report_revision_cache_202405_20260709` | included in active analyst source accumulation |
| `round695_external_feeds_lpr_repaired_20260709` | source repair only; no active factor line |
| `round690_financial_statement_*` and prior shard roots | broad statement source reached gate, but adjacent formula families failed |
| `round255_forecast_express_event_cache_20260625` | tested in Round268, rejected |
| `round232_dragon_tiger_attention_reversal_20260624` | tested/repaired, rejected or simulation-only |
| `office_desktop_20260617_daily_basic_factor_inputs` | daily-basic/direct public families hibernated |

No fresh local processed root for a new dividend, buyback, holder-number, top-holder concentration, index-rebalance, margin, or northbound mechanism was found that has not already been tested, blocked by permissions, or closed by later evidence.

## Direction Status

| Direction | Latest Evidence | Current Status | Allowed Next Action |
| --- | --- | --- | --- |
| Analyst report revision | Round701/702: `analyst_target_upside_60` H5 improved to IC `0.1511`, but still one IC year and June-cohort dependent | active source accumulation only | after quota reset, cache next month and rerun frozen prescreen |
| Financial statement / reporting timeliness | Round690 cleared source coverage; Round691-Round694 ran four adjacent statement families with 0 research leads | closed for adjacent realized-statement formula mining | only a genuinely new PIT-safe source mechanism or external expectation linkage |
| LPR / HK-hold | Round695-Round698 repaired LPR and showed `hk_hold` is quarterly after 2024-08-20 | source maintenance only | no immediate IC screen; future quarterly-state plan would need a new gate |
| Forecast/express disagreement | Round268: 3 candidates, 6 tests, 0 multiple-testing leads, 0 neutral passes, 0 research leads | hibernated | no threshold/sign/window tuning |
| Share unlock / pledge | Round251: share unlock looked strong but only 3 IC years; pledge failed direction/neutral gates | hibernated | no direct promotion or portfolio grid |
| Repurchase contextual repair | Round303: 2 candidates, 4 tests, 0 FDR leads, 0 neutral passes | hibernated | re-entry requires a new independent source or execution proof |
| Index rebalance / dragon tiger / northbound / margin | Prior rounds showed zero leads, wrong direction, style collapse, or simulation-only evidence | hibernated | no parameter variations |
| Daily-basic / low-turnover / public technical / Alpha101 | Multiple prior reviews found redundancy, extreme-trade artifacts, capacity/drawdown failure, or residual collapse | hibernated | no direct grids or sign flips |
| Official tradeability / limit-event proxy / industry breadth | Round159-161 and Round259-261 closed proxy/official/state variants | hibernated as alpha; useful as controls | controls only unless a new source mechanism is proven |
| Moneyflow residual-regime framework | project has a dedicated validation profile | validation task only, not current `factor_batch` mining | use `desktop-validation` only when assigned `factor_validation` |

## Decision

No additional no-provider factor batch should run today from the local closed-source queue. The only active mining line is analyst-report revision source accumulation, and it is blocked from further provider use until quota resets.

The next valid action after quota reset is narrow:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_analyst_report_cache.py --start-date 2024-07-01 --end-date 2024-07-31 --output-dir data\reports\<next_analyst_cache_report_dir> --processed-output-dir data\processed\<next_analyst_cache_processed_dir> --window-frequency MS --request-sleep-seconds 0 --quota-output-dir data\reports\<next_quota_preflight_dir> --quota-report-root data\reports --quota-report-root data\reports\round521_analyst_quota_pack_provenance_20260705 --quota-preflight-only
```

Only if that preflight is allowed should the project send one provider request, then rerun the same frozen analyst prescreen. No formula, sign, threshold, or holdout tuning is allowed.

If no provider request is available, the next non-provider work should be source governance only:

- update or harden queue/gate documentation;
- review whether a genuinely new PIT source exists before preregistration;
- run validation-only profiles only under `factor_validation`, not as exploratory factor mining.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit generated `data/raw`, `data/processed`, `data/reports`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
