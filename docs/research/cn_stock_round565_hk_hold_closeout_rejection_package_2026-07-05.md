# CN Stock Round565 HK-Hold Closeout Rejection Package

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-round565-pit-source-plan-20260705`

Scope: close out the Round565 HK-hold low-frequency sponsorship source family after preregistration, source-readiness checks, reference-dedup preparation, and residual IC prescreen. This package records the rejection decision and prevents parameter tuning, direction flips, portfolio grids, promotion gates, or final-holdout reads on the same failed family.

## Evidence Chain

| Step | Artifact | Result |
| --- | --- | --- |
| Candidate preregistration | `configs\factor_mining_candidate_plan_round565_hk_hold_low_frequency_state_20260705.json` | 3 candidates preregistered, candidate-plan gate `research_ready` |
| External-feed seed config | `configs\external_feed_factor_seed_preregistration_round565_hk_hold_low_frequency_state_20260705.json` | HK-hold sponsorship source leg mapped to existing join-smoke format |
| Available-date join-smoke | `docs\research\cn_stock_round565_hk_hold_low_frequency_state_join_smoke_2026-07-05.md` | 3 / 3 pass, 0 PIT violations |
| Construction smoke | `docs\research\cn_stock_round565_hk_hold_low_frequency_state_construction_smoke_2026-07-05.md` | 63-day change, 126-day persistence, and local-liquidity interaction constructed, 0 PIT violations |
| Reference-dedup prep | `docs\research\cn_stock_round565_hk_hold_reference_dedup_prep_2026-07-05.md` | Persistence showed liquidity/amount overlap; no reference reached 0.70 |
| Residual IC prescreen | `docs\research\cn_stock_round565_hk_hold_residual_ic_prescreen_2026-07-05.md` | 0 / 3 research leads |

## Residual IC Outcome

| Factor | Residual mean IC | Residual ICIR | t-stat | Bonferroni p | Positive IC rate | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `hk_hold_sponsorship_state_change_63` | 0.0052 | 0.132 | 2.21 | 0.0822 | 52.3% | rejected |
| `hk_hold_sponsorship_persistence_126` | 0.0099 | 0.136 | 2.27 | 0.0697 | 52.9% | rejected |
| `hk_hold_sponsorship_state_liquidity_interaction_63` | 0.0053 | 0.137 | 2.29 | 0.0665 | 53.8% | rejected |

All three candidates failed the effect-size and multiple-testing gate. The nominal residual t-stats are not enough because mean IC, ICIR, positive IC rate, and Bonferroni-adjusted p-values do not pass the preregistered research discipline.

## Safety And Data Policy

- No provider download was run.
- No broker connection, live account read, order placement, or automatic trading was touched.
- No portfolio grid, promotion gate, or final-holdout read was run.
- Residual IC labels ended at 2025-12-31; 2026 was not used.
- Generated reports remain under `data\reports` and out of Git.

## Decision

Round565 HK-hold low-frequency sponsorship is closed as a rejected source family for this cycle. Do not tune the same windows, flip signs, widen parameters, or attempt portfolio conversion. The next factor batch should rotate to a genuinely different PIT-safe source mechanism with a fresh candidate-plan gate.
