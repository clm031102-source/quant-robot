# CN Stock External Feed Processed Write Smoke and Factor Seed Preregistration Round170

Date: 2026-06-23

## Scope

Round170 ran the first explicit processed-write smoke for the new external feed ingestion layer and preregistered a small factor seed set. This round produced no evaluated factor, no walk-forward candidate, and no profitability claim.

- Processed root: `data/processed/tushare_external_feeds_round170_smoke_20260623`
- Seed config: `configs/external_feed_factor_seed_preregistration_round170_20260623.json`
- Safety: research-to-review only. No broker, account, order, or live-trading access.

## Processed Write Smoke

Command:

```powershell
python scripts\run_tushare_external_feed_ingest.py --start-date 2025-12-25 --end-date 2025-12-31 --output-dir data\processed\tushare_external_feeds_round170_smoke_20260623 --execute-write-processed
```

CLI result: 5 feeds, 4 pass, 1 warn, 0 fail.

Read-back audit from `DatasetStore`:

| Dataset | Rows | Date Range | Duplicate Keys | Missing `available_date` | Lag Violations |
|---|---:|---|---:|---:|---:|
| `external_margin_detail` | 21,396 | 2025-12-25 to 2025-12-31 | 0 | 0 | 0 |
| `external_hk_hold` | 3,325 | 2025-12-31 to 2025-12-31 | 0 | 0 | 0 |
| `external_hsgt_flow` | 3 | 2025-12-29 to 2025-12-31 | 0 | 0 | 0 |
| `external_index_state` | 5 | 2025-12-25 to 2025-12-31 | 0 | 0 | 0 |
| `external_macro_rates` | 5 | 2025-12-25 to 2025-12-31 | 0 | 0 | 0 |

Known warnings:

- `external_macro_rates` has missing `lpr_1y` and `lpr_5y` due LPR endpoint rate limiting or unavailable coverage in this smoke.
- `external_hk_hold` dropped 2,625 non-CN symbols; this is required for CN stock scope.

## Preregistered Factor Seeds

Six seeds were registered for the next factor-matrix join smoke:

| Factor Seed | Family | Type | First Test Direction |
|---|---|---|---|
| `margin_financing_acceleration_exhaustion_20` | margin/credit | cross-sectional | high financing acceleration as negative/crowding |
| `margin_balance_crowding_reversal_20` | margin/credit | cross-sectional | high relative financing balance as negative/crowding |
| `northbound_hold_ratio_accumulation_20` | northbound | cross-sectional | gradual holding-ratio accumulation as positive |
| `northbound_hold_accumulation_flow_regime_20` | northbound + aggregate flow | interaction | stock accumulation conditioned on aggregate flow regime |
| `index_location_value_liquidity_regime_20` | index state | regime control | gating/interactions only |
| `shibor_liquidity_tightening_regime_20` | macro liquidity | regime control | gating/interactions only |

All seeds require `available_date` joins. Aggregate HSGT, index state, and SHIBOR are not allowed as standalone stock ranks.

## Decision

Proceed to:

`round171_external_feed_factor_matrix_join_smoke`

Round171 must build a small factor matrix from the processed smoke and prove:

- no same-day `date` joins;
- `available_date <= signal_date` for every joined observation;
- no 2026 final-holdout tuning;
- no portfolio grid before IC/quantile/turnover prescreen and redundancy audit.
