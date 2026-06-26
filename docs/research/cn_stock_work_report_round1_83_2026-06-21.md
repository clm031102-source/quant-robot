# CN Stock Factor Mining Work Report Rounds 1-83 - 2026-06-21

## Executive Summary

This report summarizes the office-desktop CN stock factor-mining work through Round83.

Machine and branch:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`

Current mandate:

- Mine CN A-share stock cross-sectional alpha factors.
- Do not evaluate this branch as CN ETF rotation.
- Research-to-review only: no broker connection, no account reads, no order placement, no live trading.

Headline result:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Current active research leads: 2 diagnostic-only low-turnover leads
  - `turnover_rate_low`
  - `turnover_rate_f_low`
- Next direction: `round84_daily_basic_low_turnover_capacity_extreme_trade_diagnostic`

The day still produced useful work: false positives were killed faster, the SuperTrend family was hibernated after a costed walk-forward failure, the Tushare daily-basic long-cycle data path was verified, the alpha factory authority-config loader gap was fixed, and the first genuinely bright long-cycle daily-basic numbers surfaced. Those numbers are not tradable yet because they are capacity- and extreme-trade contaminated.

## Measured Scope

From local project artifacts as of Round83:

- Research docs under `docs/research`: more than 100 markdown files.
- Experiment-grid configs under `configs`: dozens of reusable configs.
- CN stock factor names in grids: more than 60 across baselines, public indicators, Tushare daily-basic, moneyflow, residuals, bridges, and translation tests.
- Round83 core replay: 12 daily-basic factors, 12 completed, 0 failed, 0 no-trade.
- Round80 last cloud sync: commit `c54fe106d56bf0745ad9ae09077e3ab3980dc95c`.

These are not 60 profitable factors. Most are controlled experiments, baselines, translations, rejected hypotheses, or data-quality checks. The correct profitable promotion count remains 0.

## What Was Done Recently

### Round81: SuperTrend Signal-Direction Audit

Round81 tested three pre-registered public SuperTrend/ATR-style factors:

| Factor | Total Return | Sharpe | Overlap Sharpe | Max DD | RankIC | RankIC t | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| `supertrend_volume_confirmed_10_3_20` | -65.67% | -0.4707 | -0.3203 | -80.81% | -0.0659 | -9.28 | rejected |
| `anti_supertrend_volume_confirmed_10_3_20` | -12.42% | -0.0269 | -0.0178 | -62.34% | 0.0659 | 9.28 | rejected |
| `supertrend_volume_capacity_strict_10_3_20` | +0.56% | 0.0416 | 0.0281 | -47.75% | -0.0160 | -1.53 | rejected |

Bright data:

- `anti_supertrend_volume_confirmed_10_3_20` industry-neutral RankIC 0.0888, t=46.29.
- Bottom-exclusion overlay t=7.00.
- Positive overlay rate 68.82%.
- Bottom bucket compounded return -99.33%, versus kept compounded return -62.65%.

Decision:

- No direct SuperTrend factor is promotable.
- Anti-SuperTrend is only a bottom-tail avoidance lead.
- Round82 must run one frozen costed walk-forward exclusion test.

### Round82: Anti-SuperTrend Costed Walk-Forward

Round82 ran the frozen anti-SuperTrend bottom-exclusion test:

- Factor: `anti_supertrend_volume_confirmed_10_3_20`
- Folds: 7
- Accepted folds: 0
- Mean test total return: -2.21%
- Mean test relative return: +1.81%
- Mean test overlap-adjusted Sharpe: -0.3693
- Worst test max drawdown: -22.00%
- Mean test win rate: 47.22%
- Capacity-limited trades: 0

Decision:

- SuperTrend family hibernated.
- Do not run more SuperTrend windows, quantiles, or exposure tuning.

### Round83: Tushare Daily-Basic Core Replay

Round83 verified full daily-basic coverage:

- Bar rows: 8,416,451
- Daily-basic rows: 10,700,940
- Date range: 2015-01-05 to 2025-12-31
- Data blockers: none
- Warning: `extreme_return_rows_present`

The first monolithic alpha-factory path was too slow for the large authority config, so the common research loader was fixed to accept authority bars config files. The completed replay used the experiment-grid path with factor precomputation and research-input reuse.

Round83 core replay result:

- Factors: 12
- Completed: 12
- Failed: 0
- No-trade: 0
- Promotable: 0

The two brightest rows:

| Factor | Total Return | Annual Return | Sharpe | Overlap Sharpe | Max DD | Win Rate | Mean RankIC | IC t | Relative Return | Capacity Limited | Extreme Flag |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `turnover_rate_low` | +5127.61% | 21.25% | 1.983 | 0.961 | -18.43% | 59.32% | 0.1028 | 14.99 | +2753.86% | 1437 | true |
| `turnover_rate_f_low` | +5318.72% | 19.86% | 1.872 | 0.902 | -28.56% | 57.43% | 0.1079 | 17.03 | +2944.97% | 1641 | true |

Why they are not usable yet:

- Both have many capacity-limited trades.
- Both have extreme trade flags.
- Their capacity-aware large-market variants are much weaker:
  - `turnover_rate_f_low_large_mv`: overlap Sharpe 0.279, relative return -2293.81%, capacity-limited trades 0.
  - `turnover_rate_low_large_mv`: overlap Sharpe 0.244, relative return -2306.96%, capacity-limited trades 0.

Decision:

- Keep `turnover_rate_low` and `turnover_rate_f_low` as diagnostic leads only.
- No promotion before extreme-trade attribution, capacity-clean replay, and walk-forward validation.

## Historical Bright Data

These are the most important signals found across the previous rounds. They matter because they show where signal exists, even though portfolio translation has failed so far.

| Source | Bright Evidence | Why It Matters | Why Not Promoted |
|---|---|---|---|
| Rounds 1-3 public technical | `rsi_reversal_14` Sharpe 0.349, RankIC 0.0467; `bollinger_reversal_20` RankIC 0.0487 | baseline mean-reversion has signal | drawdown -75% to -96%, tail/capacity failure |
| Rounds 4-6 data repair | false `value_low_turnover_low_tail_20` return collapsed from 91.71 to 2.36 after adjusted-ratio repair | blocked fake alpha | post-repair relative return still weak |
| Rounds 11-16 public formulas | `formula_pv_corr_reversal_20` RankIC about 0.076, t=10.88; `formula_volume_contraction_reversal_20` RankIC about 0.080, t=10.25 | formulaic price-volume ranking works statistically | 12/12 and 8/8 strong-IC cases had IC-to-portfolio gaps |
| Round58 industry-neutral formulas | `formula_volume_contraction_reversal_20` neutral RankIC 0.0910, t=49.41; `formula_pv_corr_reversal_20` neutral RankIC 0.0879, t=49.86 | signal survives industry neutralization | best portfolio Sharpe 0.3134, overlap Sharpe 0.1771 |
| Round60 bottom-exclusion overlay | `formula_pv_corr_reversal_20` overlay t=8.19, positive rate 68.43% | strong loser-avoidance signal | costed exclusion drawdown later -56.52% |
| Rounds 55-57 risk filters | overlay t up to 8.46, positive rate 70.34% | bottom-exclusion repeatability | costed portfolio Sharpe below 0.20 |
| Round64 daily-basic residuals | neutral RankIC 0.0556, 0.0546, 0.0425 | Tushare daily-basic contains cross-sectional information | long-only conversion failed |
| Round73 beta diagnostics | residual alpha t=4.39-5.42, residual Sharpe 0.62-0.76 | some spread signal after benchmark control | R2 0.992-0.994 showed beta dominance |
| Round74 engineering | fixed short-leg cost-sign bug; corrected spread Sharpe -0.516 | prevented false positive promotion | no alpha after corrected cost accounting |
| Round77 RSRS | `rsrs_reversal_18_60` total +72.07%, RankIC 0.0214, t=4.77 | public RSRS had ranking evidence | Round79 accepted folds 0/7 |
| Round81 anti-SuperTrend | neutral RankIC 0.0888, t=46.29; overlay t=7.00 | newest public indicator bottom-tail signal | Round82 walk-forward accepted folds 0/7 |
| Round83 low turnover | `turnover_rate_low` total +5127.61%, overlap Sharpe 0.961; `turnover_rate_f_low` total +5318.72%, overlap Sharpe 0.902 | strongest long-cycle raw daily-basic evidence so far | capacity-limited and extreme-trade contaminated |

## Main Failure Pattern

The project repeatedly finds ranking information, especially in loser avoidance:

- IC and RankIC are often positive.
- Industry-neutral IC often survives.
- Bottom buckets are often bad.
- Excluding weak tails often improves relative behavior.

The project has not yet found a deployable long-only stock factor because:

- top bucket returns often do not beat benchmark after costs;
- broad retained portfolios still carry too much beta and drawdown;
- capacity limits remove the most attractive raw signals;
- overlap-adjusted Sharpe is far below naive Sharpe;
- walk-forward folds reject full-sample or diagnostic positives;
- data-quality and extreme-return gates correctly block suspicious profits.

## Engineering Output

Reusable project improvements now in place:

- Startup gate for CN stock scope.
- Three-round review and ten-round sync governance.
- Data manifest with daily-basic coverage and adjusted-ratio checks.
- Authority bars config for 2015-2025 long-cycle replay.
- Research loader support for authority config files.
- IC-to-portfolio gap audit.
- Industry-neutral IC audit.
- Industry-neutral portfolio selector.
- Bottom-exclusion overlay audit.
- Costed bottom-exclusion walk-forward.
- Benchmark beta exposure audit.
- Beta-hedged spread audit and cost-sign correction.
- Public RSRS and SuperTrend factor families.
- Daily-basic core alpha-factory grid config with precomputed factor matrix reuse.
- Tests updated for authority config loading and current startup-gate governance.

## Current Conclusion

The most useful current lead is not a finished factor. It is a question:

> Can the low-turnover daily-basic anomaly survive after removing capacity-limited and extreme-trade contamination?

If yes, this becomes the first serious candidate line in a while.

If no, the low-turnover line should be hibernated just like SuperTrend, RSRS, and public formula bottom-exclusion lines.

Next action:

`round84_daily_basic_low_turnover_capacity_extreme_trade_diagnostic`

Do not push it toward paper/live until capacity-clean replay and walk-forward validation pass.
