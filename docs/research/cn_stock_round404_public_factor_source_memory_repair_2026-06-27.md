# CN Stock Round404 - Public Factor Source Memory Repair

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round404 tried to materialize all supported public Alpha101, technical, trend-volume, trend-strength, and RSRS factor values for the frozen Dragon-Hot selected-trade universe.

The goal was not to claim alpha. It was to create point-in-time public-factor context at the exact selected trade signal dates so Round405 could test public indicators as entry filters or exposure tilts.

## Engineering Finding

The first all-factor run exposed a source-materialization bug:

- family builders produced wide intermediate feature frames;
- the source tool concatenated full-market, full-date family outputs before selecting target trade rows;
- all public factors together expanded toward hundreds of millions of rows and hit memory pressure.

Two regression tests were added:

- family outputs must be narrowed before cross-family concat;
- family outputs must be targeted to selected trade date/asset pairs before cross-family concat.

The source builder now follows:

```text
family computation -> narrow factor columns -> target selected trade pairs -> concatenate small target tables
```

## Command

```powershell
python scripts\run_shortlist_public_factor_source.py --trades data\reports\round338_24h_profit_sprint_turnover_low_replacement_filters_quarantine_corrected_20260627\replace_drop_turnover_f_low10_trades_with_tradeability.parquet --output-dir data\reports\round404_24h_profit_sprint_all_public_factor_source_for_dragon_hot_20260627 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31
```

## Output

- Output dir: `data/reports/round404_24h_profit_sprint_all_public_factor_source_for_dragon_hot_20260627`
- Target trade pairs: 26,450
- Requested public factors: 32
- Target-level factor rows: 846,400
- Non-null values: 615,507
- Bar rows used: 10,785,537
- Bar assets: 5,707

Coverage was strong for Alpha101, RSI/Bollinger/Donchian/MACD, and RSRS. Trend-volume and Supertrend/Smart-money/OBV capacity-strict variants were sparse and should not be promoted from this projection alone.

## Decision

Round404 produced a reusable, lower-memory source path and a complete target-level public-factor source for Round405.

Promotion allowed: false. This is a source/tooling artifact only.
