# CN Stock Public Reference Multi-Family Preregistration - Round127

- Date: 2026-06-22
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Stage: public_reference_multi_family_preregistration
- Source audit: `docs/research/cn_stock_turnover_repair_champion_portfolio_conversion_round126_2026-06-22.md`
- Full output: `data/reports/public_reference_multi_family_preregistration_round127_20260622`
- Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Why This Round Exists

Round126 showed that the low-turnover repair champion had attractive headline total return but failed overlap-aware Sharpe, drawdown, calendar, extreme-trade, and capacity gates. The correct action is family rotation, not more low-turnover parameter tuning.

Round127 therefore pre-registers a fixed public-reference multi-family candidate set. This creates hypotheses only. It does not create profitability evidence.

## Registration Summary

- Candidates: 20
- Families: 9
- Minimum candidates required: 18
- Minimum families required: 6
- Unique candidate names: 20
- Portfolio backtest allowed candidates: 0
- Promotion allowed candidates: 0
- Next required gate: `round128_public_reference_multi_family_prescreen`
- Final holdout touched: no

## Public References Used As Hypothesis Sources

- qlib
- alphalens
- vectorbt
- pyfolio
- worldquant_101_alphas
- public supertrend
- public RSRS

## Candidate Families

| Family | Count | Representative candidates |
|---|---:|---|
| public_formula_alpha101 | 3 | `alpha101_rank_pv_reversal_liquid_20`, `alpha101_decay_reversal_amount_stability_10` |
| qlib_alpha158_feature_blend | 3 | `qlib_alpha158_kbar_momentum_lowvol_20`, `qlib_alpha158_volume_price_resonance_20_60` |
| public_technical_supertrend | 2 | `supertrend_pullback_lowvol_liquid_10_3`, `supertrend_consensus_breakout_efficiency_10_20` |
| public_technical_breakout | 1 | `donchian_breakout_efficiency_liquid_20` |
| public_rsrs_channel | 2 | `rsrs_residual_reversal_liquid_18`, `rsrs_slope_acceleration_quality_18_60` |
| smart_money_flow | 3 | `smart_money_efficiency_reversal_20`, `main_force_divergence_reversal_5_20` |
| qvm_quality_value_momentum | 2 | `qvm_quality_value_momentum_blend_20_60`, `qvm_lowvol_value_momentum_liquid_20_60` |
| volatility_reversal | 2 | `bollinger_bandwidth_reversal_liquid_20`, `rsi_macd_exhaustion_reversal_14_26` |
| market_residual_quality | 2 | `beta_neutral_momentum_residual_quality_60`, `residual_range_contraction_reversal_20` |

## Gate For Round128

Round128 must build the factor matrix and run a prescreen only. It must measure:

- mean Spearman IC
- ICIR
- IC t-stat
- IC positive rate
- quantile spread
- quantile monotonicity
- factor turnover
- coverage by date
- capacity participation
- extreme forward return rate
- source evidence status
- family redundancy correlation

Round128 must count all 20 candidates in multiple-testing accounting. It must not run a broad portfolio grid before statistical leads exist, and it must not read final holdout data.

## Decision

Proceed to `round128_public_reference_multi_family_prescreen`.

Do not resume low-turnover repair unless a genuinely new, nonredundant thesis appears.

