# CN Stock Public Technical Failure-Reversal Preregistration Round154

## Scope

- Machine/task: office_desktop / factor_validation.
- Market/asset: CN stock cross-sectional alpha.
- Source audit: `docs/research/cn_stock_round151_153_three_round_review_2026-06-23.md`.
- Negative public-reference evidence: `docs/research/cn_stock_public_reference_multi_family_prescreen_round128_2026-06-22.md`.
- Stage: preregistration only; no IC, Sharpe, return, win-rate, drawdown, portfolio, paper-ready, or live claim.

## Why This Round Exists

Round153 produced zero PIT profitability event/revision research leads after FDR, industry, size, liquidity, and Round96 static-reference de-dup gates. The correct next action is family rotation.

Round128 had earlier shown several public trend/breakout candidates were significant in the negative direction. Round154 turns that into a new fixed hypothesis set: public technical trend/breakout failures may be exploitable as reversal/crowding signals in A-shares. This is not direct promotion from negative evidence; it is a fresh preregistered batch counted in new multiple-testing accounting.

## Registration Summary

| Metric | Value |
|---|---:|
| Candidates | 8 |
| Families | 5 |
| Minimum candidates required | 8 |
| Minimum families required | 4 |
| Portfolio backtest allowed | 0 |
| Promotion allowed | 0 |
| Next required gate | `round155_public_technical_failure_reversal_prescreen` |

## Candidate Families

| Family | Candidates |
|---|---|
| public_breakout_failure_reversal | `inverse_donchian_breakout_failure_liquid_20` |
| qlib_efficiency_failure_reversal | `inverse_price_efficiency_failure_liquid_20`, `inverse_volume_price_resonance_failure_20_60` |
| supertrend_failure_reversal | `inverse_supertrend_breakout_failure_10_20`, `supertrend_extension_continuation_repair_10_3` |
| rsrs_failure_reversal | `inverse_rsrs_slope_failure_liquid_18_60`, `rsrs_residual_extreme_reversal_repair_18` |
| qlib_candlestick_failure_reversal | `inverse_kbar_momentum_failure_lowvol_20` |

## Controls

- Liquidity term remains positive in inverse formulas to avoid turning the batch into an illiquid-tail bet.
- Final holdout remains blocked.
- All candidates must be counted in FDR/multiple-testing accounting.
- Any lead must next pass neutralization, reference de-duplication, walk-forward, cost, capacity, and regime gates.

## Decision

Proceed to `round155_public_technical_failure_reversal_prescreen`.

