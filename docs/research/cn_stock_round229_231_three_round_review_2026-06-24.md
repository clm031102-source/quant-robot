# CN Stock Round229-231 Three-Round Review - 2026-06-24

## Scope

This review closes the required three-round audit block after Rounds 229, 230, and 231. Scope remains CN A-share stock cross-sectional alpha research. This is not ETF rotation, not a portfolio promotion memo, and not live trading.

## Executive Decision

Rounds 229-231 produced no promotable or paper-ready factor:

- Round229 tested public anomaly residual ensembles and found 0 residual research leads.
- Round230 tested liquidity-shock-recovery factors and found 0 residual research leads.
- Round231 tested index-rebalance passive-flow events and found 0 multiple-testing research leads.

The next round must rotate. It must not tune public anomaly weights, liquidity-shock windows, or index-rebalance directions after reading results.

Selected Round232 direction:

```text
round232_dragon_tiger_attention_reversal_event_preregistration
```

Selected family:

```text
dragon_tiger_attention_reversal_event
```

## Round Results

| Round | Direction | Candidates / Tests | Main Result | Decision |
|---:|---|---:|---|---|
| 229 | Public anomaly residual ensemble | 4 factors, h5 residual screen | Raw/neutral IC existed, but residual IC was weak and style exposure high | hibernate public anomaly residual ensemble unless new exposure repair exists |
| 230 | Liquidity shock recovery | 5 factors, h5 residual screen | Best residual IC only 0.0161 with yearly instability | hibernate liquidity shock recovery without orthogonal repair |
| 231 | Index rebalance passive flow | 5 factors, 10 event IC tests | 0 research leads; opposite-sign raw diagnostics; weak FDR/ICIR | hibernate passive-flow same-direction index-rebalance path |

## Failure Histogram

- `residual_ic_below_threshold`: Round229 and Round230.
- `high_style_or_implementation_exposure`: Round229 and Round230.
- `yearly_instability`: Round229 and Round230.
- `event_cluster_or_size_neutral_failure`: Round231.
- `raw_or_industry_neutral_ic_not_enough`: all three rounds.
- `portfolio_grid_blocked_before_validation`: all three rounds.

## Bright Data

There were useful diagnostics, but none are promotion evidence:

- Round229 showed public anomaly agreement has raw cross-sectional information, but it remains entangled with implementation/style exposure.
- Round230 showed range-shock recovery has positive raw/industry-neutral IC, but the residual signal is too weak and unstable.
- Round231 showed index-rebalance event data can be made PIT-safe and long-cycle auditable; the empirical same-direction passive-flow thesis failed.

## Method Lessons

The improved process worked:

- all three rounds used pre-registration or explicit family controls;
- no round jumped from raw IC to a TopN portfolio grid;
- long-cycle residual or PIT event screens prevented false promotion;
- failed directions were recorded into the startup contract.

The main remaining inefficiency is data-source selection. The last three rounds tested broad public/style/technical or event-supply mechanisms that are either common beta or crowded. Round232 should use a different information source with a clear PIT publication timestamp.

## Round232 Direction

Round232 will test Tushare 龙虎榜 public disclosure events:

- `top_list`: daily Dragon-Tiger list rows, public after close;
- `top_inst`: institutional seat trading detail, public after close.

Hypothesis:

Retail/speculative attention and institutional seat imbalance after an abnormal-trading disclosure can create short-horizon reversal, continuation, or liquidity-normalization effects. This is not raw moneyflow; it is a public event-disclosure surface with a known availability lag.

Hard controls:

- signal date must be the first open trade date after the `trade_date` disclosure;
- same-day trading is forbidden;
- portfolio grid is forbidden before event coverage audit and PIT IC/neutral gates;
- all factor x horizon tests count for multiple testing;
- if coverage is sparse or 0 research leads survive, rotate rather than tune reasons/windows.

## Forbidden Follow-Ups

- no public-anomaly ensemble weight or window tuning after Round229;
- no liquidity-shock recovery parameter expansion after Round230;
- no index-rebalance direction flip after Round231;
- no adding index-rebalance baskets after zero leads without a new pre-registered thesis;
- no event portfolio grid before PIT availability, industry/size neutralization, cost/capacity, regime, and final-holdout gates.

## Safety

Research-to-review only. No broker connection, no live account reads, no order placement, and no automatic live trading.
