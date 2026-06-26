# CN Stock Round238 Pre-Mining Entry Gate Enforcement

Date: 2026-06-25

## Objective

Convert the user's eight optimization points into enforceable pre-mining controls before continuing CN stock factor mining:

- A-share real tradeability rules: limit up/down, suspension, ST, new listing age, delisting risk, board permissions.
- PIT financial timing: announcement/revision availability date and signal date, not report-period end.
- Industry/style neutralization: industry, size, value, low-vol, momentum, and liquidity exposure separation.
- CN ETF boundary: stock mining cannot reuse ETF rotation evidence or signal packs.
- Portfolio construction: risk budget, volatility target, industry cap, turnover, drawdown/de-risk controls, and metric pack.
- Strict statistics: Deflated Sharpe, purged/CPCV-style checks, FDR/White Reality Check proxy, parameter sensitivity, final holdout.
- China market regime: policy/liquidity, credit, northbound/margin temperature, index location, signal-window regime coverage.
- Event factors: forecast/statement events, dividend/ex-right, buyback/holder/unlock, index rebalance, event contamination.

## Implementation

- Extended the actual CN processed mining entrypoints to require a cleared candidate-plan gate packet after the startup gate and CN stock data manifest:
  - `scripts/run_tushare_alpha_factory.py`
  - `scripts/run_experiment_grid.py`
- Added CLI option `--candidate-plan-gate-packet` to both entrypoints, defaulting to `data/reports/factor_mining_candidate_plan_gate/factor_mining_candidate_plan_gate.json`.
- Kept fixture and non-CN runs unaffected; the hard gate applies to CN processed/authority processed runs.
- Updated startup gate protocol so generated startup packets explicitly declare:
  - `candidate_plan_gate_packet_required_by_mining_entrypoints`
  - `candidate_plan_gate_packet_validated_before_factor_generation`
- Updated test fixtures to generate valid startup gate packets through the real builder instead of hand-written stale JSON.

## Verification

TDD sequence:

- Red: endpoint tests failed because `candidate_plan_gate_packet` was not supported.
- Green: after wiring validation into entrypoints, all related tests passed.

Verified commands:

```powershell
python -m unittest tests.unit.test_factor_mining_candidate_plan_gate tests.unit.test_tushare_alpha_factory_cli tests.unit.test_experiment_grid_cli tests.unit.test_factor_mining_startup_gate
```

Result: 69 tests passed.

## Label Smoke Evidence

The accounting-quality branch now has a PIT matrix-label smoke gate before any IC read:

- Report: `data/reports/round238_accounting_quality_statement_matrix_label_smoke_115_symbol_20260625/accounting_quality_statement_matrix_label_smoke.json`
- Statement assets: 115
- Factor value rows: 22,549
- Label aligned rows: 45,098
- Label coverage: 100.00%
- Alignment violation rows: 0
- Horizons: 5 and 20 trading days
- Execution lag: 1 trading day after the first tradable signal date following `ann_date`

This evidence only clears the timing/label gate. It does not clear IC quality, portfolio construction, cost, regime, or promotion gates.

## Residual IC Shape Evidence

The allowed next gate was then run on the same 115-symbol accounting-quality sample:

- Report: `data/reports/round239_accounting_quality_statement_residual_ic_shape_prescreen_115_symbol_20260625/accounting_quality_statement_residual_ic_shape_prescreen.json`
- Candidate formulas: 5
- Tests: 10
- Factor rows: 22,549
- Label aligned rows: 45,098
- FDR-significant tests: 0
- Neutral-gate pass tests: 0
- Research leads: 0
- Promotion allowed candidates: 0

Decision: do not convert the five raw accounting-quality formulas into walk-forward or portfolio grids. The current evidence says the direction needs broader data and/or formula repair, not more parameter tuning on the same raw signals.

## Decision

The project should not start new CN stock factor generation unless:

- Startup gate is generated today and cleared.
- CN stock data manifest is cleared or explicitly review-allowed.
- Candidate plan gate is generated today and cleared.
- Candidate plan declares hypothesis source, economic rationale, all eight control areas, strict promotion policy, and family-rotation rules.

This optimization does not produce a new alpha claim. It makes the next mining round harder to waste by blocking anonymous, short-sample, raw-TopN, or missing-control factor searches before they consume compute/API budget.

## Next Work

- Continue shard 6 from `symbol_offset=15` with `symbol_limit=5` only as data expansion under the same PIT readiness, statement-formula smoke, and matrix-label smoke gates.
- Repair accounting-quality formulas toward industry-relative/size-neutral composites before another IC gate.
- Keep duplicate `asset_id/end_date/ann_date/report_type` handling mandatory before persisting a factor matrix.
- Only after gate artifacts, label alignment, and sufficient cross-section coverage are current, continue CN stock accounting-quality factor mining from the approved direction.
