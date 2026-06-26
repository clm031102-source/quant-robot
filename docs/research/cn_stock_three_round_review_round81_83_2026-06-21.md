# CN Stock Three-Round Review Rounds 81-83 - 2026-06-21

## Scope

This review is the required 3-round governance checkpoint after Rounds 81, 82, and 83.

Machine/task/branch:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Scope: CN A-share stock cross-sectional alpha
- Not scope: CN ETF rotation, live trading, broker/account/order actions

## Round Summary

| Round | Direction | Result | Useful Evidence | Decision |
|---:|---|---|---|---|
| 81 | Public SuperTrend/ATR signal-direction audit | 3/3 direct cases rejected | Anti-SuperTrend neutral RankIC 0.0888, t=46.29; bottom-exclusion overlay t=7.00 and positive rate 68.82% | direct SuperTrend rejected; anti only as bottom-exclusion lead |
| 82 | Anti-SuperTrend bottom-exclusion costed walk-forward | 1/1 rejected, accepted folds 0/7 | Mean test relative return +1.81%, capacity-limited trades 0 | SuperTrend family hibernated; no more windows/quantiles |
| 83 | Tushare daily-basic core alpha factory replay | 12/12 completed, 12/12 rejected | `turnover_rate_low` total +5127.61%, Sharpe 1.983, overlap Sharpe 0.961; `turnover_rate_f_low` total +5318.72%, Sharpe 1.872, overlap Sharpe 0.902 | low-turnover lead requires capacity/extreme-trade diagnostic before any promotion |

## Promotion Count

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Research leads carried forward: 2 diagnostic leads
  - `turnover_rate_low`
  - `turnover_rate_f_low`

## Why Round81-82 Was Correctly Stopped

Round81 found that the raw SuperTrend direction was wrong for direct buying. The inverse/anti signal had strong ranking and bottom-tail evidence, but this was exactly the kind of "IC exists, portfolio fails" pattern seen earlier in the project.

Round82 froze the only justifiable follow-up and ran it through a costed walk-forward exclusion test:

- Folds: 7
- Accepted folds: 0
- Mean test total return: -2.21%
- Mean test relative return: +1.81%
- Mean test overlap-adjusted Sharpe: -0.3693
- Worst test max drawdown: -22.00%
- Capacity-limited trades: 0

Decision: hibernate SuperTrend. Do not tune windows, quantiles, or exposure. This was the first meaningful improvement over earlier behavior: the project did rotate families after a failed line instead of continuing to dig.

## Why Round83 Is Interesting But Not Yet Useful

Round83 found the strongest raw long-cycle numbers seen in this recent sequence:

- `turnover_rate_low`
  - Total return: +5127.61%
  - Annual return: 21.25%
  - Sharpe: 1.983
  - Overlap-adjusted Sharpe: 0.961
  - Max drawdown: -18.43%
  - Win rate: 59.32%
  - Mean RankIC: 0.1028
  - IC t-stat: 14.99
  - Relative return: +2753.86%
  - Capacity-limited trades: 1437
  - Extreme trade flag: true

- `turnover_rate_f_low`
  - Total return: +5318.72%
  - Annual return: 19.86%
  - Sharpe: 1.872
  - Overlap-adjusted Sharpe: 0.902
  - Max drawdown: -28.56%
  - Win rate: 57.43%
  - Mean RankIC: 0.1079
  - IC t-stat: 17.03
  - Relative return: +2944.97%
  - Capacity-limited trades: 1641
  - Extreme trade flag: true

These are bright data, but not promotion data.

The capacity-clean variants show the problem:

- `turnover_rate_f_low_large_mv`: 0 capacity-limited trades, but overlap-adjusted Sharpe only 0.279 and relative return -2293.81%.
- `turnover_rate_low_large_mv`: 0 capacity-limited trades, but overlap-adjusted Sharpe only 0.244 and relative return -2306.96%.

Interpretation:

The low-turnover anomaly may be real in the raw cross-section, but the strongest version is likely concentrated in names where execution/capacity/data-tail risk is unacceptable. The tradable version is not proven.

## Reject-Reason Review

Main reject reasons across Round81-83:

- Direct public trend signals failed direction and drawdown.
- Bottom-exclusion signals improved relative behavior but failed walk-forward acceptance.
- Raw low-turnover daily-basic signals passed headline return/Sharpe but failed capacity/extreme-trade cleanliness.
- Capacity-aware low-turnover variants were cleaner but lost most of the return engine.

## Direction Adjustment

Stop:

- SuperTrend direct long-only work.
- SuperTrend anti-exclusion continuation after 0/7 accepted folds.
- Monolithic full alpha-factory replay on the slow entrypoint for large authority configs.
- Raw low-turnover promotion claims before capacity and extreme-trade attribution.
- More TopN/window sweeps on daily-basic before the low-turnover anomaly is explained.

Continue:

- Low-turnover diagnostics only, with frozen parameters.
- Authority config loader consistency, because the slow alpha factory path exposed an entrypoint mismatch.
- Batch-sliced experiment-grid execution for large long-cycle replays.

## Next Round

Round84 should be:

`round84_daily_basic_low_turnover_capacity_extreme_trade_diagnostic`

Minimum required checks:

- extreme-trade contribution audit for `turnover_rate_low` and `turnover_rate_f_low`;
- capacity-limited trade attribution by date, asset, ADV, and return contribution;
- capacity-clean replay that blocks trades breaching the 1% ADV rule instead of merely flagging them;
- industry/size-neutral IC check for the two low-turnover leads;
- rolling walk-forward only after capacity-clean replay still has positive overlap-adjusted Sharpe and acceptable drawdown.

Budget stop-loss:

If the capacity-clean replay collapses below 0.5 overlap-adjusted Sharpe or remains deeply negative relative to benchmark, hibernate the raw low-turnover line and rotate to a different data family rather than tuning around it.
