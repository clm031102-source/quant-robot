# CN Stock Round456 User Drawdown Tolerance Paper Priority Audit

Date: 2026-06-27

Machine: office_desktop

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: re-rank current candidates under the user's stated preference: high total return and annualized return can justify a drawdown close to 30%, as long as hard gates on PIT, execution, costs, capacity, and simulation-readiness remain intact.

## Executive Decision

Round456 produces 0 new independent alpha factors.

It does produce 1 important simulation-stage decision: the highest-return paper-ready candidate is now explicitly identified as:

`paper_ready_cohort_entry_timed_range_q20_m175_cost10_vt08_max100_self_roll21_x08`

This does not replace the conservative default in the handoff. It creates a separate high-return primary candidate for paper-simulation comparison, which better matches the user's stated drawdown tolerance.

## Engineering Output

The paper handoff tool now reports both:

- `default_candidate_id`: role-based default lane;
- `primary_high_return_candidate_id`: highest annualized return among ready-for-paper-simulation candidates.

Files changed:

- `src/quant_robot/ops/simulation_shortlist_paper_handoff.py`
- `tests/unit/test_simulation_shortlist_paper_handoff.py`

This prevents a high-return paper-ready candidate from being hidden by a lower-risk role label such as `diagnostic`.

## Current Simulation-Candidate Ranking

Command:

`python scripts\run_simulation_shortlist_ranker.py --config configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json --repo-root . --output-dir data\reports\round456_24h_profit_sprint_user_drawdown_tolerance_ranker_20260627 --max-user-drawdown -0.30 --min-oos-strict-pass-rate 0.75 --duplicate-correlation 0.98`

Result:

- candidate count: 17
- eligible observation candidates: 7
- near-duplicate streams: 9
- blocked candidates: 1
- best research observation: `primary_high_return_dragon_hot_chase_alpha101_openclose_tilt_m150_self_roll21`

Best research observation metrics:

- annualized return: 7.524%
- total return: +232.15%
- overlap-adjusted Sharpe: 0.645
- Sharpe: 1.229
- max drawdown: -16.45%
- mean OOS annualized return: 8.05%
- OOS strict pass rate: 90%
- beta-hedged annualized return: 7.49%

Interpretation: this remains the best research observation, but the paper-simulation handoff must be judged only among paper-ready candidates.

## Current Paper-Ready Ranking

Command:

`python scripts\run_simulation_shortlist_paper_handoff.py --config configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json --repo-root . --output-dir data\reports\round456_24h_profit_sprint_user_drawdown_tolerance_paper_handoff_20260627 --max-user-drawdown -0.30 --min-oos-strict-pass-rate 0.75`

Result:

- handoff candidates: 8
- ready for paper simulation: 5
- blocked: 3
- role-based default: `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08`
- primary high-return candidate: `paper_ready_cohort_entry_timed_range_q20_m175_cost10_vt08_max100_self_roll21_x08`

Highest-return paper-ready candidate metrics:

- annualized return: 7.723%
- total return: +280.30%
- overlap-adjusted Sharpe: 0.512
- max drawdown: -29.31%
- win rate: 42.10%
- mean OOS annualized return: 11.739%
- OOS strict pass rate: 90%
- blockers: none under the -30% paper-handoff gate

Comparison to the role-based default:

- default annualized return: 6.663%
- default total return: +218.46%
- default overlap-adjusted Sharpe: 0.496
- default max drawdown: -26.21%
- default mean OOS annualized return: 10.043%
- default OOS strict pass rate: 90%

The high-return lane adds about +1.06 percentage points annualized and +61.84 percentage points total return, while taking about -3.10 percentage points deeper full-sample drawdown. Under the user's soft 30% tolerance, that tradeoff is worth testing in paper simulation.

## Caveats

This is still not a final promoted alpha:

- Round455 showed current shortlist streams are highly correlated, so this is not an independent blend;
- Round445 already warned that the range q20 lane is aggressive and weaker under heavier-cost stress;
- 2026 final holdout remains sealed;
- paper simulation must still check execution, capacity, slippage, position sizing, and operational stability.

## Round456 Output

- new independent alpha factors: 0
- new paper-simulation candidate identities: 0
- new high-return paper-simulation priority: 1
- reusable process improvement: 1

## Next Direction

Round457 should harden the high-return paper candidate for simulation entry:

- confirm event schema and file availability;
- compare role-based default versus high-return primary on paper-handoff fields;
- stress the high-return lane under cost/capacity/execution assumptions already available;
- keep the conservative default as a comparison lane.

Do not use this as a reason to resume range-parameter widening. The next action is simulation readiness, not another same-family grid.
