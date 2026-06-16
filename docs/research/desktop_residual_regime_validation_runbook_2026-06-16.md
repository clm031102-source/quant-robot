# Desktop Residual-Regime Validation Runbook - 2026-06-16

## Scope

- Target machines: `highspec_desktop` or `office_desktop`.
- Task type: `factor_validation`.
- Research boundary: research-to-paper only. No broker connection, no live account reads, no order placement, and no automatic live trading.
- Goal: validate the pre-registered residualized moneyflow factor family, not search for a new best-looking parameter set.

## Branch Flow

If the optimization branch has not been merged into `main`, start from it:

```powershell
git fetch origin --prune
git switch codex/factor-method-optimization-20260616
git pull --ff-only
git switch -c codex/factor-validation-residual-regime-20260616
```

If the optimization branch is already merged into `main`, start from `main` instead:

```powershell
git fetch origin --prune
git switch main
git pull --ff-only
git switch -c codex/factor-validation-residual-regime-20260616
```

## Required Data

The run expects local processed data that is not committed to Git:

- CN processed bars under `data/processed`.
- Tushare moneyflow inputs under `data/processed/tushare_moneyflow_inputs`.

The validation entrypoint fails fast with a clear message when these local inputs are missing. Missing local data is a desktop data-preparation issue, not a Git sync issue.

Run a sync audit before starting heavy validation:

```powershell
python scripts\sync_project.py --machine highspec_desktop --task factor_validation
```

Use `office_desktop` instead of `highspec_desktop` when running from the office machine.

## Validation Command

Run the strict desktop profile:

```powershell
python scripts\run_desktop_factor_validation.py
```

This wraps:

- `configs/walk_forward_tushare_moneyflow_residual_regime.json`
- processed-bars source from `data/processed`
- rolling walk-forward validation
- explicit regime lookbacks: 120, 150, 180, 252
- top-N values: 5, 10, 20
- cost assumptions: 20 and 30 bps
- capacity controls and max participation checks

The script intentionally allows zero accepted candidates. A complete rejection set is useful evidence when the underlying train/test grids did not fail.

To run the full desktop validation check chain, use:

```powershell
python scripts\run_checks.py --profile desktop-validation --execute
```

This runs unit/integration tests, Python compile, project audit, readiness checks, provider status, data catalog, data-quality audit, the residual-regime validation command, a strict market-regime coverage check from walk-forward test-fold `regime_curve.csv` files, the research-only promotion gate report, and a lightweight Markdown summary at `docs/research/desktop_residual_regime_validation_latest.md`.

For this profile, the data-quality audit is intentionally pinned to the CN Tushare residual-regime data surface instead of the default CN ETF surface:

```powershell
python scripts\run_data_quality_audit.py --data-root data\processed --market CN --output-dir data\reports\data_quality_gap_audit_tushare_moneyflow_residual_regime
```

To rebuild only the market-regime coverage pack after a completed walk-forward run:

```powershell
python scripts\run_market_regime_coverage.py --regime-curve-glob "data/reports/walk_forward_tushare_moneyflow_residual_regime/fold_*/test/*/regime_curve.csv" --output-dir data/reports/market_regime_coverage_tushare_moneyflow_residual_regime --min-regimes 2 --min-rows-per-regime 5 --require-sufficient
```

To build only the promotion gate report after a validation run, use:

```powershell
python scripts\run_promotion_report.py --config configs\promotion_gate_tushare_moneyflow_residual_regime.json
```

This does not approve live trading. It summarizes which candidates are blocked, research-only, or still missing evidence.
For this residual-regime profile, the promotion gate also requires the market-regime coverage pack. Missing or insufficient regime coverage blocks promotion even when a walk-forward row is otherwise accepted.

To rebuild only the syncable Markdown summary:

```powershell
python scripts\run_desktop_validation_summary.py
```

The summary command validates the walk-forward leaderboard against the sibling `manifest.json` and records the residual-regime data-quality audit, promotion gate, and market-regime coverage status. If cases, accepted count, or rejected count disagree, treat it as stale or mixed validation output and rerun the full desktop profile before syncing.

## Review Rules

Treat a candidate as useful only if it survives all of these checks:

- No failed train/test grid cases.
- Positive out-of-sample relative return after costs.
- Out-of-sample Sharpe must not exceed the configured overfit ceiling of `3.0`.
- Drawdown inside the configured limit.
- No capacity-limited trades or participation-rate breaches.
- IC evidence survives multiple-testing correction.
- Results are not driven by a single regime lookback.
- 2024 weakness is explained or avoided by a pre-registered regime rule.

Reject or keep as observation-only when:

- only `regime_lookback=150` works;
- RankIC or quantile spread contradicts Pearson IC;
- top5 works but top10/top20 collapse without an economic reason;
- returns vanish under 30 bps costs;
- any pass depends on excluding failed exploratory trials from the hypothesis count.

## Sync After Run

Do not commit generated reports or data. Commit only code, configs, tests, and lightweight summaries.

Audit first:

```powershell
python scripts\sync_project.py --machine highspec_desktop --task factor_validation
```

Execute only after the audit is clean:

```powershell
python scripts\sync_project.py --machine highspec_desktop --task factor_validation --execute --push
```
