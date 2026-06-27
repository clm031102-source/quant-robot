# CN Stock Round458 Simulation Paper Ops Package

Date: 2026-06-27

Machine: office_desktop

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: build a repeatable research-to-paper operations package for the current default paper lane and the user's preferred high-return paper lane.

## Executive Decision

Round458 promotes 0 new independent alpha factors.

It produces 1 reusable simulation-readiness artifact:

`data/reports/round458_24h_profit_sprint_simulation_paper_ops_package_20260627`

The package status is `paper_ops_package_ready`, with 0 blockers and 2 ready paper lanes.

This is not final promotion evidence. It is a paper-observation operating package only. The 2026 final holdout remains sealed, and no broker, account, order, or live-trading boundary is crossed.

## Paper Lanes

| Lane | Candidate | Annualized | Total | Overlap Sharpe | Max DD | OOS pass | Role |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline comparison | `paper_ready_delayed_exit_m150_cost10_vt08_max100_self_roll21_x08` | 6.663% | +218.46% | 0.496 | -26.21% | 90% | default_10bps |
| Primary high-return observation | `paper_ready_cohort_entry_timed_range_q20_m175_cost10_vt08_max100_self_roll21_x08` | 7.723% | +280.30% | 0.512 | -29.31% | 90% | diagnostic |

The high-return lane is intentionally kept as a paper-observation lane, not as the conservative default and not as a final promoted alpha.

## Risk Controls

The package carries these explicit monitoring flags:

- user drawdown tolerance: -30%
- high-return lane drawdown: -29.31%, close to the user limit
- cost-stress worst drawdown: -32.04%, below the user limit
- capacity clean through 20x AUM under the 5% ADV participation cap
- capacity not clean from 50x AUM
- extreme trade contribution share: about 35.21%
- shortlist return streams remain highly correlated, so blend expansion is blocked
- high-return lane lacks beta-hedged metrics in the current handoff row

## Engineering Output

New reusable files:

- `src/quant_robot/ops/simulation_paper_ops_package.py`
- `scripts/run_simulation_paper_ops_package.py`
- `tests/unit/test_simulation_paper_ops_package.py`

The package builder inputs:

- simulation paper handoff JSON
- trade capacity stress JSON
- extreme trade profile JSON
- simulation blend audit JSON
- current shortlist config

The package writer outputs:

- `simulation_paper_ops_package.json`
- `simulation_paper_ops_package.md`
- `simulation_paper_ops_lanes.csv`
- `simulation_paper_ops_commands.csv`

## Command

`python scripts\run_simulation_paper_ops_package.py --config configs\cn_stock_profit_sprint_simulation_shortlist_20260627.json --paper-handoff data\reports\round456_24h_profit_sprint_user_drawdown_tolerance_paper_handoff_20260627\simulation_paper_handoff.json --capacity-stress data\reports\round457_24h_profit_sprint_range_q20_capacity_stress_20260627\trade_capacity_stress_summary.json --extreme-trade-profile data\reports\round457_24h_profit_sprint_range_q20_extreme_trade_profile_20260627\extreme_trade_profile.json --blend-audit data\reports\round455_24h_profit_sprint_simulation_blend_audit_20260627\simulation_shortlist_blend_audit.json --output-dir data\reports\round458_24h_profit_sprint_simulation_paper_ops_package_20260627 --max-user-drawdown -0.30 --min-oos-strict-pass-rate 0.75`

## Round458 Output

- new independent alpha factors: 0
- new promoted simulation candidates: 0
- new paper operations package: 1
- paper lanes ready for observation: 2
- blockers: 0

## Next Direction

Round459 should complete a three-round audit for Round456 through Round458 before more mining.

After the audit, rotate away from same-family range widening. The next useful search is an independent cached PIT source or a genuinely different public technical family, with the current default and high-return lanes kept as simulation baselines.
