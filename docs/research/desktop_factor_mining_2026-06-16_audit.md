# Desktop Factor Mining Audit - 2026-06-16

## Scope

- Machine role: office desktop, high-intensity factor research node.
- Branch: `codex/factor-batch-moneyflow-alpha`.
- Research boundary: local research only; no broker connection, no account read, no orders, no live trading.
- Data policy: `data/raw`, `data/processed`, `data/reports`, parquet, large csv, logs, local credentials, and generated experiment outputs remain out of Git.

## Evidence From The 08:00 Run

- Main local report directory: `data/reports/desktop_factor_mining_20260616_0800/`.
- Last combo extension: `data/reports/desktop_factor_mining_20260616_0800/20260616_0705_local_combo_factor_extension/`.
- Experiment rows: 480.
- Windows: 2023H2, 2024H1, 2024H2, 2025H1.
- Factor family: moneyflow plus technical cross-sectional z-score blends.
- Lags: 1 and 2.
- Holdings: top5, top10, top20.
- Costs: 10 bps and 20 bps.
- Cross-window buckets: 39 rows candidate for further walk-forward, 21 observation, 60 eliminated.

## Candidate Directions

These are not trading conclusions. They are only priorities for stricter validation.

- `mf_low_plus_reversal_5`: positive IC in all four local windows at lag1, no high-Sharpe overfit flag in the cross-window candidate rows.
- `small_sell_plus_reversal_5`: positive IC in all four local windows at lag1, positive IC rate near 59 percent in the summary run.
- `mf_low_minus_volatility_20`: signal evidence exists, but at least one overfit flag keeps it in observation.

## Main Problems Found

- The source pipeline did not previously expose the 08:00 combo factors as first-class research factors.
- Walk-forward config loading needed to preserve `moneyflow_input_root` so moneyflow candidates can be reproduced from JSON configs.
- High Sharpe rows remain overfit suspects and must stay demoted unless rolling out-of-sample evidence survives.
- The 08:00 result set still lacks industry, market-cap, and liquidity neutral controls.
- The local run reused already-downloaded data near closeout; no new durable provider credential was used.

## Improvements Added

- Added first-class moneyflow plus technical combo factor construction under the normal factor schema.
- Added `moneyflow_technical_combo` as a research pipeline factor source.
- Added alpha-factory support for the pre-registered combo family.
- Added `configs/walk_forward_tushare_moneyflow_technical_combo.json` as a strict rolling validation template.
- Preserved `moneyflow_input_root` in walk-forward JSON loading and manifest output.
- Added archive replay support so local raw Tushare daily/moneyflow archives can be converted into a timestamped processed research store without overwriting existing data.
- Optimized combo pipeline calls to compute only the requested combo factor per case instead of rebuilding the full combo family for every case.

## Follow-Up Execution After Audit

- Replayed local raw Tushare archives into `data/processed/desktop_factor_mining_20260616_0830_archive_replay/`.
- Replay rows: 2,541,655 processed daily bars and 2,413,462 processed moneyflow rows.
- Replay coverage: 2023-07-03 through 2025-06-30 for moneyflow inputs.
- Ran a real-data combo alpha factory pass on the replay store: `data/reports/desktop_factor_mining_20260616_0800/20260616_0840_combo_alpha_factory_replay_top5_cost10_lag1/`.
- Full replay alpha-factory summary: 10/10 cases completed, 5 adjusted-significant rows, 0 paper-eligible rows.
- Main rejection reason for significant rows: `capacity_limited_trades_present`.
- Significant positive rows in the full replay pass included `mf_low_minus_volatility_20`, `large_minus_liquidity_20`, `small_sell_plus_reversal_5`, and `mf_low_plus_reversal_5`.
- Ran an optimized 2024H2 replay pass: `data/reports/desktop_factor_mining_20260616_0800/20260616_0850_combo_alpha_factory_replay_2024h2_optimized/`.
- 2024H2 optimized summary: 10/10 cases completed, 3 adjusted-significant rows, 0 paper-eligible rows.
- 2024H2 significant positive rows included `mf_low_plus_reversal_5` and `small_sell_plus_reversal_5`, but both remained blocked by capacity-limited trades.
- Performance issue remains: even optimized real-data combo runs are still heavy enough that follow-up work should cache base factor matrices across cases.

## Next Execution Plan

1. Run the combo alpha factory on current processed Tushare moneyflow inputs when local data coverage is ready.
2. Run rolling walk-forward with `configs/walk_forward_tushare_moneyflow_technical_combo.json`.
3. Promote only rows that pass adjusted IC, cost, drawdown, capacity, and minimum-fold gates.
4. Add neutralization controls next: industry, market cap, and liquidity residuals.
5. Keep failed and eliminated rows in the report; do not publish only winners.
6. Cache technical, moneyflow, and combo factor matrices per data window before sweeping top-n/cost/case grids.

## Strict Research Judgment

- Sharpe greater than 3 is an overfit warning, not evidence of deployability.
- A good single backtest is only a clue.
- Candidate means worth further walk-forward; it does not mean paper-ready or live-ready.
- Any future live-boundary work remains blocked until separate manual review, provider readiness, paper observation, and safety gates pass.
