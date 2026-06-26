# Round101 Capacity-Safe Price-Volume Preregistration Design

## Purpose

Round101 rotates away from the rejected profitability-quality family and pre-registers the next CN stock research family before any portfolio grid is allowed.

The new family is capacity-safe price-volume, low-volatility, reversal, and public technical composite candidates. It is not a profitability claim. It is a controlled hypothesis list for the next Alphalens-style IC, quantile, and turnover prescreen.

## Scope

- Market: CN A-share stocks only.
- Machine role: office desktop factor validation.
- Output: reusable preregistration op, CLI, tests, and lightweight docs.
- No broker connection, account reads, order placement, or live trading.
- No portfolio backtest in Round101.

## Candidate Rules

Every candidate must include:

- A unique factor name.
- Formula template and windows.
- Required bar fields.
- Economic rationale.
- Public reference tags from qlib, Alphalens, VectorBT, PyFolio, or WorldQuant 101 Alphas.
- Capacity filters: ST/suspended/limit filters, listing age, minimum signal-date amount, and maximum ADV participation.
- Explicit blockers against promotion and portfolio backtesting before the prescreen.

## Evaluation Gate

Round102 must run an Alphalens-style prescreen before any top-N portfolio grid:

- mean Spearman IC
- ICIR and t-stat
- positive IC rate
- quantile spread and monotonicity
- factor turnover
- date coverage
- capacity participation
- multiple-testing accounting

Only candidates that survive that screen can graduate to correlation deduplication and then a costed portfolio test.

## Decision

Use structured preregistration instead of random formula search. This preserves the useful public-indicator direction while preventing a repeat of prior family lock-in, short-window overfitting, and direct top-N tuning.
