# CN Stock 24h Profit Sprint - Round450-452 Audit

Date: 2026-06-27

Machine: office_desktop

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: audit the Round450/451 `entry_limit_down` formal rebuild and cost-stress work, then reset the next mining direction before continuing the 24h sprint.

## Executive Decision

Round450-452 promotes 0 new independent alpha factors.

`entry_limit_down` is useful as an execution-risk simulation comparison lane, not as a new return alpha and not as a default replacement. The full-sample and beta-hedged metrics improved, but OOS mean annualized return and OOS overlap Sharpe still slightly trail the matching base lanes. The rule should not be widened into more entry/exit tradeability-string tuning.

The active default remains:

`paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`

## Round450 Formal Rebuild

Round450 moved `entry_limit_down` from projection to cohort-entry execution:

- rule: `entry_limit_down=entry_blocked_reasons:eq:limit_down_like;limit_down_official`;
- candidate: `round450_delayed_exit_m150_entry_limit_down_cash`;
- entry-attribute cash trades: 178;
- annualized return: 6.829% versus 6.663% base;
- total return: +227.43% versus +218.46% base;
- overlap-adjusted Sharpe: 0.515 versus 0.496 base;
- max drawdown: -24.88% versus -26.21% base;
- mean OOS annualized return: 10.018% versus 10.043% base;
- mean OOS overlap Sharpe: 0.830 versus 0.831 base;
- incremental year-win rate: 36.36%.

Interpretation: this is a real execution repair, but the OOS comparison does not justify promoting it as alpha or replacing the default.

## Round451 Cost Stress

20 bps:

- candidate annualized return: 6.228% versus 6.060% base;
- candidate overlap Sharpe: 0.475 versus 0.456 base;
- candidate max drawdown: -25.83% versus -28.07% base;
- candidate mean OOS annualized return: 9.108% versus 9.132% base;
- candidate mean OOS overlap Sharpe: 0.757 versus 0.759 base;
- incremental year-win rate: 36.36%.

30 bps VT7.5:

- candidate annualized return: 5.590% versus 5.415% base;
- candidate overlap Sharpe: 0.435 versus 0.416 base;
- candidate max drawdown: -27.40% versus -29.66% base;
- candidate mean OOS annualized return: 8.177% versus 8.197% base;
- candidate mean OOS overlap Sharpe: 0.684 versus 0.684 base;
- incremental year-win rate: 63.64%.

Interpretation: heavier costs make the execution rule more attractive as a risk repair, especially on drawdown. It still does not become a new alpha source because OOS return/overlap do not beat the matched base.

## Failure Mode Caught

The line was close to becoming parameter drift:

- Round449 found a projection lead.
- Round450 rebuilt the one clean entry-known rule correctly.
- Round451 cost-stressed the same rule.
- Round452 stops the adjacent-search expansion before it becomes entry/exit string mining.

This matters because more variants such as exit-limit filters, board filters, metadata-missing filters, and industry blacklists would mostly be full-sample contribution tuning unless they have an ex ante, point-in-time rationale and a clean rebuild.

## Direction Reset

Immediate hibernations for the next work block:

- no more `entry_blocked_reasons` or `exit_blocked_reasons` string-neighborhood tuning;
- no RSRS or SuperTrend variants unless a new point-in-time source changes coverage or hypothesis;
- no PB/PS/PE threshold widening;
- no industry blacklist promotion from full-sample contribution;
- no daily-basic free-float salvage during this 24h sprint;
- no old northbound/margin revival without a new independent data-quality proof.

Allowed next work:

- use the startup gate and candidate-plan gate before any new mining batch;
- prefer a genuinely different point-in-time information source with an economic story;
- require full-sample, OOS, cost, beta, multiple-testing, and incremental robustness checks before shortlist promotion;
- keep 2026 final holdout sealed until the final designated review.

## Outcome

New independent alpha factors: 0

New paper-simulation observation lane: 1, `entry_limit_down_execution_rule_candidate`

Primary conclusion: stop this family now. It improved execution realism but did not uncover a standalone profitable factor. The next sprint action should be a gated, pre-registered search in a different point-in-time family rather than additional repairs on the same tradeability strings.
