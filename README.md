# Quant Robot

Local multi-market quantitative research framework for A-shares, A-share ETFs, Hong Kong stocks, US stocks, and crypto.

The project is currently in a Phase 5.x research-to-paper stage. It has research, walk-forward, paper simulation, promotion, Daily Ops, profile observation, Tushare activation-gate, paper-observation history, paper-ops guardrail, and paper-ops runbook workflows, but it still does not connect to real broker accounts, read live accounts, place orders, or implement automatic live trading.

## Current Status

- Cloud/research sync index: `docs/research/CURRENT_RESEARCH_INDEX.md`. Read this first after syncing on any workstation.
- Cloud branch structure: `origin/main` is the only durable remote branch after the 2026-06-27 cleanup; task branches should be temporary and deleted after merge/archive.
- Current stage: Phase 5.15 paper ops runbook.
- Latest selected paper profile: `cap60_guard12_cd3` for `CN_ETF_liquidity_10_top1_cost5_reb5`, risk tier `aggressive_growth`.
- Daily Ops status: `paper_ready` with live boundary disabled.
- Baseline Profile Observation status: stopped on `signal_data_stale`, which is why the activation chain refreshes and replays recent data.
- Real Tushare activation status: `paper_observation_ready`; readiness passed, required-asset coverage passed for `CN_ETF_XSHG_516160`, iterative expansion completed in 2 rounds, final fills are `21 / 20`, blockers are empty, and live boundary remains disabled.
- Current desktop ETF research treats Tushare `fund_basic` plus `fund_daily` as the primary CN_ETF universe and history source. CSV, AKShare, and fixtures are fallback/smoke paths only.
- Paper Observation History status: `history_clear_for_continued_paper_observation=true` with 1 recorded real Tushare activation run and zero live-boundary violations.
- Paper Ops Guardrail status: `paper_ops_watch`; continued paper observation is allowed, live readiness is false, warnings are `short_paper_history` and `provider_missing_date_rows`.
- Paper Ops Runbook status: `paper_cycle_ready`; the queue has 4 local-only, manual-start commands, and live cycle execution remains disabled.
- Audit remediation status: validation now supports rolling walk-forward folds, IC significance evidence, capacity-aware costs, stricter quality reports, stale provider-status blocking, and a central read-only execution boundary. These are stronger gates, not live-profit proof.
- Fixture activation status: `paper_observation_ready`, proving the local refresh -> replay -> sufficiency -> iterative expansion chain without network access.
- CI status: GitHub Actions now runs unit/integration tests, Python compilation, and project-audit pass checks on push and pull request.

To reproduce the real-data gate, set `TUSHARE_TOKEN` in the local shell environment and run:

```powershell
.\.venv\Scripts\python.exe scripts\run_tushare_activation_gate.py --machine highspec_desktop --report-dir data\reports\tushare_activation_gate --execute
```

Passing this gate only permits continued paper observation on refreshed data. It is not permission to trade live.

Before material desktop ETF research work, run the Quant PM startup gate so the machine, branch, required reading, research-family allocation, and `CN_ETF` objective are checked together:

```powershell
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine highspec_desktop --task factor_batch --branch <current-branch>
```

The gate blocks work when direct `CN` stock moneyflow selection is accidentally reintroduced as a primary research line. See `docs/research/quant_pm_startup_gate_2026-06-17.md`.

## What Works Now

- Canonical asset abstraction for CN, CN_ETF, HK, US, and CRYPTO.
- Offline fixture data for all research markets, including A-share ETFs.
- Unified OHLCV normalization with timezone-aware UTC timestamps.
- Parquet storage abstraction, enabled when `pyarrow` or `fastparquet` is installed.
- Implemented adapter paths for Tushare A-shares and A-share ETFs, AKShare CN/CN_ETF, yfinance HK/US, and ccxt crypto when optional packages and credentials are available. A-share ETF research can use local CSV, fixtures, AKShare, or optional Tushare ETF daily ingestion.
- Basic factors: momentum, reversal, volatility, volume change, and liquidity.
- Forward-return labels with explicit execution lag.
- IC, Rank IC, IC t-statistics, approximate p-values, positive IC rate, quantile group returns, and long-short returns.
- Research backtest with explicit execution lag, holding period, portfolio scope, transaction cost assumptions, market-impact estimates, participation-rate evidence, and conservative sleeve scaling for multi-day holding periods.
- Optional rolling walk-forward validation with fold counts, accepted-fold counts, mean out-of-sample metrics, worst out-of-sample drawdown, and fold rejection reasons.
- Research-only signal snapshots, risk-capped target weights, and advisory rebalance plans.
- Local paper trading simulation with simulated intents, fills, cash, positions, equity curve, and China-market 100-share lot rounding.
- Research decision-risk layer with benchmark comparison, cash comparison, optional regime filtering, walk-forward relative-return gates, and paper drawdown guards.
- Promotion operations summary for pre-API candidates, including live-review blockers, duplicate clusters, and local next actions.
- Promotion review packets with candidate evidence, manual-review gate state, checklist CSV, and Markdown artifacts.
- Evidence refresh plans that turn review blockers into ordered local action tracks.
- Data-quality reports and gap audits that list exact CN ETF missing asset/date rows, duplicate bars, zero volume, extreme returns, stale prices, and adjusted-close jumps.
- Provider-readiness evidence packs that classify dependency, token, adapter, market coverage, Parquet readiness, and generation date for stale-status checks.
- Provider-remediation matrices and readiness-board integration for dependency, token, adapter, and storage blockers.
- Residual blocker focus packs that prioritize projected blocker leftovers, linked work items, downstream waits, and local-only action commands.
- Residual data-gap review packs that isolate post-rehearsal blocking gap rows and write fillable local resolution templates.
- Data-gap evidence packs that attach raw CSV presence, peer-trading counts, and previous/next local rows before manual gap review.
- Residual provider review packs that isolate post-rehearsal provider blockers and write fillable local remediation templates.
- Paper-observation evidence packs that summarize observation windows, guard events, execution blocks, risk profiles, and Sharpe/drawdown trends.
- Duplicate canonical registries that persist canonical candidates, suppressed duplicate members, and suppression reasons.
- Manual-review gate rehearsal that lists clean-state requirements while proving broker/account/order boundaries stay disabled.
- Pre-API readiness board that consolidates local evidence, blockers, next actions, and live-boundary status into one artifact.
- Blocker-resolution worklist that turns readiness blockers into open local-only work items and a deduplicated action queue.
- Tushare CN ETF daily ingestion path through `fund_daily`, plus `etf_share_size` share, scale, NAV, and premium/discount auxiliary data.
- Risk-tier policy, constrained candidate search, paper-profile optimization, Daily Ops activation, profile-observation stop rules, recent-data refresh, post-refresh replay, observation sufficiency, iterative expansion, Tushare activation-gate packs, paper-observation history ledgers, paper-ops guardrail packs, and paper-only runbook command queues.
- Paper-simulation execution-block events for suspended, zero-volume, limit-up, and limit-down bars when those fields exist in local data.
- Paper-simulation fills now record participation rate, capacity-limit flags, and market-impact fees when amount data is available.
- Central execution-boundary helpers produce read-only status, non-executable manual review packets, and an explicit refusal path for any live execution request.
- CSV, JSON, and SVG report outputs.

## Run Tests

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

## Workstation Startup

Before starting work on the laptop, high-spec desktop, or office desktop, confirm the machine, task type, branch, and commit/push permission. Branches are named by work content, not by machine.

```powershell
.\.venv\Scripts\python.exe scripts\start_task_context.py
```

See `AGENTS.md`, `configs/workstations.json`, and `docs/workstation_protocol.md`.

Before starting CN stock factor mining on a desktop, run the CN stock startup gate once for the current session. This keeps CN stock alpha research separate from CN ETF rotation research and confirms the latest audit-driven next-run protocol:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_startup_gate.py --config configs\factor_mining_startup_cn_stock.json --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-stock-20260617 --current-branch codex/factor-batch-cn-stock-20260617 --market CN --asset-type stock --confirm-start
```

Then build the CN stock data manifest for the same local processed store:

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_stock_data_manifest.py --data-root data\processed\office_desktop_20260616_combined_research --output-dir data\reports\cn_stock_data_manifest
```

Both commands write local-only packets under `data/reports/` and do not authorize live trading or cloud push.
CN `processed-bars` runs through `run_tushare_alpha_factory.py` and `run_experiment_grid.py` require a same-day cleared startup packet and a same-day non-blocked CN stock data manifest by default. The startup packet must include the repeatable mining protocol from the latest audit: review rejected directions, read the latest bootstrap, tail-RankIC, and monthly-persistence diagnostics, pre-register the hold20/top50 lead, test monthly loss-control or rebalance-phase sensitivity, and preserve tail/broad RankIC before touching OOS. If the data manifest is `review_required`, read the warnings first; use `--allow-review-required-data-manifest` only after explicitly accepting them for that run.

For the daily safe-sync workflow, say `同步项目` or run an audit first:

```powershell
python scripts\sync_project.py --machine office_desktop --task factor_batch
```

Only execute and push after the audit is clean:

```powershell
python scripts\sync_project.py --machine office_desktop --task factor_batch --execute --push
```

A clean sync audit has no blocked paths, no pending branch-integration work, and an empty `branch_discovery.errors` list. If branch discovery fails, fix the Git/ref problem before pushing so another workstation's factor branch is not missed.

## Run Core Checks

This runs the local test suite, Python compile check, project audit, readiness check, provider status, provider evidence, provider remediation, provider remediation rehearsal, data catalog, data-quality gap audit, data-gap resolution, data-gap evidence, data-gap rehearsal, offline fixture research, the configurable research pipeline, the experiment grid, walk-forward validation, signal snapshot generation, paper simulation, paper observation, promotion operations summary, duplicate registry, promotion review packet, manual review rehearsal, evidence refresh plan, pre-API readiness board, readiness projection, blocker worklist, residual blocker focus pack, residual data-gap review pack, residual provider review pack, Daily Ops, profile observation, recent-data refresh, post-refresh replay, observation sufficiency, expanded observation replay, iterative observation expansion, Tushare activation gate, paper-observation history, paper-ops guardrail, paper-ops runbook, risk candidate selector, constrained candidate search, and paper profile optimizer. It does not download market data unless a stage is explicitly run in execute mode with valid provider credentials.

The batch experiment grid exits non-zero if any case fails or if no case completes. Walk-forward validation exits non-zero if the underlying train/test grids fail or if no candidate is accepted. This keeps local checks from hiding failed research runs inside CSV/JSON leaderboards.

For laptop architecture/audit work, use the laptop profile. It keeps the fast safety, provider-readiness, fixture research, signal snapshot, paper-simulation, recent-refresh dry-run, activation-gate dry-run, and paper-ops guardrail checks without running the heavier experiment grid, walk-forward, promotion, and profile-optimizer chain.

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe scripts\run_checks.py --execute
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop --execute
```

To inspect the check plan without running it:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe scripts\run_checks.py
.\.venv\Scripts\python.exe scripts\run_checks.py --profile laptop
```

## Run Project Audit

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe scripts\run_project_audit.py
```

Outputs are written to `data/reports/project_audit/`.

## Show Provider Status

```powershell
$env:PYTHONPATH='src'
python scripts\show_provider_status.py
```

This reports optional package, token, and implementation readiness for Tushare, AKShare, yfinance, ccxt, and Parquet storage.

To write review-ready provider evidence:

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_evidence.py --output-dir data\reports\provider_evidence
```

## Show Local Data Catalog

```powershell
$env:PYTHONPATH='src'
python scripts\show_data_catalog.py --root data
```

## Run Offline Fixture Research

```powershell
$env:PYTHONPATH='src'
python scripts\run_fixture_research.py
```

Outputs are written to `data/reports/fixture_research/`.

## Run Configurable Research Pipeline

```powershell
$env:PYTHONPATH='src'
python scripts\run_research_pipeline.py --source fixture --market ALL --factor momentum_2 --top-n 2 --cost-bps 5 --output-dir data\reports\research_pipeline
```

`--market ALL` uses one global portfolio by default so the combined multi-market backtest is not accidentally leveraged once per market. Single-market runs use market-level selection by default. `--forward-horizon` drives both the forward-return label horizon and the research backtest holding period. Use `--portfolio-scope` or `--periods-per-year` only when you need to override the defaults.

When real processed bars exist, point the same pipeline at a processed-bars root:

```powershell
$env:PYTHONPATH='src'
python scripts\run_research_pipeline.py --source processed-bars --data-root data\processed\tushare_fixture --market CN --factor momentum_2 --output-dir data\reports\research_pipeline_cn
```

## Run Batch Experiment Grid

This runs a local multi-market factor sweep and writes a leaderboard. Fixture results are explicitly marked as `data_mode=fixture` and are not real performance.

```powershell
$env:PYTHONPATH='src'
python scripts\run_experiment_grid.py --source fixture
```

Outputs are written to `data/reports/experiment_grid/` by default:

- `leaderboard.csv`
- `leaderboard.json`
- `manifest.json`
- one artifact folder per experiment case

Edit `configs/experiment_grid.json` to change markets, factors, transaction costs, market-impact assumptions, capacity participation limits, position counts, holding horizon, optional portfolio scope, annualization periods, ranking metric, and output path. Factor names such as `momentum_2` must reference windows included in `factor_windows`; mismatches fail fast instead of producing silent no-trade cases.

## Run Walk-Forward Validation

This splits local data into train and out-of-sample test periods, runs the same experiment candidates on both sides, and ranks candidates by sample-out stability. Fixture results remain demo-only.

```powershell
$env:PYTHONPATH='src'
python scripts\run_walk_forward.py --source fixture
```

Outputs are written to `data/reports/walk_forward/` by default:

- `walk_forward_leaderboard.csv`
- `walk_forward_leaderboard.json`
- `manifest.json`
- `train/` and `test/` per-case artifacts
- `walk_forward_folds.csv` when rolling mode is enabled

Edit `configs/walk_forward.json` to change the split date, candidate grid, acceptance thresholds, and output path. CN ETF production configs can enable `rolling_train_days`, `rolling_test_days`, `rolling_step_days`, and `min_accepted_folds`. The test segment includes train-period warmup bars for rolling factor calculation, but signals and trades are restricted to out-of-sample dates.

For the current desktop residual-regime validation profile, run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_desktop_factor_validation.py
```

This uses `configs/walk_forward_tushare_moneyflow_residual_regime.json` with processed bars and Tushare moneyflow inputs. A run with zero accepted candidates is still a valid strict-validation result when all train/test grids completed.
The residual-regime config enables `precompute_factor_matrix` so each grid run reuses one production factor matrix across TopN, cost, and regime cases instead of recomputing the same residual factors for every case.

To run the desktop validation check chain around that profile:

```powershell
$env:PYTHONPATH='src'
python scripts\run_checks.py --profile desktop-validation --execute
```

The profile also builds a strict market-regime coverage pack from walk-forward test-fold `regime_curve.csv` files, requiring both allowed and blocked regime-filter dates, then builds a research-only promotion gate report and writes `docs/research/desktop_residual_regime_validation_latest.md`. The residual-regime promotion gate requires that coverage pack, blocks single-lookback regime wins, and treats out-of-sample Sharpe above `3.0` as an overfit blocker, so one-regime or too-good-to-be-true evidence cannot be promoted by running the promotion command alone. The summary command cross-checks the leaderboard against the walk-forward `manifest.json`, verifies promotion candidate case IDs, and records data-quality, promotion-gate, and regime-coverage status, so stale or mismatched validation artifacts fail instead of producing a misleading Markdown summary.

The desktop profile's data-quality audit is pinned to the CN residual-regime data surface: `python scripts\run_data_quality_audit.py --data-root data\processed --market CN --output-dir data\reports\data_quality_gap_audit_tushare_moneyflow_residual_regime`. The residual-regime promotion gate consumes that audit JSON, so missing data-quality evidence stops the gate instead of being silently ignored. To build only the promotion report after a validation run:

```powershell
$env:PYTHONPATH='src'
python scripts\run_promotion_report.py --config configs\promotion_gate_tushare_moneyflow_residual_regime.json
```

To rebuild only the syncable Markdown summary:

```powershell
$env:PYTHONPATH='src'
python scripts\run_desktop_validation_summary.py
```

## Run Signal Snapshot

This generates the latest research signal targets and a research-only advisory rebalance plan. It does not connect to a broker, read a real account, or place orders. If no positions CSV is supplied, the run assumes an empty local paper portfolio.

```powershell
$env:PYTHONPATH='src'
python scripts\run_signal_snapshot.py --source fixture --market ALL --factor momentum_2 --top-n 2 --max-asset-weight 0.4 --min-cash-weight 0.1
```

Outputs are written to `data/reports/signal_snapshot/` by default:

- `targets.csv`
- `rebalance_plan.csv`
- `manifest.json`

`targets.csv` is the strategy target state. `rebalance_plan.csv` is explicitly marked `executable=false` and is only an advisory bridge toward later simulated trading.

## Run Paper Simulation

This runs a local simulated trading loop from factor signals. It creates research-only intents, simulated fills, positions, and an equity curve. It does not connect to a broker, does not read a real account, and does not place orders.

```powershell
$env:PYTHONPATH='src'
python scripts\run_paper_simulation.py --source fixture --market ALL --factor momentum_2 --top-n 2 --start-date 2024-01-04 --end-date 2024-01-12 --initial-cash 100000 --max-asset-weight 0.4 --min-cash-weight 0.1
```

Outputs are written to `data/reports/paper_simulation/` by default:

- `intents.csv`
- `fills.csv`
- `positions.csv`
- `equity_curve.csv`
- `snapshots.csv`
- `manifest.json`

Use `--max-drawdown-guard` and `--guard-cooldown-periods` when you want the local simulator to block new buy intents after a drawdown breach.

## Phase 2.6 Decision Risk Layer

Phase 2.6 adds benchmark/cash comparison, optional regime filtering, decision summaries, walk-forward relative-return and drawdown gates, and paper-simulation drawdown guards.

```powershell
$env:PYTHONPATH='src'
python scripts\run_research_pipeline.py --source fixture --market CN_ETF --factor momentum_2 --top-n 1 --benchmark-asset-id CN_ETF_XSHG_510300 --cash-annual-return 0.015 --regime-filter --regime-lookback 3 --min-relative-return 0 --max-drawdown-limit 0.25
```

See `docs/phase_2_6_decision_risk.md` for output fields and interpretation rules.

## Phase 2.7 Pre-API Promotion Gate

Before connecting APIs or brokers, run the local promotion gate to classify candidates as `blocked`, `research_only`, `paper_ready`, or `manual_live_review`.

```powershell
$env:PYTHONPATH='src'
python scripts\run_paper_batch.py --config configs\paper_batch_cn_etf.json
python scripts\run_promotion_report.py --config configs\promotion_gate_cn_etf.json
```

The report is written to `data/reports/promotion_gate_cn_etf/`. It blocks candidates with weak walk-forward evidence, insufficient rolling folds, weak IC significance, fixture-only data, severe data-quality failures, stale or unready provider evidence when configured, excessive drawdown, or unsafe paper-simulation metrics. It can consume one paper manifest or a directory of per-candidate paper manifests. See `docs/phase_2_7_promotion_gate.md`.

## Phase 2.8 Promotion Operations

Phase 2.8 turns promotion output into a local operations entry point and prepares the next pre-API foundations.

```powershell
$env:PYTHONPATH='src'
python scripts\run_gui.py
```

Then open:

```text
http://127.0.0.1:8765/api/promotion/ops
```

The payload summarizes promotion status, top candidate evidence, live-review blockers, duplicate signal clusters, provider/data-quality evidence, and next local actions. It remains research-only and never connects to a broker.

You can also write the same operations artifact from the CLI:

```powershell
$env:PYTHONPATH='src'
python scripts\run_promotion_ops.py --output-dir data\reports\promotion_ops
```

Outputs:

- `promotion_ops.json`
- `promotion_ops_candidates.csv`
- `promotion_ops_actions.csv`

## Phase 2.9 Promotion Review Packet

Phase 2.9 turns the operations payload into an auditable candidate review packet.

```powershell
$env:PYTHONPATH='src'
python scripts\run_promotion_ops.py --output-dir data\reports\promotion_ops
python scripts\run_promotion_review.py --output-dir data\reports\promotion_review
```

Outputs:

- `promotion_review_packet.json`
- `promotion_review_packet.md`
- `promotion_review_checklist.csv`

The local GUI also exposes the packet at `/api/promotion/review` and renders review status, checklist rows, and Markdown on the Promotion Ops page. See `docs/phase_2_9_promotion_review_packet.md`.

## Phase 3.0 Evidence Refresh

Phase 3.0 turns blocked review evidence into ordered local refresh tracks.

```powershell
$env:PYTHONPATH='src'
python scripts\run_evidence_refresh.py --output-dir data\reports\evidence_refresh
```

Outputs:

- `evidence_refresh_plan.json`
- `evidence_refresh_plan.md`
- `evidence_refresh_actions.csv`

The local GUI exposes the same plan at `/api/promotion/evidence-refresh` and renders refresh tracks plus ordered actions on the Promotion Ops page. See `docs/phase_3_0_evidence_refresh.md`.

## Phase 3.1 Data Quality Gap Audit

Phase 3.1 turns the CN ETF `missing_date_rows` blocker into exact local asset/date rows.

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_quality_audit.py --data-root data\processed\etf_csv --market CN_ETF --output-dir data\reports\data_quality_gap_audit
```

Outputs:

- `data_quality_gap_audit.json`
- `data_quality_gap_audit.md`
- `missing_dates.csv`
- `coverage_by_asset.csv`

See `docs/phase_3_1_data_quality_gap_audit.md` and `docs/roadmap_after_phase_3_0.md`.

## Phase 3.2 Provider Readiness Evidence

Phase 3.2 turns provider readiness into a review-ready evidence pack.

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_evidence.py --output-dir data\reports\provider_evidence
```

Outputs:

- `provider_evidence_pack.json`
- `provider_evidence_pack.md`
- `provider_market_matrix.csv`
- `provider_readiness.csv`

See `docs/phase_3_2_provider_readiness_evidence.md` and `docs/roadmap_after_phase_3_0.md`.

## Phase 3.3 Paper Observation Extension

Phase 3.3 turns paper-batch output into a review-ready observation pack.

```powershell
$env:PYTHONPATH='src'
python scripts\run_paper_observation.py --paper-batch-summary data\reports\paper_batch_cn_etf_candidate_search\paper_batch_summary.json --output-dir data\reports\paper_observation
```

Outputs:

- `paper_observation_pack.json`
- `paper_observation_pack.md`
- `paper_observation_candidates.csv`
- `paper_observation_risk_profiles.csv`
- `paper_observation_trend.csv`

See `docs/phase_3_3_paper_observation_extension.md` and `docs/roadmap_after_phase_3_0.md`.

## Phase 3.4 Duplicate Canonical Registry

Phase 3.4 turns duplicate candidate suppression into a stable registry.

```powershell
$env:PYTHONPATH='src'
python scripts\run_duplicate_registry.py --promotion-report data\reports\promotion_gate_cn_etf_candidate_search\promotion_report.json --output-dir data\reports\duplicate_registry
```

Outputs:

- `duplicate_canonical_registry.json`
- `duplicate_canonical_registry.md`
- `canonical_candidates.csv`
- `duplicate_members.csv`

Promotion Ops and Promotion Review Packet also include duplicate registry summary fields. See `docs/phase_3_4_duplicate_canonical_registry.md` and `docs/roadmap_after_phase_3_0.md`.

## Phase 3.5 Manual Review Gate Rehearsal

Phase 3.5 rehearses the manual review gate as a local dry run.

```powershell
$env:PYTHONPATH='src'
python scripts\run_manual_review_rehearsal.py --output-dir data\reports\manual_review_rehearsal
```

Outputs:

- `manual_review_rehearsal.json`
- `manual_review_rehearsal.md`
- `manual_review_requirements.csv`

The rehearsal records broker connection, account reads, order placement, and live trading as disabled. See `docs/phase_3_5_manual_review_gate_rehearsal.md` and `docs/roadmap_after_phase_3_0.md`.

## Phase 4.0 Pre-API Readiness Board

Phase 4.0 consolidates local evidence into one operational readiness board.

```powershell
$env:PYTHONPATH='src'
python scripts\run_pre_api_readiness_board.py --output-dir data\reports\pre_api_readiness_board
```

Outputs:

- `pre_api_readiness_board.json`
- `pre_api_readiness_board.md`
- `pre_api_readiness_items.csv`
- `pre_api_blockers.csv`
- `pre_api_next_actions.csv`

See `docs/phase_4_0_pre_api_readiness_board.md` and `docs/roadmap_after_phase_3_0.md`.

## Phase 4.1 Blocker Resolution Worklist

Phase 4.1 turns readiness-board blockers into open local work items.

```powershell
$env:PYTHONPATH='src'
python scripts\run_blocker_worklist.py --output-dir data\reports\blocker_worklist
```

Outputs:

- `blocker_resolution_worklist.json`
- `blocker_resolution_worklist.md`
- `blocker_work_items.csv`
- `blocker_action_queue.csv`

See `docs/phase_4_1_blocker_resolution_worklist.md` and `docs/roadmap_after_phase_3_0.md`.

## Phase 4.2 Data Gap Resolution Ledger

Phase 4.2 turns exact missing ETF dates into stable local resolution rows.

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_resolution.py --output-dir data\reports\data_gap_resolution
```

Outputs:

- `data_gap_resolution_ledger.json`
- `data_gap_resolution_ledger.md`
- `data_gap_resolution_rows.csv`
- `data_gap_resolution_action_queue.csv`
- `gap_resolutions_template.csv`
- `data_gap_resolution_status_options.csv`
- `data_gap_resolution_validation.csv`

Each row receives a stable `gap_id`, `resolution_status`, evidence note, recommended local command, and API-boundary blocking flag. See `docs/phase_4_2_data_gap_resolution_ledger.md` and `docs/roadmap_after_phase_3_0.md`.

## Phase 4.4 Data Gap Resolution Template

Phase 4.4 writes a fillable local CSV template from the current data-gap ledger.

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_resolution.py --output-dir data\reports\data_gap_resolution
```

Use `data\reports\data_gap_resolution\gap_resolutions_template.csv` to record local evidence per `gap_id`, then feed it back through `--resolution-file`. See `docs/phase_4_4_data_gap_resolution_template.md`.

## Phase 4.5 Data Gap Resolution Validation

Phase 4.5 validates local resolution CSV input and reports unknown gaps, unsupported statuses, and duplicate rows.

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_resolution.py --resolution-file data\reports\data_gap_resolution\gap_resolutions_template.csv --output-dir data\reports\data_gap_resolution
```

Validation output is written to `data\reports\data_gap_resolution\data_gap_resolution_validation.csv`. See `docs/phase_4_5_data_gap_resolution_validation.md`.

## Phase 4.6 Data Gap Resolution Rehearsal

Phase 4.6 generates a local rehearsal pack showing how sample resolution rows change data-gap blocking counts.

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_rehearsal.py --output-dir data\reports\data_gap_rehearsal
```

Outputs:

- `data_gap_rehearsal.json`
- `data_gap_rehearsal.md`
- `sample_gap_resolutions.csv`
- `rehearsed_data_gap_rows.csv`
- `data_gap_rehearsal_summary.csv`

See `docs/phase_4_6_data_gap_resolution_rehearsal.md`.

## Phase 4.7 Provider Remediation Matrix

Phase 4.7 turns provider-readiness blockers into local remediation rows.

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation.py --output-dir data\reports\provider_remediation
```

Outputs:

- `provider_remediation_matrix.json`
- `provider_remediation_matrix.md`
- `provider_remediation_items.csv`
- `provider_remediation_summary.csv`
- `provider_remediation_review_template.csv`
- `provider_remediation_status_options.csv`

See `docs/phase_4_7_provider_remediation_matrix.md`.

## Phase 4.8 Provider Remediation Board Integration

Phase 4.8 connects provider-remediation evidence to the pre-API readiness board.

```powershell
$env:PYTHONPATH='src'
python scripts\run_pre_api_readiness_board.py --provider-remediation data\reports\provider_remediation\provider_remediation_matrix.json --output-dir data\reports\pre_api_readiness_board
```

The board now includes a `provider_remediation` track and a `provider_remediation_items_open` blocker when remediation rows remain. See `docs/phase_4_8_provider_remediation_board_integration.md`.

## Phase 4.9 Provider Remediation Review Template

Phase 4.9 writes a fillable local review template for provider-remediation rows.

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation.py --output-dir data\reports\provider_remediation
```

Use `data\reports\provider_remediation\provider_remediation_review_template.csv` to record controlled local evidence per `remediation_id`. See `docs/phase_4_9_provider_remediation_review_template.md`.

## Phase 4.10 Provider Remediation Review Validation

Phase 4.10 validates filled provider-remediation review rows and applies valid local statuses back into provider-remediation evidence.

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation.py --review-file data\reports\provider_remediation\provider_remediation_review_template.csv --output-dir data\reports\provider_remediation
```

Validation output is written to `data\reports\provider_remediation\provider_remediation_validation.csv`. The pre-API readiness board uses `blocking_remediation_items` so non-blocking review statuses can clear the provider-remediation track while preserving the remediation history. See `docs/phase_4_10_provider_remediation_review_validation.md`.

## Phase 4.11 Provider Remediation Review Rehearsal

Phase 4.11 generates a local rehearsal pack showing how sample provider-review rows change provider-remediation blocking counts.

```powershell
$env:PYTHONPATH='src'
python scripts\run_provider_remediation_rehearsal.py --output-dir data\reports\provider_remediation_rehearsal
```

Outputs:

- `provider_remediation_rehearsal.json`
- `provider_remediation_rehearsal.md`
- `sample_provider_remediation_reviews.csv`
- `rehearsed_provider_remediation_items.csv`
- `provider_remediation_rehearsal_summary.csv`

See `docs/phase_4_11_provider_remediation_review_rehearsal.md`.

## Phase 4.16 Data Gap Evidence Pack

Phase 4.16 adds local raw-CSV context before a reviewer changes data-gap statuses. It does not resolve gaps automatically; it records whether the target raw CSV contains the missing row, how many peer ETFs traded on that date, and the target asset's previous/next local raw dates.

```powershell
$env:PYTHONPATH='src'
python scripts\run_data_gap_evidence.py --output-dir data\reports\data_gap_evidence
```

Outputs:

- `data_gap_evidence_pack.json`
- `data_gap_evidence_pack.md`
- `data_gap_evidence_rows.csv`
- `data_gap_evidence_action_queue.csv`

See `docs/phase_4_16_data_gap_evidence_pack.md`.

## Phase 4.12 Pre-API Readiness Projection Pack

Phase 4.12 combines current readiness-board evidence with rehearsal projections.

```powershell
$env:PYTHONPATH='src'
python scripts\run_readiness_projection.py --output-dir data\reports\readiness_projection
```

Outputs:

- `readiness_projection_pack.json`
- `readiness_projection_pack.md`
- `readiness_projection_items.csv`
- `readiness_projection_deltas.csv`
- `readiness_projection_residuals.csv`

See `docs/phase_4_12_pre_api_readiness_projection_pack.md`.

## Phase 4.13 Residual Blocker Focus Pack

Phase 4.13 turns projected residual blockers into a prioritized local focus pack.

```powershell
$env:PYTHONPATH='src'
python scripts\run_residual_blocker_focus.py --output-dir data\reports\residual_blocker_focus
```

Outputs:

- `residual_blocker_focus_pack.json`
- `residual_blocker_focus_pack.md`
- `residual_focus_items.csv`
- `residual_downstream_waits.csv`
- `residual_focus_actions.csv`

See `docs/phase_4_13_residual_blocker_focus_pack.md`.

## Phase 4.14 Residual Data Gap Review Pack

Phase 4.14 isolates data-gap rows that remain blocking after rehearsal and points reviewers to the data-gap evidence pack before applying local resolution statuses.

```powershell
$env:PYTHONPATH='src'
python scripts\run_residual_data_gap_review.py --output-dir data\reports\residual_data_gap_review
```

Outputs:

- `residual_data_gap_review_pack.json`
- `residual_data_gap_review_pack.md`
- `residual_data_gap_rows.csv`
- `residual_gap_review_template.csv`
- `residual_gap_action_queue.csv`
- `residual_gap_status_options.csv`

See `docs/phase_4_14_residual_data_gap_review_pack.md`.

## Phase 4.15 Residual Provider Review Pack

Phase 4.15 isolates provider-remediation rows that remain blocking after rehearsal.

```powershell
$env:PYTHONPATH='src'
python scripts\run_residual_provider_review.py --output-dir data\reports\residual_provider_review
```

Outputs:

- `residual_provider_review_pack.json`
- `residual_provider_review_pack.md`
- `residual_provider_remediation_items.csv`
- `residual_provider_review_template.csv`
- `residual_provider_action_queue.csv`
- `residual_provider_status_options.csv`

See `docs/phase_4_15_residual_provider_review_pack.md`.

## Phase 4.3 Data Gap Ledger Board Integration

Phase 4.3 connects the data-gap resolution ledger to the pre-API readiness board.

```powershell
$env:PYTHONPATH='src'
python scripts\run_pre_api_readiness_board.py --data-gap-resolution data\reports\data_gap_resolution\data_gap_resolution_ledger.json --output-dir data\reports\pre_api_readiness_board
```

The board now includes a `data_gap_resolution` track and a `data_gap_resolution_blocking_gaps` blocker when unresolved ledger rows remain. See `docs/phase_4_3_data_gap_ledger_board_integration.md`.

Tushare CN ETF ingest is now available through the same ingest CLI:

```powershell
$env:PYTHONPATH='src'
python scripts\ingest_data.py --source tushare-fixture --market CN_ETF --output-dir data\processed\tushare_etf_fixture
```

Paper simulation also records local execution-block events when bars include `suspended`, `limit_up`, or `limit_down` fields, or when an execution bar has zero volume. See `docs/phase_2_8_promotion_operations.md`.

## A-Share ETF Research

The framework includes a dedicated `CN_ETF` market and a Tushare-first ETF universe policy in `configs/universe_cn_etf.yaml`. The primary trading pool is built from Tushare `fund_basic(market='E')`, filtered to exchange-traded active ETFs as of the research date, and daily bars come from `fund_daily`. The sync also writes a point-in-time `metadata/cn_etf_rotation_membership/market=CN_ETF` surface, preserving delisted or formerly listed ETFs on dates when they were listed and excluding them after `delist_date`. Research, experiment-grid, walk-forward, signal-snapshot, and paper-simulation entrypoints keep full bars for factor warmup, then require and apply this membership surface for `processed-bars + market=CN_ETF` signals. ETF share, scale, NAV, and premium/discount auxiliary inputs come from `etf_share_size`. Static symbols, TradingView CSV, AKShare, and fixtures are fallback/smoke paths only.

For a full-history or incremental Tushare CN_ETF refresh, run the startup gate first, then use the ingest CLI:

```powershell
$env:PYTHONPATH='src'
python scripts\run_quant_pm_startup_gate.py --machine highspec_desktop --task data_pipeline --branch <current-branch>
python scripts\run_research_family_scheduler.py --config configs\research_family_scheduler_cn_etf.json
python scripts\run_tushare_cn_etf_sync.py --source tushare --start-date auto --end-date latest --output-dir data\processed\tushare_etf_full --report-dir data\reports\tushare_cn_etf_sync --min-rotation-history-rows 60 --min-rotation-median-amount 10000000 --execute
python scripts\run_data_quality_audit.py --data-root data\processed\tushare_etf_full --market CN_ETF --output-dir data\reports\data_quality_gap_audit_cn_etf_full
```

`--start-date auto` resolves to the configured full-history anchor, currently `2005-01-01` unless `--full-history-start-date` is supplied. `--end-date latest` resolves through Tushare `trade_cal` to the most recent completed open trading day and records the result under `date_resolution`; if provider readiness is missing, the run writes a blocked pack instead of guessing a trading-calendar date.

For daily refreshes after the full-history root exists, switch the start token to incremental:

```powershell
$env:PYTHONPATH='src'
python scripts\run_tushare_cn_etf_sync.py --source tushare --start-date incremental --end-date latest --output-dir data\processed\tushare_etf_full --report-dir data\reports\tushare_cn_etf_sync_incremental --min-rotation-history-rows 60 --min-rotation-median-amount 10000000 --execute
```

`--start-date incremental` reads the latest local `CN_ETF` processed bar date and starts from the next day. If the local root is current through the resolved latest completed trading day, the sync writes an `up_to_date` pack and skips downloads.

The CN_ETF sync writes `fund_daily` bars, point-in-time rotation membership, `etf_share_size` inputs, and `fund_portfolio`-derived `metadata/etf_moneyflow_baskets/market=CN_ETF`. Basket mappings use Tushare `ann_date` as `known_date`; a holding set is active only until the day before the next announcement for the same ETF.

When provider credentials are unavailable, you can still import TradingView ETF CSV exports into processed bars for smoke checks:

```powershell
$env:PYTHONPATH='src'
python scripts\import_etf_csv.py path\to\510300.csv --symbol 510300.SH --output-dir data\processed\etf_csv
```

The importer checks that a six-digit code in the CSV filename matches `--symbol`, uses an import lock to avoid concurrent year-partition rewrites, and does not count weekends as missing dates unless a real exchange calendar is provided later.
Its quality report checks missing rows across observed business days, so weekday gaps in CSV exports are flagged while weekend gaps are ignored.

Then run ETF-only research, factor mining, and paper simulation against the Tushare processed root when available:

```powershell
$env:PYTHONPATH='src'
python scripts\run_quant_pm_startup_gate.py --machine highspec_desktop --task factor_batch --branch <current-branch>
python scripts\run_research_family_scheduler.py --config configs\research_family_scheduler_cn_etf.json
python scripts\run_walk_forward.py --config configs\walk_forward_tushare_cn_etf_rotation.json --source processed-bars --data-root data\processed\tushare_etf_full
python scripts\run_walk_forward.py --config configs\walk_forward_tushare_cn_etf_share_size.json --source processed-bars --data-root data\processed\tushare_etf_full
python scripts\run_walk_forward.py --config configs\walk_forward_tushare_cn_etf_moneyflow_basket.json --source processed-bars --data-root data\processed\tushare_etf_full
python scripts\run_research_pipeline.py --source processed-bars --data-root data\processed\tushare_etf_full --market CN_ETF --factor momentum_20 --top-n 2
python scripts\run_research_pipeline.py --source processed-bars --data-root data\processed\tushare_etf_full --market CN_ETF --factor-source etf_share_size --factor-input-root data\processed\tushare_etf_full --factor share_change_1d --top-n 2
python scripts\run_research_pipeline.py --source processed-bars --data-root data\processed\tushare_etf_full --market CN_ETF --factor-source etf_moneyflow_basket --factor-input-root data\processed\tushare_etf_full --moneyflow-input-root data\processed\tushare_moneyflow_inputs --factor etf_net_mf_amount_ratio --top-n 2
python scripts\run_paper_simulation.py --source processed-bars --data-root data\processed\tushare_etf_full --market CN_ETF --factor momentum_20 --top-n 2
```

Run the research-family scheduler before material factor-mining batches. It enforces a diversified `CN_ETF` hypothesis portfolio and keeps the direct `CN` stock moneyflow selection family in `auxiliary_only` mode after repeated capacity, cost, out-of-sample, and tail-IC failures. The ETF share/scale/NAV structure family uses `factor_source=etf_share_size` against the same Tushare sync root. CN stock moneyflow can enter only through ETF-level basket aggregation with point-in-time `known_date` mappings via `factor_source=etf_moneyflow_basket`; final factors and signals remain `CN_ETF`. The default Tushare basket source is `fund_portfolio`, not a current holdings snapshot. See `docs/research/research_family_scheduler_2026-06-17.md`.

## Run Local GUI

The local GUI is research-only. It defaults to local `processed-bars` CN ETF CSV research when `data\processed\etf_csv` exists, and still includes a clearly labeled `demo_fixture` mode for smoke checks.

```powershell
$env:PYTHONPATH='src'
python scripts\run_gui.py
```

Open `http://127.0.0.1:8765` in your browser.

The GUI includes dashboard, data center, factor research, backtest report, signal snapshot, paper simulation, risk monitor, and logs/report views. Signal snapshots expose target weights and an advisory rebalance plan marked `executable=false`; paper simulation uses local bars only and produces simulated fills only.

## Phase 1.5 Real Data Foundation

Phase 1.5 adds safe real-data foundations for Tushare A-share data and TradingView CSV verification. The first implementation is offline-testable and keeps all live data dependencies optional.

```powershell
$env:PYTHONPATH='src'
python scripts\ingest_data.py --source fixture --market CN --output-dir data\processed\ingest_fixture
```

Real Tushare A-share and A-share ETF access uses `TUSHARE_TOKEN` from the environment. Never commit a real token. CN ETF fetching remains pre-broker and research-only: use local CSV or fixture workflows only for smoke checks when provider credentials are unavailable.

Tushare adjustment factors are stored as range-stable adjusted closes using `close * adj_factor` when adjustment factors are available. The pipeline avoids normalizing by the latest factor inside the requested date range because that would make the same historical date change when you request a longer range.

Before switching to real Tushare data, check optional dependencies and credentials:

```powershell
$env:PYTHONPATH='src'
python scripts\check_readiness.py
```

To test the Tushare-shaped pipeline without credentials:

```powershell
$env:PYTHONPATH='src'
python scripts\ingest_data.py --source tushare-fixture --market CN --output-dir data\processed\tushare_fixture
```

## No-Live-Trading Boundary

This repository intentionally has no real broker adapter, no order placement, no account login, and no automatic live execution. Later phases should extend from research signals to portfolio targets, then to simulated order intents, and only then to a carefully gated broker adapter.
