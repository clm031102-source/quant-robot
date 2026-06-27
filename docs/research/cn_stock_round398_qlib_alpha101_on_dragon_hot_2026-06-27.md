# CN Stock Round398 - Qlib Alpha101 On Dragon-Hot

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round398 tested whether a public Alpha101/Qlib style signal can improve the current Dragon-Hot event lane.

The key process change is that public factors should not always be forced into cash filters. The first cash-filter projection showed that the selected Qlib quantiles were profitable, so the useful interpretation is an entry exposure tilt, not an exclusion rule.

## Inputs

- Selected trades: `data/reports/round338_24h_profit_sprint_turnover_low_replacement_filters_quarantine_corrected_20260627/replace_drop_turnover_f_low10_trades_with_tradeability.parquet`
- Dragon-Hot official template: `data/reports/round383_24h_profit_sprint_dragon_tiger_official_template_projection_20260627/cash_dragon_hot_chase_20d_official_template_period_returns.csv`
- Public factor: `qlib_alpha158_return_std_position_blend_20`
- Public factor source: `data/reports/round398_24h_profit_sprint_public_alpha101_source_for_dragon_hot_20260627`
- Cash projection: `data/reports/round398_24h_profit_sprint_qlib_alpha101_on_dragon_hot_projection_20260627`
- Tilt projection: `data/reports/round398_24h_profit_sprint_qlib_alpha101_tilt_on_dragon_hot_projection_20260627`
- Wrapped events: `data/reports/round398_24h_profit_sprint_qlib_alpha101_tilt_vt6_zz500_projection_20260627`

## Tooling Added

- `scripts/run_shortlist_public_factor_entry_tilt.py`
- `build_public_factor_entry_tilt_audit`
- `parse_public_factor_tilt_spec`
- `write_public_factor_entry_tilt_audit`

The tilt tool reuses the same point-in-time public-factor join, Dragon-Hot pre-exclusion, official-template projection, and unmatched-contribution diagnostics as the cash-filter path.

## Factor Source Coverage

| Factor | Target Pairs | Matched | Missing Share |
|---|---:|---:|---:|
| `qlib_alpha158_return_std_position_blend_20` | 26,450 | 26,400 | 0.189% |

This is much cleaner than the ADX source from Round391/393.

## Cash Filter Result

Qlib cash filters did not improve high-return performance. The flagged quantiles had positive matched contribution, so cashing them reduced annualized return.

| Candidate | Ann. | Total | Overlap | Max DD | Blockers |
|---|---:|---:|---:|---:|---|
| Dragon-Hot official base | 5.94% | 1.5979 | 0.454 | -32.87% | none |
| `cash_public_qlib_a158_top10` | 5.64% | 1.4801 | 0.481 | -27.83% | none |
| `cash_public_qlib_a158_top15` | 5.46% | 1.4116 | 0.493 | -25.78% | none |

Interpretation: this public factor does not identify bad entries to remove inside the Dragon-Hot lane. It identifies entries that can tolerate more exposure.

## Tilt Result

The strict unblocked tilt candidates were top decile/top 15% with 1.25x or 1.50x selected-entry exposure.

After reusing the Round384 vol-target and ZZ500 wrapper:

| Candidate | Total | Ann. | Sharpe | Overlap | Max DD | Leave-One-Year Min Ann. |
|---|---:|---:|---:|---:|---:|---:|
| `qlib_top15_m150_vt6_zz500_mult_1.00` | 1.9530 | 6.76% | 0.962 | 0.518 | -30.52% | 4.09% |
| `qlib_top10_m150_vt6_zz500_mult_1.00` | 1.9015 | 6.65% | 0.969 | 0.522 | -29.79% | 4.05% |
| `qlib_top15_m125_vt6_zz500_mult_1.00` | 1.8819 | 6.61% | 0.974 | 0.525 | -29.53% | 4.03% |
| `qlib_top10_m125_vt6_zz500_mult_1.00` | 1.8565 | 6.55% | 0.978 | 0.527 | -29.16% | 4.01% |
| `dragon_hot_100` reference | 1.8120 | 6.45% | 0.987 | 0.532 | -28.57% | 3.96% |

## Decision

Advance `qlib_top10_m150_vt6_zz500_mult_1.00` to Round399 audit.

It is the best usable high-return tilt because it improves total and annualized return versus `dragon_hot_100` while staying just inside the user's roughly 30% drawdown tolerance. `top15_m150` is useful as an aggressive reference but is not the preferred observation because it crosses -30% drawdown.
