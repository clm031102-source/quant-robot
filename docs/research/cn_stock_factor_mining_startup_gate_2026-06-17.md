# CN Stock Factor Mining Startup Gate - 2026-06-17

## Purpose

This gate turns the 2026-06-17 audit decision into a repeatable pre-run checklist for A-share CN stock factor mining.

Run it before every new CN stock factor batch, validation rerun, or review pass. It confirms that the office/high-spec desktop is working on `market=CN`, `asset_type=stock`, and that ETF rotation evidence is out of scope for the run. After Batch 12, the next controlled task is 2025 validation of the two daily champion candidates, so create or switch to a factor-validation branch before running the validation gate.

## Default Validation Command

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py `
  --config configs\factor_mining_startup_cn_stock.json `
  --machine office_desktop `
  --task factor_validation `
  --branch codex/factor-validation-cn-stock-20260617 `
  --current-branch codex/factor-validation-cn-stock-20260617 `
  --market CN `
  --asset-type stock `
  --confirm-start
```

The command writes a local confirmation packet to:

- `data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json`
- `data/reports/factor_mining_startup_gate/factor_mining_startup_gate.md`

These outputs are local research artifacts and must not be committed.

## Batch 12 Validation Preflight

Before any 2025 validation read, run the Batch 12 validation preflight. It checks the frozen handoff, confirms the task/branch are validation-specific, confirms the 2025-only window, and blocks if 2026 final holdout is allowed or touched.

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_batch12_validation_preflight.py `
  --handoff configs\cn_stock_batch12_validation_handoff_20260617.json `
  --startup-gate-packet data\reports\factor_mining_startup_gate\factor_mining_startup_gate.json `
  --machine office_desktop `
  --task factor_validation `
  --branch codex/factor-validation-cn-stock-20260617 `
  --current-branch codex/factor-validation-cn-stock-20260617 `
  --market CN `
  --asset-type stock
```

The command writes:

- `data/reports/cn_stock_batch12_validation_preflight/batch12_validation_preflight.json`
- `data/reports/cn_stock_batch12_validation_preflight/batch12_validation_preflight.md`

If this preflight is blocked, do not run OOS validation.

## Data Manifest Command

Build the CN stock data manifest against the same processed store before running candidate generation:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py `
  --data-root data\processed\office_desktop_20260616_combined_research `
  --output-dir data\reports\cn_stock_data_manifest
```

The command writes local research artifacts to:

- `data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json`
- `data/reports/cn_stock_data_manifest/cn_stock_data_manifest.md`
- `data/reports/cn_stock_data_manifest/cn_stock_symbol_coverage.csv`

If the manifest is `blocked`, stop and fix the data or scope. If it is `review_required`, read the warnings first; only pass `--allow-review-required-data-manifest` to mining commands after explicitly accepting those warnings for the current run.

## Protected Mining Entrypoints

After the startup gate and data manifest are available, CN processed-bars mining commands can consume both packets through their default paths:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_alpha_factory.py `
  --source processed-bars `
  --data-root data\processed\office_desktop_20260616_combined_research `
  --market CN `
  --factor-source moneyflow_technical_combo `
  --moneyflow-input-root data\processed\office_desktop_20260616_combined_research `
  --startup-gate-packet data\reports\factor_mining_startup_gate\factor_mining_startup_gate.json `
  --data-manifest-packet data\reports\cn_stock_data_manifest\cn_stock_data_manifest.json `
  --output-dir data\reports\cn_stock_factor_batch_alpha_factory
```

```powershell
.\.venv\Scripts\python.exe scripts\run_experiment_grid.py `
  --config configs\experiment_grid_cn_stock_first_batch.json `
  --source processed-bars `
  --data-root data\processed\office_desktop_20260616_combined_research `
  --startup-gate-packet data\reports\factor_mining_startup_gate\factor_mining_startup_gate.json `
  --data-manifest-packet data\reports\cn_stock_data_manifest\cn_stock_data_manifest.json `
  --output-dir data\reports\cn_stock_factor_batch_grid
```

Both commands now block `source=processed-bars` plus `market=CN` runs unless `data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json` exists, is generated today, and is cleared, and `data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json` exists, is generated today, and has no blockers. Fixture runs remain available for smoke tests.

## Confirmed Scope

- Target market: `CN`
- Target asset type: `stock`
- Main objective: CN stock cross-sectional factor research
- Explicitly excluded: `CN_ETF`, `HK`, `US`, `CRYPTO`
- Live boundary: disabled
- Broker/account/order access: forbidden

## Research Direction

Every new CN stock mining run must confirm the structured direction in `configs/factor_mining_startup_cn_stock.json`:

- objective: `cn_stock_cross_sectional_alpha`
- allowed factor families: price/volume, daily-basic, moneyflow, composite, liquidity/capacity
- forbidden directions: ETF rotation, single-family lock-in, OOS tuning, IC-only promotion, capacity-blind microcap tails
- failed single-family batches must be recorded and rotated away from after the configured failed-batch limit
- positive IC alone is not enough; top-N returns, costs, capacity, drawdown, and tail-IC checks decide whether a candidate can advance

## Repeatable Mining Protocol

The 2026-06-17 batch audit is now part of the startup packet. Before each new CN stock mining or validation run, confirm that the source audit, latest bootstrap diagnostic, completed tail-RankIC broad-RankIC batch, completed monthly-persistence sensitivity batch, completed monthly loss-control/phase batch, completed previous-month threshold-robustness batch, completed RankIC-enhancement batch, completed Batch 12 champion staggered-schedule batch, and Batch 12 validation handoff have been read. Batch 12 created discovery-only OOS candidates, so the next controlled task is formal 2025 validation on a factor-validation branch, not another blind discovery batch.

Default next direction:

- `factor_validation_required_for_daily_champion_oos_candidates`

Recently rejected directions:

- single-factor top-50 daily long-only selection
- direct liquid-trend long signals
- capacity-blind microcap tails
- moneyflow-only lock-in
- regime filter as the default drawdown fix
- bootstrap-only diagnostics without broad RankIC improvement
- broad RankIC improvement without monthly-return persistence
- topN breadth expansion for monthly stability
- defensive dividend overlay for monthly stability
- previous-month-positive gate without sample robustness
- high-Sharpe low-signal-count direct OOS
- threshold tuning without RankIC significance
- previous-month zero gate with low signal sample
- component mining without RankIC confirmation
- p-value reset after champion selection
- daily schedule Sharpe treated as valid without OOS validation
- overlapping holdings treated as independent daily observations

Required experiment design for the next validation pass:

- validate only the two Batch 12 daily champion candidates at 10 bps and 20 bps
- use `2025-01-01` through `2025-12-31` only; do not read 2026 final holdout
- include overlap-aware return statistics because hold20 with daily schedules creates non-independent returns
- compare daily champions against every2/every3 controls as sanity checks
- carry forward cumulative multiple-testing accounting; do not reset p-values after choosing a champion
- keep cost, capacity, turnover, drawdown, RankIC, Tail RankIC, and monthly stability gates active
- do not tune parameters, thresholds, factor components, or schedule choices during OOS validation

## Required Startup Confirmations

The gate blocks unless these items are explicitly confirmed:

- machine confirmed
- task confirmed
- branch confirmed
- commit/push policy confirmed
- CN stock scope confirmed
- ETF rotation scope rejected
- audit optimization plan confirmed
- next direction confirmed
- candidate plan pre-registered
- portfolio construction gate confirmed
- holding and rebalance plan confirmed
- bootstrap robustness plan confirmed
- parameter sensitivity plan confirmed
- latest tail-RankIC broad-RankIC batch confirmed
- latest monthly-persistence sensitivity batch confirmed
- hold20/top50 lead confirmed
- latest monthly loss-control/phase batch confirmed
- latest previous-month threshold-robustness batch confirmed
- previous-month -1% gate confirmed
- latest RankIC-enhancement batch confirmed
- downside-range champion confirmed
- latest champion staggered-schedule batch confirmed
- Batch 12 validation handoff confirmed
- daily champion OOS candidates confirmed
- factor-validation branch confirmed
- 2025-only OOS validation plan confirmed
- overlap-adjusted statistics plan confirmed
- daily versus every2/every3 controls confirmed
- cost/capacity/turnover stress confirmed
- cumulative multiple-testing gate confirmed
- cost and capacity gate confirmed
- failed direction rotation confirmed

Use `--confirm-start` only after those items are true in the current session.

## Next Controlled Research Direction

The next controlled task should be validation, not more discovery:

- candidate 1: `rankic_neg1_downside_range_blend_hold20_top50_every1_offset0_cost10_prev_month_ret_gt_neg1`
- candidate 2: `rankic_neg1_downside_range_blend_hold20_top50_every1_offset0_cost20_prev_month_ret_gt_neg1`
- discovery-only evidence: both passed cumulative RankIC and Tail RankIC gates in Batch 12
- red flag: discovery Sharpe is above 5 because hold20 daily schedules create overlapping, non-independent return observations
- validation scope: 2025 only, on a `codex/factor-validation-cn-stock-...` branch
- controls: every2/every3 schedule checks, cost/capacity/turnover stress, cumulative multiple-test accounting, no parameter tuning

Do not promote either candidate to the factor library unless 2025 validation survives these checks. Do not read 2026 final holdout until OOS validation has already cleared and the final holdout read is explicitly authorized.

## Validation Discipline

Default split:

- discovery: `2023-07-03` through `2024-12-31`
- validation: `2025-01-01` through `2025-12-31`
- final holdout: `2026-01-01` through `2026-06-15`

Do not tune parameters after reading the 2026 final holdout.

Promotion remains blocked unless the candidate survives IC/RankIC significance, cost, capacity, drawdown, minimum-trade, regime, and walk-forward gates.
