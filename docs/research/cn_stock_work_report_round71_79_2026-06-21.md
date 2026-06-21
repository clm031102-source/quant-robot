# CN Stock Factor Mining Work Report - Rounds 71-79 - 2026-06-21

## Executive Summary

This report covers the office-desktop CN A-share stock factor-mining block from Round71 through Round79. The scope is CN stock cross-sectional alpha research, not CN ETF rotation and not live trading.

Headline result:

- Promotable profitable factors: 0.
- Paper-ready factors: 0.
- Immediate continuation candidates after Round79: 0.
- Registered public RSRS factor names: 4.
- Unique factor names directly evaluated in this block: 7.
- Direct case rows reviewed: at least 38, plus 7 rolling walk-forward folds in Round79.

The useful outcome is not a ready-to-trade factor. The useful outcome is that several tempting signals were blocked by stricter validation before they could become false positives. The work also produced reusable tooling for cash overlays, beta exposure, hedged-spread audit, public RSRS factors, and costed rolling walk-forward bottom-exclusion validation.

## What Changed In Direction

The block started with the existing public risk-filter bridge line. That line had weak but persistent relative-return hints, so Round71 to Round75 tested whether it could be translated into:

- static or dynamic cash overlays;
- benchmark beta diagnostics;
- fixed beta-hedged spreads;
- cost and impact stressed spreads.

After those failed, the line was hibernated instead of tuned further.

Round76 to Round79 rotated into a public RSRS family. The direct long-only RSRS variants failed, but `rsrs_reversal_18_60` showed a strong industry-neutral IC and a promising bottom-exclusion diagnostic. Round79 then tested the harder version: frozen parameters, long-cycle rolling train/test, costs, impact, capacity, and overlap-adjusted Sharpe. It failed that promotion gate, so the RSRS promotion path is now hibernated.

## Round Summary

| Round | Direction | Main Evidence | Decision |
|---:|---|---|---|
| 71 | Static cash overlay | Best `risk_filter_bridge_anti_obv_weighted_20`: total return 18.89%, relative return 19.62%, Sharpe 0.092, overlap-adjusted Sharpe 0.069, max DD -42.77%, positive relative folds 10/11 | rejected as alpha; risk-filter component only |
| 72 | Dynamic cash overlay | Best 120-day overlay risk-off 0.2: total return 11.39%, relative return 13.17%, overlap-adjusted Sharpe 0.0586, max DD -26.09%, positive relative folds 10/11 | rejected; drawdown improved but return stream weak |
| 73 | Benchmark beta exposure | Residual alpha t-stat 4.39-5.42 and residual Sharpe 0.62-0.76, but R2 0.992-0.994 | research lead only; mostly benchmark beta |
| 74 | Fixed beta-hedged spread | Cost-sign bug found and fixed; corrected best spread total return -12.91%, overlap-adjusted Sharpe -0.516 | rejected |
| 75 | Spread cost/impact stress | Best stressed spread total return -53.74%, overlap-adjusted Sharpe -1.701 | hibernate risk-filter bridge |
| 76 | Public RSRS pre-registration | Registered `rsrs_slope_18`, `rsrs_zscore_18_60`, `rsrs_right_skew_18_60`, `rsrs_reversal_18_60` | rotate to RSRS public-method family |
| 77 | RSRS long-cycle grid | 8/8 cases completed. Best direct row: `rsrs_reversal_18_60` top100 total return 72.07%, Sharpe 0.272, overlap-adjusted Sharpe 0.191, RankIC 0.0214, RankIC t=4.77 | rejected; one research lead |
| 78 | RSRS translation audit | `rsrs_reversal_18_60` industry-neutral RankIC 0.0253, t=24.00; bottom-exclusion overlay t=5.39, positive overlay rate 66.28% | no promotion; continue only into costed bottom-exclusion WF |
| 79 | RSRS bottom-exclusion walk-forward | 7 rolling test folds, 0 accepted; mean test total return 2.86%, mean relative return 0.46%, mean overlap-adjusted Sharpe 0.0766, worst test DD -17.90%, capacity-limited trades 0 | rejected; hibernate RSRS promotion paths |

## Bright Data Worth Looking At

These numbers are worth seeing because they explain where the research had real signal. None of them is promotion evidence by itself.

### 1. Round78 RSRS industry-neutral IC was strong

`rsrs_reversal_18_60`:

- Overall RankIC: 0.0214, t=15.97.
- Industry-neutral RankIC: 0.0253, t=24.00.
- Industry-neutral retention ratio: 1.18.

This means the signal was not merely an industry exposure artifact. That is the strongest statistical signal in this work block.

### 2. Round78 bottom-exclusion diagnostic was the best practical lead

`rsrs_reversal_18_60` as a bottom-exclusion overlay:

- Mean full-universe return: 0.9175%.
- Mean kept-universe return: 1.0210%.
- Mean bottom-quantile return: 0.5030%.
- Mean overlay excess: 0.1035%.
- Overlay t-stat: 5.39.
- Positive overlay rate: 66.28%.
- Kept compounded return: 362.69%.
- Full compounded return: 257.62%.
- Bottom compounded return: 24.21%.

This was the cleanest hint that RSRS may be better as a "do not buy the bottom bucket" filter than as a direct TopN buy factor.

### 3. Round79 showed the RSRS lead was not robust enough after harder validation

The same frozen RSRS bottom-exclusion lead was tested with 756 train days, 252 test days, 252-day rolling steps, 10 bps cost, 20 bps impact, 1% ADV max participation, and strict train/test date separation.

Result:

- Accepted folds: 0/7.
- Mean test total return: 2.86%.
- Mean test relative return: 0.46%.
- Mean test overlap-adjusted Sharpe: 0.0766.
- Worst test max drawdown: -17.90%.
- Mean test win rate: 51.47%.
- Capacity-limited trades: 0.
- Strict split violations: 0.

This is valuable negative evidence. Capacity and drawdown were not the blocker; the blocker was weak risk-adjusted return and zero accepted folds.

### 4. The best Round79 fold was positive, but not enough

Best absolute test fold:

- Test window: 2024-05-14 to 2025-05-28.
- Test total return: 16.45%.
- Test relative return: 0.91%.
- Test overlap-adjusted Sharpe: 0.3454.
- Test max drawdown: -7.77%.
- Test win rate: 61.79%.

Even this best fold stayed below the 0.5 overlap-adjusted Sharpe gate, so it cannot carry the candidate.

### 5. Round73 proved why beta diagnostics matter

The public risk-filter bridge had attractive residual-looking data:

- Residual alpha t-stat: 4.39-5.42.
- Residual Sharpe: 0.62-0.76.

But R2 was 0.992-0.994, meaning the return stream was almost completely explained by benchmark movement. The later hedged-spread tests confirmed that this was not an executable standalone alpha.

### 6. Round74 caught a serious backtest implementation bug

The beta-hedged spread initially looked much better before a short-leg cost-sign issue was found. After fixing it, the best corrected spread became:

- Total return: -12.91%.
- Overlap-adjusted Sharpe: -0.516.

This is an important engineering result because it directly prevented a false profitability claim.

### 7. Round77 had an attractive headline but failed the real gate

Best direct RSRS row:

- Factor: `rsrs_reversal_18_60`.
- Portfolio: top100.
- Total return: 72.07%.
- Sharpe: 0.272.
- Overlap-adjusted Sharpe: 0.191.
- RankIC: 0.0214.
- RankIC t-stat: 4.77.

The headline return looked interesting, but risk-adjusted return was too weak and direct long-only translation did not clear promotion.

## Engineering Work Completed

Reusable research modules and scripts added or extended:

- `src/quant_robot/ops/dynamic_cash_overlay_backtest.py`
- `scripts/run_dynamic_cash_overlay_backtest.py`
- `src/quant_robot/ops/benchmark_beta_exposure_audit.py`
- `scripts/run_benchmark_beta_exposure_audit.py`
- `src/quant_robot/ops/beta_hedged_spread_audit.py`
- `scripts/run_beta_hedged_spread_audit.py`
- `src/quant_robot/factors/public_rsrs.py`
- `src/quant_robot/ops/bottom_exclusion_walk_forward.py`
- `scripts/run_bottom_exclusion_walk_forward.py`

Configs and reports added:

- `configs/experiment_grid_cn_stock_public_rsrs_round76_20260621.json`
- `configs/experiment_grid_cn_stock_public_rsrs_reversal_translation_round78_20260621.json`
- Round71 to Round79 research reports under `docs/research/`
- Round79 walk-forward outputs under `data/reports/bottom_exclusion_walk_forward_public_rsrs_reversal_round79_20260621/`

Tests added or extended:

- `tests/unit/test_dynamic_cash_overlay_backtest.py`
- `tests/unit/test_benchmark_beta_exposure_audit.py`
- `tests/unit/test_beta_hedged_spread_audit.py`
- `tests/unit/test_public_rsrs_factors.py`
- `tests/unit/test_bottom_exclusion_walk_forward.py`
- `tests/unit/test_factor_mining_startup_gate_cli.py`

## Process Improvements Locked In

The startup gate now requires the next runs to confirm:

- CN stock scope only; do not mix this with ETF rotation evidence.
- Long-cycle same-parameter replay before profitability claims.
- Rolling walk-forward train/test split.
- Regime coverage and signal-window coverage.
- Look-ahead audit.
- Multiple-testing and overfit accounting.
- Cost, capacity, turnover, drawdown, and overlap-aware statistics.
- No promotion from IC alone.
- Translation-layer audit after strong IC but weak long-only results.
- Every 3 rounds: review, audit, direction adjustment.
- Every 10 rounds: lightweight packaging, validation, and safe GitHub sync review.
- Public-method references before burning more compute on a weak family.

## Why The Results Still Look Bad

The results look bad because the new gate is stricter than the old search behavior, and it is catching the right failures:

- IC can be statistically significant while the long-only portfolio is still weak.
- Relative return can be positive while absolute risk-adjusted return is too low.
- Cash overlays can reduce drawdown without creating alpha.
- Beta-adjusted diagnostics can look good until an executable hedge with realistic costs is tested.
- Public indicators can contain information but fail as a tradeable portfolio after costs and rolling OOS splits.
- Short-window or full-sample numbers can look interesting, but rolling walk-forward can still reject them.

This is not satisfying, but it is the right failure mode. It means the project is now less likely to promote a factor that only exists because of beta, overfitting, capacity blindness, or a coding mistake.

## Current Decision

Do not promote any factor from Round71 to Round79.

Hibernate these paths:

- public risk-filter bridge direct long-only;
- static or dynamic cash overlay as a standalone alpha improvement;
- fixed beta-hedged spread translation of the public risk-filter bridge;
- RSRS direct TopN;
- RSRS industry-neutral TopN as a promotion candidate;
- `rsrs_reversal_18_60` bottom-exclusion walk-forward;
- any RSRS window, quantile, or exposure tuning after the zero-accepted-fold Round79 result.

Keep only as low-priority references:

- RSRS reversal as evidence that industry-neutral IC and bottom-exclusion diagnostics can find real ranking information;
- risk-filter bridge as evidence that beta diagnostics must come before treating relative return as alpha.

## Next Work

Round80 should be a lightweight packaging and safe-sync boundary, then the project should rotate to a new public-method family:

`public_supertrend_exclusion_preregistration`

The next family should start with pre-registered hypotheses, not a broad blind grid:

- Use ATR/SuperTrend-style public trend state as a cross-sectional risk or exclusion signal.
- Test signal direction and reversal first.
- Run IC, industry-neutral IC, and bottom-exclusion diagnostics before portfolio expansion.
- Require costed walk-forward before any promotion claim.
- Stop after the next 3 rounds if the family repeats the same weak-risk-adjusted-return failure.

## Verification Evidence

Fresh verification run during this收口:

- Unit tests: 22 tests passed.
- Startup gate: cleared, blockers empty.
- Project audit: passed, no forbidden safety hits, config registry passed, Tushare and parquet readiness passed.
- Process check: no active factor-mining walk-forward process remained after Round79.
