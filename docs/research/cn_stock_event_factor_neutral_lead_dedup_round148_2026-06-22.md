# CN Stock Event Factor Neutral Lead Dedup Round148

Date: 2026-06-22

Machine/task: office_desktop / factor_validation

Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`

Scope: CN A-share stock cross-sectional alpha research only. This is not ETF rotation, not paper trading, and not live trading.

## Objective

Round147 found one event-factor research lead:

`event_dividend_cash_yield_announced_1y`, horizon 20.

Round148 tested whether this lead is an independent event alpha or mostly a public daily-basic dividend/value exposure. The audit was intentionally run before any portfolio grid, TopN conversion, costed backtest, or promotion claim.

## Implementation

New repeatable artifacts:

- `src/quant_robot/ops/event_factor_neutral_lead_dedup.py`
- `scripts/run_event_factor_neutral_lead_dedup.py`
- `tests/unit/test_event_factor_neutral_lead_dedup.py`
- `tests/unit/test_event_factor_neutral_lead_dedup_cli.py`

The module evaluates:

- raw RankIC for the event dividend lead;
- cross-sectional correlation versus public daily-basic references;
- exposure correlation versus `dv_ttm`, `dv_ratio`, valuation, size, volume-ratio, and liquidity proxies;
- residual RankIC after neutralizing public dividend/value/size/liquidity exposures.

The implementation blocks promotion and portfolio grids by construction.

## Live Run

Command:

```powershell
python scripts\run_event_factor_neutral_lead_dedup.py --daily-basic-root data\processed\cn_stock_long_history_2015_202306 --daily-basic-root data\processed\office_desktop_20260617_daily_basic_factor_inputs --event-start-year 2018 --event-end-year 2025 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizon 20 --execution-lag 1 --pit-lag-trade-days 1 --sample-every-n-dates 5 --min-cross-section 30 --min-ic-observations 8 --output-dir data\reports\event_factor_neutral_lead_dedup_round148_20260622
```

Output pack:

- `data/reports/event_factor_neutral_lead_dedup_round148_20260622/event_factor_neutral_lead_dedup.json`
- `data/reports/event_factor_neutral_lead_dedup_round148_20260622/event_factor_neutral_lead_dedup.md`
- reference/exposure/yearly/monthly/raw/residual IC CSV files under the same directory

Generated data/reports artifacts are not Git-tracked.

## Result Summary

Raw event-dividend lead:

- lead rows: 9,934
- raw IC observations: 90
- raw mean RankIC: 0.0834
- raw ICIR: 0.4753
- raw t-stat: 4.51
- raw IC positive rate: 70.0%
- raw yearly failures: 1, with 2021 negative

Residual after public-exposure neutralization:

- residual IC observations: 72
- residual mean RankIC: 0.0241
- residual ICIR: 0.1412
- residual t-stat: 1.20
- residual IC positive rate: 56.9%
- residual yearly failures: 3, specifically 2019, 2021, and 2022

Public-reference/exposure diagnosis:

- `daily_basic_dv_ratio`: mean correlation 0.6785, max absolute correlation 0.8195, moderate reference redundancy and high public exposure
- `daily_basic_dv_ttm`: mean correlation 0.5689, max absolute correlation 0.7463, moderate redundancy
- `daily_basic_inv_pe_ttm`: mean correlation 0.5345, max absolute correlation 0.7969, moderate redundancy

Gate blockers:

- `residual_icir_below_threshold`
- `lead_high_public_yield_or_value_exposure`
- `raw_yearly_ic_instability`
- `residual_yearly_ic_instability`

Decision:

- promotion allowed: 0
- portfolio conversion candidates: 0
- next direction: `round149_event_factor_family_rotation_after_dedup_failure`

## Audit Interpretation

The raw event-dividend signal is real enough to explain why Round147 surfaced it. However, once public dividend/value exposures are considered over the longer available daily-basic span, the incremental event component becomes weak and unstable.

The 2024-2025-only residual looked much stronger, but that was a shorter coverage artifact. The longer replay is the authority result for direction decisions.

The correct conclusion is not "dividend events are a promotable alpha"; it is:

1. Dividend announcement cash yield is a useful diagnostic signal.
2. Much of the signal overlaps public dividend/value information.
3. The residual component does not clear the long-cycle stability gate.
4. This family should not receive more parameter sweeps or direct portfolio grids now.

## Data-Provider Risk Found

A live smoke probe showed the Tushare `dividend(end_date=...)` endpoint can return exactly 2,000 rows for many annual periods, which is likely a provider page-size cap. It also returned 0 rows for `end_date=20231231` during the probe.

Observed probe:

- 20171231: 2,000 rows
- 20181231: 2,000 rows
- 20191231: 2,000 rows
- 20201231: 2,000 rows
- 20211231: 2,000 rows
- 20221231: 2,000 rows
- 20231231: 0 rows
- 20241231: 2,000 rows
- 20251231: 2,000 rows

Implication: future event-factor work must use sharded/cached endpoint ingestion with row-cap and coverage diagnostics before making any promotion claim from event data.

This provider issue does not rescue the dividend lead. It lowers confidence in direct event-factor promotion and strengthens the case for rotating away from this event-dividend line until event ingestion is repaired.

## Next Action

Do not run more event-dividend parameter variants.

Proceed to the three-round review for Rounds 146-148, then rotate to a new family or public-reference method. If event factors are revisited later, the first task must be sharded event endpoint coverage repair, not factor parameter search.
