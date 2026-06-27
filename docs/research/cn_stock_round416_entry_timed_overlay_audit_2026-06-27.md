# CN Stock Round416 - Entry-Timed Overlay Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round415 proved that the best Round407 event-return stream can be reconstructed exactly, but cannot be directly handed to paper simulation because volatility/self-risk exposure was keyed by the exit/event return date.

Round416 rebuilds the same Dragon-Hot plus Alpha101 open-close candidate with entry-timed controls:

- source selection: `cash_dragon_hot_chase_20d` plus Alpha101 open-close bottom10 1.5x tilt;
- volatility target: 6% annual vol, 84 closed-event lookback;
- self-risk: half exposure when prior 21 closed source-event return sum is negative;
- all controls use returns closed before each `entry_date`.

## Reusable Code Added

- `src/quant_robot/ops/simulation_shortlist_entry_timed_overlay.py`
- `scripts/run_simulation_shortlist_entry_timed_overlay.py`
- `tests/unit/test_simulation_shortlist_entry_timed_overlay.py`
- `tests/unit/test_simulation_shortlist_entry_timed_overlay_cli.py`

## Outputs

- Entry-timed overlay: `data/reports/round416_24h_profit_sprint_entry_timed_overlay_20260627`
- OOS split: `data/reports/round416_24h_profit_sprint_entry_timed_oos_20260627`
- Block audit: `data/reports/round416_24h_profit_sprint_entry_timed_block_audit_20260627`
- Beta audit: `data/reports/round416_24h_profit_sprint_entry_timed_beta_audit_20260627`

## Full-Sample Result

Candidate:

`alpha101_openclose_dragon_hot_entry_timed_vt6_self_roll21`

| Metric | Value |
|---|---:|
| total return | +143.58% |
| annualized return | 5.53% |
| Sharpe | 0.933 |
| overlap Sharpe | 0.487 |
| max drawdown | -21.54% |
| win rate | 40.65% |
| average vol-target exposure | 0.882 |
| average self-risk exposure | 0.824 |
| average final exposure | 0.723 |
| self-risk guard event share | 35.13% |

Paper-readiness status: pass.

The annualized return drops materially versus the exit-timed Round407 top candidate, but the entry-timed version stays inside the user's 30% drawdown tolerance and has no structural look-ahead blocker.

## OOS Split

30 rolling splits:

| Metric | Value |
|---|---:|
| mean OOS annualized return | 5.32% |
| mean OOS overlap Sharpe | 0.702 |
| worst OOS drawdown | -15.46% |
| positive OOS rate | 90.00% |
| strict pass rate | 76.67% |
| min OOS annualized return | -6.86% |
| min OOS overlap Sharpe | -1.582 |

## Block Dependence

Block audit passed:

- leave-one-year min annualized return: 2.62%;
- leave-one-year min overlap Sharpe: 0.320;
- worst removed year: 2015;
- best-month log share of total: 0.498, below the 0.60 concentration gate.

## Beta Audit

Benchmark: `zz500`

| Metric | Value |
|---|---:|
| beta | 0.0340 |
| R2 | 0.2226 |
| alpha annualized | 5.49% |
| alpha t-stat | 4.25 |
| beta-hedged annualized return | 5.49% |
| beta-hedged overlap Sharpe | 0.749 |
| beta-hedged max drawdown | -11.10% |

## Decision

Add the entry-timed candidate as the paper-simulation-safe version of the Round407 top observation.

Do not use the Round407 exit-timed self-risk stream directly for paper simulation. Its higher return is useful as research context, but Round416 is the cleaner handoff candidate because controls are decided at entry time.

Next direction:

- compare Round416 against the simpler `primary_high_return`, `primary_balanced_zz500_75`, and `primary_defensive_zz500` under the same paper-simulation adapter;
- consider a minimal cost-stress rerun from trade rows if the paper simulator requires 20-30 bps stress;
- keep searching, but treat entry-timed causality as a non-negotiable gate.
