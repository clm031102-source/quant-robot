# CN Stock Three-Round Review Rounds 84-86 - 2026-06-21

## Scope

This review is the required 3-round governance checkpoint after Rounds 84, 85, and 86.

Machine/task/branch:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Scope: CN A-share stock cross-sectional alpha
- Not scope: CN ETF rotation, live trading, broker/account/order actions

## Round Summary

| Round | Direction | Result | Useful Evidence | Decision |
|---:|---|---|---|---|
| 84 | Low-turnover capacity/extreme/calendar diagnostic | raw Round83 low-turnover returns found contaminated | capacity-limited trades 1,437/1,641; max calendar holding 787 days | raw low-turnover promotion killed |
| 85 | Capacity-clean low-turnover replay | clean returns collapsed from +5000% to +177.86%/+130.86% | IC stayed strong but overlap Sharpe only 0.410/0.294; still capacity/calendar blockers | low-turnover direct line hibernated |
| 86 | Public QVM capacity-safe replay | 4/4 QVM direct TopN cases rejected | capacity clean, best RankIC 0.0724 t=9.43, second RankIC 0.0693 t=8.93 | QVM direct TopN rejected; 2 diagnostic leads to Round87 |

## Promotion Count

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Research leads carried forward after Round86: 2 diagnostic-only QVM translation leads
  - `public_qvm_value_reversal_quality_20`
  - `public_qvm_lowbeta_value_momentum_20`

## What Improved

Rounds 84-86 materially improved the research process:

- capacity breaches are no longer only flagged after the fact;
- signal-date liquidity can now be enforced before TopN selection;
- calendar holding drift is visible and can reject candidates;
- the project stopped promoting raw full-sample return when tradeability failed;
- QVM introduced a capacity-clean public-anomaly family instead of another low-turnover sweep;
- project audit now recognizes the QVM factor source.

## Bright Data That Did Not Survive

### Round83 Raw Low-Turnover Headline

The strongest raw results entering this review were:

- `turnover_rate_low`: +5127.61% total return, Sharpe 1.983, overlap Sharpe 0.961, RankIC 0.1028.
- `turnover_rate_f_low`: +5318.72% total return, Sharpe 1.872, overlap Sharpe 0.902, RankIC 0.1079.

Round84 showed why this was not usable:

- capacity-limited trades: 1,437 and 1,641;
- extreme >5x trade returns: 19 for each;
- maximum calendar holding: 787 days;
- participation breaches up to 166.67x ADV.

### Round85 Capacity-Clean Replay

After process gates:

| Factor | Clean Total Return | Sharpe | Overlap Sharpe | Max DD | Relative Return | Calendar-Limited | Capacity-Limited | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `turnover_rate_low` | +177.86% | 0.755 | 0.410 | -34.63% | -2195.89% | 205 | 1 | rejected |
| `turnover_rate_f_low` | +130.86% | 0.582 | 0.294 | -44.97% | -2242.88% | 332 | 1 | rejected |

The IC remained real, but the tradable portfolio failed.

### Round86 Public QVM

Round86 was cleaner on capacity but weak on portfolio quality:

| Factor | Total Return | Sharpe | Overlap Sharpe | Max DD | Relative Return | RankIC | Capacity-Limited | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `public_qvm_value_reversal_quality_20` | +91.21% | 0.419 | 0.226 | -47.71% | -2282.54% | 0.0724 | 0 | rejected |
| `public_qvm_lowbeta_value_momentum_20` | +74.10% | 0.363 | 0.197 | -49.79% | -2299.65% | 0.0693 | 0 | rejected |

The positive evidence was ranking information, not profitable long-only implementation.

## Main Failure Pattern

Rounds 84-86 confirm the same structural pattern:

1. IC and raw full-sample returns can be impressive.
2. The return engine often comes from illiquidity, sparse trading, or broad CN beta.
3. Once the implementation is forced through capacity, calendar, cost, overlap, and benchmark-relative gates, the strategy quality collapses.
4. Daily-basic valuation/liquidity proxies are not a substitute for true profitability and quality data.

## Direction Adjustment

Stop:

- low-turnover direct TopN;
- low-turnover parameter/window rescue;
- QVM direct long-only promotion;
- QVM weight/window expansion;
- treating capacity-clean but low-Sharpe portfolios as useful factors.

Continue:

- bottom-exclusion translation only for the two frozen QVM leads in Round87;
- process gates for signal-date amount, capacity, calendar holding, and overlap-aware Sharpe;
- family rotation after failed translation.

## Next Round

Round87 should be:

`round87_public_qvm_bottom_exclusion_costed_walk_forward`

Budget stop-loss:

If Round87 has 0 accepted folds or negative/weak overlap-adjusted Sharpe, hibernate QVM and rotate to a true profitability-quality data readiness audit instead of tuning QVM parameters.
