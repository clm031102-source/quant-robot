# CN ETF Skip-Momentum Prescreen Closeout

Date: 2026-07-16  
Branch: `codex/factor-batch-cn-etf-price-rotation-20260716`  
Stage: `cn_etf_skip_momentum_prescreen`  
Decision: reject all frozen candidates and stop-loss `cn_etf_price_rotation`

## Executive Result

The final untested skip-momentum subspace produced zero research leads. All three frozen candidates failed the preregistered statistical and shape gates at both 5-day and 20-day horizons. No portfolio grid, walk-forward run, paper signal, promotion, or live boundary was opened.

This result closes the broader CN ETF price-rotation family together with the earlier rejections of plain momentum, risk-adjusted momentum, relative strength, theme-relative strength, reversal, and tail-guard variants. Parameter rescue, window tuning, threshold relaxation, and another price-rotation retry are prohibited.

## Frozen Contract

- Primary market: `CN_ETF`
- Analysis window: 2020-01-02 through 2024-06-28
- Final 2026 holdout: sealed and not accessed
- Execution lag: one trading day
- Horizons: 5 and 20 trading days
- Candidates: `etf_skip5_momentum_60`, `etf_skip20_momentum_120`, `fip_smooth_momentum_skip5_60`
- Historical references: momentum 20/60, risk-adjusted momentum 20/60, reversal 5/20, and market-relative strength 20/60
- Multiple testing: Benjamini-Hochberg FDR across all six candidate-horizon tests
- Overlap correction: Newey-West lag equal to horizon minus one
- Frozen config SHA-256: `75dd8529d21762804029741928287fb07ba5251bcfd85bcfe7445a029ac93611`

## Data Integrity

- Source rows: 1,119,490
- Source assets: 1,781
- Source sessions: 1,085
- Official ETF metadata assets: 1,766
- Point-in-time eligible assets: 679
- Point-in-time eligible sessions: 833
- Eligible signal rows: 227,010
- Candidate factor rows: 681,030
- Reference factor rows: 1,816,080
- Forward-label rows: 2,191,185
- Daily IC observations: 4,917
- Yearly IC rows: 24
- Candidate-reference correlation rows: 24, with no missing correlation result

Eligibility used official ETF status and list/delist lifecycle, 252 prior observations, trailing 20-day median amount of at least CNY 5 million, stale-price rate no greater than 5%, positive price and amount, and absolute one-day return no greater than 20%. The prior static Round25 universe was not reused.

## Results

| Factor | Horizon | Rank IC | ICIR | NW t | FDR q | IC > 0 | Q5-Q1 | Monotonicity | Top-Q turnover | Positive years | Max reference corr | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `etf_skip20_momentum_120` | 5 | 0.0044 | 0.013 | 0.21 | 0.9627 | 50.8% | -0.0013 | -0.90 | 9.3% | 75% | 0.401 | reject |
| `etf_skip20_momentum_120` | 20 | 0.0034 | 0.011 | 0.09 | 0.9627 | 54.4% | -0.0025 | -0.60 | 9.3% | 50% | 0.401 | reject |
| `fip_smooth_momentum_skip5_60` | 5 | 0.0009 | 0.003 | 0.05 | 0.9627 | 52.1% | -0.0006 | -0.70 | 13.1% | 50% | 0.659 | reject |
| `fip_smooth_momentum_skip5_60` | 20 | -0.0111 | -0.038 | -0.32 | 0.9627 | 49.6% | -0.0009 | -0.40 | 13.1% | 50% | 0.659 | reject |
| `etf_skip5_momentum_60` | 5 | -0.0185 | -0.051 | -0.82 | 0.9627 | 49.5% | -0.0012 | -0.60 | 11.6% | 25% | 0.880 | reject and duplicate |
| `etf_skip5_momentum_60` | 20 | -0.0528 | -0.158 | -1.33 | 0.9627 | 43.2% | -0.0070 | -0.70 | 11.6% | 25% | 0.880 | reject and duplicate |

Every row had four usable calendar years. None survived FDR, none reached mean IC or ICIR thresholds, and every quintile spread was negative. The 5-day skip/60-day momentum candidate also exceeded the 0.85 historical-duplicate ceiling against `momentum_60` at 0.8801.

## Scheduler Decision

The closed 0.30 price-rotation budget is reallocated exactly as preregistered:

| Research family | Old budget | New budget | Change |
| --- | ---: | ---: | ---: |
| `cn_etf_price_rotation` | 0.30 | 0.00 | -0.30 |
| `cn_etf_liquidity_capacity` | 0.25 | 0.35 | +0.10 |
| `cn_etf_volatility_regime` | 0.20 | 0.30 | +0.10 |
| `cn_etf_flow_breadth_aggregation` | 0.15 | 0.20 | +0.05 |
| `cn_etf_fund_structure` | 0.10 | 0.15 | +0.05 |

The scheduler remains ready with four active primary families, total primary budget 1.00, no blockers, and no warnings. Direct CN stock moneyflow selection remains auxiliary-only with zero budget.

## Limitations

- The available ETF source ends on 2024-06-28, so it cannot support a fresh 2024-H2 through 2025 walk-forward decision.
- The prescreen establishes lack of statistical support in this sample; it does not prove that every conceivable price signal is impossible.
- Costs, capacity, regime robustness, and portfolio construction were intentionally not tested because no candidate passed the cheaper statistical gate.
- No profitability claim is made. The project remains research-to-paper only.

## Next Direction

Start the next preregistered batch in `cn_etf_liquidity_capacity`, the highest-budget active family. Focus on low-turnover liquidity, amount persistence, turnover stability, crowding, and capacity-aware signals using point-in-time ETF eligibility. Before any walk-forward or promotion decision, backfill and audit 2024-H2 through 2025 ETF history. Do not reopen price rotation or direct CN stock moneyflow selection.

Local generated evidence remains under `data/reports/cn_etf_skip_momentum_prescreen_20260716` and is intentionally excluded from Git.
