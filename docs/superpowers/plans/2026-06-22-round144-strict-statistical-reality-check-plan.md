# Round144 Strict Statistical Reality Check Plan

## Context

The CN stock factor-mining process already has walk-forward validation, overlap-aware Sharpe diagnostics, and FDR-style IC accounting. The current gap is that the strict-statistics controls are not reusable as a first-class gate before factor promotion.

## Goal

Build a reusable research-only statistical reality-check layer for experiment leaderboards:

- Deflated Sharpe / Probabilistic Sharpe approximation that penalizes repeated trials.
- Benjamini-Hochberg FDR accounting on experiment p-values.
- Purged CPCV split planner with optional embargo.
- Parameter sensitivity heatmap around the best cell.
- CLI artifacts that can be referenced by the factor-mining quality gate.

## Scope

- Add `quant_robot.ops.factor_statistical_reality_check`.
- Add `scripts/run_factor_statistical_reality_check.py`.
- Add focused unit and CLI tests.
- Update `configs/factor_mining_quality_gate_cn_stock.json` evidence for strict statistics.
- Produce a lightweight Round144 research report.

## Out of Scope

- No broker connection, no account reads, no order placement, no live trading.
- No commitment that any factor is profitable.
- No full White Reality Check bootstrap in this round; FDR remains the implemented multiple-testing control while WRC is still a future enhancement.

## Verification

- Unit tests for DSR, FDR, CPCV purge/embargo, and sensitivity summaries.
- CLI test for artifact generation.
- `py_compile` on new module and script.
- Quality gate rerun to confirm strict-statistics controls have executable evidence.
