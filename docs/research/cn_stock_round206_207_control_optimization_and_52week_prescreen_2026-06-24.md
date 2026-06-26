# CN Stock Round206-207 Control Optimization And 52-Week Prescreen

- Date: 2026-06-24
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN stock cross-sectional alpha research only
- Safety: research-to-review only; no broker, no account reads, no orders, no live trading

## Objective

This work closed the remaining process gaps before restarting CN stock factor mining, then ran one controlled mining round on a newly pre-registered public-method family.

The optimized points were the ones flagged in the user review:

- A-share tradeability and survivorship constraints.
- PIT financial/event availability.
- Industry/style neutralization.
- Portfolio construction controls.
- Strict statistical controls.
- China market regime controls.
- Event-factor contamination controls.
- Family rotation after repeated failures.

## Round206 Event-Control Closeout

Round206 added a reusable `event_factor_control_gate`.

Result:

- Total event controls: 3
- Closed event controls: 3
- Hibernated controls: 1
- Controlled-retest-only controls: 1
- Coverage-blocked controls: 1
- Blockers: 0
- Event direct alpha allowed: false
- Event portfolio grid allowed: false
- Non-event direct factor generation allowed: true

Closed controls:

- `earnings_forecast_events`: hibernated after weak/negative evidence.
- `dividend_ex_right_events`: controlled retest only; raw yield-like exposure blocked without residualization and stability evidence.
- `buyback_holder_change_unlock_events`: locally coverage-blocked; does not block non-event CN stock mining.

Quality-gate status after Round206:

- Implemented controls: 33
- Partial controls: 0
- Planned controls: 1, the CN ETF dedicated signal pack, scope-exempt for CN stock mining
- Direct CN stock factor generation: allowed
- Portfolio grid and promotion: still gated by candidate-level evidence

## Candidate-Gate Optimization

The old candidate plan gate checked control declarations but did not explicitly reject hibernated family re-entry or enforce the three-round review cadence.

Round207 added a `family_rotation_policy` to `factor_mining_candidate_plan_gate`.

New blockers:

- `candidate_family_hibernated:<family>`
- `candidate_family_blocked:<family>`
- `family_rotation_review_required_after_round_limit`

Startup config now requires these confirmations before future CN stock mining:

- `round207_candidate_plan_family_rotation_policy_confirmed`
- `round207_hibernated_family_reentry_block_confirmed`
- `round207_three_round_review_limit_gate_confirmed`

Verified by tests:

- Hibernated family re-entry is blocked before new screening.
- A family at or above the configured round budget is blocked unless the three-round review is complete.
- Existing candidate-plan CLI behavior remains compatible.

## Round207 Candidate Plan

New pre-registered family:

`anchor_momentum_52week_quality`

Candidates:

1. `high_52w_proximity_liquid_quality_252_20`
2. `high_52w_pullback_resilience_252_20`
3. `high_52w_breakout_amount_confirmation_252_20`
4. `high_52w_low_drawdown_residual_anchor_252_60`

Candidate plan gate result:

- Status: research_ready
- Candidates: 4
- Complete control areas: 8 / 8
- Research screen allowed: true
- Portfolio grid allowed: false
- Promotion allowed: false
- Blockers: 0

## Round207 Long-Cycle Prescreen

Command:

```powershell
python scripts\run_high_52week_quality_prescreen.py --candidate-plan-json configs\factor_mining_candidate_plan_round207_52week_high_quality_20260624.json --output-dir data\reports\round207_52week_high_quality_prescreen_20260624 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --min-cross-section 100 --min-ic-observations 80 --min-signal-date-amount 10000000
```

Data:

- Bar rows: 10,785,537
- Assets: 5,707
- Bar window: 2015-01-05 to 2025-12-31
- Signal window: 2015-07-01 to 2025-12-31
- Label rows: 21,417,227
- Factor rows: 38,085,208
- Aligned rows: 75,581,788
- Tests: 8

Result:

- FDR-significant tests: 8 / 8
- Research leads: 0
- Promotion candidates: 0

Top observations:

| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Turnover | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `high_52w_breakout_amount_confirmation_252_20` | 20 | -0.0615 | -0.395 | -19.88 | 34.3% | -0.0720 | -0.700 | 9.4% | no |
| `high_52w_proximity_liquid_quality_252_20` | 20 | -0.0519 | -0.306 | -15.38 | 37.6% | -0.0736 | -0.700 | 11.8% | no |
| `high_52w_breakout_amount_confirmation_252_20` | 5 | -0.0516 | -0.343 | -17.31 | 36.4% | -0.0079 | -0.100 | 9.4% | no |
| `high_52w_pullback_resilience_252_20` | 20 | -0.0463 | -0.278 | -14.00 | 39.0% | -0.0401 | -0.500 | 12.6% | no |

## Interpretation

This round did not find a buyable alpha factor.

It found strong negative evidence: being close to a 52-week high, even with liquidity and quality controls, ranked worse future returns over the 2015-2025 CN stock sample.

That is useful, but it is not promotable:

- The tested direction was wrong for long-only buying.
- The negative sign was discovered after measurement, so an inverse version must be pre-registered as a new hypothesis before testing.
- No portfolio grid, walk-forward, or promotion claim is allowed from this result.

## Decision

- New factors pre-registered: 4
- Long-cycle factor tests run: 8
- Research leads: 0
- Usable/promotable factors: 0
- Useful signal clue: 1, a potential overextension/avoidance direction

Next action:

Pre-register an inverse 52-week overextension avoidance or bottom-exclusion hypothesis only if it is treated as a new round, counted as new multiple-testing exposure, and blocked from promotion until residual IC, style exposure, walk-forward, cost/capacity, and final-holdout checks pass.

If the inverse or exclusion translation fails, hibernate the whole 52-week anchor family within the three-round budget and rotate.
