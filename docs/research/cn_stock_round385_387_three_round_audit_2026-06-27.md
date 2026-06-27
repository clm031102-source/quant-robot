# CN Stock Round385-387 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## What Was Tested

| Round | Direction | Result |
|---:|---|---|
| 385 | Public price-volume selected-entry filters | Rejected; weak-close was slightly positive but too small |
| 386 | Broad CN market-temperature exposure overlays | Rejected for return objective; useful only as defensive reference |
| 387 | Self-risk budget overlays on `dragon_hot_100` | Promoted one risk-budget observation lane |

## Main Finding

The most useful result in this block is not another stock-selection factor. It is a repeatable portfolio/risk-budget rule:

`dragon_hot_100_self_roll21_sum_neg_half`

Rule:

Half exposure when the prior 21-event strategy return sum is negative.

Why it matters:

- full-sample total return improves from +181.20% to +193.10%;
- annualized return improves from 6.45% to 6.71%;
- overlap Sharpe improves from 0.532 to 0.617;
- max drawdown improves from -28.57% to -15.46%;
- ZZ500 hedged overlap improves from 0.843 to 0.979;
- ZZ500 hedged max drawdown improves from -13.28% to -9.49%.

The caveat:

OOS mean annualized return is lower than baseline: 7.20% versus 8.02%. This makes it a risk-budget observation, not a pure alpha replacement.

## Direction Audit

Round385 answered whether public technical "bad-state" filters can remove bad selected entries. The answer was mostly no. The current low-turnover basket often earns money from ugly-looking rebound/downtrend states, so simple public price-volume filters can accidentally remove profitable trades.

Round386 answered whether broad market temperature can create extra return. It did not. High-dispersion scaling reduced drawdown, but it gave up return and was inferior to existing ZZ500 risk-off lanes for the main objective.

Round387 was the productive turn. Instead of asking "which selected stock should be filtered," it asked "when should the strategy temporarily spend less risk?" That is more aligned with the current evidence because the shortlist already has a working but drawdown-sensitive return stream.

## Decisions

Add to simulation shortlist:

`primary_high_return_dragon_hot_chase_self_risk_roll21`

Status:

`simulation_shortlist_risk_budget_observation`

Keep existing default/high-return lane:

`primary_high_return_dragon_hot_chase`

Why:

- it still has stronger OOS return;
- user tolerance allows roughly 30% drawdown;
- the self-risk version should be a risk-profile competitor in simulation, not an automatic replacement.

Do not add:

- Round385 price-volume filters;
- Round386 market-temperature overlays;
- cash-heavy Round387 self-risk policies.

## Process Upgrades

New repeatable tools:

- selected-trade price-volume entry-filter projection;
- market-temperature event overlay projection output pack;
- self-risk event overlay suite;
- event beta audit for frozen event-return sources.

New rule before simulation handoff:

Every high-return event lane should be tested through the self-risk suite and event beta audit. A candidate can be promoted as a risk-budget lane only if it improves drawdown materially without destroying full-sample and OOS return.

## Next Direction

Continue mining, but the next highest-value directions are:

1. event filters with economic timing, such as unlock, pledge, buyback, shareholder reduction, dividend, and forecast revision;
2. industry/style exposure constraints around the existing low-turnover family, because current candidates are related variants;
3. ETF-aware macro/risk-budget profiles for simulation, using ETF data for exposure control rather than stock selection;
4. capacity and execution stress for the new self-risk lane before any paper-simulation handoff.
