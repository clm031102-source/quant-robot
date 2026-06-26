# CN Stock Round209 Tradeability Structure Quality Prescreen

- Date: 2026-06-24
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN stock cross-sectional alpha research only
- Safety: research-to-review only; no broker, no account reads, no orders, no live trading

## Objective

Round209 executes the direction chosen by the Round206-208 three-round review: stop extending the failed 52-week anchor family and rotate to a new information axis tied to the user's required A-share real-trading controls.

This round does not treat tradeability status as a direct live signal. The question is narrower:

- can full-window official and metadata tradeability masks explain false alpha;
- can tradeability structure produce a clean research lead;
- should the variables become hard controls for all later factor mining.

## New Project Capability

Added a repeatable tradeability-structure prescreen:

- `src/quant_robot/ops/tradeability_structure_quality_prescreen.py`
- `scripts/run_tradeability_structure_quality_prescreen.py`
- `tests/unit/test_tradeability_structure_quality_prescreen.py`
- `configs/factor_mining_candidate_plan_round209_tradeability_structure_quality_20260624.json`

The implementation uses:

- 2015-2025 CN stock bars;
- Round199 full-window tradeability mask cache;
- current and lagged mask values only;
- no 2026 final holdout;
- existing IC, quintile, turnover, and FDR machinery;
- explicit no-promotion and no-portfolio-grid policy.

## Candidate Plan Gate

Command:

```powershell
python scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round209_tradeability_structure_quality_20260624.json --quality-gate data\reports\round206_quality_gate_after_event_control_gate_20260623\factor_mining_quality_gate.json --gate-stage discovery --output-dir data\reports\round209_tradeability_structure_quality_candidate_plan_gate_20260624
```

Result:

- Status: `research_ready`
- Candidate count: 4
- Complete control areas: 8 / 8
- Blockers: 0
- Research screen allowed: true
- Portfolio grid allowed: false
- Promotion allowed: false

## Candidates

| Factor | Hypothesis |
|---|---|
| `tradeability_persistence_quality_20` | Persistent buy/sell availability plus liquidity may reduce implementation drag. |
| `entry_exit_friction_avoidance_20` | Repeated entry/exit blocks may expose paper-return artifacts. |
| `limit_lock_pressure_avoidance_20` | Frequent official limit-up, limit-down, or suspension states can distort executable returns. |
| `metadata_survivorship_quality_120` | New listing, delisted/inactive, board-permission blocks, and metadata flags may reveal survivorship and execution-risk contamination. |

## Full-Sample Prescreen

Command:

```powershell
python scripts\run_tradeability_structure_quality_prescreen.py --candidate-plan-json configs\factor_mining_candidate_plan_round209_tradeability_structure_quality_20260624.json --tradeability-mask-root data\processed\round199_tradeability_mask_cache_2015_2025_with_stock_basic_20260623 --output-dir data\reports\round209_tradeability_structure_quality_prescreen_20260624 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --min-cross-section 100 --min-ic-observations 80 --min-signal-date-amount 10000000
```

Data:

- Bar rows: 10,785,537
- Assets: 5,707
- Mask rows: 10,785,537
- Mask years: 2015-2025
- Official blocked rows: 613,142
- Metadata blocked rows: 3,739,869
- Factor rows: 40,537,352
- Label rows: 21,417,227
- Aligned rows: 80,479,700
- Tests: 8

## Results

| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Turnover | FDR | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `entry_exit_friction_avoidance_20` | 20 | -0.0300 | -0.196 | -10.08 | 44.1% | 0.0723 | 0.600 | 2.6% | yes | no |
| `metadata_survivorship_quality_120` | 20 | -0.0266 | -0.168 | -8.66 | 44.3% | 0.0866 | 0.600 | 2.3% | yes | no |
| `tradeability_persistence_quality_20` | 20 | -0.0200 | -0.128 | -6.59 | 47.1% | 0.0705 | 0.600 | 3.0% | yes | no |
| `entry_exit_friction_avoidance_20` | 5 | -0.0193 | -0.141 | -7.29 | 44.5% | 0.0180 | 0.600 | 2.6% | yes | no |
| `metadata_survivorship_quality_120` | 5 | -0.0180 | -0.127 | -6.54 | 44.9% | 0.0228 | 0.700 | 2.3% | yes | no |
| `tradeability_persistence_quality_20` | 5 | -0.0117 | -0.084 | -4.33 | 46.9% | 0.0179 | 0.600 | 3.0% | yes | no |
| `limit_lock_pressure_avoidance_20` | 20 | -0.0075 | -0.054 | -2.79 | 47.5% | -0.0146 | -0.600 | 3.9% | yes | no |
| `limit_lock_pressure_avoidance_20` | 5 | -0.0002 | -0.001 | -0.07 | 49.9% | -0.0043 | -0.600 | 3.9% | no | no |

## Interpretation

Round209 found no usable profitability factor.

The important signal is diagnostic, not promotional:

- 7 / 8 tests are FDR-significant, so tradeability structure contains information.
- All mean IC values are non-positive, so the pre-registered higher-is-better direction fails.
- Positive-IC rates are below 50%, far below the 55% research-lead gate.
- Several rows show positive Q5-Q1 but negative rank IC, which means the shape is non-monotonic or nonlinear, not a clean ranking factor.
- Low turnover is not enough; low turnover with wrong-way IC is still not alpha.

Conclusion: tradeability structure should be used as a hard execution/survivorship control and false-alpha explanation layer, not as a standalone alpha family.

## Process Change

Startup confirmations were extended so future mining must remember:

- `round209_tradeability_structure_quality_preregistration_confirmed`
- `round209_tradeability_mask_cache_required_confirmed`
- `round209_tradeability_structure_prescreen_confirmed`
- `round209_zero_tradeability_structure_research_leads_confirmed`
- `round209_tradeability_as_risk_control_not_promotion_confirmed`

## Decision

- Promotable factors: 0
- Paper-ready factors: 0
- Research leads: 0
- Useful reusable artifact: yes, tradeability mask based prescreen and risk-control columns
- Family status: do not tune tradeability structure into a standalone alpha without a new economic hypothesis

Next valid work:

```text
round210_use_tradeability_mask_as_hard_control_then_rotate_to_new_economic_family
```

Round210 should not:

- invert these candidates and call the negative IC a discovery;
- run portfolio grids from Round209;
- claim low turnover as enough evidence;
- treat ST/new-listing/delisting/board flags as alpha.

Round210 should:

- keep Round199 tradeability masks as mandatory controls;
- test a genuinely economic source with PIT timing or industry/style residualization;
- include tradeability exposure diagnostics for every candidate before portfolio conversion.
