# CN Stock Round565 HK-Hold Low-Frequency State Join Smoke

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-round565-pit-source-plan-20260705`

Scope: convert the three Round565 HK-hold low-frequency state candidates into the existing external-feed join-smoke format, then verify point-in-time `available_date` alignment over the preregistered source window. This is source-readiness evidence only. It is not IC, a portfolio backtest, promotion evidence, or a final-holdout read.

## Inputs

Candidate plan:

```text
configs\factor_mining_candidate_plan_round565_hk_hold_low_frequency_state_20260705.json
```

Seed config:

```text
configs\external_feed_factor_seed_preregistration_round565_hk_hold_low_frequency_state_20260705.json
```

Processed source root:

```text
data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623
```

Signal window:

```text
2024-07-01 to 2025-12-31
```

The 2025-12-31 raw HK-hold observation is available on 2026-01-05, so it is not eligible for 2025 signal dates.

## Command

```powershell
.\.venv\Scripts\python.exe scripts\run_external_feed_factor_matrix_join_smoke.py --processed-root data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623 --seed-config configs\external_feed_factor_seed_preregistration_round565_hk_hold_low_frequency_state_20260705.json --output-dir data\reports\round565_hk_hold_low_frequency_state_join_smoke_20260705 --market CN --signal-start-date 2024-07-01 --signal-end-date 2025-12-31
```

## Result

| Metric | Value |
| --- | ---: |
| Seed count | 3 |
| Pass count | 3 |
| Warn count | 0 |
| Fail count | 0 |
| Insufficient-history count | 0 |
| Total joined rows | 5,983,389 |
| Available-date violations | 0 |
| Same-day/future raw-date violations | 0 |

Per-seed summary:

| Seed | Status | Joined rows | Signal dates | Unique symbols | HK-hold observation dates | PIT violations |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `hk_hold_sponsorship_state_change_63` | pass | 1,994,463 | 547 | 3,865 | 40 | 0 |
| `hk_hold_sponsorship_persistence_126` | pass | 1,994,463 | 547 | 3,865 | 40 | 0 |
| `hk_hold_sponsorship_state_liquidity_interaction_63` | pass | 1,994,463 | 547 | 3,865 | 40 | 0 |

The source-smoke deliberately uses only `external_hk_hold` columns: `symbol`, `available_date`, `hold_ratio`, and `hold_vol`. It does not substitute aggregate HSGT flow for the liquidity interaction. The local price-volume liquidity leg must be added in the next construction smoke and then deduped against price-volume, moneyflow, and style exposures before any residual IC screen.

## Decision

Round565 has cleared the available-date join-smoke for the HK-hold sponsorship source leg. The next allowed step is a low-frequency state construction smoke that creates the 63-day change, 126-day persistence, and local-liquidity interaction inputs with explicit reference dedup preparation. Portfolio grids, promotion gates, final-holdout tuning, provider downloads, and old northbound accumulation or crowding/reversal reruns remain forbidden.
