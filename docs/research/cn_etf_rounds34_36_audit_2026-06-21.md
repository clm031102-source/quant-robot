# CN ETF Rounds34-36 Audit

Date: 2026-06-21
Machine: office_desktop
Task: factor_validation
Branch: codex/factor-validation-cn-stock-long-cycle-20260618

## Scope

This audit covers the second 3-round block under the new rule: review every 3 rounds, adjust direction, and avoid wasting compute on weak paths.

## Round Summary

| Round | Direction | Cases | Result | Decision |
|---:|---|---:|---|---|
| 34 | Tushare ETF fund_basic metadata | n/a | 2814 metadata rows, 252/264 liquid ETF coverage | Enabled theme tests |
| 35 | Raw ETF theme breadth | 12 | 0 accepted, 0 positive Sharpe, capacity issues in all cases | Fix tie/capacity issue |
| 36 | Liquid-adjusted ETF theme breadth | 10 | 0 accepted, capacity fixed, still 0 positive Sharpe | Stop standalone theme breadth |

## Findings

1. Metadata work was necessary and reusable.

The project can now repeatably fetch Tushare `fund_basic` and build ETF theme maps. This improves the framework even though the first theme factor tests failed.

2. Raw theme breadth failed partly for a real implementation reason.

Theme-level scores assign the same value to all ETFs inside the same theme. Without a liquidity tie-break, TopN can select weaker trading representatives. Round35 showed capacity-limited trades in every case.

3. The liquid tie-break fixed execution, not alpha.

Round36 reduced capacity-limited cases from 12/12 to 0/10, confirming the fix. But every case still had negative Sharpe and negative annualized return. The standalone theme breadth signal is not worth expanding now.

4. The current best research lead remains price-volume range contraction.

Across Rounds31-36, the only factor with a positive OOS cluster is still `formula_range_contraction_breakout_20`, especially Top5/Top10 with 5 bps cost and rebalance 5/10.

## Direction Change

For the next 3-round block:

- Round37: test defensive/low-volatility/liquidity ETF rotation on the same liquid universe.
- Round38: test the range-contraction breakout lead under simple risk-state or benchmark trend filters only if preflight confirms enough rebalance opportunities.
- Round39: audit defensive versus range-contraction evidence and decide whether either deserves a stricter long-cycle/promotion gate.

Guardrails:

- Do not continue standalone theme breadth this cycle.
- Do not promote `formula_range_contraction_breakout_20` without stronger significance or a documented portfolio-level alternative gate.
- Keep testing costs conservative; 10 bps sensitivity already showed fragility in Round33.
- Treat infrastructure wins separately from alpha wins.

## Candidate Ledger

| Candidate | Status | Decision |
|---|---|---|
| `formula_range_contraction_breakout_20_top5_cost5_reb10` | Best research lead | Continue validation |
| `formula_range_contraction_breakout_20_top10_cost5_reb10` | Research lead | Continue validation |
| Liquid-adjusted theme breadth | Infrastructure only | Keep code, stop alpha expansion |
| Raw theme breadth | Failed | Do not expand |
| Tail-guard reversal | Failed | Do not expand |
