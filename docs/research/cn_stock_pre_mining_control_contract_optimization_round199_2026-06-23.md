# CN Stock Pre-Mining Control Contract Optimization Round199

Date: 2026-06-23

## Objective

This round optimizes the CN stock factor-mining workflow before resuming profitable-factor discovery. It converts the user's required control list into a machine-readable startup contract so every new run must explicitly surface the hard constraints that were missing or only partially applied in earlier mining work.

This round does not claim any new profitable factor. It is process-control work that must happen before direct factor generation resumes.

## Why This Was Needed

Earlier rounds produced many weak or unusable candidates because several research risks were handled as scattered notes instead of a single startup contract:

- Real A-share tradeability was incomplete: limit-up/down, suspension, ST, delisting, listing age, and board-permission evidence were not fully covered across 2015-2025.
- Some factor families could still drift toward short-window or point-parameter optimization before full long-cycle replay.
- IC, portfolio return, cost, capacity, drawdown, win-rate, and regime evidence were not presented as one mandatory pre-mining checklist.
- CN stock mining and CN ETF rotation evidence needed a stronger boundary so ETF-specific signals do not contaminate stock-factor conclusions.
- Portfolio construction was too often raw TopN-first; risk budget, volatility targeting, industry constraints, turnover constraints, stop/de-risk rules, and metric packs need to be visible before portfolio-grid work.

## Implemented Optimization

Added `pre_mining_control_contract` to the startup gate packet in `src/quant_robot/ops/factor_mining_startup.py`.

The contract contains eight required areas:

1. `a_share_real_tradeability`
2. `financial_pit_timing`
3. `industry_style_neutralization`
4. `cn_etf_rotation_boundary`
5. `portfolio_construction`
6. `strict_statistics`
7. `china_market_regime`
8. `event_factors`

Each area now carries:

- required quality controls
- required outputs
- current control status from the quality gate
- evidence and next action text
- `direct_mining_ready`
- direct-mining blockers

The startup validation now rejects a cleared startup packet if this contract is absent or incomplete.

## Important Contract Details

Portfolio construction now explicitly requires the metrics the user asked to see before interpreting candidate quality:

- `total_return`
- `annual_return`
- `sharpe`
- `cost_adjusted_sharpe`
- `max_drawdown`
- `win_rate`
- `turnover`
- `capacity_usage`

Strict statistics now explicitly requires:

- `deflated_sharpe`
- `cpcv_summary`
- `white_reality_check_or_fdr`
- `parameter_sensitivity_heatmap`
- `overlap_adjusted_statistics`
- `final_holdout_status`

The contract policy is conservative: when any required control is `partial`, `planned`, or `missing`, direct factor generation remains blocked. Allowed work stays limited to quality-control implementation, data coverage audits, and candidate preregistration without profit claims.

## Config Update

Updated `configs/factor_mining_startup_cn_stock.json` with:

- `pre_mining_control_contract_confirmed`

This makes the contract a first-class startup confirmation for the CN stock workflow.

## Result

The project now has a repeatable pre-mining gate that directly addresses the user's optimization list:

- A-share real trading rules
- financial point-in-time timing
- industry and style neutralization
- CN ETF rotation boundary
- portfolio construction beyond TopN
- strict statistical reality checks
- China market regime
- event-factor controls

Current conclusion remains unchanged: direct CN stock factor generation is blocked until official tradeability coverage and the remaining quality controls are complete. The next valid work is to continue long-cycle official tradeability backfill, then wire the masks into factor matrix and portfolio execution gates.

## Verification Scope For This Round

Fresh verification should include:

```powershell
python -m unittest tests.unit.test_factor_mining_startup_gate tests.unit.test_factor_mining_startup_gate_cli
python -m py_compile src\quant_robot\ops\factor_mining_startup.py scripts\run_factor_mining_startup_gate.py
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start --output-dir data\reports\round199_startup_gate_pre_mining_control_contract_20260623
```
