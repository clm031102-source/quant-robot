# CN Stock Negative-IC Trend Accumulation Prescreen Round107

Date: 2026-06-22

## Scope

Round107 replayed the 10 Round106 pre-registered inverse trend/amount accumulation candidates on the CN stock long-cycle authority data. This is a statistical prescreen only. It does not promote any factor to paper-ready or live use.

The run preserved the user risk clarification: a drawdown near 30 percent can be acceptable when return quality is strong, but drawdown tolerance does not waive capacity, extreme-trade, cost, execution, lookahead, or multiple-testing gates.

## Command

```powershell
python scripts\run_negative_ic_trend_accumulation_prescreen.py --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\negative_ic_trend_accumulation_prescreen_round107_20260622 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 5,20 --execution-lag 1 --min-cross-section 30 --min-ic-observations 20 --min-signal-date-amount 10000000
```

## Data Window

- Bar assets: 5,707
- Bar rows: 10,785,537
- Bar date range: 2015-01-05 to 2025-12-31
- Signal date range: 2015-02-02 to 2025-12-31
- Label date range: 2015-01-05 to 2025-12-23
- Final 2026 holdout included: false

## Summary

- Candidates: 10
- Factor names with rows: 10
- Factor rows: 100,177,920
- Label rows: 21,417,227
- Aligned rows: 198,871,948
- Tests: 20
- FDR-significant tests: 20
- Research leads: 1
- Promotion allowed candidates: 0

## Research Lead

| Factor | Horizon | Mean IC | ICIR | t-stat | IC>0 | Q5-Q1 | Monotonicity | Top turnover | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| overheat_avoidance_relative_strength_60 | 20 | 0.0417 | 0.309 | 15.75 | 60.9% | 0.0519 | 0.700 | 18.1% | research lead only |

Interpretation: the useful signal is not the whole inverse trend/amount family. The only lead is a 60-day relative-strength overheat avoidance score at the 20-day horizon. Its IC and quantile spread pass the prescreen gate, while turnover is moderate. It still has the blocker `promotion_requires_later_walk_forward_cost_capacity_regime_gates`.

## Important Non-Leads

- `overheat_avoidance_composite_20_60` had stronger IC at 20 days (0.0637, ICIR 0.477) but failed monotonicity with only 0.100, so it is not a lead.
- `anti_money_pressure_efficiency_20`, `anti_volume_weighted_momentum_quality_20`, and `anti_turnover_expansion_momentum_10_40` had positive IC but negative Q5-Q1 spread and weak or negative monotonicity, so their ranking shape is not portfolio-safe.
- Short-horizon 5-day variants generally failed ICIR, Q5-Q1, or monotonicity gates.

## Decision

Next direction: `round108_negative_ic_trend_accumulation_lead_dedup`.

Allowed next work:

- Correlation de-duplication of `overheat_avoidance_relative_strength_60` against existing price-volume, low-vol reversal, momentum, turnover, and liquidity factors.
- Capacity and extreme-trade diagnostics before any portfolio conversion.
- If still distinct, a costed walk-forward bridge can be designed.

Rejected next work:

- Same-family weight/window tuning after seeing Round107.
- Portfolio grid before correlation de-duplication.
- Treating drawdown tolerance as a waiver for capacity or extreme-trade gates.
- Promoting `overheat_avoidance_composite_20_60` from IC alone while monotonicity is weak.

## Conclusion

Round107 produced 1 useful research lead out of 10 candidates. This is a meaningful improvement over the prior fully rejected positive trend/amount direction, but it is not a profitable strategy yet. The correct next move is narrow validation of the single lead, not broad same-family expansion.
