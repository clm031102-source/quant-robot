# CN Stock Round226 Method Optimization Contract - 2026-06-24

## Purpose

Round225 rejected the financial PIT post-announcement gap-reversal line in walk-forward validation:

- 0 accepted cases.
- 0 promotable factors.
- Lowering portfolio value to 100k fixed capacity, but did not fix fold instability or deep drawdown.
- The best repair probe still had only 2/4 accepted folds and about -63% worst drawdown.

Round55-75 also showed that public trend-volume, anti-OBV, smart-money quality, and the public risk-filter bridge can identify weak bottom tails, but failed as tradable long-only alpha:

- direct TopN use was rejected;
- bottom-exclusion diagnostics had useful t-stats but weak absolute Sharpe;
- static and dynamic cash overlays reduced drawdown mechanically without improving return quality;
- corrected beta-hedged spread was negative after costs;
- stress cost tests confirmed rejection.

Round226 therefore optimizes the mining method before more factor mining. This is a process-control round, not a new alpha claim.

## Implemented Optimization

The startup gate now emits a machine-readable `method_optimization_contract` and validates that it exists before accepting a cleared startup packet.

The contract makes these rules explicit:

- No promotion claim is allowed without the method contract.
- No raw TopN expansion is allowed without the method contract.
- A family with zero accepted walk-forward cases must be hibernated unless a new orthogonal hypothesis is pre-registered.
- Re-entering a failed family requires a new hypothesis, not another parameter grid.
- Every factor-mining run must review the eight method areas before factor generation.

## Eight Required Method Areas

| Area | Required purpose |
|---|---|
| `a_share_real_tradeability` | Limit-up/down, suspension, ST, new-listing, delisting, and board-permission constraints. |
| `financial_pit_timing` | Announcement date, revision date, available date, signal lag, and no report-period-end leakage. |
| `industry_style_neutralization` | Industry, size, value, low-vol, momentum, and liquidity exposure separation before raw TopN expansion. |
| `cn_etf_rotation_boundary` | Keep CN stock factor mining separate from ETF rotation signal packs. |
| `portfolio_construction` | Require profit rate, annual return, Sharpe, cost-adjusted Sharpe, max drawdown, win rate, turnover, and capacity. |
| `strict_statistics` | Require Deflated Sharpe, CPCV or purged CV, White Reality Check or FDR, sensitivity heatmap, and holdout audits. |
| `china_market_regime` | Require policy/liquidity, credit, northbound/margin/turnover temperature, index location, and signal-window regime coverage. |
| `event_factors` | Require available/effective dates, event type, contamination audit, event-neutral IC, and lag days. |

## Hibernated Or Blocked Directions

- `public_risk_filter_bridge`: hibernated after Round75 spread-stress failure.
- `public_supertrend`: hibernated as a promotion path after bottom-exclusion walk-forward failure.
- `public_trend_volume_single_filter`: blocked as a standalone promotion path.
- `financial_post_announcement_gap_reversal_without_new_orthogonal_repair`: blocked after Round225 zero accepted walk-forward cases.

## Config Changes

Updated `configs/factor_mining_startup_cn_stock.json`:

- `source_audit` now points to this Round226 report.
- `next_direction` is now `round227_public_method_family_rotation_candidate_plan_after_method_contract`.
- New rejected directions record Round226 hibernation decisions.
- New required design items require family stop-loss and Round227 candidate family rotation.
- New confirmations require the method contract, public risk-filter hibernation, gap-reversal rotation, and Round227 plan acknowledgement.

Updated startup gate code:

- `src/quant_robot/ops/factor_mining_startup.py` adds `method_optimization_contract`.
- `validate_cleared_startup_gate_packet` rejects startup packets without the contract.
- `scripts/run_factor_mining_startup_gate.py` renders the contract in Markdown.

## Decision

Promotable profitable factors from Round226: 0.

Paper-ready factors from Round226: 0.

Useful result: a stricter repeatable mining gate that prevents three previously expensive mistakes:

- continuing a failed family after zero accepted walk-forward cases;
- treating bottom-exclusion or risk-filter diagnostics as tradable alpha;
- running direct TopN grids before tradeability, PIT, neutralization, portfolio, statistics, China regime, and event controls are declared.

## Next Direction

Round227 should run a public-method family-rotation candidate plan, not another gap-reversal or public risk-filter bridge grid.

Allowed next work:

- choose a new, economically interpretable family from public/literature/market-mechanism sources;
- pre-register candidate names, formulas, windows, tradeability controls, PIT controls, neutralization plan, portfolio policy, strict statistics, regime controls, and event contamination checks;
- block portfolio grids until the candidate plan and source-evidence gates clear.

Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading.
