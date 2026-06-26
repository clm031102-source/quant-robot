# CN Stock Round259 Listing-Age / Board Structural Residual Prescreen

- Date: 2026-06-26
- Machine: office_desktop
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Stage: `listing_age_board_residual_prescreen`
- Candidate plan: `configs/factor_mining_candidate_plan_round259_listing_age_board_structural_20260626.json`
- Candidate plan gate: `data/reports/round259_listing_age_board_candidate_plan_gate_20260626/factor_mining_candidate_plan_gate.json`
- Full core output: `data/reports/round259_listing_age_board_full_core_20260626/listing_age_board_residual_prescreen.json`

## Why This Round

Round258 rejected the `daily_basic` valuation repair line after coverage repair because the signal failed quantile shape and collapsed after style residualization. Round259 therefore rotated to a non-daily-basic, non-forecast, non-moneyflow, non-public-technical reentry family: A-share listing-age and board-permission structural constraints.

This family directly targets real A-share implementation issues from the control contract:

- fresh listing/new-share distortion;
- delisting/list-status survivorship risk;
- STAR/GEM/BSE board-permission and access frictions;
- whether these structural variables are alpha or only industry/style/size/liquidity beta.

## Controls

- Final holdout excluded: 2026 data was not used.
- Analysis window: 2015-01-01 through 2025-12-31.
- Bars roots:
  - `data/processed/cn_stock_long_history_2015_202306`
  - `data/processed/office_desktop_20260616_combined_research`
- Stock-basic metadata source:
  - `data/processed/round198_tradeability_long_cycle_official_backfill_20260623/metadata/tushare_stock_basic`
- Candidate count: 7.
- Horizons: 5d and 20d.
- Core residual gate:
  - raw IC;
  - industry-neutral IC;
  - size/liquidity/vol residual IC;
  - yearly stability;
  - amount/ADV capacity filter.

Reference-factor de-duplication was skipped in the full core run because no residual candidate survived the core gate. If a future structural candidate passes the core gate, public-reference de-duplication must be run before any walk-forward or portfolio preflight.

## Full-Sample Result

- Bar rows: 10,785,537
- Assets: 5,707
- Factor rows: 70,897,158
- Industry-neutral rows: 70,882,390
- Residual rows: 70,323,744
- Label rows: 21,442,336
- Tests: 14
- Residual research leads: 0
- Portfolio preflight candidates: 0
- Promotion candidates: 0

The 2024Q1 smoke had 5 provisional residual leads, but the long-cycle run rejected all of them. This is exactly why the project now requires full-sample replay before believing short-window discoveries.

## Best Diagnostics

| Factor | H | Raw IC | Industry-Neutral IC | Residual IC | Residual ICIR | Residual t | IC>0 | Yearly Failures | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `listing_age_log_seasoned_252` | 20 | 0.0151 | 0.0202 | 0.0188 | 0.156 | 8.01 | 57.3% | 4 | close but below residual IC/ICIR/stability gates |
| `listing_age_board_compound_risk_avoidance` | 20 | 0.0156 | 0.0205 | 0.0180 | 0.154 | 7.92 | 56.3% | 6 | close but unstable and below gate |
| `fresh_listing_opening_risk_avoidance_120` | 20 | 0.0278 | 0.0103 | -0.0262 | -0.197 | -10.09 | 39.5% | 9 | raw signal reverses after residualization |
| `listing_age_young_overhang_avoidance_252` | 20 | 0.0274 | 0.0166 | -0.0126 | -0.100 | -5.15 | 42.9% | 7 | raw signal is not residual alpha |
| `board_permission_mainboard_preference` | 20 | 0.0096 | 0.0094 | 0.0061 | 0.082 | 4.21 | 54.6% | 5 | too weak after neutralization |

## Diagnosis

The family produced some economically plausible raw effects, especially around fresh listings and young-stock overhang. But those effects did not remain clean after industry and size/liquidity/vol controls:

- `fresh_listing_opening_risk_avoidance_120` had a decent raw h20 IC, then flipped to a negative residual IC. That means the apparent edge is more likely a structural exposure bucket than a clean ranking alpha.
- `listing_age_log_seasoned_252` and `listing_age_board_compound_risk_avoidance` came closest, but both missed the minimum residual IC of 0.02, had residual ICIR only around 0.15, and failed yearly stability.
- Board-permission standalone effects were weak and unstable.

So this family is useful as a risk/control diagnostic, not as a standalone profitability factor.

## Decision

Round259 produced:

- 7 pre-registered factors;
- 14 factor x horizon tests;
- 0 residual research leads;
- 0 portfolio candidates;
- 0 promotion candidates.

The listing-age/board structural family is hibernated for alpha mining. Do not tune thresholds, flip signs, or run portfolio grids from these results.

Next direction:

`round260_rotate_after_listing_age_board_structural_failure`

Round260 must rotate again instead of trying `listing_age` parameter variations.
