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
- `src/quant_robot/research/decision.py` now rejects rows with `capacity_limited_trades > 0`, preventing capacity-breached long-cycle rows from being labelled as approved.
- `tests/unit/test_decision_risk.py` covers the capacity rejection path.
- `src/quant_robot/factors/moneyflow_technical.py` now registers two capacity-tier moneyflow combo factors:
  - `mf_low_amount_bucket_rank_20`
  - `small_sell_amount_bucket_rank_20`
- `tests/unit/test_moneyflow_technical_combo_factors.py` verifies that the amount-bucket rank factors compare moneyflow inside traded-amount tiers and gate thin names.

## Data Coverage Finding

The earlier authority-bars configuration was not promotion-grade. The recent processed store marked 2024 bars as `adjusted=false`; because the second authority segment had `adjusted_only=true`, long-cycle runs that claimed 2015-2025 coverage could omit 2024.

The configuration was corrected and the experiment-grid CLI now has a year-coverage gate, so future authority long-cycle runs fail fast if any required year is missing.

## Corrected Raw Moneyflow Rerun

After the authority-bars coverage fix, the office desktop reran the two raw moneyflow top2 factors with the same long-cycle parameters:

- `net_mf_amount_ratio_low`
- `small_order_sell_pressure`

Result:

- Completed cases: 12.
- Failed cases: 0.
- Capacity-clean cases: 0.
- Drawdown-clean cases at -30%: 0.
- Overlap-adjusted Sharpe >= 1 cases: 0.
- Promotable factors: 0.

Interpretation:

- The raw signals still show statistical residue, including positive IC and selected-tail RankIC.
- The portfolio expression is not tradable: every row breached capacity and every row had max drawdown worse than -30%.
- Pre-correction raw moneyflow reports should be treated as stale for promotion decisions.

## Corrected Low-Turnover Rerun

The office desktop also reran the two daily-basic low-turnover factors through 2024, because the old authority-bars issue could affect 2024 validation:

- `turnover_rate_low`
- `turnover_rate_f_low`

Result:

- Completed cases: 12.
- Failed cases: 0.
- Runner-approved cases after the capacity gate fix: 0.
- Capacity-clean cases: 0.
- Drawdown-clean cases at -30%: 0.
- Overlap-adjusted Sharpe >= 1 cases: 0.
- Promotable factors: 0.

Interpretation:

- The low-turnover anomaly remains statistically real; full-universe RankIC and selected-tail RankIC are still positive and significant.
- The standalone portfolio remains unusable: even top200 breaches the 1% ADV capacity threshold by a wide margin and has drawdown worse than -45%.
- Pre-correction daily-basic turnover reports should be treated as stale for promotion decisions.

## Corrected Residual/Gated Moneyflow Rerun

The office desktop reran the residual/gated moneyflow-combo controls because they are the closest existing attempt to preserve moneyflow signal while controlling capacity:

- `large_resid_liquidity_gate_20`
- `large_resid_liq_vol_amt_20`
- `large_resid_liq_vol_amt_gate_20`
- `mf_low_minus_volatility_liquidity_gate_20`

Result:

- Completed cases: 16.
- Failed cases: 0.
- Runner-approved cases under strict gates: 0.
- Capacity-clean cases: 10.
- Drawdown-clean cases at -30%: 0.
- Overlap-adjusted Sharpe >= 1 cases: 0.
- Promotable factors: 0.

Interpretation:

- The liquidity gates can control participation in many rows.
- The traded portfolio still fails badly: leading rows have max drawdown around -80% or worse and overlap-adjusted Sharpe near 0.21.
- Several residual/gated rows have significantly negative selected-tail RankIC, so the capacity control often destroys or inverts the useful tail.
- Pre-correction residual/gated reports should be treated as stale for promotion decisions.

## Corrected Residual Liquidity/Amount Rerun

The office desktop reran the two residual liquidity/amount moneyflow-combo candidates after the authority-bars coverage fix:

- `mf_low_resid_liq_amt_20`
- `small_sell_resid_liq_amt_20`

Result:

- Completed cases: 12.
- Failed cases: 0.
- Runner-approved cases under strict gates: 0.
- Capacity-clean cases: 0.
- Drawdown-clean cases at -30%: 0.
- Overlap-adjusted Sharpe >= 1 cases: 0.
- Positive significant selected-tail RankIC cases: 0.
- Promotable factors: 0.

Interpretation:

- Same-day residualization against liquidity and traded amount is not a promotion path.
- `mf_low_resid_liq_amt_20` can show high annualized return in narrow topN rows, but it fails drawdown, capacity, and selected-tail RankIC badly.
- `small_sell_resid_liq_amt_20` has slightly better overlap-adjusted Sharpe, but still fails capacity, drawdown, and selected-tail direction.
- Pre-correction residual liquidity/amount reports should be treated as stale for promotion decisions.

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
