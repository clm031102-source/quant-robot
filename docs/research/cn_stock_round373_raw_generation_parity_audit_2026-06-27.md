# CN Stock Round373 - Raw Generation Parity Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: simulation-readiness audit for the 24h profit-factor sprint. Research-to-review only; no broker, account, order, or live-trading access.

## Why This Round

The simulation shortlist currently has replay checks: event files reproduce the metrics stored in config. That is necessary but not sufficient.

Before simulation handoff, the project also needs a raw-data-to-event generation path. Otherwise the event files are evidence artifacts, not a repeatable production-style research pipeline.

Round373 audits whether the new reusable low-turnover generation tool reproduces the official Round338/Round339 event stream.

## Output

`data/reports/round373_24h_profit_sprint_raw_generation_parity_audit_20260627`

Compared sources:

- official: `data/reports/round339_24h_profit_sprint_replacement_filters_voltarget_wrappers_20260627/replace_drop_turnover_f_low10_base_period_returns.csv`
- generated: `data/reports/round367_24h_profit_sprint_turnover_low_mainboard_prerank_replacement_20260627/replace_drop_turnover_f_low10_entry_cash_after_period_returns.csv`

## Event-Stream Parity

| Metric | Official | Generated |
|---|---:|---:|
| period rows | 834 | 868 |
| total return | +150.65% | +144.38% |
| annualized return | 5.71% | 5.33% |
| Sharpe | 0.779 | 0.738 |
| overlap Sharpe | 0.428 | 0.407 |
| max drawdown | -35.29% | -36.99% |
| win rate | 41.13% | 41.13% |

Date parity:

- union dates: 966;
- overlap dates: 736;
- official dates missing in generated: 98;
- extra generated dates: 132;
- dates with absolute difference above 1 bp: 261;
- max absolute date difference: 0.574%.

## Trade-Level Parity

The trade-level selection is much closer than the event stream:

| Metric | Value |
|---|---:|
| official trade rows | 26,450 |
| generated trade rows | 26,450 |
| common trade keys | 26,150 |
| missing generated trade keys | 300 |
| extra generated trade keys | 300 |
| official entry-allowed rows | 20,382 |
| generated entry-allowed rows | 20,371 |

This means the main gap is not a completely different alpha. It is mostly calendar/aggregation parity, plus a small replacement-filter tie/threshold difference.

## Official Period vs Official Trade Exit Grouping

Even the official trade file grouped by `exit_date` does not exactly match the official period return file:

- official period dates: 834;
- official trade exit dates: 872;
- dates with absolute difference above 1 bp: 44;
- max absolute difference: 0.292%;
- official period return sum: 0.9657;
- trade-exit grouped sum: 0.9482.

So the event stream uses a specific period-calendar normalization beyond a naive `groupby(exit_date)` sum.

## Diagnosis

The raw-to-event generation gap is primarily an event calendar problem:

1. selection is almost the same, but not perfectly identical;
2. naive exit-date grouping creates a different event calendar;
3. the official Round339 event calendar must be treated as a required template until the generation rule is reconstructed and tested.

## Decision

Do not claim raw-data-to-event generation is solved.

Round374 should implement a reusable event-calendar parity layer:

- optionally consume an official calendar template;
- align generated trade returns to the template;
- report missing/extra event dates;
- block promotion when generated metrics differ from the official stream beyond tolerance.

Only after this is passing should the project generate simulation shortlist event streams from raw processed data.
