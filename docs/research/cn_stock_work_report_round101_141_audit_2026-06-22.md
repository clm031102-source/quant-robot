# CN Stock Factor Mining Work Report and Audit - Rounds 101-141

Date: 2026-06-22

## Scope

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stock cross-sectional factor research
- Not in scope: ETF rotation, broker connection, account reads, order placement, live trading
- Final holdout: 2026 data must remain unread until a clean OOS/paper gate exists

## Executive Conclusion

Rounds 101-140 produced several statistically interesting research leads, but produced:

| Category | Count |
|---|---:|
| Promotable profitable factors | 0 |
| Paper-ready factors | 0 |
| Manual/live usable factors | 0 |
| Current active empirical candidate | 0 |
| Research leads worth remembering | 6-8, depending on whether duplicate horizons are counted |

The work was not empty. It found useful signal clusters, repaired several methodological problems, and built reusable gates. But as of this report, no factor has survived the full chain of long-cycle evidence, cost, capacity, data quality, redundancy, walk-forward, regime/stress, and holdout discipline.

Round141 was started as the required clean walk-forward after Round140. During收口 I found a validation-design issue: the first Round141 implementation re-anchored the 20-day rebalance schedule inside each fold, so it was not strictly the same calendar strategy. I fixed the code to use a fixed global rebalance calendar and verified the unit/regression tests, but the true full-data rerun was intentionally interrupted by the user. Therefore Round141 has engineering readiness, not final empirical evidence.

## Round Arc

| Rounds | Direction | Brightest Evidence | Audit Decision |
|---|---|---|---|
| 101-103 | Capacity-safe price-volume low-vol/reversal | Round102 processed 100,830,409 factor rows and 200,175,023 aligned rows; found 1 strict lead | Hibernated standalone line due redundancy |
| 104-108 | Trend/amount and inverse overheat | `overheat_avoidance_relative_strength_60`: IC 0.0417, ICIR 0.309, t-stat 15.75 | Hard redundancy blocked portfolio bridge |
| 110-112 | Market-residual risk premia | `beta_adjusted_range_contraction_60`: IC 0.0559, ICIR 0.371, t-stat 18.89, Q5-Q1 0.1273, monotonicity 1.000 | 2015 weakness plus exposure/redundancy blocked promotion |
| 114-116 | Public Alpha101/Qlib-style methods | `qlib_alpha158_return_std_position_blend_20`: IC 0.0415, ICIR 0.323, t-stat 16.68; all years 2015-2025 positive | Redundant with low-vol/reversal/liquidity cluster |
| 118-120 | Incremental residual over known cluster | Raw `range_contraction_incremental_residual_20`: IC 0.0548, ICIR 0.530, t-stat 27.10 | Fixed reference audit found 0 true incremental leads |
| 122-126 | Low-turnover repair and costed portfolio conversion | Raw low-turnover returns exceeded 5000%; repaired champion IC 0.1033, ICIR 0.6485, t-stat 33.35 | Round126 costed TopN conversion rejected all 12 cases |
| 127-130 | Public multi-family and Alpha101 rank PV reversal | 20 candidates, 9 families, 60 tests; `alpha101_rank_pv_reversal_liquid_20` 20d IC 0.0489, ICIR 0.526, t-stat 23.85 | Residual IC turned negative; PV/Alpha101 reversal cluster hibernated |
| 131-134 | Daily-basic non-price public carry | `daily_basic_free_float_supply_quality_20` strict-clean residual: IC 0.0361, ICIR 0.5546, t-stat 13.43 | Allowed one constrained portfolio conversion only |
| 135-137 | Daily-basic stress-guard preflight and data audit | Round136 showed huge apparent returns | Round137 found mixed adjusted/unadjusted price-basis phantom alpha |
| 138-140 | Price-basis repair, event audit, event-adjusted clean rerun | Round140 best clean preflight: total 21.31%, annual 18.99%, Sharpe 0.820, overlap Sharpe 1.043, max DD -16.37%, OOS overlap Sharpe 5.165, extreme trades 0 | Still not promotable; required clean walk-forward |
| 141 | Clean walk-forward framework | Fixed global rebalance-calendar implementation and tests | Full empirical rerun not completed before收口 |

## Brightest Data

### 1. Raw Low-Turnover Return Engine

| Factor | Total Return | Annualized | Sharpe | Overlap Sharpe | Max DD | Win Rate |
|---|---:|---:|---:|---:|---:|---:|
| `turnover_rate_low` | 5127.61% | 21.25% | 1.983 | 0.961 | -18.43% | 59.32% |
| `turnover_rate_f_low` | 5318.72% | 19.86% | 1.872 | 0.902 | -28.56% | 57.43% |

Audit: not worthless, but not usable. Round126 showed the costed portfolio path had best overlap-adjusted Sharpe only 0.226, max drawdown around -69.55%, and extreme trade diagnostics too large to ignore.

### 2. Repaired Low-Turnover Champion

| Factor | Horizon | IC | ICIR | t-stat | IC+ | Q5-Q1 | Top Turnover | Max ADV Participation at 5m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `turnover_rate_f_low_participation_budget_100k_20` | 20 | 0.1033 | 0.6485 | 33.35 | 75.35% | 0.0673 | 27.81% | 0.5000% |

Audit: strong research lead, but raw-source correlation was 1.000 and costed portfolio conversion failed.

### 3. Public/Qlib Lead

| Factor | Horizon | IC | ICIR | t-stat | IC+ | Q5-Q1 | Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|
| `qlib_alpha158_return_std_position_blend_20` | 5 | 0.0415 | 0.323 | 16.68 | 63.4% | 0.01794 | 34.9% |

Audit: useful public-method evidence, but redundant with the same low-vol/reversal/liquidity cluster.

### 4. Public Alpha101 Rank PV Reversal

| Factor | Horizon | IC | ICIR | t-stat | IC+ | Q5-Q1 | Mono | Top Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `alpha101_rank_pv_reversal_liquid_20` | 20 | 0.0489 | 0.526 | 23.85 | 69.1% | 0.0089 | 0.900 | 17.5% |
| `alpha101_rank_pv_reversal_liquid_20` | 10 | 0.0453 | 0.496 | 22.55 | 69.8% | 0.0057 | 0.900 | 17.5% |
| `alpha101_rank_pv_reversal_liquid_20` | 5 | 0.0431 | 0.471 | 21.44 | 68.4% | 0.0037 | 0.900 | 17.5% |

Audit: the positive evidence disappeared after residualizing against the existing PV/Alpha101 cluster. The family was hibernated.

### 5. Daily-Basic Free-Float Supply Quality

| Stage | Key Evidence | Audit |
|---|---|---|
| Round132 raw | IC 0.0392, ICIR 0.3113, t-stat 7.54 | Research lead only |
| Round133 residual | IC 0.0345, ICIR 0.5259, t-stat 12.73 | Residual survived neutralization |
| Round134 strict-clean residual | IC 0.0361, ICIR 0.5546, t-stat 13.43, IC+ 75.77% | Allowed one portfolio preflight |
| Round136 pre-audit portfolio | 1212.90% total in best stress-guard case | Contaminated by price-basis and extreme-trade issues |
| Round140 event-adjusted clean rerun | Best clean preflight: 21.31% total, 18.99% annual, Sharpe 0.820, overlap Sharpe 1.043, max DD -16.37%, OOS overlap Sharpe 5.165, extreme trades 0 | Clean enough for walk-forward, not promotion |

Audit: this is the current best-looking clean lead, but it is stress-guard dependent, has short daily-basic history starting 2023-07-03, and still needs the corrected Round141 fixed-calendar walk-forward rerun.

## Engineering and Process Improvements

- Long-cycle replay is now mandatory before claims.
- The project separated CN stock factor mining from CN ETF rotation.
- 2026 final holdout discipline is explicit.
- Three-round review and audit cadence is now documented.
- Ten-round packaging/sync cadence is documented, but data outputs remain forbidden for Git.
- Public Alpha101/Qlib/supertrend/RSRS style hypotheses were included as sources, but not treated as proof.
- Multiple-testing accounting, redundancy checks, capacity, costs, drawdown, overlap-adjusted Sharpe, extreme trades, and stress/regime gates are now explicit.
- Round137/138 identified and repaired mixed adjusted/unadjusted price-basis phantom alpha.
- Round139 deduped 156 true-close extreme trade rows into 15 unique event paths.
- Round140 removed all 15 event paths before portfolio construction.
- Round141 code was corrected so walk-forward validation keeps a fixed global rebalance calendar instead of re-anchoring each fold.

## Why Nothing Is Usable Yet

1. High total return was repeatedly not enough. The low-turnover line looked excellent on total return but failed after costed portfolio conversion, overlap-aware Sharpe, drawdown, and extreme-trade checks.
2. IC was repeatedly not enough. Several factors had good IC/t-stat, but translated poorly into a tradable TopN path or collapsed under redundancy/residual audits.
3. Public formulas produced signals, but many were members of an already crowded low-vol/reversal/liquidity cluster.
4. The strongest daily-basic factor has real statistical evidence, but its usable history starts in 2023 and its portfolio evidence is still preflight-only.
5. Extreme data artifacts were a major source of false optimism. The project caught a serious mixed price-basis bug before promotion.
6. Multiple-testing risk is large. Many families, horizons, costs, and capital levels were tested, so only out-of-sample/walk-forward survivors should be trusted.
7. Walk-forward is not optional. The corrected Round141 empirical run remains the next gate.

## Current State

Completed and verified in code:

- Round140 event-adjusted clean rerun module, CLI, tests, report.
- Round141 fixed-calendar clean walk-forward module, CLI, tests.
- Startup gate updated through Round140/Round141 direction.

Verification evidence from收口:

- `python -m unittest tests.unit.test_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward tests.unit.test_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_cli`: 3 tests OK.
- Extended regression set covering Round139/140/141 and startup gate: 12 tests OK.
- `python -m py_compile src\quant_robot\ops\daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward.py scripts\run_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward.py`: exit 0.
- No background `python` process was running after the user interruption.

Not completed:

- Corrected Round141 full-data walk-forward rerun. The first run was superseded because it re-anchored rebalance dates; the corrected rerun was interrupted before completion.
- No commit or push was performed in this收口 because the user asked for report/audit first and the worktree contains many untracked code/docs plus generated data outputs that require sync policy review before GitHub push.

## Audit Judgment

The work direction improved substantially after the user challenged the process. Earlier work spent too much time around moneyflow/price-volume-like families and could have rotated faster. The later rounds are more professional:

- hypotheses are preregistered,
- failed families are hibernated,
- public methods are used as idea sources,
- long-cycle and multiple-testing rules are explicit,
- cost/capacity/data-quality gates are hard,
- and the current daily-basic lead is being forced through a proper clean walk-forward gate.

But the project still has no deployable alpha. The correct management decision is:

1. Do not promote anything.
2. Do not tune the daily-basic free-float supply quality line further until the corrected Round141 fixed-calendar walk-forward run completes.
3. If corrected Round141 fails accepted folds, hibernate this family and rotate.
4. If corrected Round141 passes, only then run final paper gate/holdout discipline; still no live/manual trading.
5. Keep separating CN stock factor mining from ETF rotation. ETF rotation should use ETF-specific data and portfolio logic, not CN stock cross-sectional factors unless intentionally used as a market-breadth overlay.

## Next Concrete Action

When work resumes, run exactly:

```powershell
python scripts\run_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward.py
```

Expected decision rule:

- If accepted candidates = 0: hibernate daily-basic free-float supply quality and rotate family.
- If accepted candidates > 0: do not promote; run paper gate/final holdout protocol only once.

