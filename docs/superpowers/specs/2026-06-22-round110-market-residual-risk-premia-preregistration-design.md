# Round110 Market Residual Risk Premia Preregistration Design

## Context

Rounds107-109 produced no promotable CN stock factor. The only Round107 research lead was capacity-clean but hard redundant with existing price-volume candidates, while the Round109 overnight/intraday gap family had 13 FDR-significant tests but zero research leads. The next family should reduce hidden beta risk instead of continuing same-family price, volume, gap, or anti-overheat variants.

## Goal

Pre-register a public-reference market residual risk premia family for CN stock cross-sectional factor mining. The family must separate market exposure from candidate alpha before any portfolio grid, so the next prescreen can test whether low beta, low downside beta, idiosyncratic volatility, and residual return effects have independent predictive value.

## Requirements

- Use CN stock scope only.
- Use Round107-109 three-round review as the source audit.
- Build candidates as hypotheses, not promotion evidence.
- Use an equal-weight CN stock market proxy computed from available signal-date data.
- Candidate names must clearly show beta, downside beta, idiosyncratic risk, residual return, or crash-resilience semantics.
- Direction remains `higher_is_better`, where higher scores mean safer or more attractive residual/risk-adjusted exposure.
- Do not allow portfolio backtest, top-N grid, or promotion before IC, quantile, turnover, capacity, redundancy, and market-exposure prescreen.
- Do not touch the 2026 final holdout.
- Keep public-reference rationale: factor model construction, Alphalens/qlib signal prescreening, low-volatility/beta anomaly, residual reversal/momentum, vectorbt/pyfolio later risk attribution.

## Candidate Shape

Round110 will pre-register ten candidates:

- Low market beta over 120 days.
- Low downside beta over 120 days.
- Low idiosyncratic volatility over 60 days.
- Residual reversal after a 60-day beta estimate.
- Residual momentum quality over 20 and 120 days.
- Low market correlation over 60 days.
- Crash-resilience score over 60 days.
- Beta-adjusted range contraction over 60 days.
- Low downside residual volatility over 60 days.
- Positive residual skew over 60 days.

These formulas are hypotheses only. They can proceed to Round111 prescreen, but cannot be promoted or portfolio-tested from registration alone.

## Testing

Tests must prove:

- The default candidate list is unique and has at least eight candidates.
- Every candidate is CN stock, has capacity filters, public references, economic rationale, and promotion disabled.
- Every candidate requires `adj_close` and `market_equal_weight_return`.
- Build output records Round107-109 as source context and points next direction to Round111 prescreen.
- Output explicitly blocks top-N portfolio work before residual IC/quantile/turnover prescreen.
- CLI writes JSON, Markdown, and CSV outputs.

## Self-Review

- No direct portfolio backtest or walk-forward is included.
- No 2026 holdout is touched.
- The design explicitly targets hidden beta and redundant price-volume signal risk.
- The scope is one preregistration artifact plus startup-gate update and research report.
