# CN Stock PV Corr Reversal Bottom-Exclusion Round60

Date: 2026-06-21
Machine: office_desktop
Branch: codex/factor-validation-cn-stock-long-cycle-20260618
Scope: CN stock cross-sectional alpha
Safety: research-to-review only; no broker connection, no account reads, no order placement, no live trading

## Goal

Test whether the cleanest Round58 public-formula lead, `formula_pv_corr_reversal_20`, is useful as a bottom-quantile exclusion overlay rather than a direct long-only buy factor.

## Inputs

- Config: `configs/experiment_grid_cn_stock_pv_corr_reversal_conversion_round60_20260621.json`
- Factor source: `public_formula_price_volume`
- Factor: `formula_pv_corr_reversal_20`
- Period: 2015-01-05 through 2025-12-31
- Forward horizon: 20 trading days
- Execution lag: 1
- Bottom quantile: 20%
- Rebalance intervals audited: 5 and 10

## Results

### Rebalance 5

Output: `data/reports/bottom_exclusion_overlay_pv_corr_reversal_round60_20260621_reb5`

- Classification: `bottom_exclusion_candidate`
- Date-factor rows: 530
- Input rows: 1,665,578
- Mean full return: 0.0066
- Mean kept return: 0.0085
- Mean bottom return: -0.0009
- Mean overlay excess return: 0.0019
- Overlay t-stat: 8.19
- Positive overlay rate: 68.43%
- Compounded full return: 3.3280
- Compounded kept return: 11.8192
- Compounded bottom return: -0.9529

### Rebalance 10

Output: `data/reports/bottom_exclusion_overlay_pv_corr_reversal_round60_20260621_reb10`

- Classification: `bottom_exclusion_candidate`
- Date-factor rows: 265
- Input rows: 832,387
- Mean full return: 0.0070
- Mean kept return: 0.0091
- Mean bottom return: -0.0012
- Mean overlay excess return: 0.0021
- Overlay t-stat: 6.42
- Positive overlay rate: 70.45%
- Compounded full return: 1.2049
- Compounded kept return: 3.0062
- Compounded bottom return: -0.8154

## Interpretation

`formula_pv_corr_reversal_20` is not currently a promotable buy signal, but it has a repeatable bottom-risk signal. The bottom 20% bucket is persistently damaging across both rebalance schedules. This explains part of the Round58 contradiction: the factor has ranking power, but long-only top-N construction is not the right translation layer yet.

## Decision

- Promotable factor: 0
- Paper-ready factor: 0
- Research lead: 1
- Next step: costed bottom-exclusion portfolio backtest with walk-forward and capacity gates

Do not promote this overlay directly. It is diagnostic evidence only until a portfolio-level exclusion strategy beats costs, capacity, drawdown, and walk-forward gates.
