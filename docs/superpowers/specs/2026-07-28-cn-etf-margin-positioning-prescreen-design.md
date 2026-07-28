# CN ETF Margin-Positioning Prescreen Design

## Frozen candidate

Test exactly one candidate:
`etf_residual_margin_financing_growth_reversal_20`.

For each ETF, calculate the exact-session 20-day log change in financing
balance using source dates. Join the observation only on its audited next
session `available_date`. Daily winsorize and standardize that change, then
residualize it against 20- and 60-session ETF returns, 20-session realized
volatility, 20-session log average traded amount, and SSE venue. The factor is
the negative residual: unusually rapid leveraged-position growth is
preregistered as subsequent crowding reversal.

The 5-session horizon is primary and the 20-session horizon is diagnostic.
The diagnostic cannot rescue a failed primary. One candidate across two fixed
horizons is the complete hypothesis set; sign, lookback, controls, thresholds,
and horizons cannot change after labels are read.

## Data and point-in-time rules

- Source: the hash-bound margin-positioning dataset approved on 2026-07-28.
- Analysis: 2020-01-02 through 2024-06-28.
- Final holdout: 2026 onward, skipped before read.
- The factor date is `available_date`, never the raw source date.
- Exact-session lags are required; no forward fill.
- Factor and label rows whose required market-session window crosses
  2020-05-28 or 2020-06-03 are excluded.
- ETF eligibility uses official lifecycle, at least 120 prior observations,
  20-session trailing median amount of at least CNY 5 million, and existing
  stale-price/return-integrity rules.

## Evaluation and stop policy

Reuse the strict CN ETF prescreen gates: FDR, mean Rank IC, ICIR, positive IC
rate, quintile monotonicity, yearly consistency, reference correlation, direct
exposure correlation, turnover, 10 bps net spread, and every-date capacity at
CNY 100,000 per position and 1% one-way participation.

Closed ETF-family references and direct margin-growth/style exposures are
mandatory. Prior CN-stock margin-credit residual failure is recorded as a
mechanism warning, not treated as positive evidence.

The preregistration creates exactly one hash-bound execution authorization.
No rerun, sign flip, window tuning, control removal, threshold relaxation,
subgroup rescue, portfolio grid, walk-forward, holdout read, paper signal, or
live action is allowed.

