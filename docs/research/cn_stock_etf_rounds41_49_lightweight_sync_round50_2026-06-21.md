# CN Stock / CN ETF Rounds 41-49 Lightweight Sync - Round 50 - 2026-06-21

## Scope

This is the 10-round packaging checkpoint before GitHub safe-sync.

The goal is to keep useful code, configs, tests, and lightweight reports, while leaving generated data and heavy experiment outputs under `data/` only.

## Round Outcomes

| Round | Direction | Result | Promotable |
|---:|---|---|---:|
| 41 | CN ETF range-contraction composite variants | Liquidity/low-vol tie-breakers did not improve the lead | 0 |
| 42 | CN ETF long-cycle replay of range-contraction lead | Long-cycle evidence weakened the short-sample lead | 0 |
| 44 | CN ETF public technical and trend-volume full-sample screen | OBV/SuperTrend looked weak and capacity-sensitive | 0 |
| 45 | Strict capacity replay for OBV/SuperTrend | Capacity fixed, returns turned negative | 0 |
| 46 | CN stock `stock_basic` industry metadata foundation | 5,529 A-share rows available for industry audits | 0 |
| 47 | Three-round audit | Direction changed from ETF indicator sweeps to CN stock translation-layer diagnostics | 0 |
| 48 | CN stock industry-neutral IC audit | 3 public formula factors keep strong within-industry RankIC | 0 |
| 49 | CN stock industry-neutral portfolio backtest | 12/12 rejected; positive absolute rows still fail relative return and Sharpe | 0 |

Current status:

- Manual/live usable factors: 0
- Paper-ready factors: 0
- Promotable factors: 0
- Research leads: 1 weak translation lead, `formula_pv_corr_reversal_20` as an exclusion/risk-control candidate only

## Useful Code Added

Decision safety:

- `min_total_return` gate in decision / pipeline / experiment grid / walk-forward config mapping.

Data foundation:

- Tushare stock_basic ingest with industry, area, stock market, list dates, and HS flags.

Audit tools:

- IC-to-portfolio gap audit already present from Round15.
- New industry-neutral IC audit:
  - `src/quant_robot/ops/industry_neutral_ic_audit.py`
  - `scripts/run_industry_neutral_ic_audit.py`

Portfolio construction:

- New industry-neutral TopN selector:
  - `select_industry_neutral_top_n`
  - `selection_method="industry_neutral_top_n"` through the backtest engine and research pipeline
  - `scripts/run_industry_neutral_portfolio_backtest.py`

Process guardrail:

- CN stock startup gate now requires translation-layer audits:
  - IC-to-portfolio gap audit
  - industry-neutral IC audit
  - translation-layer plan before more raw TopN sweeps

## Rejected Or Hibernated Directions

Do not keep spending budget on:

- CN ETF basic momentum / RSI / MACD / Bollinger / Donchian sweeps
- CN ETF OBV / SuperTrend after strict capacity replay
- standalone ETF theme breadth
- range-contraction tie-breaker variants
- raw CN stock public formula TopN expansion
- industry-blind TopN after strong IC but rejected long-only evidence

## Current Diagnosis

The main failure was not only a bad factor formula. The stronger issue is translation:

- public formula factors have real cross-sectional rank information,
- industry-neutral IC survives,
- naive long-only buy lists still do not beat the benchmark,
- tail IC and realized holdings are unstable,
- benchmark-relative performance is the hard blocker.

So the next useful experiment is not another parameter grid. It is a benchmark-aware exclusion/risk-control test:

- avoid bottom-ranked names,
- compare against broad equal-weight or benchmark-like exposure,
- keep cost/capacity/turnover gates,
- do not tune formula parameters after reading these results.

## Verification

Passed:

```powershell
python -m unittest tests.unit.test_backtest tests.unit.test_research_pipeline tests.unit.test_industry_neutral_ic_audit tests.unit.test_factor_mining_startup_gate tests.unit.test_factor_mining_startup_gate_cli tests.unit.test_decision_risk tests.unit.test_experiment_runner tests.unit.test_tushare_mapping tests.unit.test_tushare_adapter tests.unit.test_tushare_stock_basic_ingest tests.unit.test_project_audit
```

Result:

- 157 tests passed

Passed:

```powershell
python scripts\run_project_audit.py --json
```

Result:

- configs scanned: 54
- files scanned: 707
- safety passes: true
- factor config registry passes: true
- forbidden hits: none

## Sync Boundary

Syncable:

- source code
- tests
- configs
- lightweight docs

Not syncable:

- `data/raw/`
- `data/processed/`
- `data/reports/`
- logs
- tokens
- credentials
- broker/account/order data

Round50 conclusion: sync code/config/test/doc work only. Generated reports remain local.
