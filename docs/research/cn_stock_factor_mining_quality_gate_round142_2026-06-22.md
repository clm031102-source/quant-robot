# CN Stock Factor Mining Quality Gate Round142

Date: 2026-06-22

## Purpose

Round142 converts the user audit points into a reusable pre-mining quality gate. The goal is to stop blind factor mining before every run by forcing the project to classify real-market constraints, PIT data timing, neutralization, ETF scope, construction, statistical rigor, China regime, and event coverage.

This is a process and safety upgrade. It does not promote any factor.

## Files Added Or Changed

- Added `src/quant_robot/ops/factor_mining_quality_gate.py`.
- Added `scripts/run_factor_mining_quality_gate.py`.
- Added `configs/factor_mining_quality_gate_cn_stock.json`.
- Updated `src/quant_robot/ops/factor_mining_startup.py` to embed the quality gate in startup packets.
- Updated `scripts/run_factor_mining_startup_gate.py` to render the gate in Markdown.
- Updated `configs/factor_mining_startup_cn_stock.json` to reference the quality gate config.
- Added tests:
  - `tests/unit/test_factor_mining_quality_gate.py`
  - `tests/unit/test_factor_mining_quality_gate_cli.py`
  - startup-gate assertions in `tests/unit/test_factor_mining_startup_gate_cli.py`

## Current Gate Result

Generated packet:

- `data/reports/factor_mining_quality_gate_round142/factor_mining_quality_gate.json`
- `data/reports/factor_mining_quality_gate_round142/factor_mining_quality_gate.md`
- `data/reports/factor_mining_startup_gate_round142/factor_mining_startup_gate.json`
- `data/reports/factor_mining_startup_gate_round142/factor_mining_startup_gate.md`

Current classification:

- Total controls: 32
- Implemented: 1
- Partial: 10
- Planned: 21
- Missing: 0
- Startup gate: cleared
- Promotion gate: blocked

Interpretation:

- New mining can continue only after seeing and acknowledging the gate.
- No candidate can be promoted merely because startup is cleared.
- Promotion remains blocked until planned/partial controls become implemented or explicitly not applicable.

## Eight Required Areas

1. CN stock tradeability:
   limit up/down, suspension, ST, new listing age, delisting risk, and board permission.

2. Financial PIT timing:
   announcement-date lag, revision announcements, and report-release timing instead of report-period timing.

3. Industry/style neutralization:
   industry exposure, style exposure, size/value/low-vol/momentum/liquidity decomposition, and residualized factor options.

4. ETF rotation scope boundary:
   keep this branch CN stock only; ETF rotation needs its own ETF signal pack.

5. Portfolio construction:
   risk budget, volatility targeting, industry constraints, turnover constraints, and stop-loss/de-risk rules.

6. Strict statistics:
   Deflated Sharpe, CPCV, White Reality Check or FDR, and parameter sensitivity heatmaps.

7. China market regime:
   policy/liquidity regime, credit cycle, northbound/margin/turnover temperature, and index-location state.

8. Event factors:
   earnings forecast, dividend/ex-right, buyback/holder/unlock, and index rebalance events.

## Immediate Implication

The project was not merely short of better factor formulas. It was missing a mandatory gate that distinguishes:

- "classified enough to continue discovery"
- "implemented enough to allow promotion"

Round142 adds that distinction. The next useful work should implement the highest-risk missing controls first, especially tradeability masks and strict statistics, before burning more compute on broad factor sweeps.

## Verification

Commands run:

```powershell
python -m unittest tests.unit.test_factor_mining_quality_gate tests.unit.test_factor_mining_quality_gate_cli tests.unit.test_factor_mining_startup_gate_cli
python -m json.tool configs\factor_mining_quality_gate_cn_stock.json > $null
python -m json.tool configs\factor_mining_startup_cn_stock.json > $null
python -m py_compile src\quant_robot\ops\factor_mining_quality_gate.py src\quant_robot\ops\factor_mining_startup.py scripts\run_factor_mining_quality_gate.py scripts\run_factor_mining_startup_gate.py
python scripts\run_factor_mining_quality_gate.py --config configs\factor_mining_quality_gate_cn_stock.json --output-dir data\reports\factor_mining_quality_gate_round142
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start --output-dir data\reports\factor_mining_startup_gate_round142
```

All verification commands completed successfully.
