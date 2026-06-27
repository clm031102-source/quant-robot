# CN Stock Round382 - Dragon-Tiger Cash Filter Quickcheck

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock event-factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Turn the Round381 Dragon-Tiger selected-trade risk tags into a naive portfolio-level quickcheck.

Important: this round uses trade-level exit-date aggregation. It is useful for research triage, but not simulation-ready until it reproduces the official event calendar.

## Output

- Quickcheck: `data/reports/round382_24h_profit_sprint_dragon_tiger_cash_filter_quickcheck_20260627`
- OOS split: `data/reports/round382_24h_profit_sprint_dragon_tiger_cash_filter_oos_20260627`
- Calendar parity: `data/reports/round382_24h_profit_sprint_dragon_tiger_naive_calendar_parity_20260627`

## Full-Sample Quickcheck

Naive exit-date aggregation, entry-cash returns:

| Candidate | Total | Ann. | Sharpe | Overlap | Max DD |
|---|---:|---:|---:|---:|---:|
| `naive_entry_cash_base` | +146.29% | 5.35% | 0.747 | 0.411 | -36.26% |
| `cash_dragon_hot_chase_20d` | +154.56% | 5.55% | 0.789 | 0.433 | -34.28% |
| `cash_dragon_net_buy_20d` | +153.66% | 5.53% | 0.788 | 0.432 | -34.07% |
| `cash_dragon_hot_sell_60d` | +153.24% | 5.52% | 0.813 | 0.445 | -29.96% |
| `cash_dragon_net_sell_60d` | +150.47% | 5.45% | 0.821 | 0.448 | -29.53% |

## OOS Quickcheck

Rolling fixed test windows from the reusable OOS split tool:

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| `cash_dragon_hot_chase_20d` | 8.82% | 0.901 | -24.25% | 90.00% |
| `cash_dragon_net_buy_20d` | 8.74% | 0.891 | -24.11% | 90.00% |
| `naive_entry_cash_base` | 8.66% | 0.883 | -24.54% | 90.00% |
| `cash_dragon_hot_sell_60d` | 8.22% | 0.825 | -23.89% | 90.00% |
| `cash_dragon_net_sell_60d` | 8.16% | 0.825 | -23.84% | 90.00% |

## Calendar Parity Gate

The naive generated base remains blocked against the frozen official Round339 base:

- reference dates: 834;
- generated dates: 872;
- missing generated dates: 93;
- extra generated dates: 131;
- date-return drift count: 44;
- total-return drift: -4.36%;
- blockers: missing dates, extra dates, date-return drift, total/Sharpe/overlap/drawdown drift.

## Decision

`cash_dragon_hot_chase_20d` is a real research lead, not a simulation candidate.

Next required work:

1. reconstruct it on the official 834-date event template;
2. rerun block/OOS/cost/beta checks after calendar-safe reconstruction;
3. only then compare it against `primary_high_return` and `primary_defensive_zz500`.
