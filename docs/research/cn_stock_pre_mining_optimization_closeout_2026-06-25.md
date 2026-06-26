# CN Stock Pre-Mining Optimization Closeout - 2026-06-25

## Scope

This closeout turns the user's eight requested optimization areas into the mandatory pre-mining gate for CN stock alpha research on `office_desktop`.

This is not an alpha result report. It makes no Sharpe, annual-return, profit-rate, win-rate, RankIC, or promotion claim.

## Inputs Reviewed

- Startup gate config: `configs/factor_mining_startup_cn_stock.json`
- Quality gate config: `configs/factor_mining_quality_gate_cn_stock.json`
- Candidate plan gate: `configs/factor_mining_candidate_plan_round232_dragon_tiger_attention_reversal_20260624.json`
- Round232 Dragon-Tiger coverage progress: `docs/research/cn_stock_round232_dragon_tiger_full_coverage_shard_progress_2026-06-24.md`
- Generated quality gate packet: `data/reports/factor_mining_quality_gate_cn_stock_20260625_pre_mining_optimization/factor_mining_quality_gate.json`
- Generated control closeout audit: `data/reports/factor_mining_control_closeout_audit_20260625_pre_mining_optimization/factor_mining_control_closeout_audit.json`

## Optimization Decision

The CN stock pre-mining control contract is now the first gate before new factor generation:

- A-share real trading constraints: implemented.
- Financial PIT timing: implemented.
- Industry/style neutralization: implemented.
- CN ETF rotation signal boundary: implemented for scope separation; the ETF-only signal pack is `not_applicable` to CN stock evidence and must be handled in a separate CN_ETF task.
- Portfolio construction policy: implemented.
- Strict statistics: implemented.
- China market regime context: implemented.
- Event-factor coverage: implemented.
- Final holdout promotion gate: implemented.

The quality gate generated on 2026-06-25 reports:

- total controls: 34;
- implemented controls: 33;
- not applicable controls: 1;
- planned controls: 0;
- missing controls: 0;
- missing evidence controls: 0;
- missing next-action controls: 0;
- status: `promotion_ready` at the quality-control layer;
- direct factor generation allowed by quality gate: true;
- direct mining blockers: 0.

This does not mean any factor is promotable. Candidate-level, walk-forward, long-cycle, cost/capacity, neutralization, source-evidence, and final-holdout gates still decide whether any discovered factor can progress.

## ETF Boundary Fix

The prior quality gate treated `cn_etf_dedicated_signal_pack_for_etf_rotation` as `planned`, which could make the CN stock workflow appear incomplete because an ETF-only signal pack was not built in this branch.

That was the wrong scope. The corrected state is:

- `stock_vs_etf_scope_boundary`: `implemented`;
- `cn_etf_dedicated_signal_pack_for_etf_rotation`: `not_applicable` for CN stock;
- CN ETF rotation remains a separate task with its own universe, Tushare ETF data path, factor set, and evidence packet.

This prevents both errors:

- using CN stock evidence as if it were ETF rotation evidence;
- blocking CN stock factor research because an ETF-only signal pack has not been built in the CN stock branch.

## Next Allowed Work

For Round232 Dragon-Tiger attention/reversal research:

- the full 2015-2025 Dragon-Tiger coverage gate has passed;
- the first 1-day PIT event IC prescreen has run on 2026-06-25;
- result: 5 candidates tested, 0 direct research leads, 2 size/style residual repair candidates;
- the Round233 size residual repair has run on 2026-06-25;
- residual repair result: 2 candidates tested, 0 research leads, both neutral gates pass but ICIR remains below 0.30 and quantile monotonicity is weak at 0.40;
- next required direction: `round234_hibernate_or_rotate_dragon_tiger_after_size_residual_repair_failure`;
- do not run portfolio grids before residual repair, candidate gate, duplicate/exposure controls, walk-forward, cost/capacity, regime, and final-holdout checks;
- do not claim profitability before long-cycle same-parameter replay, walk-forward, cost/capacity, strict statistics, regime coverage, and final-holdout checks.

For future non-Round232 factor mining:

- run startup gate once per session;
- run candidate plan gate before generating candidates;
- every active candidate must declare hypothesis source, economic rationale, all eight control areas, and strict promotion policy;
- after every three factor-mining rounds, review and rotate or stop weak families;
- after every ten rounds, package lightweight results and safe-sync only after validation and forbidden-path checks.

## Verification

Commands run after this closeout:

```powershell
python scripts\run_factor_mining_quality_gate.py --config configs\factor_mining_quality_gate_cn_stock.json --output-dir data\reports\factor_mining_quality_gate_cn_stock_20260625_pre_mining_optimization
python scripts\run_factor_mining_control_closeout_audit.py --quality-gate-config configs\factor_mining_quality_gate_cn_stock.json --output-dir data\reports\factor_mining_control_closeout_audit_20260625_pre_mining_optimization
```

Observed:

- quality gate status: `promotion_ready`;
- control closeout status: `direct_mining_ready`;
- direct factor generation allowed only through the candidate plan gate;
- no broker, account, order, or live-trading boundary is opened.
