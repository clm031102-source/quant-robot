# Round691 Financial Reporting Timeliness Design

Date: 2026-07-09
Branch: `codex/factor-batch-cn-stock-financial-reporting-timeliness-round691-20260709`
Machine: `office_desktop`
Task: `factor_batch`

## Decision

Use approved approach A: preregister a dedicated CN stock `financial_reporting_timeliness` candidate plan first, then run a specialized point-in-time prescreen. The first implementation step is not an IC screen. It is a candidate plan gate that must reach `research_ready`.

This design replaces the stale Round690 branch suggestion with the branch prefix accepted by `configs/factor_mining_startup_cn_stock.json`: `codex/factor-batch-cn-stock-...`.

## Current Evidence

- Round690 cleared the financial reporting timeliness source gate with 1,002 unique symbols and blockers `[]`.
- Startup context on 2026-07-09 selected `office_desktop`, `factor_batch`, and the Round691 CN stock branch.
- Quant PM startup gate returned `status=ready`, `primary_market=CN_ETF`, and blockers `[]`.
- Factor mining startup gate returned `status=cleared` and blockers `[]` after the branch prefix was corrected.
- CN stock data manifest returned blockers `[]`, `bar_asset_ids=5774`, `moneyflow_asset_ids=5648`, and date range `2015-01-05` to `2026-06-15`.
- Manifest warnings are `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`; these are audit inputs, not alpha evidence.

## Scope

Round691 is a research-screen-only preregistration and candidate-plan gate for CN stocks. It must not run portfolio grids, promotion gates, sign/window tuning, mixed-window harvesting, live trading logic, broker reads, account reads, order placement, or automatic trading.

The 2026 window remains final holdout only. Candidate design and prescreen work must use the long-cycle window ending 2025-12-31 for research and validation decisions.

## Candidate Set

All candidates use point-in-time financial statement availability. A value can become tradable only on the first valid trading date after `ann_date` or an explicitly later effective date. Period-end-only availability is forbidden.

1. `frt_reporting_lag_short`
   - Family: `financial_reporting_timeliness`
   - Formula idea: higher score for shorter `ann_date - end_date` reporting lag.
   - Rationale: faster reporting can proxy stronger controls, lower opacity, and faster information release.

2. `frt_reporting_lag_improvement_4q`
   - Formula idea: higher score when the current quarter's reporting lag improves versus the same quarter one year earlier.
   - Rationale: improving reporting discipline can indicate better operating cadence or disclosure quality.

3. `frt_reporting_lag_stability_8q`
   - Formula idea: higher score for lower trailing 8-quarter reporting-lag variability.
   - Rationale: stable reporting cadence can reduce uncertainty and event-timing noise.

4. `frt_early_report_quality_combo`
   - Formula idea: frozen equal-weight combination of timely reporting and a PIT-safe quality or cash-conversion component, only if required columns are available.
   - Rationale: timeliness is more plausible when paired with realized quality rather than treated as a standalone calendar artifact.

5. `frt_late_reporter_risk_avoidance`
   - Formula idea: negative score for extreme late reporters after the announcement becomes observable.
   - Rationale: very late reporting may proxy opacity, weak controls, or operating friction.

No parameter grid is allowed in the candidate plan. Any variants must be counted as separate tests and preregistered before screening.

## Data Flow

1. Confirm the branch and startup gates.
2. Write `configs/factor_mining_candidate_plan_round691_financial_reporting_timeliness_20260709.json`.
3. Declare all default CN stock control areas required by the candidate plan gate.
4. Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round691_financial_reporting_timeliness_20260709.json --output-dir data\reports\round691_financial_reporting_timeliness_candidate_plan_gate_20260709
```

5. Proceed to prescreen only if the gate returns `research_ready`, `candidate_plan_gate_cleared=true`, and blockers `[]`.

## Controls

The candidate plan must declare the complete default CN stock control set:

- A-share tradeability controls.
- Financial PIT timing controls.
- Source sample integrity controls.
- Industry and style neutralization controls.
- ETF rotation scope boundary controls.
- Portfolio construction controls, even though portfolio work is blocked at this stage.
- Strict statistics controls.
- China market regime controls.
- Event contamination controls.

Promotion policy must keep `promotion_allowed=false` and `portfolio_backtest_allowed_before_prescreen=false`, while declaring all required future promotion gates as required.

## Prescreen Design

The prescreen should reuse existing statement-matrix and residual-IC patterns rather than forcing the generic Tushare alpha factory, which does not currently support this family. The prescreen must report:

- PIT signal-date alignment proof.
- Candidate coverage by year and symbol.
- Neutral IC and residual IC at fixed 5D and 20D horizons.
- Quantile shape and monotonicity diagnostics.
- Industry, size, liquidity, value, low-vol, and momentum exposure diagnostics.
- Multiple-testing count for every active candidate and any rejected candidate.
- Explicit proof that portfolio backtests, promotion, and final holdout reads were not run.

## Error Handling

Stop if any startup or candidate plan gate has blockers. Stop if PIT alignment cannot prove `signal_date > ann_date`. Stop if required controls are missing. Stop if generated outputs touch forbidden Git paths, include credentials, or contain raw/processed data that should stay out of Git.

Manifest warnings must be carried into the prescreen report. Extreme return rows require a data-quality note before any result is interpreted. Moneyflow coverage warnings are not directly blocking for this family, but they matter for style/liquidity control coverage.

## Verification

Before implementation is considered ready for review:

- `scripts/run_quant_pm_startup_gate.py` must be `ready`.
- `scripts/run_factor_mining_startup_gate.py` must be `cleared`.
- `scripts/run_cn_stock_data_manifest.py` must have blockers `[]`.
- Candidate plan gate must be `research_ready`.
- `git status --short` must show only allowed source, config, doc, or lightweight summary changes.
- No `data/raw`, `data/processed`, `data/reports`, large CSV/Parquet, logs, tokens, broker credentials, account data, or order data may be staged.

## Next Step After Review

After this spec is reviewed, invoke the writing-plans workflow and produce an implementation plan for the candidate plan JSON plus candidate gate run. Do not start IC prescreening until the candidate gate clears.
