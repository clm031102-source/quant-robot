# CN Stock Round450 Entry Limit Down Formal Rebuild

Date: 2026-06-27

Scope: formalize the Round449 entry-known `entry_limit_down` projection as a
cohort-entry-timed execution rule on the delayed-exit simulation shortlist. This
is research-to-review only. The 2026 final holdout remains sealed.

## Why This Round Exists

Round449 found that trades blocked at entry by
`limit_down_like;limit_down_official` had negative contribution in the frozen
low-turnover trade tape. That result was only a projection. Round450 rebuilt the
rule inside the cohort-entry-timed generator so the cash decision is applied
before cohort aggregation, volatility targeting, self-risk, and paper-readiness
checks.

This is an execution-risk rule, not an independent alpha factor.

## Reusable Support Added

Files:

- `src/quant_robot/ops/simulation_shortlist_cohort_entry_timed.py`
- `scripts/run_simulation_shortlist_cohort_entry_timed.py`
- `tests/unit/test_simulation_shortlist_cohort_entry_timed.py`
- `tests/unit/test_simulation_shortlist_cohort_entry_timed_cli.py`

New API/CLI support:

- Python parameter: `entry_attribute_cash_rules`
- CLI argument: `--entry-attribute-cash-rule`
- Rule used in this round:
  `entry_limit_down=entry_blocked_reasons:eq:limit_down_like;limit_down_official`

Behavior:

- matching trade rows are marked as `entry_attribute_cash_filter`;
- matching trades have pre-overlay contribution set to cash/zero before cohort
  grouping;
- the JSON summary records `entry_attribute_cash_trade_count` and
  `entry_attribute_cash_rule_counts`;
- existing Dragon cash, public-factor tilt, volatility target, and self-risk
  overlays remain compatible.

## Formal Rebuild Input

Command family:

`python scripts\run_simulation_shortlist_cohort_entry_timed.py --entry-attribute-cash-rule "entry_limit_down=entry_blocked_reasons:eq:limit_down_like;limit_down_official" ...`

Output:

`data/reports/round450_24h_profit_sprint_entry_limit_down_formal_rebuild_20260627`

Key inputs:

- trade source:
  `data/reports/round432_24h_profit_sprint_delayed_exit_return_repair_20260627/delayed_exit_trade_rows.csv`
- delayed-exit return column: `delayed_exit_weighted_return`
- delayed-exit date column: `delayed_exit_date`
- public factor: `alpha101_open_close_pressure_fade_10`, bottom 10%,
  exposure multiplier 1.50
- target annual volatility: 8%
- lookback events: 84
- self-risk: prior 21 closed events sum below 0 maps exposure to 0.80

## Full-Sample Result

Candidate:

`round450_delayed_exit_m150_entry_limit_down_cash`

Formal summary:

- entry-attribute cash trades: 178
- cohort count: 1,113
- unique exit-date count: 905
- Dragon cash trades: 360
- public tilt trades: 2,420
- missing public-factor share: 0.00%
- paper-readiness blockers: none

Metrics:

| Metric | Base `round432_delayed_exit_m150` | Entry-limit-down formal rebuild | Delta |
|---|---:|---:|---:|
| Annualized return | 6.663% | 6.829% | +0.165% |
| Total return | +218.46% | +227.43% | +8.97% |
| Sharpe | 0.968 | 0.995 | +0.027 |
| Overlap-adjusted Sharpe | 0.496 | 0.515 | +0.019 |
| Max drawdown | -26.21% | -24.88% | +1.34% |
| Win rate | 41.33% | 41.33% | +0.00% |
| Leave-one-year min annualized | 5.001% | 5.011% | +0.010% |
| Leave-one-year min overlap Sharpe | 0.425 | 0.432 | +0.007 |
| Best-month log share | 45.72% | 44.65% | -1.07% |

Full sample favors the entry-limit-down rebuild on ordinary metrics.

## OOS Split Audit

Output:

`data/reports/round450_24h_profit_sprint_entry_limit_down_formal_oos_20260627`

OOS split audit does not favor the rebuild:

| Metric | Base | Entry-limit-down |
|---|---:|---:|
| Mean OOS annualized return | 10.043% | 10.018% |
| Mean OOS overlap Sharpe | 0.831 | 0.830 |
| Worst OOS drawdown | -19.30% | -19.38% |
| OOS strict pass rate | 90.00% | 90.00% |
| Positive OOS rate | 90.00% | 90.00% |

The base candidate is still the OOS winner by a small margin.

## Incremental Robustness

Output:

`data/reports/round450_24h_profit_sprint_entry_limit_down_formal_incremental_robustness_20260627`

Incremental robustness versus base:

- CPCV annualized-win rate: 68.33%
- CPCV overlap-win rate: 68.33%
- CPCV drawdown-win rate: 64.17%
- CPCV strict-pass rate: 60.83%
- CPCV max-drawdown-floor pass rate: 92.50%
- bootstrap annualized-win rate: 78.50%
- bootstrap overlap-win rate: 85.70%
- bootstrap drawdown-win rate: 86.90%
- bootstrap strict-pass rate: 44.50%
- bootstrap max-drawdown-floor pass rate: 64.10%
- year win rate: 36.36%

The bootstrap profile says this is a useful repair candidate. The year win rate
says it is not strong enough to call a broad independent edge.

## Beta And Statistical Reality

Beta audit output:

`data/reports/round450_24h_profit_sprint_entry_limit_down_formal_beta_20260627`

CSI500 beta-adjusted diagnostics slightly favor the rebuild:

- alpha annualized: 7.516%
- alpha t-stat: 4.415
- CSI500 beta: 0.047
- beta R2: 0.266
- hedged annualized return: 7.573%
- hedged overlap Sharpe: 0.800
- hedged max drawdown: -13.86%

Statistical reality output:

`data/reports/round450_24h_profit_sprint_entry_limit_down_formal_stat_reality_20260627`

The two-row reality check has both base and entry-limit-down passing deflated
Sharpe and FDR. This supports statistical acceptability of the rebuilt lane, but
it is not proof of incremental alpha because the base lane also passes and the
incremental year win rate is weak.

## Decision

Round450 promotes 0 new independent alpha factors.

`entry_limit_down` is allowed as a paper-simulation comparison observation if
the simulation stage wants an execution-risk variant. It should not replace the
current default because:

- OOS mean annualized return is slightly weaker than base;
- OOS mean overlap Sharpe is slightly weaker than base;
- worst OOS drawdown is slightly weaker than base;
- incremental year win rate is only 36.36%;
- the rule fixes an execution-risk pocket rather than creating a separate
  return engine.

Default remains:

`paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`

Process rule: do not keep tuning entry/exit tradeability strings. The next
mining work should rotate to a genuinely different point-in-time factor family
with economic rationale, then run long-sample, OOS, cost, beta, concentration,
and statistical-reality checks before any handoff discussion.

## Verification

Commands run:

- `python -m unittest tests.unit.test_simulation_shortlist_cohort_entry_timed tests.unit.test_simulation_shortlist_cohort_entry_timed_cli`
- `python -m unittest tests.unit.test_simulation_shortlist_cohort_entry_timed tests.unit.test_simulation_shortlist_cohort_entry_timed_cli tests.unit.test_shortlist_trade_attribute_cash_filter tests.unit.test_shortlist_public_factor_source tests.unit.test_simulation_shortlist_paper_handoff`

Both passed.

Safety: research-to-review only. No broker connection, no account reads, no
orders, and no live trading.
