# CN Stock Round220 Industry Leader-Lag Smoke

Date: 2026-06-24

Scope: CN A-share stock cross-sectional factor research. This is a functionality smoke and process checkpoint, not a profitability claim, not ETF rotation, and not live trading.

## What Changed

Implemented the Round220 `industry_leader_lag_residual_diffusion` family as a runnable factor and residual-prescreen path:

- `src/quant_robot/factors/industry_leader_lag.py`
- `src/quant_robot/ops/industry_leader_lag_residual_prescreen.py`
- `scripts/run_industry_leader_lag_residual_prescreen.py`
- Unit coverage for factor construction, residual prescreen, CLI output, and loader year-partition pushdown.

The shared bar loader now skips `year=YYYY` partitions outside the requested window and filters each file immediately after read. This directly reduces wasted memory and time for long-cycle factor mining.

## Smoke Run

Artifact:

`data/reports/industry_leader_lag_residual_prescreen_round220_smoke_20260624/`

Command shape:

`python scripts/run_industry_leader_lag_residual_prescreen.py --analysis-start-date 2024-01-01 --analysis-end-date 2024-03-31 --candidate-factor-name industry_leader_laggard_gap_reversion_5_20 --sample-every-n-dates 10 --min-cross-section 10 --min-ic-observations 3`

Data footprint:

- Asset count: 5,363
- Bar rows: 309,950
- Factor rows: 194,775
- Industry-neutral rows: 194,775
- Residual rows: 194,775
- Label rows: 277,786
- Reference factor rows: 1,054,467
- Reference factor count: 9

Single-candidate smoke result:

- Factor: `industry_leader_laggard_gap_reversion_5_20`
- Horizon: 5
- Raw mean Spearman IC: 0.1334
- Industry-neutral mean Spearman IC: 0.1307
- Residual mean Spearman IC: 0.0932
- Residual ICIR: 0.374
- Residual IC t-stat: 2.118
- Residual positive IC rate: 68.75%
- High reference redundancy count: 0
- High style exposure count: 0

## Audit Decision

This is an encouraging smoke result, but it is not usable evidence. It covers only 2024Q1, one candidate, one horizon, lenient smoke thresholds, and no long-cycle, cost, capacity, walk-forward, regime, or multiple-testing gate.

Therefore the smoke lead is blocked from direct cost-capacity preflight or promotion.

Update after full replay:

- The required full 2015-2025 sharded prescreen was completed in `docs/research/cn_stock_round220_industry_leader_lag_sharded_full_2026-06-24.md`.
- All six Round220 candidates were rejected at the residual prescreen gate.
- The smoke lead `industry_leader_laggard_gap_reversion_5_20` fell to full-sample residual IC 0.0175 and failed 2025.
- The active next direction is now `round221_rotate_after_industry_leader_lag_residual_failure`.

Original next direction, now completed:

`round220_industry_leader_lag_full2015_2025_sharded_prescreen`

Required before any portfolio grid:

- Run all six registered Round220 candidates over 2015-01-01 to 2025-12-31.
- Use year/month sharding or cached reference/factor matrices to avoid another full-memory rebuild.
- Preserve the same leader definition and parameters used in the smoke.
- Count all candidate x horizon tests in multiple-testing accounting.
- Recheck residual IC shape, yearly stability, reference redundancy, style exposure, China regime coverage, and tradeability/capacity gates.

Hard rejects:

- Treating the 2024Q1 smoke as profitability evidence.
- Sending the smoke lead directly to TopN, Sharpe, win-rate, or cost-capacity portfolio grid.
- Re-tuning leader quantile, horizon, or formulas after seeing the smoke without a new preregistration.
