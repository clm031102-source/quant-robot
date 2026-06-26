# CN Stock Round108 Negative-IC Lead Dedup Audit

Round108 audited the sole Round107 research lead, `overheat_avoidance_relative_strength_60`, before allowing any portfolio grid or parameter tuning. The goal was to decide whether this lead deserved a cost/capacity bridge or whether it was mostly a duplicate of information already rejected or hibernated.

## Scope

- Machine/task context: `office_desktop`, CN stock `factor_validation`.
- Data window: 2015-01-05 to 2025-12-31 bars; 2015-01-12 to 2025-12-30 signals.
- Inputs: 5,707 assets and 10,785,537 bar rows.
- Final holdout: not included.
- Stage: research-to-review only. No broker connection, account read, order placement, or live trading.

## Lead Evidence

Round107 confirmed `overheat_avoidance_relative_strength_60` as the only research lead:

- Horizon: 20 trading days.
- Prescreen IC: positive and statistically meaningful in the Round107 prescreen.
- Prescreen blocker: `promotion_requires_later_walk_forward_cost_capacity_regime_gates`.

Round108 did not invalidate the lead on raw capacity:

| Metric | Value |
|---|---:|
| Top quantile dates audited | 523 |
| Top quantile rows audited | 393,694 |
| Median amount | 101,121,459.50 |
| Median ADV20 amount | 141,095,423.82 |
| Amount breach count | 0 |
| ADV20 breach count | 0 |
| Extreme abs return >= 9.5% rate | 1.75% |
| Extreme abs return >= 20% count | 642 |

This means the lead is cleaner than the earlier raw low-turnover anomaly from a direct liquidity standpoint. The failure is not a simple drawdown preference issue and not a raw capacity failure.

## Dedup Result

The lead was compared against 29 reference candidates across same-family negative trend/amount candidates, positive trend/amount source candidates, and prior capacity-safe price-volume candidates.

| Metric | Value |
|---|---:|
| Compared candidates | 29 |
| Correlation observations | 15,167 |
| Highly redundant candidates | 7 |
| Moderately redundant candidates | 16 |
| Unique candidates | 6 |
| Hard-blocking redundant candidates | 2 |
| Source-lineage redundant candidates | 7 |

Hard blockers:

| Reference family | Factor | Mean corr | Mean abs corr | Max abs corr | Blocker |
|---|---|---:|---:|---:|---|
| `capacity_safe_price_volume` | `price_volume_trend_quality_20_60` | -0.6872 | 0.6876 | 0.8656 | hard blocking redundancy |
| `capacity_safe_price_volume` | `skip5_momentum_lowvol_20` | -0.3273 | 0.3334 | 0.8649 | hard blocking redundancy |

The lead is also strongly opposite to the positive trend source line, especially `liquidity_qualified_relative_strength_60` with mean correlation `-0.8955`. That confirms lineage: Round107 mostly found an inverse version of the prior trend/amount structure, not a new independent return engine.

## Decision

- Promotion allowed: no.
- Cost/capacity bridge allowed: no, not after hard-blocking redundancy.
- Next direction: `round109_family_rotation_after_round108_dedup_failure`.
- Hibernated: `overheat_avoidance_relative_strength_60` as a standalone continuation line.

The correct response is to rotate family, preferably toward a public-reference method with a different source of information, instead of tuning the same inverse trend/amount lead.

## Note On Drawdown Tolerance

The user can accept roughly 30% drawdown when total return, annual return, Sharpe, win rate, and long-cycle evidence are strong. That policy does not waive hard gates for capacity, tradeability, extreme-trade contamination, cost, future-function risk, or hard redundancy. A drawdown can be a soft tolerance; execution feasibility and leakage controls remain hard gates.
