# CN Stock Factor Mining Work Report Rounds 1-86 - 2026-06-21

## Executive Summary

Current context:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Mandate: CN A-share stock cross-sectional alpha research, not ETF rotation
- Safety: research-to-review only; no broker, account, order, or live-trading actions

Headline status through Round86:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Current diagnostic leads: 2 public QVM translation leads only
- Current next direction: `round87_public_qvm_bottom_exclusion_costed_walk_forward`

The project has found repeated cross-sectional information, but not yet a robust deployable A-share stock factor. The main failure mode is now clear: positive IC or full-sample return often disappears once capacity, calendar holding, costs, overlap-adjusted Sharpe, walk-forward stability, drawdown, and benchmark-relative behavior are enforced.

## Round86 Work Completed

Round86 rotated away from the hibernated raw low-turnover line and added a capacity-safe public quality/value/momentum factor source:

- `public_qvm_value_momentum_lowvol_20`
- `public_qvm_dividend_quality_momentum_20`
- `public_qvm_value_reversal_quality_20`
- `public_qvm_lowbeta_value_momentum_20`

The implementation is reusable:

- New factor source: `daily_basic_public_quality_value_momentum`
- Pipeline support for the new source
- Experiment runner precompute support
- Project audit registry support
- Unit tests for factor construction, no-lookahead behavior, pipeline wiring, runner precompute, startup gate, and project audit

Round86 used full long-cycle authority data with:

- 2015-01-05 to 2025-12-31 sample
- TopN 100
- 20-bar holding horizon
- 5-bar rebalance cadence
- 10 bps cost
- 20 bps market impact
- 1% ADV max participation
- signal-date amount >= 10,000,000
- max calendar holding <= 60 days
- factor-matrix precompute/reuse enabled

## Round86 Results

| Factor | Total Return | Annual Return | Sharpe | Overlap Sharpe | Max DD | Win Rate | Relative Return | RankIC | IC t | Tail IC t | Calendar-Limited | Capacity-Limited | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `public_qvm_value_reversal_quality_20` | +91.21% | 3.71% | 0.419 | 0.226 | -47.71% | 51.11% | -2282.54% | 0.0724 | 9.43 | 1.40 | 204 | 0 | rejected |
| `public_qvm_lowbeta_value_momentum_20` | +74.10% | 3.07% | 0.363 | 0.197 | -49.79% | 50.49% | -2299.65% | 0.0693 | 8.93 | 1.81 | 201 | 0 | rejected |
| `public_qvm_dividend_quality_momentum_20` | +30.10% | 1.43% | 0.198 | 0.104 | -58.05% | 49.04% | -2343.64% | 0.0324 | 4.26 | 1.99 | 193 | 0 | rejected |
| `public_qvm_value_momentum_lowvol_20` | +24.11% | 1.18% | 0.169 | 0.090 | -60.22% | 49.89% | -2349.63% | 0.0321 | 4.34 | 1.69 | 210 | 0 | rejected |

Round86 good news:

- Capacity gate worked: all 4 cases had 0 capacity-limited trades.
- Maximum participation stayed around 0.15% ADV.
- The two best factors still had statistically positive full-sample RankIC.

Round86 bad news:

- No factor passed promotion gates.
- Overlap-adjusted Sharpe stayed below 0.23.
- Drawdowns were too large.
- Relative return versus the CN stock benchmark was deeply negative.
- Calendar-limited trades still appeared, so implementation quality is not clean enough.

## Best Historical Evidence So Far

| Area | Bright Data | Final Status |
|---|---|---|
| RSI/Bollinger technical baselines | RankIC about 0.047-0.049 | rejected for drawdown, tail, and capacity weakness |
| Data repair | false +91.71x return collapsed to +2.36x after adjusted-ratio repair | fake alpha correctly killed |
| Public price-volume formulas | `formula_pv_corr_reversal_20` RankIC about 0.076, t=10.88 | portfolio translation failed |
| Industry-neutral formula replay | neutral RankIC about 0.088-0.091, t near 49 | strong IC, weak portfolio Sharpe |
| Bottom-exclusion overlays | overlay t up to 8.46, positive rate about 70% | costed portfolios failed drawdown/Sharpe |
| Daily-basic residuals | neutral RankIC 0.042-0.056 | long-only conversion failed |
| Benchmark beta diagnostics | residual alpha t=4.39-5.42 | beta dominance too high |
| RSRS public indicator | `rsrs_reversal_18_60` total +72.07%, t=4.77 | walk-forward accepted folds 0/7 |
| SuperTrend public indicator | anti-SuperTrend neutral RankIC 0.0888, t=46.29 | walk-forward accepted folds 0/7 |
| Daily-basic low turnover raw | total return above +5000%, overlap Sharpe near 0.9-1.0 | rejected by Round84/85 tradeability checks |
| Public QVM composite | best RankIC 0.0724, t=9.43 with 0 capacity-limited trades | rejected by Sharpe, drawdown, relative return, and calendar gates |

## Recent Round Progression

| Round | Direction | Key Result | Decision |
|---:|---|---|---|
| 81 | Public SuperTrend/ATR signal audit | anti-SuperTrend neutral RankIC 0.0888, t=46.29; direct portfolios failed | no promotion; only bottom-exclusion lead |
| 82 | Anti-SuperTrend costed walk-forward exclusion | accepted folds 0/7; mean test overlap Sharpe -0.3693 | SuperTrend hibernated |
| 83 | Tushare daily-basic core alpha factory | `turnover_rate_low` +5127.61%, Sharpe 1.983; `turnover_rate_f_low` +5318.72%, Sharpe 1.872 | bright but contaminated; diagnostics required |
| 84 | Low-turnover capacity/extreme/calendar diagnostic | capacity breaches 1,437/1,641; max calendar holding 787 days | raw low-turnover promotion killed |
| 85 | Capacity-clean low-turnover replay | clean returns fell to +177.86%/+130.86%; overlap Sharpe 0.410/0.294 | low-turnover direct line hibernated |
| 86 | Public QVM capacity-safe replay | best +91.21%, Sharpe 0.419, RankIC 0.0724, but relative return -2282.54% | no promotion; 2 diagnostic translation leads |

## What Was Built Across These Rounds

Reusable research infrastructure now added or hardened:

- Long-cycle full-sample CN stock authority data workflow for 2015-2025.
- Startup gate and direction governance for each mining round.
- Three-round review cadence and ten-round sync/report cadence.
- Authority config loader consistency for large experiment-grid runs.
- Precomputed factor-matrix reuse for long-cycle grids.
- Public technical indicator families including RSRS and SuperTrend.
- Daily-basic alpha factory and public QVM composite factor source.
- Industry-neutral IC, bottom-exclusion overlay, benchmark-beta, and IC-to-portfolio gap diagnostics.
- Signal-date liquidity gate: `min_signal_amount`.
- Calendar holding gate: `max_calendar_holding_days`.
- Capacity and extreme-trade diagnostics.
- Decision rejection for capacity/calendar implementation failures.
- Project audit registration for the new QVM source.

## Why No Useful Factor Yet

The results are poor because the project is now testing more honestly:

- Full-sample return is not enough; low-turnover looked excellent until tradeability was enforced.
- IC is not enough; several families rank stocks correctly but fail long-only portfolio conversion.
- Public indicators often work better as loser-avoidance signals than direct buy signals.
- Benchmark-relative behavior matters; many absolute-positive strategies still badly underperform broad CN stock exposure.
- Naive Sharpe has repeatedly overstated quality; overlap-adjusted Sharpe is the harder and more useful number.
- Calendar-time realism matters for sparse-trading names; a 20-bar hold can become hundreds of calendar days without gates.

## Current Conclusion

As of Round86, the project has no deployable profitable factor. It does have useful research assets and a clearer failure map.

The most promising current thread is not to tune QVM weights or windows. It is to test whether the two QVM leads can work as bottom-exclusion or portfolio-construction filters:

- Freeze `public_qvm_value_reversal_quality_20`
- Freeze `public_qvm_lowbeta_value_momentum_20`
- Run costed bottom-exclusion / translation-layer walk-forward
- Require improved overlap-adjusted Sharpe, drawdown, relative return, and zero capacity/calendar blockers before any promotion discussion

If that fails, hibernate QVM and rotate families again.
