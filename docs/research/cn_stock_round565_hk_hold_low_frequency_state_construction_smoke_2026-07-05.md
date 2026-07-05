# CN Stock Round565 HK-Hold Low-Frequency State Construction Smoke

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-round565-pit-source-plan-20260705`

Scope: run a read-only construction smoke for the Round565 HK-hold low-frequency sponsorship candidates using existing local processed HK-hold and CN stock bar data. This checks whether the source leg, 63-day change, 126-day persistence, and local-liquidity interaction can be constructed without point-in-time violations. It does not compute return labels, IC, portfolio performance, promotion gates, provider downloads, or final-holdout tuning.

## Inputs

| Input | Path |
| --- | --- |
| Candidate plan | `configs\factor_mining_candidate_plan_round565_hk_hold_low_frequency_state_20260705.json` |
| Seed config | `configs\external_feed_factor_seed_preregistration_round565_hk_hold_low_frequency_state_20260705.json` |
| HK-hold source root | `data\processed\tushare_external_feeds_round172_long_cycle_monthly_20260623` |
| Bar source root | `data\processed\office_desktop_20260616_combined_research` |
| Generated report | `data\reports\round565_hk_hold_low_frequency_state_construction_smoke_20260705` |

Signal window: 2024-07-01 to 2025-12-31.

The smoke used only existing local processed data. The interaction candidate used local ADV20 amount rank from bars as the liquidity leg. It did not substitute aggregate HSGT flow or revive old northbound-flow regimes.

## Result

| Metric | Value |
| --- | ---: |
| Joined rows | 1,241,443 |
| Joined signal dates | 364 |
| Joined symbols | 3,568 |
| HK-hold observation dates used | 39 |
| First joined signal date | 2024-07-03 |
| Last joined signal date | 2025-12-31 |
| Max raw HK-hold date used | 2025-09-30 |
| Max available date used | 2025-10-09 |
| Available-date violations | 0 |
| Same-day/future raw-date violations | 0 |
| 2025-12-31 raw rows used before 2026 availability | 0 |

The 2025-12-31 raw HK-hold observation is available on 2026-01-05, so it was not eligible for any 2025 signal date and was not used.

## Feature Coverage

| Feature | Non-null rows | Nonzero rows | Signal dates | Symbols |
| --- | ---: | ---: | ---: | ---: |
| `hk_hold_sponsorship_state_change_63` | 1,017,109 | 819,115 | 301 | 3,552 |
| `hk_hold_sponsorship_persistence_126` | 1,020,661 | 936,437 | 302 | 3,552 |
| `hk_hold_sponsorship_state_liquidity_interaction_63` | 1,017,109 | 819,115 | 301 | 3,552 |

## Decision

Round565 has cleared both the available-date join-smoke and a first construction smoke for the HK-hold sponsorship source leg. The next allowed step is reference dedup preparation against price-volume, moneyflow, and style exposures, followed only then by a research-only residual IC prescreen with multiple-testing accounting.

Still forbidden: portfolio grids, promotion gates, final-holdout tuning, provider downloads, old northbound accumulation or crowding/reversal reruns, margin-credit reentry, broker connection, account reads, order placement, and live trading.
