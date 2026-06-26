# CN Stock Round264 Public Tradeable Indicator Composite Preregistration

## Scope

Round264 starts after the Round263 historical lead recovery audit rejected all old bright candidates. This round does not promote a factor and does not run a portfolio grid. It pre-registers a new, narrower public-indicator composite family and immediately validates the candidate plan gate.

Entrypoint:

```powershell
python scripts\run_public_tradeable_indicator_composite_preregistration.py --output-dir data\reports\round264_public_tradeable_indicator_composite_preregistration_20260626
```

Generated outputs:

- `public_tradeable_indicator_composite_preregistration.json`
- `public_tradeable_indicator_composite_preregistration.md`
- `public_tradeable_indicator_composite_candidates.csv`
- `factor_mining_candidate_plan_gate.json`
- `factor_mining_candidate_plan_gate.md`

## Result

| Metric | Value |
| --- | ---: |
| Pre-registered candidates | 8 |
| Candidate families | 4 |
| Candidate plan gate blockers | 0 |
| Portfolio grids allowed | 0 |
| Promotion allowed | 0 |

Candidate plan gate status: `research_ready`.

Next required gate:

`round265_public_tradeable_indicator_composite_long_cycle_residual_prescreen`

## Why This Direction

Round263 showed that historical high-return candidates were not recoverable:

- Round126 low-turnover repair had high total return but failed overlap Sharpe, drawdown, extreme-trade, and walk-forward gates.
- Alpha101 and main-force candidates failed quantile shape or weak ICIR checks.
- Qlib/market-residual candidates were too redundant with low-volatility, reversal, liquidity, and market-exposure references.

Round264 therefore does not re-enter single SuperTrend, OBV, Alpha101, low-turnover, or raw moneyflow grids. It tests public indicators only as fixed economic hypotheses inside compact composites:

- trend exhaustion and reversal;
- volume-price absorption;
- volatility compression breakout quality;
- risk-adjusted momentum quality.

## Candidates

| Factor | Family | Main Idea |
| --- | --- | --- |
| `mfi_cmf_exhaustion_reversal_liquid_14_20` | trend exhaustion/reversal | MFI and CMF exhaustion with liquidity and short reversal. |
| `supertrend_pullback_absorption_quality_10_3_20` | trend exhaustion/reversal | SuperTrend is only a state input, confirmed by volume absorption and ATR risk. |
| `obv_cmf_absorption_reversal_quality_20` | volume-price absorption | OBV/CMF absorption with downside-risk control. |
| `volume_dryup_pullback_liquid_reversal_5_20` | volume-price absorption | Pullback plus volume dry-up, with liquidity fixed up front. |
| `atr_bandwidth_compression_breakout_quality_20` | volatility compression | ATR/Bollinger compression plus path efficiency. |
| `donchian_atr_compression_breakout_efficiency_20` | volatility compression | Donchian location with ATR compression and path efficiency. |
| `adx_efficiency_momentum_quality_14_20` | risk-adjusted momentum | ADX trend strength with path efficiency and low volatility. |
| `macd_rsi_momentum_exhaustion_quality_14_26` | risk-adjusted momentum | MACD/RSI reclaim quality, not threshold tuning. |

## Gates Before Any Portfolio Test

Round265 must be a long-cycle residual prescreen, not a portfolio backtest.

Required metrics:

- long-cycle raw IC;
- industry-neutral IC;
- size/liquidity/volatility residual IC;
- quantile spread and monotonicity;
- factor turnover;
- public-reference overlap;
- 2015 regime contribution;
- capacity participation;
- final-holdout exclusion.

Promotion remains blocked until walk-forward, costs, capacity, regime coverage, overlap-adjusted statistics, parameter sensitivity, multiple-testing control, and final-holdout read-once rules are satisfied.

## Decision

Round264 completed preregistration only.

Next direction:

`round265_public_tradeable_indicator_composite_long_cycle_residual_prescreen`

Blocked re-entry remains active for:

- single SuperTrend / public trend-volume grids;
- Round126 low-turnover repair;
- Alpha101 rank price-volume direct grids;
- Qlib Alpha158 direct grids;
- raw smart-money-flow reference grids;
- market residual range-contraction grids without a new orthogonal thesis.
