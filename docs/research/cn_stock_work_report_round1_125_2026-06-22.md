# CN Stock Factor Mining Work Report Rounds 1-125 - 2026-06-22

## Current Mandate

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Scope: CN A-share stock cross-sectional alpha research
- Not scope: ETF rotation, broker connection, account reads, orders, or live trading
- Governance: review every 3 factor batches, package/sync every 10 batches

## Headline Result

Through Round125:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Current active research line: repaired low-turnover daily-basic engine
- Current actionable candidate: 1 frozen champion for a costed portfolio-conversion audit
- Current next direction: `round126_turnover_repair_champion_costed_portfolio_conversion`

This is not yet a profitable project result. The best current outcome is narrower and more useful: a raw high-return low-turnover anomaly that was previously blocked by capacity now has one capacity-clean repaired champion worth a costed TopN audit.

## Latest Round125 Result

Round125 audited the five Round124 turnover-repair research-lead rows:

| Metric | Value |
|---|---:|
| Input tests | 12 |
| Research-lead rows | 5 |
| Unique lead factor names | 3 |
| Raw-source clusters | 2 |
| Raw-clone rows | 4 |
| High-redundancy rows | 1 |
| Nonredundant new alpha rows | 0 |
| Capacity-clean rows through 5m notional | 5 |
| Costed portfolio conversion candidates allowed | 1 |
| Promotion allowed | 0 |

Champion:

| Factor | Horizon | IC | ICIR | t-stat | IC+ | Q5-Q1 | Mono | Top turnover | Max ADV participation at 5m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `turnover_rate_f_low_participation_budget_100k_20` | 20 | 0.1033 | 0.6485 | 33.35 | 75.35% | 0.0673 | 0.900 | 27.81% | 0.5000% |

Important interpretation:

- This champion is strong enough for one costed portfolio-conversion audit.
- It is not an independent new factor because raw-source correlation is 1.000.
- It should be treated as a capacity repair of `turnover_rate_f_low`, not as a fresh alpha family.

## Recent Work Arc

| Rounds | Work | Bright data | Decision |
|---|---|---|---|
| 91-99 | Tushare financial/profitability PIT path | 5,208 non-BJ symbols, 44 quarters, 229,152 planned requests, full100 shard 4,328 final rows, duplicate 0, PIT pass | data path useful; profitability IC screen had 0 multiple-testing leads |
| 101-103 | Capacity-safe price-volume low-vol/reversal family | Round102 processed 100,830,409 factor rows and 200,175,023 aligned rows; 1 strict lead | Round103 found high redundancy, hibernated standalone line |
| 104-108 | Trend/amount and inverse overheat line | Round107 found 1 lead: `overheat_avoidance_relative_strength_60`, IC 0.0417, ICIR 0.309, t 15.75 | Round108 hard redundancy blocked portfolio bridge |
| 110-112 | Market-residual risk premia | Round111 lead `beta_adjusted_range_contraction_60`: IC 0.0559, ICIR 0.371, t 18.89, Q5-Q1 0.1273, monotonicity 1.000 | 2015 weakness plus redundancy/exposure blocked promotion |
| 114-116 | Public Alpha101/Qlib-style methods | Round115 lead `qlib_alpha158_return_std_position_blend_20`: IC 0.0415, ICIR 0.323, t 16.68; all years 2015-2025 positive in Round116 | highly redundant with low-vol/reversal/liquidity cluster; promotion 0 |
| 118-120 | Incremental residual over known cluster | Round120 raw lead `range_contraction_incremental_residual_20`: IC 0.0548, ICIR 0.530, t 27.10 | fixed reference audit showed 0 true incremental leads |
| 122-125 | Low-turnover capacity repair | raw `turnover_rate_low` total 5127.61%, annual 21.25%, Sharpe 1.983; raw `turnover_rate_f_low` total 5318.72%, annual 19.86%, Sharpe 1.872; Round125 repaired champion capacity-clean through 5m | 1 frozen champion allowed for costed conversion; promotion 0 |

## Brightest Data So Far

1. Raw low-turnover return engine:

| Factor | Raw total | Annualized | Sharpe | Overlap Sharpe | Max DD | Win rate |
|---|---:|---:|---:|---:|---:|---:|
| `turnover_rate_low` | 5127.61% | 21.25% | 1.983 | 0.961 | -18.43% | 59.32% |
| `turnover_rate_f_low` | 5318.72% | 19.86% | 1.872 | 0.902 | -28.56% | 57.43% |

Why it was not promoted: capacity-limited trades were 1437 and 1641, and max participation was 166.67 and 8.80 before repair.

2. Repaired low-turnover prescreen:

| Factor | Horizon | IC | ICIR | t-stat | Q5-Q1 | Top turnover | Raw corr |
|---|---:|---:|---:|---:|---:|---:|---:|
| `turnover_rate_f_low_participation_budget_100k_20` | 20 | 0.1033 | 0.6485 | 33.35 | 0.0673 | 27.81% | 1.000 |
| `turnover_rate_low_participation_budget_100k_20` | 20 | 0.0973 | 0.5563 | 28.61 | 0.0648 | 23.20% | 1.000 |

Why it was not promoted: these are raw clones after dedup and still lack costed walk-forward portfolio evidence.

3. Public/Qlib lead:

| Factor | Horizon | IC | ICIR | t-stat | IC+ | Q5-Q1 | Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|
| `qlib_alpha158_return_std_position_blend_20` | 5 | 0.0415 | 0.323 | 16.68 | 63.4% | 0.01794 | 34.9% |

Bright point: every year from 2015 through 2025 had positive mean IC. Blocker: redundancy and episodic exposure.

4. Market-residual lead:

| Factor | Horizon | IC | ICIR | t-stat | IC+ | Q5-Q1 | Mono | Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `beta_adjusted_range_contraction_60` | 20 | 0.0559 | 0.371 | 18.89 | 67.1% | 0.1273 | 1.000 | 6.3% |

Bright point: clean ranking shape. Blocker: 2015 failure and exposure/redundancy.

5. Engineering throughput:

- Round102: 200,175,023 aligned factor-label rows.
- Round107: 198,871,948 aligned rows.
- Round111: 195,158,252 aligned rows.
- Round115: 301,552,533 aligned rows.
- Round124: 120,634,176 aligned factor-label rows.

The office desktop is now running long-cycle, high-volume, pre-registered screens instead of short-window parameter fishing.

## Why There Is Still No Usable Factor

The project has repeatedly found statistically active signals, but the usable-factor bar is higher:

- IC strength is not portfolio profitability.
- FDR significance is not enough when many families and parameters have been tested.
- Public technical signals repeatedly collapse into the same low-vol/reversal/liquidity cluster.
- Several good-looking lines are hidden exposure, beta, liquidity, or capacity artifacts.
- The strongest low-turnover returns were execution-dirty before Round125.
- No current candidate has passed costed TopN walk-forward, regime coverage, overlap-aware returns, and final holdout discipline.

## Process Improvements Completed

- Long-cycle 2015-2025 replay is mandatory before claims.
- 2026 is protected as final holdout.
- Preregistration is required before candidate generation.
- Every three rounds trigger review and family stop-loss.
- Every ten rounds trigger packaging/safe-sync review.
- Cost, capacity, turnover, extreme-return, redundancy, exposure, regime, and multiple-testing gates are explicit.
- Drawdown tolerance is separated from capacity. A 30% drawdown may be acceptable, but it cannot waive tradability or leakage gates.
- Round125 adds a new dedup and small-capital sensitivity gate so duplicate repair rows cannot be counted as new alpha.

## Next Work

Round126 should run one narrow audit:

`turnover_rate_f_low_participation_budget_100k_20`, horizon 20, frozen parameters.

Required checks:

- costed TopN portfolio conversion with realistic commissions/slippage;
- overlap-aware Sharpe and return statistics;
- capacity and participation stress for 100k, 500k, 1m, and 5m;
- regime and signal-window coverage;
- yearly/monthly stability;
- no parameter tuning after seeing results;
- no 2026 final holdout read.

If Round126 fails, the low-turnover repair line should be hibernated and the project should rotate rather than continue tuning the same family.

