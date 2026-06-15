# Tushare 2000 Real Data Alpha Factory Design

Status: pending user approval before implementation
Date: 2026-06-15
Worktree: `C:\Users\11042\.config\superpowers\worktrees\lhjqr\audit-remediation-suite`

## Goal

Turn the current research framework from a mostly price-only technical-factor system into a real Tushare-backed daily alpha factory. The system should ingest Tushare 2000-point daily research data, generate pre-registered factor candidates, validate them with no-lookahead walk-forward tests, and only promote candidates that survive costs, capacity, data quality, and statistical significance gates.

This phase improves the probability of finding a tradable edge. It does not claim that Tushare data or any single factor guarantees profitability.

## Current Evidence

The audit-remediation worktree already contains stricter walk-forward validation, IC statistics, cost and capacity modeling, provider status timestamps, quality report extensions, and a live-execution boundary. Those changes are still uncommitted in this worktree.

The current Tushare adapter supports `daily`, `fund_daily`, `adj_factor`, `trade_cal`, and `stock_basic`. It does not yet expose `daily_basic`, `moneyflow`, `stk_limit`, `index_daily`, or other 2000-point research endpoints.

The current ingest pipeline writes `raw/tushare/daily`, `raw/tushare/fund_daily`, and `processed/bars`. It does not write a normalized `processed/factor_inputs` dataset.

The current factor engine computes technical factors from bars only. It cannot mine valuation, turnover, market-cap, liquidity, money-flow, or limit-up/limit-down factors from Tushare research tables.

Fresh readiness checks in this worktree show `TUSHARE_TOKEN` is not set, `tushare` is not installed, and no parquet engine is installed. There is no `.env` file in the worktree, and `.env` files are ignored by git.

## Tushare Data Scope

The first implementation wave uses daily data that is useful for alpha research and fits the 2000-point service tier shown in the official Tushare permission and frequency pages:

- `daily_basic`: valuation, turnover, volume ratio, market cap, and other daily indicators.
- `daily`: A-share OHLCV bars, already partly supported.
- `fund_daily`: exchange-traded fund OHLCV bars, already partly supported.
- `trade_cal`: open trading dates, already supported.
- `stock_basic`: A-share instrument metadata, already supported.
- `moneyflow`: second-wave candidate for flow factors after the daily-basic path is stable.
- `stk_limit`: second-wave candidate for limit-price and limit-event filters.
- `index_daily`: second-wave candidate for benchmark and regime features.

The design intentionally excludes minute data, intraday execution simulation, and independently licensed real-time feeds from this phase. Official Tushare documentation lists minute and several real-time datasets as separate permissions, so the 2000-point path should not silently depend on them.

References:

- Tushare permission table: https://tushare.pro/document/1?doc_id=108
- Tushare frequency and independent-permission table: https://tushare.pro/document/1?doc_id=290
- Tushare minute-data permission note: https://tushare.pro/document/1?doc_id=234

## Architecture

### Adapter Layer

Extend `src/quant_robot/data/adapters/tushare_adapter.py` with explicit fetch methods for the selected research endpoints:

- `fetch_daily_basic_by_trade_date(trade_date: str) -> pd.DataFrame`
- `fetch_moneyflow_by_trade_date(trade_date: str) -> pd.DataFrame`
- `fetch_stk_limit_by_trade_date(trade_date: str) -> pd.DataFrame`
- `fetch_index_daily(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame`

The first implementation task should add only `daily_basic`. Other methods should be planned but added only when their tests and downstream usage are ready.

### Mapping Layer

Extend `src/quant_robot/data/sources/tushare_mapping.py` with normalized mappers. The `daily_basic` mapper should output stable local columns:

- `symbol`
- `date`
- `turnover_rate`
- `turnover_rate_f`
- `volume_ratio`
- `pe`
- `pe_ttm`
- `pb`
- `ps`
- `ps_ttm`
- `dv_ratio`
- `dv_ttm`
- `total_share`
- `float_share`
- `free_share`
- `total_mv`
- `circ_mv`

Numeric fields should be coerced with `pd.to_numeric(..., errors="coerce")`. Dates should be parsed from Tushare `trade_date` into local date values. Missing optional columns should be created as null columns when Tushare returns a reduced field set.

### Ingest Layer

Create a focused ingest module for Tushare research inputs:

`src/quant_robot/data/ingest/tushare_factor_inputs.py`

Responsibilities:

- Use `trade_cal` to iterate open dates.
- Fetch `daily_basic` by trade date.
- Write raw data to `raw/tushare/daily_basic/trade_date=YYYYMMDD`.
- Normalize to `processed/factor_inputs/frequency=1d/market=CN/year=YYYY`.
- Resume completed trade dates through `IngestManifest`.
- Produce `factor_input_quality_report.json`.
- Fail the manifest entry if raw download succeeds but normalized processing fails.

The normalized factor-input rows should use `asset_id` values consistent with existing CN stock bars, for example `CN_XSHE_000001`.

### Factor Layer

Add a separate factor builder for Tushare daily-basic inputs:

`src/quant_robot/factors/tushare_inputs.py`

Initial pre-registered factor names:

- `turnover_rate`
- `turnover_rate_f`
- `volume_ratio`
- `pe_ttm_inverse`
- `pb_inverse`
- `ps_ttm_inverse`
- `dv_ttm`
- `total_mv_log`
- `circ_mv_log`

The inverse valuation factors should handle zero and negative denominators as missing values, not as huge values. Market-cap factors should use natural log after validating positive input. Factor outputs should conform to existing `FACTOR_COLUMNS`.

### Research Pipeline Layer

Extend `ResearchPipelineConfig` with:

- `factor_source`: `technical`, `tushare_daily_basic`, or `combined`.
- `factor_input_root`: optional path to a dataset store containing `processed/factor_inputs`.
- `factor_input_required`: boolean gate for production-grade runs.

When `factor_source` uses Tushare daily-basic inputs, the pipeline should load factor inputs, compute factor rows, and merge them with labels by `asset_id` and `date`.

No-lookahead rule: `daily_basic` values are end-of-day research inputs. Signals stamped on date D may only be traded with at least one-bar execution lag. The research pipeline should reject Tushare daily-basic runs with `execution_lag < 1`.

### Candidate Search Layer

Add a small runner that searches only the pre-registered factor family rather than arbitrary ad hoc combinations:

`scripts/run_tushare_alpha_factory.py`

The runner should:

- Accept bars root, factor-input root, date range, market, costs, capacity, and output directory.
- Run each factor through the existing research pipeline.
- Run walk-forward validation for candidates that pass minimum IC observations.
- Track the number of tested hypotheses.
- Export `candidate_leaderboard.csv`, `candidate_leaderboard.json`, and per-factor artifacts.

The leaderboard should include:

- factor name
- mean IC
- IC t-stat
- IC p-value
- multiple-test adjusted p-value
- positive IC rate
- out-of-sample walk-forward return
- accepted fold count
- max drawdown
- turnover
- total cost bps
- max participation rate
- decision status
- rejection reason

### Promotion Gate Integration

Promotion should require stronger evidence for Tushare factor candidates than fixture or exploratory runs:

- provider status must show Tushare ready when the run claims Tushare provenance.
- run artifacts must include factor-input provenance.
- `data_mode` must be research, not fixture.
- IC observations must meet the configured minimum.
- p-value must pass the configured multiple-test adjustment rule.
- positive IC rate must meet the configured minimum.
- rolling walk-forward must meet minimum fold and accepted-fold thresholds.
- cost and capacity metrics must be present.
- quality report severe fields must be zero or below configured thresholds.

### Secrets and Environment

Do not commit tokens. Do not print tokens. Do not write tokens into reports, manifests, or git-tracked docs.

The first implementation should keep `TUSHARE_TOKEN` as an environment secret. A separate explicitly approved enhancement may add a local `.env` loader, but only if tests prove `.env` stays ignored and token values never appear in logs.

Minimum local activation commands for real Tushare runs:

```powershell
python -m pip install ".[data,parquet]"
$env:TUSHARE_TOKEN = "<local token value>"
$env:PYTHONPATH = "src"
python scripts\check_readiness.py
```

## Testing Strategy

Implementation must follow TDD.

Minimum tests before production code:

- adapter calls `daily_basic` with a `trade_date` and maps a fake client response.
- `map_tushare_daily_basic` normalizes dates, symbols, numeric fields, and missing optional fields.
- factor-input ingest writes raw data, processed data, manifest entries, and a quality report.
- ingest resume skips completed trade dates without re-fetching.
- failed normalization marks manifest entries failed.
- daily-basic factor builder emits only `FACTOR_COLUMNS`.
- inverse valuation factors treat invalid denominators as missing values.
- research pipeline rejects Tushare daily-basic factors with `execution_lag < 1`.
- research pipeline can run a fake bars plus fake factor-input dataset end to end.
- alpha factory runner exports a leaderboard with hypothesis counts and adjusted p-values.
- promotion gate rejects Tushare candidates without provider readiness or factor-input provenance.

Fresh verification before claiming completion:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q src scripts tests
python scripts\run_project_audit.py --json
```

Real-data smoke verification is conditional on local dependency and token availability:

```powershell
$env:PYTHONPATH = "src"
python scripts\check_readiness.py
python scripts\run_tushare_smoke.py
```

## Phased Delivery

### Phase A: Real Daily-Basic Dataset

Deliver `daily_basic` adapter, mapper, ingest, manifest, processed factor-input dataset, and tests. Success means local fake-client tests pass and real smoke can run when token and package are present.

### Phase B: Daily-Basic Factor Mining

Deliver factor builders, research pipeline integration, no-lookahead enforcement, and a first candidate leaderboard. Success means each candidate has IC evidence, adjusted p-value evidence, walk-forward evidence, and cost/capacity evidence.

### Phase C: Research Gate Hardening

Deliver promotion-gate checks for factor-input provenance, Tushare provider readiness, adjusted significance, and severe data-quality fields. Success means weak or fake candidates cannot be promoted by configuration accident.

### Phase D: Real Data Observation

Run real Tushare ingest and alpha factory after the token and packages are available. Success means artifacts are produced from actual Tushare rows and candidates either fail with clear reasons or enter paper observation with strict risk limits.

### Phase E: Small-Capital Live Readiness

Only after paper observation is long enough and promotion gates pass, add broker-specific execution adapters behind the existing live-execution boundary. Success means the system can produce non-executable approval packets first, then small-capital live orders only after explicit operator approval and kill-switch validation.

## Non-Goals

This phase will not:

- claim profitability before out-of-sample and paper-observation evidence exists.
- add broker live order submission.
- use minute data or real-time feeds that require separate Tushare permissions.
- optimize arbitrary parameter grids without hypothesis tracking and multiple-test correction.
- silently use same-day close-derived signals for same-day execution.

## Approval Request

Implementation may start after the user approves this design. The first code task after approval should be a TDD implementation plan for Phase A.
