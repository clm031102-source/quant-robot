# CN ETF Rounds37-39 Audit

Date: 2026-06-21

## Scope

This audit covers the mandated 3-round review block:

- Round37: standalone defensive `low_volatility_*` / `high_liquidity_*`.
- Round38: hard regime-filter preflight and exposure-0.6 replay for `formula_range_contraction_breakout_20`.
- Round39: audit and direction reset.

## Round-Level Summary

| Round | Work | Cases | Accepted | Useful Outcome |
|---|---|---:|---:|---|
| 37 | Defensive low-vol/high-liquidity ETF factors | 48 | 0 | Failed as standalone alpha; keep as risk/capacity components. |
| 38a | Hard positive-momentum regime overlay | 0 | 0 | Blocked by preflight: too few allowed dates. |
| 38b | Range contraction at 0.6 exposure | 12 | 0 | Same lead remains positive but not statistically promotable. |
| 39 | Audit | n/a | n/a | Narrow next direction to range-contraction robustness and composites. |

## Key Findings

Round37 defensive factors are not standalone alpha.

- 48/48 rejected.
- Positive Sharpe rows: 0/48.
- Positive annualized return rows: 1/48.
- Best row: `low_volatility_20_top10_cost5_reb20`, Sharpe -0.0399, annualized return 0.13%, max drawdown -0.46%.
- Interpretation: useful as a defensive/capacity ingredient, not as a primary profit signal.

Hard regime filtering should not be used on this ETF sample.

- Positive-momentum regime filter had median allowed dates far below the project threshold.
- Even 5-day lookback only gave median 10.5 allowed rebalance dates per fold.
- 60/120/180 lookbacks were worse and introduced zero-allowed folds.
- Interpretation: hard regime deletion would create low-power, cherry-picked evidence.

`formula_range_contraction_breakout_20` remains the only serious CN ETF lead.

Original exposure 0.8 Round33:

- 18 cases, 0 accepted, 9 positive Sharpe, 10 positive annualized return, 7 with at least 3 accepted folds.
- Best: `top5_cost5_reb10`, Sharpe 1.8316, annualized 1.91%, relative 6.26%, max drawdown -0.24%, adjusted IC p=1.0.

Exposure 0.6 Round38:

- 12 cases, 0 accepted, 9 positive Sharpe, 9 positive annualized return, 7 with at least 3 accepted folds.
- Best: `top5_cost5_reb10`, Sharpe 1.8334, annualized 1.43%, relative 6.03%, max drawdown -0.18%, adjusted IC p=1.0.

The signal shape is stable under lower exposure, but the promotion blocker remains statistical:

- adjusted IC p-value is still 1.0,
- train performance is weak/mixed,
- 10 bps costs sharply reduce the cluster,
- evidence is still not long-cycle enough.

## Direction Decision

Stop:

- standalone `low_volatility_*` / `high_liquidity_*` mining,
- hard positive-momentum regime filters on this 2020-2024 ETF sample,
- adding unrelated public indicators before resolving the current lead.

Continue:

- `formula_range_contraction_breakout_20` as the primary ETF research lead,
- same-parameter replay and long-cycle validation,
- composites that use low-vol/high-liquidity as tie-breakers or risk stabilizers rather than primary alpha,
- strict cost checks at 5 bps and 10 bps.

## Next Block Plan

Round40:

- Run verification.
- Run safe sync audit.
- Commit and push code/config/docs to GitHub.

Round41:

- Build a pre-registered composite around `formula_range_contraction_breakout_20` plus liquidity/low-volatility tie-breakers.
- Keep the grid small: Top5/10, cost 5/10, rebalance 5/10/20.

Round42:

- Run same-parameter full-sample replay for the best range-contraction rows.
- If longer ETF history is locally available, run long-cycle replay before expanding factor families.

Round43:

- Audit Rounds41-42.
- Decide whether the range-contraction lead graduates to paper-candidate research, stays research-only, or is retired.
