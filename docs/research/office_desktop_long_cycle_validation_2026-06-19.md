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
- `src/quant_robot/experiments/runner.py` now accepts a progress callback and emits `precompute_start`, `precompute_done`, per-case `case_start` / `case_done`, and `grid_done` events.
- `scripts/run_experiment_grid.py` now streams progress JSON lines to stderr for long authority-data runs, including bar-load start/done events.
- `tests/unit/test_experiment_runner.py` and `tests/unit/test_experiment_grid_cli.py` cover progress callback forwarding and emitted event order.

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

## Closeout Note

The office desktop started a corrected-coverage daily-basic value/yield width stress run for:

- `dv_ttm`
- `ps_ttm_inverse`
- `pb_inverse`

The run reached 8 of 12 cases before this sync closeout and was stopped before a complete leaderboard was produced. It is not counted as a completed factor result or promotion/rejection decision.

The repository change that survives from that attempt is the progress instrumentation above. Future long-cycle grid runs should use the stderr progress stream so a stuck or expensive case is visible before deciding whether to continue, narrow the grid, or terminate.

## PB Incremental Long-Cycle Rerun

After adding case-level checkpointing, the office desktop completed the missing `pb_inverse` daily-basic width stress subset:

- Factor: `pb_inverse`
- Cases: topN 100/200 x cost 10/20 bps
- Period: 2015-01-05 through 2024-12-31
- No 2025 validation or 2026 final holdout read.

Result:

- Completed cases: 4.
- Runner-approved cases: 0.
- Capacity-clean cases: 0.
- Drawdown-clean cases at -30%: 0.
- Overlap-adjusted Sharpe >= 1 cases: 0.
- Positive benchmark-relative return cases: 0.
- Positive significant selected-tail RankIC cases: 0.
- Strict promotable cases: 0.

Best row by overlap-adjusted Sharpe:

- `CN_pb_inverse_top100_cost10_reb5`
- Annualized return: 0.78%.
- Sharpe: 0.127.
- Overlap-adjusted Sharpe: 0.066.
- Win rate: 46.7%.
- Max drawdown: -61.9%.
- Benchmark-relative return: -1222.1%.
- Capacity-limited trades: 23.

Interpretation:

- `pb_inverse` has positive full-universe RankIC over the long sample, but the top-N traded expression fails.
- The portfolio has severe drawdown, weak Sharpe, capacity breaches, and deeply negative benchmark-relative performance.
- Selected-tail RankIC does not confirm that the top-N basket captures the full-universe signal.
- Decision: reject `pb_inverse` as a standalone CN-stock profitability factor under this protocol.

Process note:

- `partial_leaderboard.jsonl` worked as intended and preserved completed cases during long runs.
- Runtime evidence shows a new efficiency target: cost-only variants rerun the same signal path. Future workflow should reuse signal/holdings artifacts across cost scenarios.

## Dividend Yield Incremental Long-Cycle Rerun

The office desktop then completed the `dv_ttm` daily-basic width stress subset using the new checkpoint/resume flow:

- Factor: `dv_ttm`
- Cases: topN 100/200 x cost 10/20 bps
- Period: 2015-01-05 through 2024-12-31
- No 2025 validation or 2026 final holdout read.

Result:

- Completed cases: 4.
- Runner-approved cases: 0.
- Capacity-clean cases: 0.
- Drawdown-clean cases at -30%: 0.
- Overlap-adjusted Sharpe >= 1 cases: 0.
- Positive benchmark-relative return cases: 0.
- Positive significant selected-tail RankIC cases: 0.
- Strict promotable cases: 0.

Best row by overlap-adjusted Sharpe:

- `CN_dv_ttm_top100_cost10_reb5`
- Annualized return: 2.56%.
- Sharpe: 0.269.
- Overlap-adjusted Sharpe: 0.144.
- Win rate: 52.9%.
- Max drawdown: -55.4%.
- Benchmark-relative return: -1188.0%.
- Capacity-limited trades: 128.

Interpretation:

- `dv_ttm` is stronger than `pb_inverse` on standalone absolute metrics, and the full-universe RankIC is positive and significant.
- It still fails as a tradable standalone profitability factor because drawdown, capacity, benchmark-relative performance, and selected-tail evidence all fail.
- Decision: reject `dv_ttm` as a standalone CN-stock profitability factor under this protocol.

Process note:

- Checkpoint/resume is now implemented and test-covered.
- Resume rows are guarded by a grid configuration fingerprint, so a same-name case from a different date window or parameter set is not reused.
- Research-input reuse is now implemented and test-covered for topN/cost breadth variants.

## Long-Cycle Runner Efficiency Upgrade

The office desktop converted the observed duplicate-work bottleneck into a reusable runner feature:

- `prepare_research_pipeline_inputs(...)` now builds the reusable side of a research run once: filtered bars, factor inputs, selected factor rows, forward labels, regime rows, IC, quantile groups, long-short returns, benchmark curve, portfolio scope, and annualization.
- `run_research_pipeline(...)` can now consume prepared inputs and rerun only the topN/cost-sensitive backtest, selected-tail IC, benchmark comparison, decision, and artifact export.
- `ExperimentGridConfig.reuse_research_inputs` caches prepared inputs inside a grid run.
- The cache fingerprint excludes only runtime-only fields such as `top_n`, `cost_bps`, cost-model parameters, capital size, decision thresholds, cash return, and output path. It still includes factor name/source, market, sample dates, signal dates, horizon, lag, rebalance interval, quantiles, benchmark, portfolio scope, and regime settings.
- Existing long-cycle CN-stock and Tushare moneyflow validation configs now enable `reuse_research_inputs`; the moneyflow walk-forward templates also enable factor-matrix precompute where appropriate.

Expected effect:

- Same factor, same long sample, same rebalance/regime, multiple topN/cost cases no longer recompute the expensive signal/label/IC/regime path.
- This does not change the economics of any backtest result; it only removes repeated preparation work.
- Checkpoint/resume and research-input reuse can be used together: completed case rows are still skipped first, then remaining cases share prepared inputs where safe.

## Daily-Basic Capacity-Aware Composite Rerun

The next pre-registered direction tested whether the strongest raw daily-basic cluster was just a capacity/illiquidity artifact. Four capacity-aware daily-basic composites were added and run over the same long-cycle protocol:

- `turnover_rate_low_large_mv`
- `turnover_rate_f_low_large_mv`
- `dv_ttm_large_mv`
- `ps_ttm_inverse_large_mv`

Design:

- Each factor blends the original signal's same-date cross-sectional z-score with `log(circ_mv)` cross-sectional z-score.
- The aim is to keep the low-turnover / value intuition while explicitly rewarding larger, more tradable names before top-N selection.
- Cases: 4 factors x topN 50/100/200 x cost 10/20 bps = 24.
- Period: 2015-01-05 through 2024-12-31.
- No 2025 validation or 2026 final holdout read.
- Runner settings: `precompute_factor_matrix=true`, `resume_completed_cases=true`, `reuse_research_inputs=true`.

Result:

- Completed cases: 24.
- Failed cases: 0.
- Runner-approved cases: 0.
- Positive benchmark-relative return cases: 0.
- Drawdown-clean cases at -30%: 0.
- Overlap-adjusted Sharpe >= 1 cases: 0.
- Capacity-clean cases: 12.
- Positive significant selected-tail RankIC cases: 14.
- Strict promotable cases: 0.

Best 10 bps rows by factor:

- `ps_ttm_inverse_large_mv`, top50: annualized return -0.03%, Sharpe 0.067, overlap-adjusted Sharpe 0.033, win rate 50.9%, max drawdown -65.8%, benchmark-relative return -1237.7%, capacity-limited trades 1.
- `dv_ttm_large_mv`, top200: annualized return -0.13%, Sharpe 0.040, overlap-adjusted Sharpe 0.022, win rate 54.1%, max drawdown -57.0%, benchmark-relative return -1239.9%, capacity-limited trades 2.
- `turnover_rate_f_low_large_mv`, top200: annualized return -0.78%, Sharpe -0.033, overlap-adjusted Sharpe -0.017, win rate 48.4%, max drawdown -63.8%, benchmark-relative return -1253.7%, capacity-limited trades 0.
- `turnover_rate_low_large_mv`, top50: annualized return -1.25%, Sharpe -0.038, overlap-adjusted Sharpe -0.019, win rate 51.6%, max drawdown -66.7%, benchmark-relative return -1252.6%, capacity-limited trades 0.

Interpretation:

- The large-market-cap blend reduced capacity pressure for the low-turnover variants, but it also removed the profitable part of the raw low-turnover signal.
- The PS and dividend variants are slightly less bad on overlap-adjusted Sharpe, but they still fail relative return, drawdown, and in several cases capacity.
- This is evidence that the original daily-basic low-turnover edge is heavily tied to a neglected/illiquid tail. A blunt large-cap blend is not enough.
- Decision: reject all four as standalone factors. Future work should try liquidity-neutral buckets or explicit capacity-tiered portfolios rather than a single large-cap additive blend.

## Follow-Up Queue

## Daily-Basic Size-Bucket-Neutral Rerun

The office desktop resumed and completed the size-bucket-neutral daily-basic rerun after the sync. The run used a fresh startup gate and CN stock data manifest:

- Startup gate: cleared for `office_desktop`, `factor_validation`, CN stock scope.
- Data manifest: `review_required` with no blockers; warnings were `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- Factors:
  - `turnover_rate_low_mv_bucket_rank`
  - `turnover_rate_f_low_mv_bucket_rank`
  - `dv_ttm_mv_bucket_rank`
  - `ps_ttm_inverse_mv_bucket_rank`
- Cases: 4 factors x topN 50/100/200 x cost 10/20 bps = 24.
- Period: 2015-01-05 through 2024-12-31.
- No 2025 validation or 2026 final holdout read.
- Runner settings: `precompute_factor_matrix=true`, `resume_completed_cases=true`, `reuse_research_inputs=true`.

Result:

- Completed cases: 24.
- Failed cases: 0.
- Runner-approved cases: 0.
- Capacity-clean cases with zero limited trades: 0.
- Max-participation <= 1% cases: 0.
- Positive benchmark-relative return cases: 11.
- Drawdown-clean cases at -30%: 0.
- Overlap-adjusted Sharpe >= 1 cases: 0.
- Positive significant selected-tail RankIC cases: 6.
- Strict promotable cases: 0.

Best 10 bps rows by factor:

- `turnover_rate_low_mv_bucket_rank`, top50: annualized return 49.43%, Sharpe 2.096, overlap-adjusted Sharpe 0.940, win rate 60.4%, max drawdown -58.9%, benchmark-relative return 1973.3%, capacity-limited trades 1574, max participation 30.3x ADV.
- `turnover_rate_f_low_mv_bucket_rank`, top50: annualized return 44.00%, Sharpe 1.913, overlap-adjusted Sharpe 0.854, win rate 58.2%, max drawdown -64.9%, benchmark-relative return 1383.5%, capacity-limited trades 1586, max participation 30.3x ADV.
- `ps_ttm_inverse_mv_bucket_rank`, top50: annualized return 6.26%, Sharpe 0.520, overlap-adjusted Sharpe 0.266, win rate 52.0%, max drawdown -62.8%, benchmark-relative return -1065.0%, capacity-limited trades 91.
- `dv_ttm_mv_bucket_rank`, top50: annualized return 5.04%, Sharpe 0.423, overlap-adjusted Sharpe 0.222, win rate 54.3%, max drawdown -54.9%, benchmark-relative return -1143.1%, capacity-limited trades 224.

Watchlist, not promotion:

- Ten parameter rows met a loose research-watch filter of positive relative return, annualized return > 10%, Sharpe > 1, and significant positive RankIC.
- All ten came from the two low-turnover families; none came from dividend yield or inverse PS.
- All ten still failed hard gates because drawdown exceeded -30% and capacity-limited trades were present.

Interpretation:

- Size-bucket neutralization preserved the long-cycle low-turnover signal, unlike the blunt large-market-cap blend.
- The edge is not ready for promotion: every row fails drawdown and capacity, and no row reaches overlap-adjusted Sharpe >= 1 after overlapping-return correction.
- Dividend yield and inverse PS bucket ranks should be rejected as standalone directions under this protocol.
- The next aligned direction is not more value-parameter tuning. It is a capacity-constrained low-turnover transformation: liquidity floor, ADV/amount gate, position-cap-aware selection, or explicit capacity-tiered portfolio construction.

## Daily-Basic Liquid Low-Turnover Rerun

The office desktop then tested a stricter liquidity-gated version of the low-turnover signal through the new `daily_basic_technical_combo` factor source:

- `turnover_rate_low_liquid_mv_bucket_rank`
- `turnover_rate_f_low_liquid_mv_bucket_rank`

Design:

- Compute a 20-day rolling ADV proxy from stock bars `amount`.
- Rank liquidity inside each size bucket, not globally, so small-cap buckets are not automatically removed.
- Keep only the more liquid half of each size bucket, then rank low turnover inside the same bucket.
- Cases: 2 factors x topN 50/100/200 x cost 10/20 bps = 12.
- Period: 2015-01-05 through 2024-12-31.
- No 2025 validation or 2026 final holdout read.
- Runner settings: `precompute_factor_matrix=true`, `resume_completed_cases=true`, `reuse_research_inputs=true`.

Result:

- Completed cases: 12.
- Failed cases: 0.
- Runner-approved cases: 0.
- Capacity-clean cases with zero limited trades: 0.
- Max-participation <= 1% cases: 0.
- Positive benchmark-relative return cases: 0.
- Drawdown-clean cases at -30%: 0.
- Overlap-adjusted Sharpe >= 1 cases: 0.
- Positive significant selected-tail RankIC cases: 0.
- Strict promotable cases: 0.

Best 10 bps rows by factor:

- `turnover_rate_low_liquid_mv_bucket_rank`, top200: annualized return 1.20%, Sharpe 0.170, overlap-adjusted Sharpe 0.090, win rate 49.4%, max drawdown -57.9%, benchmark-relative return -1200.6%, capacity-limited trades 20, max participation 7.58x ADV.
- `turnover_rate_f_low_liquid_mv_bucket_rank`, top200: annualized return 0.66%, Sharpe 0.116, overlap-adjusted Sharpe 0.061, win rate 49.0%, max drawdown -62.6%, benchmark-relative return -1218.7%, capacity-limited trades 19, max participation 7.58x ADV.

Interpretation:

- The liquidity gate materially reduced capacity pressure compared with the raw size-bucket low-turnover factors, but it also destroyed the top-N profitability.
- Full-universe RankIC stayed positive and significant, while selected-tail RankIC turned weak or negative. The tradable basket is not capturing the apparent universe-level signal.
- Decision: reject both liquid-gated factors as standalone candidates.
- Methodological takeaway: low-turnover remains a diagnostic signal worth studying, but a hard liquidity floor is not enough. The next useful work should test risk-managed or capacity-tiered expressions rather than more simple value/turnover parameter tuning.

Next office-desktop work should prioritize corrected-coverage reruns of older moneyflow and residualized candidates before treating any previous long-cycle report as promotion evidence. Reports produced before the authority-bars coverage fix should be considered stale unless rerun under the year-coverage gate. For daily-basic low-turnover, continue only through capacity-aware portfolio construction or risk-control transformations, not as a raw top-N long-only signal.

## Residual/Regime Holdout Guard Fix

The office desktop started the pre-wired residual moneyflow/regime validation profile and found a sample-boundary issue before accepting any new evidence:

- Startup gate cleared for `office_desktop`, `factor_validation`, CN stock scope, commits/pushes disabled.
- CN stock data manifest was `review_required` with no blockers; warnings were `extreme_return_rows_present` and `moneyflow_symbol_coverage_below_bars`.
- The first profile attempt failed because the residual config pointed to missing `data/processed/tushare_moneyflow_inputs`.
- Local authority moneyflow inputs exist through `configs/cn_stock_authority_moneyflow_inputs_2015_2025.json`; the residual and technical-combo walk-forward configs now point there.
- A fold-schedule audit then found that default processed bars from `data/processed` would generate rolling folds through 2026-06-04, which would touch the final holdout.
- The default desktop residual bars root now uses `configs/cn_stock_authority_bars_2015_2025.json`, and `scripts/run_walk_forward.py` can load authority bars configs directly.
- Regression tests now cover both authority bars loading and the desktop default data root.

Verification after the fix:

- Affected unit tests: 44 passed.
- Project audit: passed.
- Corrected fold schedule: 38 folds, bars end at 2025-12-31, final fold test ends at 2025-12-02.
- No 2026 final holdout dates are included in the corrected residual/regime run.

Current status:

- The stale residual walk-forward output from the wrong data root was deleted from `data/reports/walk_forward_tushare_moneyflow_residual_regime`.
- The corrected residual/regime validation was restarted with authority bars and authority moneyflow inputs.
- Results are not yet promotion evidence until the walk-forward leaderboard, market-regime coverage pack, promotion gate, and desktop validation summary all complete.

### Residual/Regime 20-Fold Interim Checkpoint

As of 2026-06-20 03:52 +0800, the corrected residual/regime run had completed 20 of the 38 authority-data rolling folds and had started `fold_21`.

Interim evidence from the completed test leaderboards:

- Completed test rows: 1,920.
- Unique parameter cases: 96.
- Complete folds: 20.
- Runner-approved rows: 46 / 1,920.
- Approved rows were clustered in `fold_05`, `fold_11`, and `fold_16`; `fold_20` had 0 approved rows.
- No parameter case was approved in more than 2 of 20 folds.

Best case-level rows by strict cross-fold survival:

- `CN_large_minus_liquidity_20_top10_cost20_reb1_regime120`: approved in 2/20 folds, positive relative return in 10/20 folds, drawdown-clean in 18/20 folds, capacity-clean in 3/20 folds, mean overlap-adjusted Sharpe 0.079, mean relative return 5.28%, worst drawdown -36.6%, max participation 8.60x ADV.
- `CN_large_resid_liquidity_20_top10_cost20_reb1_regime120`: approved in 2/20 folds, positive relative return in 10/20 folds, drawdown-clean in 17/20 folds, capacity-clean in 2/20 folds, mean overlap-adjusted Sharpe -0.118, mean relative return 3.19%, worst drawdown -38.1%, max participation 8.60x ADV.
- `CN_large_resid_liq_vol_amt_20_top10_cost20_reb1_regime120`: approved in 2/20 folds, positive relative return in 10/20 folds, drawdown-clean in 17/20 folds, capacity-clean in 2/20 folds, mean overlap-adjusted Sharpe -0.266, mean relative return 2.92%, worst drawdown -38.0%, max participation 8.60x ADV.

Factor-family aggregate after 20 folds:

- `large_minus_liquidity_20`: 14 approved rows, 184 positive-relative rows, mean relative return 3.80%, mean overlap-adjusted Sharpe -0.714, worst drawdown -44.3%, max participation 17.20x ADV.
- `large_resid_liquidity_20`: 11 approved rows, 174 positive-relative rows, mean relative return 1.79%, mean overlap-adjusted Sharpe -0.902, worst drawdown -47.4%, max participation 17.20x ADV.
- `large_resid_liq_vol_amt_20`: 11 approved rows, 172 positive-relative rows, mean relative return 1.76%, mean overlap-adjusted Sharpe -0.969, worst drawdown -48.6%, max participation 17.20x ADV.
- `large_resid_liq_vol_amt_gate_20`: 10 approved rows and 464 capacity-clean rows, but only 10 positive-relative rows, mean relative return -27.5%, mean overlap-adjusted Sharpe -4.095, worst drawdown -52.4%.

Interim conclusion:

- There is still no promotable or paper-ready residual/regime factor.
- The apparent winners are local-window effects: approved rows are concentrated in a few folds and do not survive broad cross-fold stability.
- Top5/top10 variants can show high single-fold returns, but they fail capacity and drawdown controls; the capacity-gated variant fixes capacity while destroying returns.
- `large_minus_liquidity_20` remains the least-bad research line because it has the highest approved-row count and relative-return breadth, but it is not useful enough for promotion under the current gate.

Immediate continuation:

- `fold_21` completed at 2026-06-20 04:44 +0800 with 0 approved rows out of 96.
- The top `fold_21` rows had high single-fold Sharpe, but were rejected because capacity-limited trades were present and IC/tail-IC significance was not present.

### Startup Gate Long-Cycle Hardening

As of 2026-06-20 05:24 +0800, the repeatable CN stock factor-mining startup gate was hardened so future office/high-spec desktop runs cannot silently fall back to the older short-window workflow.

Changes made:

- `configs/factor_mining_startup_cn_stock.json` now requires `long_cycle_replay` and `same_parameter_full_sample` windows from `2015-01-01` through `2025-12-31`.
- The default experiment design now requires same-parameter long-cycle replay, full-sample diagnostic reruns, rolling walk-forward train/test splits, market-regime coverage, look-ahead audit, and overfit/multiple-testing audit before new profitability claims.
- `src/quant_robot/ops/factor_mining_startup.py` now rejects cleared startup packets that lack the long-cycle stage policy or the long-cycle per-run confirmations.
- `docs/research/cn_stock_factor_mining_startup_gate_2026-06-17.md` now states that 2023-2024 discovery evidence is legacy first-pass evidence only; it must be replayed across the long cycle before it can influence promotion or new mining direction.

Verification:

- Added a failing test proving old startup packets without long-cycle protocol were previously accepted.
- Focused startup-gate tests now pass: 10/10.
- Related startup/alpha gate tests now pass: 15/15.
- Full unit suite now passes: 622/622.
- `compileall` passed for `src`, `scripts`, `tests`, and `quant_robot`.
- Project audit passed with 545 files scanned.

### Residual/Regime 22-Fold Interim Checkpoint

As of 2026-06-20 05:39 +0800, `fold_22` had completed and `fold_23` had been created.

Completed evidence:

- Complete folds: 22 / 38.
- Completed test rows: 2,112.
- Runner-approved rows: 66 / 2,112.
- Approved rows by fold: `fold_05` 18, `fold_11` 24, `fold_16` 4, `fold_22` 20.
- There are still no approved rows outside those four local windows.

`fold_22` was a strong single-fold rebound for the capacity-gated residual line:

- `fold_22` approved rows: 20 / 96.
- All 20 approved rows came from `large_resid_liq_vol_amt_gate_20`.
- The best single-fold approved top5 rows reached Sharpe 3.64 and overlap-autocorrelation-adjusted Sharpe 3.27, with annualized return 31.3%, win rate 59.0%, max drawdown -9.35%, and no capacity-limited trades.

Cross-fold aggregation still blocks promotion:

- Best strict-survival case: `CN_large_resid_liq_vol_amt_gate_20_top5_cost20_reb1_regime120`, approved in 3/22 folds (`fold_11`, `fold_16`, `fold_22`), positive relative return in only 3/22 folds, drawdown-clean in 11/22, capacity-clean in 20/22, mean overlap-adjusted Sharpe -2.20, mean relative return -19.44%, worst drawdown -46.8%, max participation 0.83x ADV.
- Best non-gated breadth case remains `CN_large_minus_liquidity_20_top10_cost20_reb1_regime120`, approved in 2/22 folds, positive relative return in 12/22, drawdown-clean in 20/22, capacity-clean in only 3/22, mean overlap-adjusted Sharpe 0.72, mean relative return 9.76%, worst drawdown -36.6%, max participation 8.60x ADV.
- Factor aggregate after 22 folds: `large_resid_liq_vol_amt_gate_20` has the most approved rows (30) and the cleanest capacity profile (488/528 capacity-clean rows), but mean overlap-adjusted Sharpe is -3.67 and mean relative return is -25.2%.
- `large_minus_liquidity_20` has weaker capacity (62/528 capacity-clean rows) but broader positive relative-return coverage (228/528 rows), with mean overlap-adjusted Sharpe -0.11 and mean relative return 7.95%.

Interim conclusion:

- `fold_22` is useful diagnostic evidence, not promotion evidence.
- The capacity-gated residual line can work in isolated regimes, but across 22 folds it remains a negative-return filter.
- The ungated `large_minus_liquidity_20` line still has the best breadth but fails capacity badly.
- No residual/regime factor is promotable or paper-ready at this checkpoint.

### Residual/Regime 23-Fold Interim Checkpoint

As of 2026-06-20 06:35 +0800, `fold_23` had completed and `fold_24` had been created.

`fold_23` evidence:

- `fold_23` approved rows: 8 / 96.
- All approved rows again came from `large_resid_liq_vol_amt_gate_20`, concentrated in top5 variants.
- The best `fold_23` gated top5 cost20 rows had Sharpe 3.00, overlap-autocorrelation-adjusted Sharpe 2.98, annualized return 182.0%, relative return 23.7%, win rate 54.1%, max drawdown -12.3%, and no capacity-limited trades.

23-fold aggregation:

- Complete folds: 23 / 38.
- Completed test rows: 2,208.
- Runner-approved rows: 74 / 2,208.
- Approved rows by fold: `fold_05` 18, `fold_11` 24, `fold_16` 4, `fold_22` 20, `fold_23` 8.
- Best strict-survival gated case: `CN_large_resid_liq_vol_amt_gate_20_top5_cost20_reb1_regime120`, approved in 4/23 folds, positive relative return in only 4/23 folds, drawdown-clean in 12/23, capacity-clean in 21/23, mean overlap-adjusted Sharpe -1.98, mean relative return -17.6%, worst drawdown -46.8%.
- Best breadth case remains `CN_large_minus_liquidity_20_top10_cost20_reb1_regime120`, approved in 2/23 folds, positive relative return in 13/23, drawdown-clean in 21/23, capacity-clean in only 3/23, significant IC in 8/23, mean overlap-adjusted Sharpe 1.07, mean relative return 13.9%, worst drawdown -36.6%, max participation 8.60x ADV.

Factor-family aggregate after 23 folds:

- `large_resid_liq_vol_amt_gate_20`: 38 approved rows, 512/552 capacity-clean rows, but mean overlap-adjusted Sharpe -3.52 and mean relative return -24.3%.
- `large_minus_liquidity_20`: 14 approved rows, 252 positive-relative rows, mean overlap-adjusted Sharpe 0.18, mean relative return 11.31%, but only 62/552 capacity-clean rows and max participation 17.20x ADV at the family level.
- `large_resid_liquidity_20`: 11 approved rows, mean overlap-adjusted Sharpe -0.02, mean relative return 8.70%, capacity still poor.
- `large_resid_liq_vol_amt_20`: 11 approved rows, mean overlap-adjusted Sharpe -0.09, mean relative return 8.55%, capacity still poor.

Interim conclusion:

- `fold_22` and `fold_23` show a local favorable regime for the gated top5 expression, but the full 23-fold record still says that gate destroys returns outside isolated windows.
- `large_minus_liquidity_20` is now the best research lead by breadth and mean relative return, but it remains non-tradable under current capacity constraints.
- No factor is promotable or paper-ready at 23/38 folds.

### Residual/Regime 24-Fold Interim Checkpoint

As of 2026-06-20 07:32 +0800, `fold_24` had completed and `fold_25` had been created.

`fold_24` evidence:

- `fold_24` approved rows: 0 / 96.
- `fold_24` significant-positive IC rows: 0 / 96.
- This fold is a strong counterexample to the `fold_22`/`fold_23` gated top5 rebound.

24-fold aggregation:

- Complete folds: 24 / 38.
- Completed test rows: 2,304.
- Runner-approved rows: 74 / 2,304.
- Approved rows remain concentrated in `fold_05`, `fold_11`, `fold_16`, `fold_22`, and `fold_23`; no approved rows appeared in `fold_24`.
- Best strict-survival gated case: `CN_large_resid_liq_vol_amt_gate_20_top5_cost20_reb1_regime120`, approved in 4/24 folds, positive relative return in only 4/24, drawdown-clean in 13/24, capacity-clean in 22/24, mean overlap-adjusted Sharpe -1.95, mean relative return -17.3%, worst drawdown -46.8%.
- Best breadth case: `CN_large_minus_liquidity_20_top10_cost20_reb1_regime120`, approved in 2/24 folds, positive relative return in 14/24, drawdown-clean in 22/24, capacity-clean in only 3/24, significant IC in 8/24, mean overlap-adjusted Sharpe 1.17, mean relative return 15.75%, worst drawdown -36.6%, max participation 8.60x ADV.

Factor-family aggregate after 24 folds:

- `large_resid_liq_vol_amt_gate_20`: 38 approved rows, 536/576 capacity-clean rows, but mean overlap-adjusted Sharpe -3.51 and mean relative return -24.1%.
- `large_minus_liquidity_20`: 14 approved rows, 276 positive-relative rows, mean overlap-adjusted Sharpe 0.32, mean relative return 13.61%, but only 62/576 capacity-clean rows.
- `large_resid_liquidity_20`: 11 approved rows, mean overlap-adjusted Sharpe 0.10, mean relative return 10.57%, capacity still poor.
- `large_resid_liq_vol_amt_20`: 11 approved rows, mean overlap-adjusted Sharpe 0.04, mean relative return 10.57%, capacity still poor.

Interim conclusion:

- The gated residual factor is capacity-clean but still economically bad across the long cycle; `fold_24` breaks the short `fold_22`/`fold_23` favorable streak.
- `large_minus_liquidity_20` remains the only research lead worth watching because breadth and mean relative return continue to improve, but it is still blocked by severe capacity constraints and sparse approvals.
- No factor is promotable or paper-ready at 24/38 folds.

### Residual/Regime 25-Fold Interim Checkpoint

As of 2026-06-20 08:32 +0800, `fold_25` had completed and `fold_26` had been created.

`fold_25` evidence:

- `fold_25` approved rows: 0 / 96.
- `fold_25` significant-positive IC rows: 36 / 96.
- This fold shows that positive IC alone still does not translate into a tradable approved portfolio under the current cost, capacity, drawdown, and relative-return gates.

25-fold aggregation:

- Complete folds: 25 / 38.
- Completed test rows: 2,400.
- Runner-approved rows: 74 / 2,400.
- Approved rows remain concentrated in `fold_05`, `fold_11`, `fold_16`, `fold_22`, and `fold_23`; `fold_24` and `fold_25` both added 0 approved rows.
- Best strict-survival gated case: `CN_large_resid_liq_vol_amt_gate_20_top5_cost20_reb1_regime120`, approved in 4/25 folds, positive relative return in only 4/25, capacity-clean in 23/25, mean overlap-adjusted Sharpe -2.01, mean relative return -18.1%, worst drawdown -46.8%.
- Best breadth case: `CN_large_minus_liquidity_20_top10_cost20_reb1_regime120`, approved in 2/25 folds, positive relative return in 14/25, drawdown-clean in 23/25, capacity-clean in only 3/25, significant IC in 9/25, mean overlap-adjusted Sharpe 1.13, mean relative return 15.05%, worst drawdown -36.6%, max participation 8.60x ADV.

Factor-family aggregate after 25 folds:

- `large_resid_liq_vol_amt_gate_20`: 38 approved rows, 560/600 capacity-clean rows, but mean overlap-adjusted Sharpe -3.54 and mean relative return -24.6%.
- `large_minus_liquidity_20`: 14 approved rows, 285 positive-relative rows, mean overlap-adjusted Sharpe 0.32, mean relative return 13.37%, but only 62/600 capacity-clean rows.
- `large_resid_liquidity_20`: 11 approved rows, mean overlap-adjusted Sharpe 0.08, mean relative return 10.05%, capacity still poor.
- `large_resid_liq_vol_amt_20`: 11 approved rows, mean overlap-adjusted Sharpe 0.02, mean relative return 10.01%, capacity still poor.

Interim conclusion:

- Two consecutive zero-approved folds after the `fold_22`/`fold_23` rebound strongly support the prior view that the gated residual signal is regime-local and not broadly robust.
- `large_minus_liquidity_20` remains a research lead, not a tradable factor, because capacity failure is persistent and approvals are sparse.
- No factor is promotable or paper-ready at 25/38 folds.

### Residual/Regime 26-Fold Interim Checkpoint

As of 2026-06-20 09:29 +0800, `fold_26` had completed and `fold_27` had been created.

`fold_26` evidence:

- `fold_26` approved rows: 0 / 96.
- `fold_26` significant-positive IC rows: 0 / 96.
- `fold_24`, `fold_25`, and `fold_26` now form three consecutive zero-approved folds after the `fold_22`/`fold_23` gated rebound.

26-fold aggregation:

- Complete folds: 26 / 38.
- Completed test rows: 2,496.
- Runner-approved rows: 74 / 2,496.
- Approved rows remain concentrated in `fold_05`, `fold_11`, `fold_16`, `fold_22`, and `fold_23`.
- Best strict-survival gated case: `CN_large_resid_liq_vol_amt_gate_20_top5_cost20_reb1_regime120`, approved in 4/26 folds, positive relative return in only 4/26, capacity-clean in 24/26, mean overlap-adjusted Sharpe -2.05, mean relative return -17.8%, worst drawdown -46.8%.
- Best breadth case: `CN_large_minus_liquidity_20_top10_cost20_reb1_regime120`, approved in 2/26 folds, positive relative return in 15/26, drawdown-clean in 24/26, capacity-clean in only 3/26, significant IC in 9/26, mean overlap-adjusted Sharpe 1.08, mean relative return 14.68%, worst drawdown -36.6%, max participation 8.60x ADV.

Factor-family aggregate after 26 folds:

- `large_resid_liq_vol_amt_gate_20`: 38 approved rows, 584/624 capacity-clean rows, but mean overlap-adjusted Sharpe -3.57 and mean relative return -24.3%.
- `large_minus_liquidity_20`: 14 approved rows, 301 positive-relative rows, mean overlap-adjusted Sharpe 0.29, mean relative return 13.03%, but only 62/624 capacity-clean rows.
- `large_resid_liquidity_20`: 11 approved rows, mean overlap-adjusted Sharpe 0.06, mean relative return 9.89%, capacity still poor.
- `large_resid_liq_vol_amt_20`: 11 approved rows, mean overlap-adjusted Sharpe 0.02, mean relative return 9.91%, capacity still poor.

Interim conclusion:

- The gated residual factor should be treated as rejected as a standalone line unless a new, pre-registered thesis explains and controls its narrow favorable windows.
- `large_minus_liquidity_20` remains a research lead because it has the best breadth, but current capacity constraints still block any promotion.
- No factor is promotable or paper-ready at 26/38 folds.
