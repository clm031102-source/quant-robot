# CN Stock Round565 HK-Hold Low-Frequency State Preregistration

Date: 2026-07-05

Machine context: office desktop as the main work machine

Branch: `codex/factor-batch-cn-stock-round565-pit-source-plan-20260705`

Scope: start the next factor-batch cycle from clean `main`, run the required startup gates, collect the required two-reviewer checkpoint feedback, and preregister a new PIT-safe orthogonal source family without running factor IC, portfolio grids, promotion gates, provider downloads, or final-holdout tuning.

## Startup Evidence

| Check | Result |
| --- | --- |
| Source branch | latest `main`, synchronized with `origin/main` |
| New branch | `codex/factor-batch-cn-stock-round565-pit-source-plan-20260705` |
| Startup context | `office_desktop` / `factor_batch`, branch matched |
| Quant PM startup gate | `ready`, blockers `[]` |
| CN stock startup gate | `cleared`, blockers `[]` |
| CN stock data manifest | `review_required`, blockers `[]` |
| Data manifest warnings | `extreme_return_rows_present`, `moneyflow_symbol_coverage_below_bars` |

Data manifest summary:

| Metric | Value |
| --- | ---: |
| Bar rows | 3,806,375 |
| Bar symbols | 5,634 |
| Moneyflow rows | 3,606,228 |
| Moneyflow symbols | 5,312 |
| Date start | 2023-07-03 |
| Date end | 2026-06-15 |

## Reviewer Checkpoint

The continuing goal requires two fresh reviewers every ten-round checkpoint. Round563 had a local review package, so Round565 created two actual review agents before starting the new cycle.

Quant PM reviewer:

- Recommended a new topic branch from latest `main`.
- Recommended a single new preregistered PIT-safe orthogonal source family before any factor generation.
- Rejected daily-basic valuation repair, direction flips, parameter widening, portfolio grids, promotion, final-holdout tuning, and generated-data commits.

Ordinary-user reviewer:

- Recommended a clearer `Start Here` section for the next operator.
- Flagged that `CURRENT_RESEARCH_INDEX.md` contains many historical commands that are easy to copy by mistake.
- Recommended a concrete branch example, explicit stop conditions, and a concise current checklist.

Round565 implemented the non-invasive part of that feedback by adding a `Start Here` section to `docs\research\ROUND564_NEXT_STEPS_CHECKLIST.md`.

## Candidate Plan

New config:

```text
configs\factor_mining_candidate_plan_round565_hk_hold_low_frequency_state_20260705.json
```

Family:

```text
hk_hold_low_frequency_state
```

Why this family:

- It uses existing local processed external-feed evidence only.
- It treats HK-hold coverage improvement as source-quality evidence, not as an old northbound factor rerun.
- It explicitly avoids old direct northbound accumulation, old northbound crowding/reversal, margin-credit, daily-basic valuation repair, and LPR-dependent macro factors.
- It frames HK-hold as a low-frequency sponsorship state or interaction source rather than a daily direct rank.

Active preregistered candidates:

| Factor | Hypothesis |
| --- | --- |
| `hk_hold_sponsorship_state_change_63` | Slow changes in foreign holding sponsorship may identify durable ownership state shifts after available-date alignment. |
| `hk_hold_sponsorship_persistence_126` | Persistent foreign sponsorship states may interact with later cross-sectional returns after residual controls. |
| `hk_hold_sponsorship_state_liquidity_interaction_63` | Sponsorship state crossed with local liquidity quality must survive dedup against price-volume, moneyflow, and style exposures. |

## Candidate-Plan Gate

Command:

```powershell
python scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round565_hk_hold_low_frequency_state_20260705.json --gate-stage discovery --output-dir data\reports\round565_hk_hold_low_frequency_state_candidate_plan_gate_20260705
```

Result:

| Metric | Value |
| --- | ---: |
| Status | `research_ready` |
| Candidate-plan gate cleared | true |
| Candidate count | 3 |
| Active candidate count | 3 |
| Complete control areas | 9 / 9 |
| Blockers | 0 |
| Research screen allowed | true |
| Portfolio grid allowed | false |
| Promotion allowed | false |

## Decision

Round565 opens only the source-readiness/preregistration lane for HK-hold low-frequency state candidates. It does not permit IC claims, portfolio conversion, promotion, or final-holdout reads. The next useful step is a source-construction smoke that verifies low-frequency state construction, available-date alignment, and reference dedup inputs before any residual IC screen.

## Follow-On Source Join Smoke

After preregistration, Round565 added a dedicated external-feed seed config:

```text
configs\external_feed_factor_seed_preregistration_round565_hk_hold_low_frequency_state_20260705.json
```

The available-date join-smoke over 2024-07-01 to 2025-12-31 passed for all 3 HK-hold sponsorship seeds:

| Metric | Value |
| --- | ---: |
| Pass count | 3 / 3 |
| Joined rows | 5,983,389 |
| Joined signal dates | 547 |
| Unique symbols per seed | 3,865 |
| Available-date violations | 0 |
| Same-day/future raw-date violations | 0 |

This remains source-readiness evidence only. The local price-volume liquidity leg for `hk_hold_sponsorship_state_liquidity_interaction_63` is intentionally not replaced by aggregate HSGT flow.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- No provider download.
- No final-holdout tuning.
- No daily-basic valuation repair.
- No old northbound accumulation or crowding/reversal rerun.
- No margin-credit reentry.
- Generated `data/reports` artifacts remain out of Git.
