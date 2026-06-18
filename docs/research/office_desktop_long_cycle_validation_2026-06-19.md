# Office Desktop Long-Cycle Validation - 2026-06-19

## Scope

- Machine role: `office_desktop`.
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`.
- Task type: `factor_validation`.
- Market and asset type: CN stocks.
- Boundary: research-to-paper only. No broker connection, live account reads, order placement, or automatic live trading.

## Completed Repository Changes

This pass converted a local audit issue into repeatable repository checks:

- `configs/cn_stock_authority_bars_2015_2025.json` now allows the recent processed-bar segment to include unadjusted 2023-2025 rows.
- `scripts/run_experiment_grid.py` now rejects `authority-processed-bars` runs when the loaded bars do not cover every calendar year between the configured start and end dates.
- `tests/unit/test_experiment_grid_cli.py` covers the missing-year rejection path.
- `src/quant_robot/factors/moneyflow_technical.py` now registers two capacity-tier moneyflow combo factors:
  - `mf_low_amount_bucket_rank_20`
  - `small_sell_amount_bucket_rank_20`
- `tests/unit/test_moneyflow_technical_combo_factors.py` verifies that the amount-bucket rank factors compare moneyflow inside traded-amount tiers and gate thin names.

## Data Coverage Finding

The earlier authority-bars configuration was not promotion-grade. The recent processed store marked 2024 bars as `adjusted=false`; because the second authority segment had `adjusted_only=true`, long-cycle runs that claimed 2015-2025 coverage could omit 2024.

The configuration was corrected and the experiment-grid CLI now has a year-coverage gate, so future authority long-cycle runs fail fast if any required year is missing.

## Amount-Bucket Factor Audit

The corrected 2015-2025 authority-bars pass tested the two new amount-bucket factors across 12 width/cost cases.

Result:

- Completed cases: 12.
- Failed cases: 0.
- Capacity-limited cases: 0.
- Promotable factors: 0.

Interpretation:

- The construction solved the mechanical capacity problem.
- It did not preserve enough alpha after the liquidity tiering.
- Leading rows still had weak Sharpe, very large drawdowns, weak or negative selected-tail RankIC, and negative benchmark-relative performance.

## Current Decision

Both new factors are rejected as profitability candidates:

- `mf_low_amount_bucket_rank_20`: rejected. Capacity-clean, but benchmark-relative performance and tail evidence failed.
- `small_sell_amount_bucket_rank_20`: rejected. Capacity-clean, but selected tail evidence inverted and drawdown remained too large.

The useful output is methodological rather than a tradable factor: amount-tier ranking is now implemented and test-covered, but this specific moneyflow pair should not be promoted.

## Follow-Up Queue

Next office-desktop work should prioritize corrected-coverage reruns of older moneyflow and residualized candidates before treating any previous long-cycle report as promotion evidence. Reports produced before the authority-bars coverage fix should be considered stale unless rerun under the year-coverage gate.
