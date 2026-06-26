# CN Stock Three-Round Review - Rounds 71-73 - 2026-06-21

## Scope

This review covers the governance checkpoint after Rounds 71, 72, and 73.

The block stayed on long-cycle CN A-share authority data from 2015 through 2025 and used unchanged public risk-filter bridge factor parameters. It focused on portfolio translation rather than new factor-name expansion.

## Round Summary

| Round | Direction | Factors | Result | Decision |
|---|---|---:|---|---|
| 71 | Static cash exposure sensitivity | 3 | Best total 18.89%, relative 19.62%, Sharpe 0.0920, overlap Sharpe 0.0686, max DD -42.77% | no candidate; exposure scaling rejected |
| 72 | Dynamic market-state cash overlay | 3 | Best dynamic total 11.39%, relative 13.17%, overlap Sharpe 0.0586, max DD -26.09% | no candidate; dynamic overlay not enough |
| 73 | Benchmark beta exposure diagnostic | 3 | Residual alpha t-stat 4.39-5.42 and residual Sharpe 0.62-0.76, but dynamic R2 0.992-0.994 | research lead with beta only |

Unique factor names evaluated in this block: 3.

Promotable profitable factors: 0.

Paper-ready factors: 0.

Useful outputs:

- A reusable dynamic cash-overlay backtest tool.
- A reusable benchmark beta exposure audit tool.
- Evidence that the public risk-filter bridge family has a measurable residual spread after benchmark beta control.
- Evidence that the same family remains unacceptable as a standalone long-only profitable factor.

## Reject Reason Histogram

- `overlap_adjusted_sharpe_too_low`: 6 portfolio/overlay cases at the best-factor summary level.
- `absolute_drawdown_too_high`: static exposure cases and dynamic overlay cases still fail the spirit of the risk gate.
- `market_beta_dominates_long_only_returns`: all 3 beta-audit cases have R2 above 0.991.
- `translation_layer_not_yet_tradable`: all 3 beta-audit cases need a hedged/spread audit before any promotion discussion.

## Main Finding

The project did not waste this three-round block, because it changed the diagnosis:

Before Round73, this family looked like a weak defensive long-only signal. After Round73, the better description is:

`small stock-selection spread embedded inside a high-beta long-only basket`.

That is an important distinction. The next step should not be more windows, more risk-off thresholds, or more public risk-filter variants. It should be a translation-layer audit that asks whether the spread can be monetized after realistic costs and constraints.

## Stop-Loss Decisions

Do not continue:

- static exposure scaling as alpha improvement;
- short-lookback dynamic market-state overlays for this family;
- more long-only cash-overlay parameter tuning;
- more `risk_filter_bridge_*` variants before the hedged/spread audit.

Keep only as spread research leads:

- `risk_filter_bridge_agreement_20`
- `risk_filter_bridge_anti_obv_weighted_20`

Demote:

- `risk_filter_bridge_equal_20`, because it is weaker on both dynamic total return and residual Sharpe.

## Process Adjustment

The next cycle must keep the same governance rule the user specified:

- every 3 rounds: review evidence, reject reasons, and direction ROI before continuing;
- every 10 rounds: package lightweight results and push through the safe-sync flow after validation;
- every new family: compare against public-method patterns before spending compute;
- every weak direction: stop after one failed batch unless a new translation layer changes the question.

## Next Direction

Run a beta-hedged spread translation audit for the two remaining public risk-filter bridge leads.

Pre-registered thesis:

The useful signal may live in the spread between the kept basket and its equal-weight benchmark, not in the absolute long-only return stream. The next test must include costs, turnover, capacity, beta exposure, drawdown, overlap-aware statistics, and fold stability.

If the spread audit fails, hibernate the public risk-filter bridge family and rotate to a different public-method factor family.
