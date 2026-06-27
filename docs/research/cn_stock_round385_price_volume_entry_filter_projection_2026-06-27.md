# CN Stock Round385 - Price-Volume Entry Filter Projection

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Round385 rotates away from the Dragon-Tiger event family and tests public price-volume ideas as secondary risk filters on the current selected low-turnover basket.

The tested hypothesis is narrow:

- use only information available on `signal_date`;
- identify selected entries with public technical risk states;
- cash those selected entries by subtracting their trade contribution from the frozen official event-return template;
- judge the result against the same official calendar, OOS split, block, and beta checks.

This is not a standalone all-market price-volume factor sweep. Round158 already rejected the standalone price-volume shock-reversal family, so Round385 tests the more practical selected-entry filter use case.

## New Tooling

- `src/quant_robot/ops/shortlist_price_volume_entry_filter.py`
- `scripts/run_shortlist_price_volume_entry_filter.py`
- `tests/unit/test_shortlist_price_volume_entry_filter.py`

The tool joins selected trades to CN stock bars on `asset_id + signal_date`, computes rolling price-volume states using past and current signal-date information only, and projects flagged trade contribution onto the frozen official template.

## Outputs

- Projection: `data/reports/round385_24h_profit_sprint_price_volume_entry_filter_projection_20260627`
- OOS split: `data/reports/round385_24h_profit_sprint_price_volume_entry_filter_oos_20260627`
- Block audit: `data/reports/round385_24h_profit_sprint_price_volume_entry_filter_block_audit_20260627`
- Beta audit: `data/reports/round385_24h_profit_sprint_price_volume_entry_filter_beta_audit_20260627`

Feature coverage was adequate:

| Trades | Matched | Missing | Missing Share |
|---:|---:|---:|---:|
| 26,450 | 26,297 | 153 | 0.58% |

## Full-Sample Projection

Baseline official template:

- total return: +150.65%;
- annualized return: 5.71%;
- Sharpe: 0.779;
- overlap Sharpe: 0.428;
- max drawdown: -35.29%.

| Candidate | Flagged Trades | Total | Ann. | Overlap | Max DD | Full-Sample Delta |
|---|---:|---:|---:|---:|---:|---:|
| `cash_pv_weak_close_range_expansion_20d` | 54 | +151.03% | 5.72% | 0.429 | -35.15% | +0.38% total |
| `cash_pv_short_squeeze_exhaustion_5d` | 28 | +150.63% | 5.71% | 0.429 | -35.01% | flat |
| `cash_pv_breakdown_volume_spike_20d` | 30 | +149.20% | 5.67% | 0.425 | -35.32% | negative |
| `cash_pv_overheat_volume_climax_20d` | 92 | +145.83% | 5.59% | 0.428 | -35.50% | negative |
| `cash_pv_downtrend_high_vol_60d` | 994 | +127.31% | 5.09% | 0.389 | -39.22% | strongly negative |

The only full-sample positive result is `pv_weak_close_range_expansion_20d`, and the effect size is too small for shortlist promotion.

## OOS Split

| Candidate | Mean OOS Ann. | Mean OOS Overlap | Worst OOS DD | Strict Pass |
|---|---:|---:|---:|---:|
| `cash_pv_overheat_volume_climax_20d` | 8.93% | 0.878 | -23.84% | 90.00% |
| `cash_pv_weak_close_range_expansion_20d` | 8.88% | 0.875 | -23.97% | 90.00% |
| `official_base` | 8.90% | 0.875 | -24.00% | 90.00% |
| `cash_pv_breakdown_volume_spike_20d` | 8.84% | 0.873 | -24.00% | 90.00% |
| `cash_pv_short_squeeze_exhaustion_5d` | 8.88% | 0.871 | -23.90% | 90.00% |
| `cash_pv_downtrend_high_vol_60d` | 8.47% | 0.831 | -24.25% | 90.00% |

The OOS result is not enough to override the full-sample evidence. `overheat_volume_climax` has a small OOS mean advantage but loses materially in the full official sample, mainly because it cashes profitable high-attention rebound entries.

## Beta Sanity Check

Using the corrected Round384 benchmark event-return method:

| Candidate | Benchmark | Beta | R2 | Hedged Ann. | Hedged Overlap | Hedged DD |
|---|---|---:|---:|---:|---:|---:|
| `cash_pv_weak_close_range_expansion_20d` | ZZ500 | 0.0468 | 0.2665 | 5.69% | 0.713 | -16.35% |
| `official_base` | ZZ500 | 0.0469 | 0.2669 | 5.68% | 0.710 | -16.47% |
| `cash_pv_overheat_volume_climax_20d` | ZZ500 | 0.0459 | 0.2635 | 5.56% | 0.709 | -15.61% |
| `cash_pv_downtrend_high_vol_60d` | ZZ500 | 0.0448 | 0.2620 | 5.06% | 0.657 | -15.92% |

The weak-close filter does not materially change beta exposure. The improvement versus baseline is tiny.

## Decision

Do not add any Round385 price-volume entry filter to the simulation shortlist.

Keep `pv_weak_close_range_expansion_20d` as a research note only. It is calendar-safe and slightly positive, but its edge is too small to justify another simulation lane.

Reject these filters for current shortlist use:

- `pv_downtrend_high_vol_60d`, because it removes a large block of profitable selected entries and worsens drawdown;
- `pv_overheat_volume_climax_20d`, because the OOS mean looks mildly good but the full official sample deteriorates;
- `pv_breakdown_volume_spike_20d`, because it is negative in full-sample projection;
- `pv_short_squeeze_exhaustion_5d`, because it is effectively flat and too sparse.

## Process Lesson

Public price-volume indicators are useful as structured risk hypotheses, but the current low-turnover selected basket already benefits from some ugly-looking rebound/downtrend states. Do not blindly cash all public "bad technical state" entries.

Next work should rotate again rather than tune these thresholds. Better directions:

- event filters with economic timing, such as unlock, pledge, buyback, dividend, and shareholder reduction;
- portfolio construction improvements, such as drawdown budget, industry caps, and event overlap controls;
- ETF-aware macro regime overlays that change exposure rather than stock selection;
- formal factor-family pre-registration before parameter expansion.
