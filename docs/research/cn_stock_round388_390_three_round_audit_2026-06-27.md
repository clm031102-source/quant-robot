# CN Stock Round388-390 Three-Round Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## What Was Tested

| Round | Direction | Result |
|---:|---|---|
| 388 | Apply self-risk overlay to primary cost-stress lanes | Useful risk-budget evidence, not default replacement |
| 389 | Cash filters from board, metadata, exchange, HS eligibility | Rejected |
| 390 | Industry/board/exchange/HS contribution concentration | Diagnostic only; no hard bucket factor |

## Main Finding

The best actionable outcome in this block is still the self-risk overlay:

`roll21_sum_neg_half`

It reduces drawdown materially across cost levels, including 30 bps stress, but does not beat the baseline on mean OOS return. That makes it a risk-profile competitor for simulation, not the main high-return default.

The structural-attribute work is mostly negative:

- board exclusions do not improve the current return stream;
- missing metadata exclusions reduce return;
- northbound eligibility separates where the stream lives but does not improve return-risk;
- industry contribution is diversified enough that a hard industry deletion would likely overfit.

## Key Numbers

Round388 cost30 self-risk stress:

- annualized return: 5.57%;
- overlap Sharpe: 0.511;
- max drawdown: -17.36%;
- mean OOS annualized return: 5.52%;
- worst OOS drawdown: -13.52%;
- strict pass rate: 76.67%.

Round389 best non-improving structural filter:

- `cash_missing_stock_market`;
- annualized return: 5.62%;
- overlap Sharpe: 0.428;
- max drawdown: -34.62%;
- matched flagged contribution: +0.0158;
- rejected because return falls versus the official template.

Round390 industry concentration:

- 97 industries audited;
- best industry: 汽车配件, contribution 0.1041, 10.98% share;
- worst industry: 工程机械, contribution -0.0129, -1.36% share;
- top five net contribution share: 31.31%;
- top ten gross contribution share: 38.51%.

## Direction Audit

This block did not find a new independent stock-selection alpha. It improved process quality and clarified what not to do.

Round388 was aligned with the project objective because it tested whether a promising risk-budget rule survives cost pressure. It did.

Round389 was necessary because A-share real trading constraints can kill backtests. The negative result is useful: simple structural deletions are not the source of edge.

Round390 prevents the next common mistake: overfitting an industry rule after seeing one good or bad bucket. The evidence says the current stream has industry tilts, but not a single dominant industry dependency.

## Decisions

Keep in simulation shortlist:

- `primary_high_return`;
- `primary_high_return_dragon_hot_chase`;
- `primary_high_return_dragon_hot_chase_self_risk_roll21`;
- existing defensive ZZ500 lanes.

Do not add:

- cost-stressed self-risk as a replacement default;
- board/metadata/northbound cash filters;
- hard industry bucket filters.

## Process Upgrades

New repeatable tooling:

- trade-attribute cash-filter projection;
- trade group contribution audit;
- self-risk cost stress and OOS comparison around frozen event streams.

New rule:

Before adding any industry/style/board rule to the shortlist, first run contribution concentration by group and by year. A candidate should not be promoted if its apparent edge mostly comes from one bucket or one calendar block.

## Next Direction

The next highest-value work is not more blunt filtering. It should focus on:

1. industry-aware exposure caps or risk budgets, with no parameter search beyond simple pre-registered cap levels;
2. public indicator families with clear behavioral logic, such as SuperTrend, KAMA/ADX trend state, breadth, and volatility compression;
3. corporate event families with timing logic, such as buyback, reduction, unlock, pledge, dividend, and forecast revision;
4. capacity and execution stress for the current simulation shortlist before paper-simulation handoff.
