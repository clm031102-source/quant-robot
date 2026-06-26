# CN Stock Round267 Forecast/Express Disagreement Preregistration

Round267 is a workflow-optimization and preregistration round, not a profitability claim.

## Scope

- Machine/task: `office_desktop` / `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market/scope: CN A-share stock cross-sectional alpha research
- Not scope: CN ETF rotation, broker/account/order access, live trading, final-holdout tuning

## What Changed

The candidate-plan gate now has a ninth required discovery control area:

- `source_sample_integrity`

It forces every future mining plan to declare:

- endpoint permission or cached source manifest;
- point-in-time available-date semantics;
- same-parameter 2015-2025 full-sample replay;
- train/test or walk-forward split;
- future-function/static leakage audit;
- rejected-hypothesis counting.

The promotion policy was also hardened to require data-source proof, full-sample regime coverage, future-function audit, Deflated Sharpe or FDR, CPCV or purged walk-forward, White Reality Check or multiple-test adjustment, parameter-sensitivity heatmap, and profit/drawdown/win-rate reporting before any promotion discussion.

## Direction

Round267 uses the Round255 forecast/express event cache as the source proof:

| Feed | Rows | Assets | Date range |
|---|---:|---:|---|
| forecast | 78,573 | 5,728 | 2015-01-01..2025-12-31 |
| express | 20,304 | 4,280 | 2015-01-06..2025-10-22 |

This does not revive the rejected standalone express-surprise or forecast-guidance lines. The new hypothesis is narrower:

Expectation changes may be underreacted to when later earnings express information disagrees with earlier forecast ranges, especially after industry-relative and style controls.

## Preregistered Candidates

| Candidate | Family | Status | Portfolio | Promotion |
|---|---|---|---:|---:|
| `event_forecast_express_disagreement_1q` | `forecast_express_disagreement_event` | pre_registered | false | false |
| `event_forecast_express_disagreement_industry_relative_1q` | `forecast_express_disagreement_event` | pre_registered | false | false |
| `event_forecast_express_stale_forecast_correction_1q` | `forecast_express_disagreement_event` | pre_registered | false | false |

## Candidate Plan Gate

- Config: `configs/factor_mining_candidate_plan_round267_forecast_express_disagreement_20260626.json`
- Gate output: `data/reports/round267_forecast_express_disagreement_candidate_plan_gate_20260626/factor_mining_candidate_plan_gate.json`
- Gate status: `research_ready`
- Candidates: 3
- Complete control areas: 9 / 9
- Blockers: none
- Research screen allowed: true
- Portfolio grid allowed: false
- Promotion allowed: false

## Next Action

Round268 may implement the PIT factor formulas and run the same-parameter 2015-2025 full-sample prescreen.

Required next checks:

- signal date uses the later available event date, shifted by `pit_lag_trade_days=1` and `execution_lag=1`;
- no same-day event trading;
- industry-neutral, size/liquidity-neutral, and residual IC;
- yearly and 2015 contribution breakout;
- quantile shape and top-quantile turnover;
- FDR or equivalent multiple-test control;
- no portfolio grid unless residual lead exists.

No factor, portfolio candidate, paper-ready signal, manual signal, or live signal was produced in Round267.
