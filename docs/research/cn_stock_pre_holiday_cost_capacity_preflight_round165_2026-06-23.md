# CN Stock Pre-Holiday Cost Capacity Preflight Round165

## Executive Summary

- Source residual prescreen: `docs/research/cn_stock_cn_calendar_seasonality_residual_prescreen_round164_2026-06-23.md`.
- Stage: cost/capacity preflight for the single frozen Round164 lead.
- Factor: `pre_holiday_liquidity_avoidance_5_3`.
- Data window: 2015-01-05 to 2025-12-31.
- Signal rows: 749,675.
- Signal dates: 210.
- Cases tested: 12 cost/capital combinations.
- Hard-blocked cases: 12.
- Walk-forward candidates: 0.
- Promotion candidates: 0.
- Next direction: `round166_calendar_seasonality_hibernation_after_cost_capacity_failure`.

Round165 did not find a tradable calendar-seasonality candidate. The best case had positive long-cycle return, but failed the overlap-adjusted quality gate and calendar holding gate. Capacity limitations also appeared at larger capital levels. This means the calendar-seasonality family should be hibernated instead of tuned further.

## Frozen Test Design

The preflight intentionally did not tune the Round164 lead. It used a single frozen factor and a small execution stress grid:

| Field | Value |
|---|---:|
| Factor | `pre_holiday_liquidity_avoidance_5_3` |
| TopN | 100 |
| Holding period | 5 |
| Rebalance interval | 1 signal date |
| Execution lag | 1 |
| Periods per year | 21.0 |
| Cost bps | 5, 10, 20 |
| Portfolio value | 100k, 500k, 1m, 5m |
| Market impact bps | 10 |
| Minimum signal amount | 10,000,000 |
| Max participation rate | 1% |
| Min overlap-adjusted Sharpe | 0.5 |

## Leaderboard Read

| Cost | Capital | Total Return | Annualized | Sharpe | Overlap Sharpe | MaxDD | Win Rate | Capacity Limited Trades | Decision |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 5 bps | 100k | 48.29% | 2.85% | 0.594 | 0.443 | -10.66% | 55.1% | 0 | reject |
| 5 bps | 500k | 48.27% | 2.85% | 0.594 | 0.442 | -10.66% | 55.1% | 0 | reject |
| 5 bps | 1m | 48.26% | 2.85% | 0.593 | 0.442 | -10.66% | 55.1% | 1 | reject |
| 5 bps | 5m | 48.10% | 2.85% | 0.592 | 0.441 | -10.67% | 55.1% | 4 | reject |
| 10 bps | 100k | 42.23% | 2.55% | 0.534 | 0.398 | -10.83% | 54.4% | 0 | reject |
| 10 bps | 5m | 42.05% | 2.54% | 0.532 | 0.397 | -10.83% | 54.4% | 4 | reject |
| 20 bps | 100k | 30.83% | 1.94% | 0.414 | 0.310 | -11.15% | 53.4% | 0 | reject |
| 20 bps | 5m | 30.67% | 1.93% | 0.412 | 0.308 | -11.16% | 53.4% | 4 | reject |

The best raw-looking case is the 5 bps / 100k case: total return 48.29%, annualized return 2.85%, Sharpe 0.594, max drawdown -10.66%, and win rate 55.1%. It still failed because the overlap-adjusted Sharpe was only 0.443, below the 0.5 preflight threshold.

## Why The Cost Grid Failed

1. **Overlap-adjusted quality was below gate.**

   The strategy only trades around sparse pre-holiday states. Raw Sharpe overstates the quality because nearby holding windows and clustered event periods are not fully independent. After overlap/autocorrelation adjustment, the best Sharpe fell to 0.443 and the 20 bps cases fell near 0.31.

2. **The annualized return was too low for a promotion path.**

   The total return looks respectable because the sample covers roughly 11 years, but the best annualized return was only 2.85%. That is not enough to justify a standalone CN stock alpha path after execution frictions.

3. **Costs degraded the signal cleanly.**

   Increasing cost from 5 bps to 10 bps cut total return from about 48.3% to about 42.2%. Increasing cost to 20 bps cut it to about 30.8%. A robust edge should not depend on the cheapest execution assumption when the signal is sparse.

4. **Capacity risk appeared before the factor became useful.**

   Capacity-limited trades were already present at 1m and 5m capital. This is not catastrophic by itself, but it blocks the "just scale it" argument because the signal does not have enough overlap-adjusted quality before capacity stress.

5. **The calendar holding gate filtered trades.**

   The backtest recorded 90 calendar-limited trades. That indicates the factor is mechanically tied to calendar windows where holding/execution constraints matter. This is a hard warning against expanding holiday windows after seeing the result.

## Decision

Do not send `pre_holiday_liquidity_avoidance_5_3` to walk-forward validation. Do not tune pre-holiday windows, cost assumptions, or TopN to rescue it.

The correct follow-up is to hibernate the calendar-seasonality family and rotate to a new family or a data-feed audit that can unlock genuinely new information. Total return alone is not a promotion criterion, and drawdown tolerance does not waive overlap-adjusted quality, cost, capacity, or calendar holding gates.

