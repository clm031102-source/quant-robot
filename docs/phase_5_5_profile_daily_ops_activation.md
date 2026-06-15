# Phase 5.5 Profile Daily Ops Activation

This phase activates the selected Phase 5.4 paper profile inside Daily Ops.

It does not enable live trading. It turns the optimizer result into a repeatable research-to-paper operating candidate with visible parameters, paper simulation risk, advisory tickets, and explicit safety boundaries.

## Command

```powershell
python scripts\run_daily_ops.py --paper-profile-pack data\reports\paper_profile_optimizer\paper_profile_optimizer_pack.json --output-dir data\reports\daily_ops
```

When a selected paper profile is provided, Daily Ops now:

- applies the selected profile's sizing parameters to signal generation;
- applies the selected profile's sizing and drawdown guard parameters to paper simulation;
- uses the selected risk tier's drawdown limit unless a command-line limit is explicitly provided;
- records the activated profile in `daily_ops_pack.json`, Markdown, CSV summary, and GUI snapshots.

## Current Activated Profile

- candidate: `CN_ETF_liquidity_10_top1_cost5_reb5`
- profile: `cap60_guard12_cd3`
- risk tier: `aggressive_growth`
- max asset weight: `0.60`
- max gross exposure: `1.00`
- min cash weight: `0.00`
- max drawdown guard: `0.12`
- guard cooldown periods: `3`

## Current Daily Ops Result

- stage: `phase_5_5_profile_daily_ops_activation`
- run date: `2026-06-14`
- decision status: `paper_ready`
- paper trading allowed: `true`
- live boundary allowed: `false`
- non-manual blocking reasons: none
- manual blocker still present: `manual_live_review_not_enabled`
- advisory tickets: `1`
- total return: `0.9393583013097269`
- max equity drawdown: `-0.25203058064713424`
- ending equity on 100000 initial cash: `193935.8301309727`
- guard events: `712`
- execution blocks: `0`

Interpretation: the project now has an operational paper candidate for the user's early aggressive-growth phase. It is still not a live-trading system. The next step is observation discipline: daily drift checks, data freshness checks, stop rules, and recent-market validation with Tushare-adjusted data.

## Next Push

- add a paper observation ledger for the activated profile;
- add daily stop-condition evaluation for drawdown, stale data, missing bars, and profile drift;
- refresh recent ETF data through Tushare and rerun the activated profile;
- compare aggressive, balanced, and capital-preservation versions before any live-broker discussion.

