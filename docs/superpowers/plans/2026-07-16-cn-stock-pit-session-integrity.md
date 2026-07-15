# CN Stock PIT Session Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed CN stock asset-session and price-integrity evidence chain, add targeted legacy suspension backfill, and expose a lifecycle-clean authority view for future research.

**Architecture:** Pure pandas audit modules classify gaps and price transitions independently of filesystem and provider code. Thin CLIs load local authority/evidence artifacts and write deterministic packets, while a symbol-scoped Tushare ingestion module supplies only missing legacy suspension intervals. Authority-bar configuration applies lifecycle and adjustment quarantines at read time without rewriting historical parquet files.

**Tech Stack:** Python 3.11, pandas, pathlib, unittest/pytest, existing `DatasetStore`, `TushareAdapter`, authority-bar loader, and atomic storage helpers.

---

## File Map

- Create `src/quant_robot/data/asset_session_integrity.py`: pure lifecycle, daily suspension, legacy interval, and gap classification logic.
- Create `src/quant_robot/ops/cn_stock_asset_session_integrity_audit.py`: packet rendering and artifact writing.
- Create `scripts/run_cn_stock_asset_session_integrity_audit.py`: authority/evidence loading and CLI exit behavior.
- Create `src/quant_robot/data/ingest/tushare_legacy_suspension.py`: targeted normalization, validation, and storage.
- Create `scripts/ingest_tushare_legacy_suspension.py`: unresolved-asset driven provider command.
- Modify `src/quant_robot/data/adapters/tushare_adapter.py`: symbol-scoped legacy `suspend` method.
- Modify `src/quant_robot/storage/authority_bars.py`: optional lifecycle filtering controls.
- Create `configs/cn_stock_authority_bars_2015_2025_lifecycle_clean.json`: future safer authority view.
- Create `src/quant_robot/ops/cn_stock_price_integrity_audit.py`: extreme transition classification and packet writing.
- Create `scripts/run_cn_stock_price_integrity_audit.py`: local price-audit CLI.
- Modify `src/quant_robot/ops/cn_stock_data_manifest.py`: optional integrity packet blockers and provenance.
- Modify `scripts/run_cn_stock_data_manifest.py`: integrity packet arguments.
- Add focused unit and CLI tests under `tests/unit/`.
- Add a lightweight final evidence summary under `docs/research/`.

### Task 1: Pure Asset-Session Classification

**Files:**
- Create: `src/quant_robot/data/asset_session_integrity.py`
- Test: `tests/unit/test_asset_session_integrity.py`

- [ ] **Step 1: Write failing classification tests**

Add fixtures with one listed asset, one XBEI pre-list asset, one missing-metadata asset, a daily suspension, and an open-ended legacy interval. Assert one exclusive classification per gap and assert that observed pre-list rows are reported.

```python
result = classify_asset_sessions(
    bars=bars,
    expected_sessions=pd.DataFrame({"date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])}),
    stock_basic=stock_basic,
    daily_suspension=daily_suspension,
    legacy_suspension=legacy_suspension,
)
assert result.summary["raw_gap_rows"] == 2
assert set(result.gaps["classification"]) == {
    "official_daily_suspension",
    "official_legacy_suspension",
}
```

- [ ] **Step 2: Verify the tests fail**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_asset_session_integrity.py -q`

Expected: collection fails because `quant_robot.data.asset_session_integrity` does not exist.

- [ ] **Step 3: Implement minimal pure classification**

Define immutable result data and the public API:

```python
@dataclass(frozen=True)
class AssetSessionClassification:
    gaps: pd.DataFrame
    coverage_by_asset: pd.DataFrame
    observed_outside_lifecycle: pd.DataFrame
    summary: dict[str, Any]

def classify_asset_sessions(
    *,
    bars: pd.DataFrame,
    expected_sessions: pd.DataFrame,
    stock_basic: pd.DataFrame,
    daily_suspension: pd.DataFrame | None = None,
    legacy_suspension: pd.DataFrame | None = None,
) -> AssetSessionClassification:
    normalized = _normalize_evidence(
        bars=bars,
        expected_sessions=expected_sessions,
        stock_basic=stock_basic,
        daily_suspension=daily_suspension,
        legacy_suspension=legacy_suspension,
    )
    return _classify_normalized_evidence(normalized)
```

Normalize dates once, reject duplicate stock-basic asset IDs and duplicate evidence keys, clip expected sessions to first/last observed dates, and classify in this order: outside lifecycle, daily suspension, legacy interval, missing metadata, unresolved active session. A resume date is excluded from the suspension interval; null/`19000101` is open-ended.

- [ ] **Step 4: Run focused tests**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_asset_session_integrity.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit the pure classifier**

```powershell
git add src/quant_robot/data/asset_session_integrity.py tests/unit/test_asset_session_integrity.py
git commit -m "feat: classify CN stock asset-session gaps"
```

### Task 2: Session Audit Packet and CLI

**Files:**
- Create: `src/quant_robot/ops/cn_stock_asset_session_integrity_audit.py`
- Create: `scripts/run_cn_stock_asset_session_integrity_audit.py`
- Test: `tests/unit/test_cn_stock_asset_session_integrity_audit.py`
- Test: `tests/unit/test_cn_stock_asset_session_integrity_audit_cli.py`
- Modify: `tests/unit/test_script_workspace_imports.py`

- [ ] **Step 1: Write failing packet and CLI tests**

Assert blocked status for unresolved active sessions and observed lifecycle contamination, `review_required` when all gaps are officially explained, deterministic CSV filenames, research-only safety text, and CLI exit code 3 unless `--allow-blocked` is supplied.

```python
packet = build_cn_stock_asset_session_integrity_audit(
    bars=bars,
    expected_sessions=sessions,
    stock_basic=stock_basic,
    daily_suspension=suspension,
)
assert packet["status"] == "blocked"
assert "unresolved_active_sessions" in packet["decision"]["blockers"]
```

- [ ] **Step 2: Verify the tests fail**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_cn_stock_asset_session_integrity_audit.py tests/unit/test_cn_stock_asset_session_integrity_audit_cli.py -q`

Expected: imports fail because packet and CLI modules do not exist.

- [ ] **Step 3: Implement packet rendering and atomic outputs**

Expose these concrete interfaces:

```python
def build_cn_stock_asset_session_integrity_audit(
    *,
    bars: pd.DataFrame,
    expected_sessions: pd.DataFrame,
    stock_basic: pd.DataFrame,
    daily_suspension: pd.DataFrame | None = None,
    legacy_suspension: pd.DataFrame | None = None,
    source_root: str | Path | None = None,
) -> tuple[dict[str, Any], AssetSessionClassification]:
    classification = classify_asset_sessions(
        bars=bars,
        expected_sessions=expected_sessions,
        stock_basic=stock_basic,
        daily_suspension=daily_suspension,
        legacy_suspension=legacy_suspension,
    )
    return _packet_from_classification(classification, source_root), classification

def write_cn_stock_asset_session_integrity_audit(
    output_dir: str | Path,
    packet: dict[str, Any],
    classification: AssetSessionClassification,
) -> None:
    _write_packet_and_frames(output_dir, packet, classification)
```

Write JSON/Markdown plus `asset_session_gap_classifications.csv`, `unresolved_asset_sessions.csv`, `unresolved_assets.csv`, `observed_outside_lifecycle.csv`, and `coverage_by_asset.csv`. Store only samples in JSON so the packet stays lightweight.

- [ ] **Step 4: Implement local artifact loaders and CLI**

The CLI arguments are:

```text
--data-root
--market CN
--calendar-path
--calendar-manifest-path
--evidence-root
--legacy-suspension-root
--output-dir
--allow-blocked
```

Load authority bars through `load_authority_processed_bars_from_config`, validate the calendar artifact, and load all parquet partitions under `metadata/tushare_stock_basic`, `processed/tradeability_suspension`, and optional `processed/legacy_suspension`. Missing mandatory evidence is a blocker, not an empty successful feed.

- [ ] **Step 5: Run focused tests**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_cn_stock_asset_session_integrity_audit.py tests/unit/test_cn_stock_asset_session_integrity_audit_cli.py tests/unit/test_script_workspace_imports.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit the audit surface**

```powershell
git add src/quant_robot/ops/cn_stock_asset_session_integrity_audit.py scripts/run_cn_stock_asset_session_integrity_audit.py tests/unit/test_cn_stock_asset_session_integrity_audit.py tests/unit/test_cn_stock_asset_session_integrity_audit_cli.py tests/unit/test_script_workspace_imports.py
git commit -m "feat: add CN stock session integrity audit"
```

### Task 3: Targeted Legacy Suspension Evidence

**Files:**
- Modify: `src/quant_robot/data/adapters/tushare_adapter.py`
- Create: `src/quant_robot/data/ingest/tushare_legacy_suspension.py`
- Create: `scripts/ingest_tushare_legacy_suspension.py`
- Modify: `tests/unit/test_tushare_adapter.py`
- Create: `tests/unit/test_tushare_legacy_suspension_ingest.py`
- Create: `tests/unit/test_tushare_legacy_suspension_ingest_cli.py`

- [ ] **Step 1: Write failing adapter and ingestion tests**

Use a fake provider returning duplicate intervals and `resume_date="19000101"`. Assert a symbol-scoped call, open-ended normalization, duplicate rejection, asset/symbol mapping validation, data-quality-only scope, and one stored parquet dataset.

```python
frame = adapter.fetch_legacy_suspension("002260.SZ", "2015-01-01", "2025-12-31")
assert client.calls[-1] == (
    "suspend",
    {"ts_code": "002260.SZ", "start_date": "20150101", "end_date": "20251231"},
)
```

- [ ] **Step 2: Verify the tests fail**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_tushare_adapter.py tests/unit/test_tushare_legacy_suspension_ingest.py tests/unit/test_tushare_legacy_suspension_ingest_cli.py -q`

Expected: legacy method/module imports fail.

- [ ] **Step 3: Add the adapter method**

```python
def fetch_legacy_suspension(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    return self._call(
        self.client.suspend,
        ts_code=ts_code,
        start_date=_date_to_tushare(start_date),
        end_date=_date_to_tushare(end_date),
    )
```

- [ ] **Step 4: Implement targeted ingestion**

Expose `run_tushare_legacy_suspension_ingest(adapter, unresolved_assets, start_date, end_date, output_dir)`. Require unique `asset_id`/`symbol` rows, reject more than 100 requested assets unless an explicit code-level override is added later, normalize intervals, and write `processed/legacy_suspension` plus an ingestion report.

- [ ] **Step 5: Implement CLI and run tests**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_tushare_adapter.py tests/unit/test_tushare_legacy_suspension_ingest.py tests/unit/test_tushare_legacy_suspension_ingest_cli.py tests/unit/test_script_workspace_imports.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit provider evidence support**

```powershell
git add src/quant_robot/data/adapters/tushare_adapter.py src/quant_robot/data/ingest/tushare_legacy_suspension.py scripts/ingest_tushare_legacy_suspension.py tests/unit/test_tushare_adapter.py tests/unit/test_tushare_legacy_suspension_ingest.py tests/unit/test_tushare_legacy_suspension_ingest_cli.py tests/unit/test_script_workspace_imports.py
git commit -m "feat: ingest targeted legacy suspension evidence"
```

### Task 4: Lifecycle-Clean Authority View

**Files:**
- Modify: `src/quant_robot/storage/authority_bars.py`
- Modify: `tests/unit/test_authority_bars.py`
- Create: `configs/cn_stock_authority_bars_2015_2025_lifecycle_clean.json`

- [ ] **Step 1: Write failing lifecycle configuration tests**

Assert parsing of `stock_basic_root`, `enforce_official_lifecycle`, and `exclude_assets_without_lifecycle_metadata`. Build bars before/inside/after lifecycle plus an unknown asset and assert only inside-lifecycle known rows survive.

```python
assert set(filtered["date"].astype(str)) == {"2024-01-03"}
assert set(filtered["asset_id"]) == {"CN_XSHE_KNOWN"}
```

- [ ] **Step 2: Verify the tests fail**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_authority_bars.py -q`

Expected: config attributes are absent and rows are not filtered.

- [ ] **Step 3: Implement lifecycle controls**

Extend `AuthorityBarsConfig` with optional fields and add a helper that loads all `metadata/tushare_stock_basic` parquet files, rejects duplicate `asset_id` rows, left-joins list/delist dates, excludes unknown metadata when configured, and clips bars inclusively to official dates. Apply the filter after adjusted-ratio repair/exclusion and before `validate_market_data`.

- [ ] **Step 4: Add the new config**

Copy the existing authority segments and set:

```json
{
  "repair_adjusted_ratio_mass_jumps": true,
  "exclude_adjusted_ratio_jump_assets": true,
  "adjusted_ratio_jump_threshold": 1.5,
  "stock_basic_root": "data/processed/round198_tradeability_long_cycle_official_backfill_20260623",
  "enforce_official_lifecycle": true,
  "exclude_assets_without_lifecycle_metadata": true
}
```

- [ ] **Step 5: Run focused tests and load smoke**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_authority_bars.py -q`

Run: `.venv\Scripts\python.exe -c "from quant_robot.storage.authority_bars import load_authority_processed_bars_from_config as load; b=load('configs/cn_stock_authority_bars_2015_2025_lifecycle_clean.json', ('CN',)); print(len(b), b.asset_id.nunique())"`

Expected: tests pass and the smoke prints positive rows/assets with fewer rows than the historical clean view.

- [ ] **Step 6: Commit the authority view**

```powershell
git add src/quant_robot/storage/authority_bars.py tests/unit/test_authority_bars.py configs/cn_stock_authority_bars_2015_2025_lifecycle_clean.json
git commit -m "feat: enforce official CN stock lifecycles"
```

### Task 5: Extreme-Return Integrity Audit

**Files:**
- Create: `src/quant_robot/ops/cn_stock_price_integrity_audit.py`
- Create: `scripts/run_cn_stock_price_integrity_audit.py`
- Create: `tests/unit/test_cn_stock_price_integrity_audit.py`
- Create: `tests/unit/test_cn_stock_price_integrity_audit_cli.py`

- [ ] **Step 1: Write failing price classification tests**

Construct transitions for adjustment-ratio discontinuity, outside lifecycle, official post-suspension reopening, unexplained raw jump, and combined move. Assert exclusive classification and decision severity.

```python
packet, rows = build_cn_stock_price_integrity_audit(
    bars=bars,
    stock_basic=stock_basic,
    daily_suspension=suspension,
    legacy_suspension=legacy,
    extreme_return_threshold=0.50,
    adjusted_ratio_threshold=1.50,
)
assert set(rows["classification"]) == expected_classes
assert packet["status"] == "blocked"
```

- [ ] **Step 2: Verify the tests fail**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_cn_stock_price_integrity_audit.py tests/unit/test_cn_stock_price_integrity_audit_cli.py -q`

Expected: module imports fail.

- [ ] **Step 3: Implement pure transition audit and writer**

Sort by asset/date, compute previous raw/adjusted prices, adjusted ratio and reciprocal jump score, elapsed days, and absolute adjusted return. Use lifecycle first, adjustment-ratio second, official suspension across the missing interval third, then raw/combined unexplained classes. Write JSON/Markdown, `extreme_return_rows.csv`, and `price_integrity_blockers.csv` atomically.

- [ ] **Step 4: Implement CLI and focused tests**

The CLI mirrors session evidence arguments, adds `--extreme-return-threshold`, `--adjusted-ratio-threshold`, and `--allow-blocked`, and defaults to the lifecycle-clean authority config.

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_cn_stock_price_integrity_audit.py tests/unit/test_cn_stock_price_integrity_audit_cli.py tests/unit/test_script_workspace_imports.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit the price audit**

```powershell
git add src/quant_robot/ops/cn_stock_price_integrity_audit.py scripts/run_cn_stock_price_integrity_audit.py tests/unit/test_cn_stock_price_integrity_audit.py tests/unit/test_cn_stock_price_integrity_audit_cli.py tests/unit/test_script_workspace_imports.py
git commit -m "feat: audit CN stock price integrity"
```

### Task 6: Manifest Gate, Full Evidence Run, and Closeout

**Files:**
- Modify: `src/quant_robot/ops/cn_stock_data_manifest.py`
- Modify: `scripts/run_cn_stock_data_manifest.py`
- Modify: `tests/unit/test_cn_stock_data_manifest.py`
- Create: `docs/research/cn_stock_session_price_integrity_2026-07-16.md`

- [ ] **Step 1: Write failing manifest packet tests**

Pass blocked/session and review-required/price packets into `build_cn_stock_data_manifest`. Assert blocked evidence adds manifest blockers, packet hashes/statuses are preserved, and no packet leaves historical behavior unchanged.

```python
manifest = build_cn_stock_data_manifest(
    bars=bars,
    moneyflow_inputs=moneyflow,
    source_root="authority.json",
    session_integrity_packet={"status": "blocked", "decision": {"blockers": ["x"]}},
)
assert "asset_session_integrity_blocked" in manifest["decision"]["blockers"]
```

- [ ] **Step 2: Verify the test fails, then implement the gate**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_cn_stock_data_manifest.py -q`

Expected before implementation: unexpected keyword argument failure.

Add optional session/price packets, provenance summaries, and blockers. Add CLI packet path arguments and JSON loading.

- [ ] **Step 3: Run the initial full session audit**

```powershell
.venv\Scripts\python.exe scripts/run_cn_stock_asset_session_integrity_audit.py --data-root configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json --calendar-path data/processed/trading_calendars/cn_tushare_2015_2025/cn_trading_calendar.csv --calendar-manifest-path data/processed/trading_calendars/cn_tushare_2015_2025/cn_trading_calendar_manifest.json --evidence-root data/processed/round198_tradeability_long_cycle_official_backfill_20260623 --output-dir data/reports/cn_stock_asset_session_integrity_20260716_initial --allow-blocked
```

Expected: 337,904 classified gaps, 48,990 observed out-of-lifecycle rows, and a finite unresolved asset list.

- [ ] **Step 4: Fetch targeted legacy evidence and rerun**

```powershell
.venv\Scripts\python.exe scripts/ingest_tushare_legacy_suspension.py --unresolved-assets data/reports/cn_stock_asset_session_integrity_20260716_initial/unresolved_assets.csv --start-date 2015-01-01 --end-date 2025-12-31 --output-dir data/processed/cn_stock_legacy_suspension_20260716
```

```powershell
.venv\Scripts\python.exe scripts/run_cn_stock_asset_session_integrity_audit.py --data-root configs/cn_stock_authority_bars_2015_2025_lifecycle_clean.json --calendar-path data/processed/trading_calendars/cn_tushare_2015_2025/cn_trading_calendar.csv --calendar-manifest-path data/processed/trading_calendars/cn_tushare_2015_2025/cn_trading_calendar_manifest.json --evidence-root data/processed/round198_tradeability_long_cycle_official_backfill_20260623 --legacy-suspension-root data/processed/cn_stock_legacy_suspension_20260716 --output-dir data/reports/cn_stock_asset_session_integrity_20260716_final --allow-blocked
```

Expected: lifecycle contamination is zero in the clean view and unresolved active sessions are reduced or explicitly retained as blockers.

- [ ] **Step 5: Run the price audit and gated manifest**

```powershell
.venv\Scripts\python.exe scripts/run_cn_stock_price_integrity_audit.py --data-root configs/cn_stock_authority_bars_2015_2025_lifecycle_clean.json --evidence-root data/processed/round198_tradeability_long_cycle_official_backfill_20260623 --legacy-suspension-root data/processed/cn_stock_legacy_suspension_20260716 --output-dir data/reports/cn_stock_price_integrity_20260716 --allow-blocked
```

Generate the lifecycle-clean data manifest with both audit packet paths. Expected: the manifest truthfully blocks if any unresolved source defects remain; no allow flag converts evidence into clearance.

- [ ] **Step 6: Run regression verification**

Run focused tests:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_asset_session_integrity.py tests/unit/test_cn_stock_asset_session_integrity_audit.py tests/unit/test_cn_stock_asset_session_integrity_audit_cli.py tests/unit/test_tushare_adapter.py tests/unit/test_tushare_legacy_suspension_ingest.py tests/unit/test_tushare_legacy_suspension_ingest_cli.py tests/unit/test_authority_bars.py tests/unit/test_cn_stock_price_integrity_audit.py tests/unit/test_cn_stock_price_integrity_audit_cli.py tests/unit/test_cn_stock_data_manifest.py -q
```

Run full tests and project audit:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts/run_project_audit.py --json
git diff --check
```

Expected: all tests pass, project audit reports no new critical blockers, and diff check is clean.

- [ ] **Step 7: Write evidence summary and commit**

Record exact initial/final classification counts, legacy evidence coverage, lifecycle-clean row/asset counts, price classifications, remaining blockers, and the next CN_ETF preregistered direction. Do not claim data clearance if unresolved rows remain.

```powershell
git add src/quant_robot/ops/cn_stock_data_manifest.py scripts/run_cn_stock_data_manifest.py tests/unit/test_cn_stock_data_manifest.py docs/research/cn_stock_session_price_integrity_2026-07-16.md
git commit -m "feat: gate manifests on CN stock integrity evidence"
```
