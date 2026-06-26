# CN Stock Daily-Basic Free-Float Supply Quality True-Close Extreme Trade Liquidity/Limit Audit - Round139

Date: 2026-06-22

Stage: `daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit`

Source: Round138 price-basis repaired rerun.

Output:

- JSON: `data/reports/daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit_round139_20260622/daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit.json`
- CSV: `data/reports/daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit_round139_20260622/daily_basic_free_float_supply_quality_true_close_extreme_trade_path_audit.csv`
- Markdown: `data/reports/daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit_round139_20260622/daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit.md`

## Objective

Round138 removed the mixed adjusted/unadjusted price-basis phantom-alpha problem, but still had 156 true-close extreme trade rows. Round139 asks whether those high-return paths are tradable enough to justify further work under the user's higher drawdown tolerance.

This round does not mine new factors. It audits the existing extreme-trade evidence before any promotion or further parameter sweep.

## Method

- Deduplicate extreme trade rows by `(asset_id, signal_date, entry_date, exit_date)`.
- Join CN daily bars and Tushare stock-basic metadata.
- Flag entry limit-up-like paths, exit limit-down-like paths, BSE paths, new listings, low entry amount, missing price paths, zero-volume/suspended paths, and missing metadata.
- Keep final holdout closed.

Default hard checks:

- Minimum listing age: 120 calendar days.
- Minimum entry amount: 10,000,000.
- Limit detection: 95% of the asset board's daily limit threshold.
- Board thresholds: main board 10%, STAR/ChiNext 20%, BSE 30%.

## Results

- Raw extreme trade rows: 156.
- Unique trade paths after dedupe: 15.
- Repeated parameter rows removed: 141.
- Blocked unique paths: 4.
- No-obvious-tradeability-blocker paths: 11.
- Entry limit-up-like paths: 0.
- Exit limit-down-like paths: 1.
- BSE paths: 2.
- Low entry-amount paths: 1.
- New-listing paths: 0.
- Missing metadata paths: 0.
- Missing price paths: 0.
- Zero-volume paths: 0.
- Suspended paths: 0.

The strongest clean-looking paths by gross return were:

| Asset | Entry | Exit | Gross Return | Entry Amount | Class |
|---|---|---|---:|---:|---|
| CN_XSHG_600410 | 2025-07-29 | 2025-08-26 | 136.20% | 1,602,945,009 | no obvious blocker |
| CN_XSHE_002130 | 2024-03-01 | 2024-03-29 | 78.83% | 282,675,843 | no obvious blocker |
| CN_XSHE_300253 | 2025-01-24 | 2025-03-03 | 77.91% | 270,721,456 | no obvious blocker |
| CN_XSHG_600363 | 2024-09-25 | 2024-10-30 | 74.89% | 220,468,180 | no obvious blocker |
| CN_XSHE_002365 | 2025-03-31 | 2025-04-29 | 73.19% | 37,838,991 | no obvious blocker |

The main blocked paths were:

- `CN_XBEI_920438`: 152.33% gross return, BSE execution/permission/regime risk.
- `CN_XSHE_002469`: 94.85% gross return, exit limit-down sell execution risk.
- `CN_XBEI_920476`: 65.00% gross return, BSE execution/permission/regime risk.
- `CN_XSHG_600360`: -56.03% gross return, low entry amount liquidity risk.

## Interpretation

The high total-return candidates are not promotable yet, but Round139 materially improves the diagnosis.

The old "156 extreme trades" headline was misleading because it counted repeated cost/capital/guard parameter rows as independent evidence. After dedupe there are only 15 real trade paths. That removes a major false-confidence source.

The result is not a full rejection. Eleven paths have no obvious limit, listing-age, BSE, missing-data, suspension, zero-volume, or low-entry-amount blocker. Those paths are the only legitimate reason to continue this line.

The promotion answer is still no because this is an audit, not a clean walk-forward validation. Even if the user can tolerate a 30% drawdown, that tolerance does not waive execution quality, event effects, capacity, repeated-row dedupe, or final-holdout discipline.

## Decision

Promotion: `0`.

Research continuation: yes, but only through an event-adjusted clean rerun of the 11 no-obvious-blocker paths.

Next direction:

`round140_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_or_manual_review`

Required before any promotion:

- Rerun no-obvious-blocker paths under event-adjusted execution.
- Exclude or separately gate BSE, exit-limit, and low-entry-amount paths.
- Do not count repeated parameter rows as independent alpha.
- Keep final holdout closed.
- Require cost/capacity/regime walk-forward evidence after the clean rerun.

