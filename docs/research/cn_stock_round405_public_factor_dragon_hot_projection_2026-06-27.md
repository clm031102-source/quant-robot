# CN Stock Round405 - Public Factor Dragon-Hot Projection

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round405 tested whether public factors can improve the frozen Dragon-Hot event lane as:

- selected-entry cash filters;
- selected-entry 1.50x exposure tilts.

This explicitly avoided treating raw public technical indicators as standalone profitable factors.

## Inputs

- Base template: `data/reports/round383_24h_profit_sprint_dragon_tiger_official_template_projection_20260627/cash_dragon_hot_chase_20d_official_template_period_returns.csv`
- Selected trades: `data/reports/round338_24h_profit_sprint_turnover_low_replacement_filters_quarantine_corrected_20260627/replace_drop_turnover_f_low10_trades_with_tradeability.parquet`
- Public factor source: `data/reports/round404_24h_profit_sprint_all_public_factor_source_for_dragon_hot_20260627/public_factor_values_for_shortlist.parquet`
- Dragon-Tiger source: `data/processed/round232_dragon_tiger_attention_reversal_20260624`

## Cash Filter Result

Output: `data/reports/round405_24h_profit_sprint_all_public_factor_cash_filter_on_dragon_hot_20260627`

Base template:

- annualized return: 5.94%
- total return: +159.79%
- overlap Sharpe: 0.454
- max drawdown: -32.87%

Best unblocked cash filters:

| Candidate | Annualized | Overlap Sharpe | Max Drawdown | Blockers |
|---|---:|---:|---:|---|
| `cash_public_alpha101_open_close_pressure_fade_10_top10` | 6.17% | 0.523 | -27.22% | none |
| `cash_public_alpha101_vwap_proxy_reversion_liquid_20_top10` | 6.14% | 0.520 | -27.32% | none |
| `cash_public_alpha101_intraday_close_position_reversal_top10` | 6.10% | 0.518 | -27.35% | none |

## Tilt Result

Output: `data/reports/round405_24h_profit_sprint_all_public_factor_tilt_on_dragon_hot_20260627`

Best high-return tilts before wrapper:

| Candidate | Annualized | Overlap Sharpe | Max Drawdown | Blockers |
|---|---:|---:|---:|---|
| `tilt_public_alpha101_open_close_pressure_fade_10_bottom10_m150` | 6.72% | 0.483 | -32.56% | none |
| `tilt_public_alpha101_vwap_proxy_reversion_liquid_20_bottom10_m150` | 6.70% | 0.481 | -32.54% | none |
| `tilt_public_alpha101_intraday_close_position_reversal_bottom10_m150` | 6.63% | 0.477 | -32.52% | none |

## Decision

Advance both paths to Round406:

- Cash filters are cleaner risk-adjusted candidates.
- Tilts are aggressive high-return observations and require vt6/ZZ500 wrapper audit before simulation consideration.

Sparse Supertrend/Smart-money/OBV results remain diagnostics only because missing shares are too high.
