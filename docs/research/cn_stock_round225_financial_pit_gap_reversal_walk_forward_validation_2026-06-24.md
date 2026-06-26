# CN Stock Round225 Financial PIT Gap Reversal Walk-Forward Validation

- Date: 2026-06-24
- Machine/task: office_desktop / factor_validation
- Source audit: `docs/research/cn_stock_round224_financial_pit_post_announcement_gap_reversal_walk_forward_preflight_2026-06-24.md`
- Stage: financial_pit_post_announcement_gap_reversal_walk_forward_cost_capacity_regime_validation
- Promotion allowed: false

## Execution Control

The first full-grid attempt used the Round224 frozen grid directly and was stopped after exceeding 10 minutes. That was a process issue: full cost/capital expansion is too expensive before a cheap sentinel confirms the family is viable.

The CLI was changed so default execution uses a sentinel grid:

- TopN: 20
- Holding period: 5
- Rebalance interval: 5
- Cost: 10 bps
- Capital: 1,000,000 CNY

The full grid remains available only through explicit `--full-grid`.

## Sentinel Result

Output: `data/reports/financial_pit_post_announcement_gap_reversal_walk_forward_validation_round225_sentinel_20260624`

- Cases: 3
- Accepted: 0
- Rejected: 3
- Fold rows: 12
- Capacity-limited trades: 118 per case at 1,000,000 CNY
- Worst drawdown: about -66% to -68%
- Promotion candidates: 0

Even though mean test total return was positive around 20%-23%, all candidates failed because fold-level losses, drawdown, and capacity violations were too severe.

## Capacity Repair Probe

Output: `data/reports/financial_pit_post_announcement_gap_reversal_walk_forward_validation_round225_cap100k_top20_50_20260624`

This probe reduced capital to 100,000 CNY and tested TopN 20 and 50.

- Cases: 6
- Accepted: 0
- Rejected: 6
- Capacity-limited trades: 0
- Best mean test total return: 29.86%
- Best mean test overlap-adjusted Sharpe: 1.162
- Worst drawdown: about -63% to -66%
- Accepted folds: 2 of 4 for all top cases

Lower capital fixed the capacity problem but did not fix cycle instability or drawdown. Fold 1, covering 2019-2020, lost roughly 49%-56% across the candidates. Fold 2 was profitable but still breached the hard drawdown limit around -52%.

## Audit Conclusion

This family has a real-looking residual IC and positive average test return, but it is not currently usable:

- 0 accepted walk-forward cases
- 0 promotable factors
- Capacity can be repaired by reducing capital, but drawdown and early-cycle failure remain
- Positive average return is misleading because fold-level failure is severe

Next direction: `round226_rotate_or_repair_gap_reversal_after_walk_forward_failure`.

Do not expand the gap-reversal grid unless a new preregistered repair specifically targets fold-1 regime failure and drawdown control without reading final holdout.
