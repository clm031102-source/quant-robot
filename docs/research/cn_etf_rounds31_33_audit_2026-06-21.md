# CN ETF Rounds31-33 Audit

Date: 2026-06-21
Machine: office_desktop
Task: factor_validation
Branch: codex/factor-validation-cn-stock-long-cycle-20260618

## Scope

This audit covers the three work rounds after the new operating rule: every 3 rounds, review evidence and adjust direction.

## Round Summary

| Round | Direction | Cases | Result | Decision |
|---:|---|---:|---|---|
| 31 | Public tail-guard reversal | 4 | 0 accepted, negative OOS Sharpe | Stop expanding |
| 32 | Public price-volume formula family | 10 | 0 accepted, one strong research lead | Keep one candidate |
| 33 | Robustness test for range-contraction breakout | 18 | 0 accepted, positive 5 bps cluster but no IC significance | Pre-register, not promote |

## What Improved

The workflow is now better than the earlier moneyflow-only grind:

- It uses long-cycle walk-forward validation on the CN ETF universe, not short 2023-2024 snippets.
- It rotates factor families instead of staying trapped in one failed direction.
- It records negative evidence instead of endlessly adding parameters.
- It treats adjusted IC significance and cost sensitivity as blockers, even when Sharpe looks good.

## Findings

1. Tail-guard reversal does not fit current CN ETF rotation.

Round31 showed negative annualized return and negative Sharpe across the family. This should not receive more parameter search right now.

2. Range-contraction breakout is the first real lead in this cycle.

Round32 and Round33 both point to `formula_range_contraction_breakout_20`. The best 5 bps cases have positive OOS return, positive relative return, and low drawdown. This deserves more structured validation.

3. The lead is not yet a profitable deployable factor.

All cases fail adjusted IC significance. Cost doubling from 5 bps to 10 bps damages the result sharply. That means the signal is fragile and may not survive real execution assumptions.

4. The next bottleneck is ETF-specific context.

Pure single-ETF price/volume formulas are not enough. ETF rotation usually needs theme/sector breadth, risk-on/risk-off state, and benchmark regime context. The code has an `etf_theme_breadth` factor source, but the current wide ETF data root lacks `metadata/tushare_fund_basic`, so theme mapping is not yet available in this run.

## Direction Change

For the next 3-round block:

- Round34: add or build the missing CN ETF `fund_basic` metadata path so `etf_theme_breadth` can run.
- Round35: run ETF theme breadth walk-forward on the same 264-ETF liquid universe.
- Round36: combine/compare theme breadth with the pre-registered `formula_range_contraction_breakout_20` lead, then audit again.

Guardrails:

- No promotion without adjusted IC evidence or a clear alternative promotion rule documented in advance.
- No more expansion of tail-guard reversal unless a future audit provides a specific reason.
- No more broad parameter sweeps on range-contraction breakout before theme/risk context is tested.
- Keep Top5/Top10 and 5 bps as research settings; treat 10 bps failure as a live-trading warning.

## Current Candidate Ledger

| Candidate | Status | Why |
|---|---|---|
| `formula_range_contraction_breakout_20_top5_cost5_reb10` | Research lead only | Best stability, 4/4 folds, Sharpe 1.83, but adjusted IC p=1.0 |
| `formula_range_contraction_breakout_20_top10_cost5_reb10` | Research lead only | Higher annualized return and win rate, 3/4 folds, but adjusted IC p=1.0 |
| `formula_volume_contraction_momentum_confirmed_20_60` | Watchlist | Positive return/relative return, weaker Sharpe and not significant |
| Tail-guard reversal factors | Retired for now | Negative OOS Sharpe and no significance |
