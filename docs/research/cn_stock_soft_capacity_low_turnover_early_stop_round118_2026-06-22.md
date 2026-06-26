# CN Stock Soft-Capacity Low-Turnover Early Stop Round118 - 2026-06-22

## Scope

This round re-opened the low-turnover question raised by the latest review:

- `turnover_rate_low` and `turnover_rate_f_low` had strong raw total return and Sharpe in Round83.
- They were not promotable because the raw versions were capacity/extreme-trade contaminated.
- The user can tolerate roughly 30% drawdown, but capacity, extreme-return, and execution gates remain hard gates.

Instead of promoting the raw factors, Round118 ran the already pre-registered soft-capacity bridge:

- `turnover_rate_low_adv_blend_mv_bucket_rank`
- `turnover_rate_f_low_adv_blend_mv_bucket_rank`

Command started:

```powershell
.venv\Scripts\python.exe scripts\run_desktop_factor_validation.py --config configs\walk_forward_cn_stock_daily_basic_soft_capacity_turnover_20260620.json --data-root configs\cn_stock_authority_bars_2015_2024.json --source processed-bars
```

## Early Stop Evidence

The run completed the first three OOS folds before being stopped by a budget stop-loss audit.

Audit command:

```powershell
.venv\Scripts\python.exe scripts\run_walk_forward_early_stop_audit.py --walk-forward-root data\reports\walk_forward_cn_stock_daily_basic_soft_capacity_turnover_20260620 --output-dir data\reports\walk_forward_early_stop_audit_soft_capacity_low_turnover_round118_20260622 --min-completed-folds 3 --expected-rows-per-fold 36 --min-positive-relative-rows 1 --min-accepted-rows 1 --min-capacity-clean-rate 0.95
```

Result:

| Metric | Value |
|---|---:|
| Completed OOS folds | 3 |
| Inspected rows | 108 |
| Accepted rows | 0 |
| Positive-relative rows | 0 |
| Capacity-clean rows | 108 |
| Capacity-clean rate | 100.00% |
| Early stop recommended | true |

Best overlap-Sharpe row in each completed fold:

| Fold | Best overlap Sharpe | Best relative return | Accepted? |
|---|---:|---:|---|
| fold_01 | 8.552 | -0.0111 | no |
| fold_02 | 3.073 | -0.3390 | no |
| fold_03 | 12.920 | -0.0381 | no |

## Interpretation

The soft-capacity blend did what it was designed to do on the early folds: it removed the obvious capacity-limited trade problem. That is useful.

But it did not produce tradable alpha evidence:

- 0/108 rows were accepted.
- 0/108 rows had positive benchmark-relative return.
- The strongest overlap-Sharpe rows still lagged the benchmark.

This is exactly why high raw total return is not enough. The raw low-turnover line made money in places that were hard to trade. The soft-capacity bridge made the trades cleaner, but the return edge did not survive enough to justify finishing a long, expensive walk-forward run.

## Decision

Round118 result:

- Promotable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Research lead retained: no standalone soft-capacity low-turnover lead

Decision:

- Stop the soft-capacity low-turnover validation after three clean but non-relative-positive OOS folds.
- Record this as a budget stop-loss, not as a full final rejection of every possible low-turnover expression.
- Do not run more low-turnover TopN/window/liquidity sweeps unless a new construction directly targets relative return while keeping capacity clean.

Next direction:

`round119_lowvol_reversal_liquidity_cluster_incremental_residual_preregistration`

The next line should return to the Round117 conclusion: the public Alpha101/Qlib low-vol/reversal/liquidity cluster contains signal, but direct promotion is redundant. The next useful work is incremental residualization against the known cluster and exposure controls, not another standalone low-turnover sweep.
