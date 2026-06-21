# CN ETF Range Contraction Composite Round41

Date: 2026-06-21

## Objective

Test whether lightweight liquidity and low-volatility tie-breakers improve the current best CN ETF lead, `formula_range_contraction_breakout_20`, under the Round38 risk setting.

This round intentionally did not expand to unrelated public indicators. It only compared:

- `formula_range_contraction_breakout_20`
- `formula_range_contraction_breakout_liquid_20`
- `formula_range_contraction_breakout_lowvol_20`
- `formula_range_contraction_breakout_liquid_lowvol_20`

## Implementation

Added three formula variants in `src/quant_robot/factors/public_formula_price_volume.py`:

- `formula_range_contraction_breakout_liquid_20`: base range-contraction score plus a small ADV z-score tie-breaker.
- `formula_range_contraction_breakout_lowvol_20`: base score plus a small low-tail-volatility tie-breaker.
- `formula_range_contraction_breakout_liquid_lowvol_20`: base score plus smaller liquidity and low-volatility tie-breakers.

All variants keep the same tradeable filter as the base formula.

TDD evidence:

- Added tests for registered names.
- Added tests that liquidity variant prefers a more liquid peer.
- Added tests that low-volatility variant prefers a smoother peer.
- Added tests that composite keeps illiquid and high-tail assets filtered.

## Preflight

Config: `configs/walk_forward_cn_etf_liquid_range_contraction_composite_round41_20260621.json`

Preflight cleared:

- Assets: 264 liquid CN ETFs.
- Dates: 1085.
- Folds: 4.
- Minimum rebalance opportunities: 26.
- Median rebalance opportunities: 26.
- Zero-allowed folds: 0.

## Walk-Forward Results

- Cases: 48.
- Accepted: 0.
- Rejected: 48.
- Positive Sharpe: 35/48.
- Positive annualized return: 34/48.
- Cases with at least 3 accepted folds: 23/48.
- No capacity-limited trades in the top rows.
- All rows remain blocked by adjusted IC significance.

Top rows:

| Case | Accepted Folds | Sharpe | Ann. Return | Relative Return | Win Rate | Max DD | Adj. IC p |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CN_ETF_formula_range_contraction_breakout_20_top5_cost5_reb10` | 4/4 | 1.8334 | 1.43% | 6.03% | 56.25% | -0.18% | 1.0 |
| `CN_ETF_formula_range_contraction_breakout_20_top10_cost5_reb10` | 3/4 | 1.5847 | 3.01% | 6.77% | 66.67% | -1.73% | 1.0 |
| `CN_ETF_formula_range_contraction_breakout_lowvol_20_top10_cost5_reb10` | 3/4 | 1.5688 | 2.95% | 6.74% | 64.58% | -1.75% | 1.0 |
| `CN_ETF_formula_range_contraction_breakout_liquid_20_top5_cost5_reb10` | 4/4 | 1.4785 | 1.21% | 5.93% | 54.17% | -0.19% | 1.0 |
| `CN_ETF_formula_range_contraction_breakout_liquid_20_top10_cost5_reb10` | 3/4 | 1.5283 | 2.83% | 6.68% | 64.58% | -1.75% | 1.0 |

Aggregate by factor:

| Factor | Cases | Positive Sharpe | Positive Ann. Return | Avg Sharpe | Avg Ann. Return | Avg Relative Return | Max Sharpe | Max Ann. Return | Max Accepted Folds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `formula_range_contraction_breakout_20` | 12 | 9 | 9 | 0.6897 | 1.13% | 5.87% | 1.8334 | 3.60% | 4 |
| `formula_range_contraction_breakout_liquid_20` | 12 | 9 | 9 | 0.4305 | 0.81% | 5.72% | 1.5283 | 3.19% | 4 |
| `formula_range_contraction_breakout_lowvol_20` | 12 | 9 | 8 | 0.1278 | 0.53% | 5.59% | 1.5688 | 2.95% | 4 |
| `formula_range_contraction_breakout_liquid_lowvol_20` | 12 | 8 | 8 | 0.0689 | 0.42% | 5.54% | 1.5064 | 2.74% | 4 |

Cost sensitivity:

| Cost | Cases | Positive Sharpe | Positive Ann. Return | Avg Sharpe | Avg Ann. Return | Avg Relative Return | Max Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 bps | 24 | 23 | 24 | 1.1265 | 1.61% | 6.10% | 1.8334 |
| 10 bps | 24 | 12 | 10 | -0.4681 | -0.16% | 5.26% | 0.8021 |

Direct comparison at the strongest base setting, Top5 / 5 bps / rebalance 10:

| Factor | Sharpe | Ann. Return | Relative Return | Win Rate | Max DD |
|---|---:|---:|---:|---:|---:|
| Base | 1.8334 | 1.43% | 6.03% | 56.25% | -0.18% |
| Liquid | 1.4785 | 1.21% | 5.93% | 54.17% | -0.19% |
| LowVol | 1.1976 | 0.81% | 5.74% | 50.00% | -0.19% |
| LiquidLowVol | 1.1734 | 0.93% | 5.79% | 50.00% | -0.22% |

## Interpretation

The composite variants did not improve the lead. Liquidity and low-volatility tie-breakers made the signal slightly more conservative, but reduced Sharpe and return in the key rows. The strongest factor remains the original `formula_range_contraction_breakout_20`.

The 5 bps cluster remains positive, but 10 bps rows deteriorate sharply. This keeps the signal research-only and cost-sensitive.

## Decision

Do not promote any Round41 factor.

Keep the new composite factor names registered as tested variants, but do not continue tuning their weights in the next round.

Round42 should run same-parameter replay / long-cycle replay for the original base lead, especially:

- `CN_ETF_formula_range_contraction_breakout_20_top5_cost5_reb10`
- `CN_ETF_formula_range_contraction_breakout_20_top10_cost5_reb10`
- `CN_ETF_formula_range_contraction_breakout_20_top5_cost5_reb5`
- `CN_ETF_formula_range_contraction_breakout_20_top10_cost5_reb5`
