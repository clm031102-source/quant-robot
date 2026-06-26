# CN Stock Round342 - Trade Capacity Stress

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Purpose

Round342 turns capacity from a single 1,000,000 portfolio-value check into an AUM stress test.

The new reusable tool is:

`scripts/run_trade_capacity_stress.py`

It reads one or more `trades_with_tradeability.parquet` files, scales `participation_rate` by AUM multipliers, and reports capacity breaches against a max participation cap.

Output:

`data/reports/round342_24h_profit_sprint_trade_capacity_stress_20260627`

2026 final holdout remains unused.

## Candidates

| Candidate | Role | Trade Source |
|---|---|---|
| `safer_cash_proxy_no_extra` | Conservative capacity proxy for the safer cash benchmark | Round338 `replace_no_extra_filter` trades |
| `threshold_low05_vol6_candidate` | Safer threshold variant | Round341 5% replacement trades |
| `balanced_low10_vol6_candidate` | Current primary simulation candidate | Round341 10% replacement trades |
| `threshold_low15_aggressive` | Aggressive threshold variant | Round341 15% replacement trades |
| `aggressive_low20_or_pb` | Aggressive replacement research line | Round338 low20-or-PB replacement trades |

Note: the exact `cash_low_turnover_f_bottom20` trade parquet was not available. `safer_cash_proxy_no_extra` is a conservative capacity proxy because the cash filter can only remove entry trades, not add them.

## Capacity Stress

Participation limit: 5% of entry amount.

Base portfolio value: 1,000,000. Multipliers therefore correspond to roughly 1m, 5m, 10m, 20m, 50m, and 100m notional if all else is unchanged.

| Candidate | 20x Max Participation | 20x Breaches | 50x Max Participation | 50x Breaches | 100x P99 Participation | 100x Breaches |
|---|---:|---:|---:|---:|---:|---:|
| `safer_cash_proxy_no_extra` | 2.28% | 0 | 5.70% | 2 | 5.62% | 376 |
| `threshold_low05_vol6_candidate` | 2.46% | 0 | 6.16% | 4 | 5.80% | 446 |
| `balanced_low10_vol6_candidate` | 2.56% | 0 | 6.40% | 6 | 5.98% | 477 |
| `threshold_low15_aggressive` | 4.38% | 0 | 10.94% | 7 | 5.90% | 446 |
| `aggressive_low20_or_pb` | 4.38% | 0 | 10.94% | 3 | 5.91% | 433 |

## Entry Blocking

| Candidate | Entry Allowed | Entry Blocked | Entry Blocked Rate |
|---|---:|---:|---:|
| `safer_cash_proxy_no_extra` | 20,841 | 5,609 | 21.21% |
| `threshold_low05_vol6_candidate` | 20,506 | 5,944 | 22.47% |
| `balanced_low10_vol6_candidate` | 20,382 | 6,068 | 22.94% |
| `threshold_low15_aggressive` | 20,269 | 6,181 | 23.37% |
| `aggressive_low20_or_pb` | 20,151 | 6,299 | 23.81% |

## Interpretation

Capacity is not the binding blocker for the current simulation scale.

All tested candidates are clean at 20x the 1,000,000 base portfolio value under the 5% participation cap. At 50x, breaches appear but are rare:

- balanced candidate: 6 breaches out of 20,382 entry-allowed trades;
- safer proxy: 2 breaches out of 20,841 entry-allowed trades;
- aggressive low20-or-PB: 3 breaches out of 20,151 entry-allowed trades.

At 100x, capacity is no longer clean. The breach rate is roughly 1.8%-2.3% across candidates, and p99 participation sits around or above the 5% cap.

## Decision

Keep the primary simulation candidate unchanged:

`turnover_rate_low Top50 hold20 reb5 cost5 + replace_drop_turnover_f_low10 + entry_cash + vol_target_6_lb84`

Capacity conclusion:

- acceptable for small to medium simulation scale up to roughly 20x the 1,000,000 research notional;
- monitor at 50x because rare tails breach the cap;
- not clean at 100x without additional liquidity sizing, trade slicing, or ADV-aware target weights.

The next blocker remains 2017-2018 regime loss and drawdown, not immediate execution capacity.
