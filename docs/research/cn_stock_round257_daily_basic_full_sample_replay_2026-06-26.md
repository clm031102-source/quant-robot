# CN Stock Round257 Daily-Basic Full-Sample Replay

- Date: 2026-06-26
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock factor mining, not CN ETF rotation
- Stage: same-parameter long-cycle replay, not portfolio validation
- Final holdout: excluded; 2026 data remains read-once only after OOS clearance

## Objective

Round257 answers the short-sample concern directly: replay the frozen Round131/Round132 daily-basic non-price public carry candidates over the full available 2015-2025 CN stock cycle without changing formulas, windows, signs, lags, horizons, or capacity thresholds.

This round is intentionally an audit replay. It is not a new daily-basic parameter search and it does not grant portfolio-grid or promotion permission.

## Candidate Gate

- Candidate plan: `configs/factor_mining_candidate_plan_round257_daily_basic_full_sample_replay_20260626.json`
- Candidate gate output: `data/reports/round257_daily_basic_full_sample_replay_candidate_plan_gate_20260626`
- Gate status: research_ready
- Candidates: 10
- Complete control areas: 8 / 8
- Research screen allowed: true
- Portfolio grid allowed: false
- Promotion allowed: false

## Execution

The first full 10-candidate run timed out after about 604 seconds without writing a complete result. The tooling was then optimized so `run_daily_basic_non_price_public_carry_prescreen.py` accepts `--candidate-name` and the daily-basic prescreen computes only requested candidate values. The replay was completed as five frozen-parameter shards of two candidates each.

- Bars roots:
  - `data/processed/cn_stock_long_history_2015_202306`
  - `data/processed/office_desktop_20260616_combined_research`
- Daily-basic roots:
  - `data/processed/cn_stock_long_history_2015_202306`
  - `data/processed/office_desktop_20260617_daily_basic_factor_inputs`
- Analysis window: 2015-01-01 to 2025-12-31
- Signal dates: 2015-01-05 to 2025-12-31
- Horizons: 5, 20
- Execution lag: 1
- Min cross-section: 100
- Min IC observations: 80
- Min field coverage ratio: 0.80
- Min field coverage clean ratio: 0.80
- Min capacity clean ratio: 0.80
- Min signal-date amount: 10,000,000

## Combined Results

- Unique factors: 10
- Factor x horizon tests: 20
- FDR-significant tests: 20
- Strict research leads: 0
- Promotion candidates: 0
- Coverage-pass candidates: 3
- Bar rows: 10,785,537
- Daily-basic rows: 10,700,940
- Factor rows across shards: 107,009,400
- Aligned rows across shards: 212,265,780
- Combined output: `data/reports/round257_daily_basic_non_price_public_carry_full_sample_replay_20260626_combined`

## Top Diagnostics

| Factor | H | IC | ICIR | t | IC>0 | Q5-Q1 | Mono | Field clean | Cap clean | 11y positive | 2025 IC | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| daily_basic_valuation_reversion_quality_60 | 20 | 0.0657 | 0.519 | 26.73 | 69.1% | 0.0543 | 0.70 | 68.4% | 94.8% | 11/11 | 0.0738 | diagnostic repair candidate |
| daily_basic_valuation_reversion_quality_60 | 5 | 0.0502 | 0.403 | 20.78 | 66.1% | 0.0181 | 0.60 | 68.4% | 94.8% | 11/11 | 0.0564 | blocked by coverage and shape |
| daily_basic_value_yield_size_neutral_20 | 20 | 0.0463 | 0.302 | 15.52 | 60.7% | 0.0158 | 0.50 | 86.2% | 94.8% | 10/11 | 0.0393 | shape weak |
| daily_basic_free_float_supply_quality_20 | 20 | 0.0269 | 0.199 | 10.23 | 57.6% | 0.1034 | 0.90 | 99.4% | 94.8% | 9/11 | 0.0575 | ICIR too low |
| daily_basic_crowding_value_yield_balance_20 | 20 | 0.0349 | 0.321 | 16.54 | 63.0% | -0.0368 | -0.80 | 91.1% | 94.8% | 10/11 | 0.0181 | negative quantile spread |

## Audit Interpretation

The full-sample replay found broad rank correlation, but not tradable evidence. All 20 factor x horizon tests were FDR-significant, yet zero passed the strict research-lead gate because the long-only quantile shape, field coverage, or ICIR failed. This is exactly why the workflow should not promote factors from short windows, single metrics, or raw TopN total return.

The strongest diagnostic is `daily_basic_valuation_reversion_quality_60` at horizon 20. It has strong long-cycle IC, ICIR above 0.5, 69.1% positive daily IC rate, positive Q5-Q1, monotonicity at the 0.70 threshold, and 11/11 positive calendar-year mean IC. The blocker is not alpha absence; it is implementation evidence: field coverage clean ratio is 68.4%, below the 80% hard threshold, and the factor still needs style/industry exposure and walk-forward cost/capacity validation.

`daily_basic_free_float_supply_quality_20` has the best quantile shape, with Q5-Q1 0.1034 and monotonicity 0.90, but ICIR is only 0.199 and 2023 was negative. It should remain a diagnostic reference, not a next-round primary candidate.

The crowding/value candidates are especially dangerous: their IC can look positive while Q5-Q1 is negative and monotonicity is inverted. They should not be sign-flipped after reading this result; any reuse would require a fresh orthogonal hypothesis.

## Decision

- Promotable factors: 0
- Strict research leads: 0
- Diagnostic candidates worth one repair audit: 1
- Next allowed work: `daily_basic_valuation_reversion_quality_60` coverage repair plus style/industry exposure audit, with the formula and sign frozen.
- Forbidden next work: direct daily-basic portfolio grid, direction flip, new daily-basic parameter sweep, 2026 holdout tuning, or promoting IC-only evidence.

## Round258 Contract

Round258 may only do a narrow repair audit:

- Re-check required-field availability for `pb`, `ps_ttm`, and `dv_ttm`.
- Compare the original formula with a pre-registered coverage-repaired audit variant only if the source field substitution is justified before seeing portfolio results.
- Run industry/style exposure decomposition: size, value, low-vol, momentum, liquidity, industry.
- Block portfolio conversion unless the factor survives coverage, residual IC, quantile shape, cost/capacity, and regime checks.
- If coverage repair or residual exposure fails, hibernate the daily-basic non-price public carry direct line and rotate to a new orthogonal family.
