# CN Stock Aggressive Turnover Capacity Audit Round122 - 2026-06-22

## Scope

This round answers the user's question about why two high-return low-turnover factors are not promotable when a roughly 30% drawdown is acceptable.

Source report:

`data/reports/experiment_grid_cn_stock_tushare_daily_basic_alpha_factory_core_round83_20260621/leaderboard.csv`

New audit artifact:

`data/reports/aggressive_turnover_capacity_audit_round122_20260622`

Risk interpretation:

- A drawdown near 30% is not enough by itself to reject a high-return candidate.
- Capacity, participation rate, extreme trade returns, costs, and tradability remain hard gates.
- A capacity-clean repair must keep enough overlap-adjusted Sharpe and benchmark-relative return before it can advance.

## Result

| Raw factor | Raw total | Raw annualized | Raw Sharpe | Raw overlap Sharpe | Raw max DD | Raw win rate | Capacity trades | Max participation | Repair factor | Repair total | Repair overlap Sharpe | Repair relative |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| `turnover_rate_low` | 5127.61% | 21.25% | 1.983 | 0.961 | -18.43% | 59.32% | 1437 | 166.67 | `turnover_rate_low_large_mv` | 66.78% | 0.244 | -23.07 |
| `turnover_rate_f_low` | 5318.72% | 19.86% | 1.872 | 0.902 | -28.56% | 57.43% | 1641 | 8.80 | `turnover_rate_f_low_large_mv` | 79.94% | 0.279 | -22.94 |

## Interpretation

The raw factors are real research leads, not junk:

- Both have strong total return.
- Both have acceptable drawdown under the user's aggressive risk tolerance.
- Both have strong RankIC t-statistics and good raw overlap-adjusted Sharpe.

They are still not promotable because the return source is not execution-clean:

- `turnover_rate_low` has 1437 capacity-limited trades, max participation rate 166.67, and an extreme-trade flag.
- `turnover_rate_f_low` has 1641 capacity-limited trades, max participation rate 8.80, and an extreme-trade flag.
- The existing binary large-market-cap repair removes the capacity block but collapses return quality:
  - total-return capture only 1.30% and 1.50%;
  - overlap-Sharpe capture only 25.39% and 30.94%;
  - benchmark-relative return remains strongly negative.

## Decision

Promotion status:

- Promotable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Research leads retained: 2
- Capacity-repair failed pairs: 2

These factors should be classified as:

`research_lead_capacity_repair_failed`

They should not be classified as fully discarded alpha. They also should not be promoted from raw total return.

## Process Change

The project now has a reusable audit entrypoint:

```powershell
python scripts\run_aggressive_turnover_capacity_audit.py --leaderboard data\reports\experiment_grid_cn_stock_tushare_daily_basic_alpha_factory_core_round83_20260621\leaderboard.csv --output-dir data\reports\aggressive_turnover_capacity_audit_round122_20260622 --target-factor turnover_rate_low --target-factor turnover_rate_f_low --user-max-drawdown-tolerance 0.30
```

This locks the distinction between:

- drawdown tolerance: adjustable by user risk profile;
- capacity/tradability: hard gate;
- large-cap repair: only useful if return quality survives.

## Next Direction

Advance to:

`round123_turnover_continuous_capacity_weight_repair_preregistration`

Rationale:

- The raw low-turnover edge is the strongest historical daily-basic lead.
- A blunt `_large_mv` repair is too destructive.
- One more disciplined repair path is justified if it is preregistered and cheap:
  - continuous ADV / market-cap capacity weighting;
  - smaller-capital sensitivity replay;
  - stricter stale-price and extreme-trade data-quality audit;
  - no raw low-turnover promotion without a capacity-clean repair.

If Round123 cannot keep relative return while removing capacity/extreme-trade blockers, the low-turnover family should stay hibernated and the project should return to financial profitability-quality coverage work.
