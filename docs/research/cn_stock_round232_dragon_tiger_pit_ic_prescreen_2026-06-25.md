# CN Stock Round232 Dragon-Tiger PIT IC Prescreen - 2026-06-25

## Scope

This report records the first full-sample point-in-time IC prescreen for the Round232 Dragon-Tiger attention/reversal candidate family.

It is not a portfolio backtest and makes no Sharpe, annual return, profit-rate, win-rate, or promotion claim.

## Inputs

- Processed Dragon-Tiger stock-day root: `data/processed/round232_dragon_tiger_attention_reversal_20260624`
- Candidate plan: `configs/factor_mining_candidate_plan_round232_dragon_tiger_attention_reversal_20260624.json`
- Output directory: `data/reports/round232_dragon_tiger_pit_ic_prescreen_20260625`
- Analysis window: 2015-01-01 through 2025-12-31
- Horizon: 1 trading day
- PIT rule: Dragon-Tiger event date is shifted to `available_date`; same-day event trading is blocked.

## Result

- Candidates tested: 5
- Factor rows: 777,349
- Label rows: 10,774,125
- Aligned rows: 742,130
- FDR-significant tests: 5
- Neutral-gate pass tests: 0
- Direct research leads: 0
- Style residual repair candidates: 2
- Promotion allowed candidates: 0

## Top Candidates

| Factor | IC | ICIR | t | IC>0 | Q5-Q1 | Industry-neutral IC | Size-neutral IC | Size retention | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `dragon_tiger_net_buy_continuation_1d` | 0.0962 | 0.494 | 25.47 | 66.0% | 0.0186 | 0.2828 | 0.0243 | 0.252 | repair candidate |
| `dragon_tiger_institutional_net_buy_pressure_1d` | 0.0962 | 0.497 | 25.61 | 66.6% | 0.0187 | 0.2896 | 0.0244 | 0.254 | repair candidate |
| `dragon_tiger_institutional_disagreement_abs_pressure_1d` | 0.0670 | 0.315 | 16.23 | 61.0% | 0.0174 | 0.2926 | -0.0168 | 0.250 | rejected before repair |
| `dragon_tiger_net_sell_exhaustion_reversal_1d` | -0.0596 | -0.349 | -18.02 | 37.8% | -0.0049 | 0.2876 | -0.0203 | 0.340 | rejected |
| `dragon_tiger_abnormal_attention_reversal_1d` | -0.0590 | -0.269 | -13.87 | 42.1% | -0.0167 | 0.2119 | 0.0211 | 0.357 | rejected |

## Interpretation

The two net-buy pressure signals are interesting but not promotable. Their raw IC and industry-neutral IC are strong, yet only about one quarter of the raw IC survives the size-neutral retention gate. This means the current signal is still too entangled with size/liquidity/attention exposure to justify a direct portfolio grid.

The immediate next step was residual repair:

```text
round233_dragon_tiger_size_residual_repair_before_portfolio_grid_preflight
```

Round233 has now run and produced zero research leads after residual repair. The next required direction is:

```text
round234_hibernate_or_rotate_dragon_tiger_after_size_residual_repair_failure
```

## Blocked Actions

- No Dragon-Tiger portfolio grid.
- No promotion.
- No final holdout read.
- No same-family threshold tuning just to inflate the already-seen IC.

## Verification

Fresh commands run:

```powershell
python -m unittest tests.unit.test_dragon_tiger_pit_ic_prescreen tests.unit.test_dragon_tiger_pit_ic_prescreen_cli
python scripts\run_dragon_tiger_pit_ic_prescreen.py --processed-root data\processed\round232_dragon_tiger_attention_reversal_20260624 --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --stock-basic data\processed\cn_stock_metadata --candidate-plan-json configs\factor_mining_candidate_plan_round232_dragon_tiger_attention_reversal_20260624.json --output-dir data\reports\round232_dragon_tiger_pit_ic_prescreen_20260625 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --execution-lag 1 --pit-lag-trade-days 1 --min-cross-section 20 --min-ic-observations 30 --min-neutral-rank-ic 0.01 --min-neutral-ic-t-stat 2.0 --min-neutral-retention 0.50 --allow-not-ready
```
