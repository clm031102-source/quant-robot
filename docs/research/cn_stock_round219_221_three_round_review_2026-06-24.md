# CN Stock Round219-221 Three-Round Review

Date: 2026-06-24

Scope: CN A-share stock cross-sectional alpha research. This review covers the latest three factor-family batches after the method/startup-gate optimization. It is not ETF rotation, not a portfolio backtest, and not a promotion memo.

## Executive Decision

Rounds 219-221 tested three mechanism families under long-cycle residual controls:

- Round219: public trend-strength state, including ADX/KAMA/Aroon/WilliamsR-style state variables.
- Round220: industry leader-lag diffusion.
- Round221: FIP / information-discreteness path quality.

Result:

- Implemented/preregistered factor names across the three families: 18.
- Full-sample residual tests: 18.
- Residual research leads: 0.
- Portfolio preflight candidates: 0.
- Promotion candidates: 0.

Decision:

- Stop all direct continuation in the three families.
- Do not run TopN, Sharpe, annual-return, win-rate, or cost/capacity grids on these rejected candidates.
- Preserve the sharded full-cycle residual infrastructure because it improved rigor and runtime feasibility.
- Rotate Round222 to a new orthogonal family: `financial_pit_post_announcement_drift`.

## Round Results

| Round | Direction | Candidates | Best Evidence | Main Failure | Decision |
|---:|---|---:|---|---|---|
| 219 | Public trend-strength state | 6 | Best residual IC around 0.0120, residual ICIR 0.210 | 6/6 residual IC below gate; 6/6 yearly instability; 5/6 high exposure | hibernate |
| 220 | Industry leader-lag diffusion | 6 | `industry_leader_pullback_resilience_10_5` residual IC 0.0262, ICIR 0.374, IC+ 66.45% | raw yearly instability; smoke lead collapsed to residual IC 0.0175 and failed 2025 | hibernate unless new orthogonal thesis |
| 221 | Information discreteness / FIP | 6 | Best residual IC 0.0141, ICIR 0.193 | 6/6 residual IC and ICIR below gate; 6/6 high exposure; 6/6 residual yearly instability | hibernate |

## What Was Useful

The useful output is process and evidence, not alpha:

- The full-cycle sharded residual route now works for heavy 2015-2025 CN-stock factor families.
- The project no longer treats Q1/Q2 smoke, raw IC, or short-window results as profit evidence.
- The research path now blocks portfolio grids before residual IC, yearly stability, reference de-duplication, exposure checks, cost/capacity, and regime coverage.
- Round220 streaming aggregation reduced the need to hold all full-window matrices at once.
- Round221 proved that information-discreteness/FIP is mostly a trend, volatility, and liquidity exposure carrier in this universe.

## Failure Pattern

The last three rounds failed for a shared reason:

- Raw technical or behavioral price-shape signals often look interesting before controls.
- After industry/style residualization, most of the apparent edge collapses.
- The surviving fragments are not stable enough by year.
- Exposure audit repeatedly finds size, liquidity, volatility, return, or amount-trend dependence.

This is evidence that the project should stop spending cycles on more price-shape variants unless a new family has a genuinely new information channel or timing mechanism.

## Why Not Continue FIP

Round221 did not just miss the strict promotion gate. It failed at the research-lead gate:

- Best residual IC was only 0.0141 versus a 0.02 minimum.
- Best residual ICIR was only 0.193 versus a 0.5 minimum.
- Every candidate had high style exposure.
- Every candidate had residual yearly instability.
- 2015 exposed negative or weak behavior across most candidates.

Tuning windows after this would be multiple-testing overfit. A portfolio grid would turn a weak residual diagnostic into a false profit search.

## Round222 Direction

Selected next family:

`financial_pit_post_announcement_drift`

Selected next direction:

`round222_financial_pit_post_announcement_drift_preregistration`

Reason:

This family is orthogonal to the last three failures. It uses event timing and point-in-time availability rather than another price-shape rank. It also directly addresses the user-requested control gap: financial report availability must be based on `ann_date`, `available_date`, and `signal_date`, not report-period end dates.

The family must not repeat the failed direct profitability-quality tuning. It should test post-announcement underreaction, event-day reaction, announcement-lag behavior, and reaction-volume disagreement using strictly lagged event availability.

## Round222 Required Controls

Before any IC or portfolio claim, Round222 must have:

- PIT financial root from Round202 or a newer filtered root.
- `ann_date`, `available_date`, `signal_date`, and `signal_lag_calendar_days` preserved into each factor row.
- No same-day announcement reaction trading; event-day reaction may only be used from the next tradable signal date.
- Financial coverage audit before factor IC, especially if the root still only covers the shard1 full100 universe.
- A-share tradeability mask: ST, suspension, limit-up/down untradable states, new/retiring listings, board restrictions when available.
- Industry/style residual evaluation against size, liquidity, value, volatility, and price-momentum exposures.
- Public reference de-duplication against prior profitability-quality, valuation, low-volatility, reversal, and event families.
- Multiple-testing ledger and no tuning after reading full-sample results.
- No TopN grid before residual IC shape and yearly stability pass.

## Stop-Loss Rules

Round222 must stop or rotate if:

- financial coverage is too narrow for a full-cycle cross-sectional claim;
- the candidates are just direct profitability metrics with new names;
- residual IC collapses after size/liquidity/value/style controls;
- event reaction depends on using same-day close information before it was tradable;
- the best signal only works in one announcement season or one regime;
- the result needs many parameter tweaks to look good.

## Safety

Research-to-review only. No broker connection, no live account reads, no order placement, and no automatic live trading.
