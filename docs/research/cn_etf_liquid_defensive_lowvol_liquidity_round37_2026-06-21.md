# CN ETF Liquid Defensive Low-Vol/Liquidity Round37

Date: 2026-06-21

## Objective

Test public, economically grounded defensive ETF rotation signals instead of continuing weak moneyflow/theme paths:

- `low_volatility_20`, `low_volatility_60`: negative realized volatility.
- `high_liquidity_20`, `high_liquidity_60`: negative Amihud illiquidity.

The goal was to check whether low-volatility or high-liquidity ETF selection can produce a robust standalone rotation edge after costs, or should only be kept as a risk/capacity component.

## Preflight

Initial 10/20-day rebalance-only design was blocked by the ETF validation preflight because each OOS fold had only 13 rebalance opportunities, below the project minimum of 20.

Final preflight-cleared design added 5-day rebalance as a power check while keeping 10/20-day rebalance for stability and cost sensitivity:

- Assets: 264 liquid CN ETFs.
- Dates: 1085.
- Folds: 4.
- Minimum allowed rebalance opportunities: 26.
- Median allowed rebalance opportunities: 26.
- Zero-allowed fold count: 0.

## Configuration

- Config: `configs/walk_forward_cn_etf_liquid_defensive_lowvol_liquidity_round37_20260621.json`
- Output: `data/reports/walk_forward_cn_etf_liquid_defensive_lowvol_liquidity_round37_20260621`
- Factor source: `technical`
- Costs: 5 bps, 10 bps.
- TopN: 5, 10.
- Rebalance intervals: 5, 10, 20.
- Total cases: 48.
- Hypothesis adjustment: 48 cases.

## Results

All 48 cases were rejected. No case had positive Sharpe.

Top rows by leaderboard rank:

| Case | Accepted Folds | Sharpe | Ann. Return | Relative Return | Win Rate | Max DD | Adj. IC p |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CN_ETF_low_volatility_20_top10_cost5_reb20` | 2/4 | -0.0399 | 0.13% | 5.42% | 58.33% | -0.46% | 1.0 |
| `CN_ETF_high_liquidity_60_top10_cost5_reb20` | 3/4 | -0.1207 | -1.30% | 4.71% | 45.83% | -3.78% | 1.0 |
| `CN_ETF_low_volatility_60_top10_cost5_reb20` | 1/4 | -0.4125 | -0.20% | 5.26% | 54.17% | -0.49% | 1.0 |
| `CN_ETF_high_liquidity_20_top10_cost5_reb20` | 2/4 | -0.3505 | -1.87% | 4.44% | 50.00% | -2.94% | 1.0 |

Aggregate by factor:

| Factor | Cases | Positive Sharpe | Positive Ann. Return | Avg Sharpe | Avg Ann. Return | Avg Relative Return | Max Sharpe |
|---|---:|---:|---:|---:|---:|---:|---:|
| `low_volatility_20` | 12 | 0 | 1 | -3.5332 | -2.10% | 4.34% | -0.0399 |
| `high_liquidity_60` | 12 | 0 | 0 | -2.2535 | -4.19% | 3.32% | -0.1207 |
| `high_liquidity_20` | 12 | 0 | 0 | -2.1558 | -4.39% | 3.22% | -0.3505 |
| `low_volatility_60` | 12 | 0 | 0 | -4.2191 | -2.19% | 4.30% | -0.4125 |

Cost sensitivity:

| Cost | Cases | Positive Sharpe | Positive Ann. Return | Avg Sharpe | Avg Ann. Return | Avg Relative Return |
|---:|---:|---:|---:|---:|---:|---:|
| 5 bps | 24 | 0 | 1 | -1.5975 | -2.08% | 4.34% |
| 10 bps | 24 | 0 | 0 | -4.4833 | -4.34% | 3.25% |

Rebalance sensitivity:

| Rebalance | Cases | Positive Sharpe | Positive Ann. Return | Avg Sharpe | Avg Ann. Return | Avg Relative Return |
|---:|---:|---:|---:|---:|---:|---:|
| 5 days | 16 | 0 | 0 | -3.6542 | -5.11% | 2.87% |
| 10 days | 16 | 0 | 0 | -3.2199 | -3.10% | 3.85% |
| 20 days | 16 | 0 | 1 | -2.2471 | -1.43% | 4.66% |

## Interpretation

This family is defensive rather than alpha-producing. It improves relative return versus `CN_ETF_XSHG_510300`, especially at 20-day rebalance and Top10, but absolute returns and Sharpe remain unacceptable after costs.

The best row, `low_volatility_20_top10_cost5_reb20`, is close to cash-like with tiny drawdown and positive relative return, but it has:

- negative Sharpe,
- only 2/4 accepted folds,
- adjusted IC p-value of 1.0,
- no evidence that predictive ranking power survives multiple testing.

## Decision

Do not promote any Round37 factor.

Keep `low_volatility_*` and `high_liquidity_*` as reusable infrastructure for:

- risk overlays,
- capacity filters,
- tie-breakers,
- composite factor construction.

Do not continue standalone defensive low-vol/high-liquidity mining in the next block. Round38 should return to the best current research lead, `formula_range_contraction_breakout_20`, and test whether it survives a risk/regime state overlay rather than pure parameter expansion.
