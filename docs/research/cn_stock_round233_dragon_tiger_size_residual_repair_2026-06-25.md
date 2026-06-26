# CN Stock Round233 Dragon-Tiger Size Residual Repair - 2026-06-25

## Scope

This report records the residual repair step after Round232 found two Dragon-Tiger net-buy pressure candidates with strong raw IC but weak size-neutral retention.

It is not a portfolio backtest and makes no Sharpe, annual return, profit-rate, win-rate, or promotion claim.

## Inputs

- Processed Dragon-Tiger stock-day root: `data/processed/round232_dragon_tiger_attention_reversal_20260624`
- Source PIT IC report: `data/reports/round232_dragon_tiger_pit_ic_prescreen_20260625`
- Output directory: `data/reports/round233_dragon_tiger_size_residual_repair_20260625`
- Analysis window: 2015-01-01 through 2025-12-31
- Residual exposure: daily cross-sectional `log_adv20` rank
- Horizon: 1 trading day

## Result

- Source factor rows: 310,858
- Residual factor rows: 290,792
- Aligned rows: 289,846
- Candidates tested: 2
- FDR-significant tests: 2
- Neutral-gate pass tests: 2
- Research leads: 0
- Promotion allowed candidates: 0

## Candidate Details

| Factor | IC | ICIR | t | IC>0 | Q5-Q1 | Monotonicity | Industry-neutral IC | Size-neutral IC | Size retention | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `dragon_tiger_net_buy_continuation_size_residual_1d` | 0.0486 | 0.291 | 15.00 | 59.8% | 0.0084 | 0.40 | 0.2553 | 0.0309 | 0.636 | rejected |
| `dragon_tiger_institutional_net_buy_pressure_size_residual_1d` | 0.0486 | 0.293 | 15.12 | 60.7% | 0.0083 | 0.40 | 0.2625 | 0.0311 | 0.640 | rejected |

## Interpretation

The residual repair worked technically: both candidates now pass the neutral gates and retain more than 60% of their size-neutral signal. However, they still fail the research-lead gate because ICIR remains below 0.30 and quantile monotonicity is weak at 0.40.

This means the family has a real diagnostic signal but not a clean enough shape for portfolio conversion. The correct action is not threshold tuning or direct TopN conversion. The family should be hibernated unless a new orthogonal Dragon-Tiger hypothesis is registered.

Next direction:

```text
round234_hibernate_or_rotate_dragon_tiger_after_size_residual_repair_failure
```

## Blocked Actions

- No Dragon-Tiger portfolio grid.
- No promotion.
- No final holdout read.
- No same-family parameter expansion to chase the already-seen IC.

## Verification

Fresh commands run:

```powershell
python -m unittest tests.unit.test_dragon_tiger_size_residual_repair tests.unit.test_dragon_tiger_size_residual_repair_cli
python scripts\run_dragon_tiger_size_residual_repair.py --processed-root data\processed\round232_dragon_tiger_attention_reversal_20260624 --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --stock-basic data\processed\cn_stock_metadata --output-dir data\reports\round233_dragon_tiger_size_residual_repair_20260625 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 30 --min-neutral-rank-ic 0.01 --min-neutral-ic-t-stat 2.0 --min-neutral-retention 0.50 --allow-not-ready
```
