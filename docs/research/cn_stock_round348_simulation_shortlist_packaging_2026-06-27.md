# CN Stock Round348 - Simulation Shortlist Packaging

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round348 converts the current evidence into a repeatable simulation shortlist package.

This round does not run a new backtest. It packages the accepted candidate tiers and their constraints so the next machine or thread can enter simulation-readiness review without manually reconstructing parameters from multiple reports.

## Outputs

Config:

`configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json`

Runbook:

`docs/research/cn_stock_profit_sprint_simulation_shortlist_runbook_2026-06-27.md`

2026 final holdout remains unused.

## Candidate Tiers

| Candidate | Status | Role |
|---|---|---|
| `primary_high_return` | shortlist default | Highest return, accepts near-30% drawdown |
| `primary_defensive_zz500` | preferred defensive | Best balance of return, drawdown, cost robustness, and beta audit |
| `safer_defensive_zz500` | ultra-defensive reference | Low-drawdown comparison line |

## Superseded Evidence

The package explicitly blocks two invalid outputs:

- first Round346 cost stress output, because it failed to reproduce official vol-target events;
- first Round347 beta audit output, because it reported intercept-subtracted residuals instead of beta-hedged returns.

## Decision

The project now has a concrete simulation shortlist rather than a loose list of promising factors.

Next work should review Rounds346-348 together, then either:

- prepare a final-holdout read-once protocol; or
- continue mining only if it is clearly aimed at beating the packaged shortlist.
