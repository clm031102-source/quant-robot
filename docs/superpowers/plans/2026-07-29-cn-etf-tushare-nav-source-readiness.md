# CN ETF Tushare NAV Source Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a point-in-time-safe, resumable Tushare `fund_nav` source audit for the frozen CN ETF universe, without reading labels or authorizing a factor, then record the operator's small-capital economics and the broker-integration boundary needed for later paper execution.

**Architecture:** Add the smallest missing adapter surface, keep raw provider responses separate from a deterministic canonical NAV table, and evaluate the canonical table with a pure readiness function whose frozen gates match the approved design. The execution CLI loads tracked configuration plus ignored local authorities, writes only ignored data/reports, and refuses factor, return, portfolio, paper-signal, broker, account, and order actions. A result of `ready` may only authorize a separately preregistered one-shot NAV-premium prescreen.

**Tech Stack:** Python 3.12, pandas, pyarrow, pytest, existing `TushareAdapter`, existing `DatasetStore`, existing CN trading calendar authority, existing Quant PM startup gate.

---

## Frozen Decisions

- Machine/task/branch: `office_desktop` / `factor_review` / `codex/factor-review-cn-etf-current-access-20260728`.
- Analysis window: `2020-01-02` through `2024-06-28`; read the calendar through `2024-07-05` only to compute the next official session.
- Final 2026 holdout remains sealed.
- Target universe: `data/processed/cn_etf_pcf_target_universe_2020_2024/target_universe.csv`.
- Comparison source: `data/processed/cn_etf_fund_structure_public_2020_2024`.
- Close authority: `data/processed/tushare_etf_wide_history_2023_2026`.
- New source output: `data/processed/cn_etf_tushare_nav_2020_2024`.
- New report output: `data/reports/cn_etf_tushare_nav_source_readiness_20260729`.
- Canonical `known_from` is the first official CN session strictly later than both `nav_date` and `ann_date`.
- Source readiness never reads returns, creates factors, ranks portfolios, generates paper signals, connects to a broker, reads an account, or places an order.
- Operator inputs: CNY 1,000–3,000 capital, 0.5 bp commission per side, 10 bp slippage per side, CNY 5 minimum-commission stress, 40% absolute drawdown veto, 8% paper-promotion drawdown cap, 252-session maximum holding period, CNY 1,000 maximum single position, CNY 60 daily-loss cap, and 1% ADV maximum one-way participation.

## Task 1: Add the Minimal Tushare `fund_nav` Adapter Surface

**Files:**
- Modify: `tests/unit/test_tushare_mapping.py`
- Modify: `tests/unit/test_adapters.py`
- Modify: `src/quant_robot/data/sources/tushare_mapping.py`
- Modify: `src/quant_robot/data/adapters/tushare_adapter.py`

- [ ] **Step 1: Write failing mapping tests**

Add tests proving that the mapper:

```python
def test_map_tushare_fund_nav_normalizes_dates_and_numbers() -> None:
    raw = pd.DataFrame(
        {
            "ts_code": ["510300.SH"],
            "ann_date": ["20200103"],
            "nav_date": ["20200102"],
            "unit_nav": ["4.1234"],
            "accum_nav": ["4.5678"],
            "accum_div": ["0.4444"],
            "net_asset": ["100.0"],
            "total_netasset": ["200.0"],
            "adj_nav": ["4.1000"],
            "update_flag": ["1"],
        }
    )

    result = map_tushare_fund_nav(raw)

    assert result.loc[0, "symbol"] == "510300.SH"
    assert result.loc[0, "ann_date"] == pd.Timestamp("2020-01-03")
    assert result.loc[0, "nav_date"] == pd.Timestamp("2020-01-02")
    assert result.loc[0, "unit_nav"] == pytest.approx(4.1234)
    assert result.loc[0, "update_flag"] == pytest.approx(1.0)
```

Also cover an empty response and a missing required column.

- [ ] **Step 2: Run the mapping tests and observe RED**

Run:

```powershell
python -m pytest tests/unit/test_tushare_mapping.py -q
```

Expected: collection or import failure because `map_tushare_fund_nav` does not exist.

- [ ] **Step 3: Implement the mapper**

In `tushare_mapping.py`, add a stable ordered schema:

```python
FUND_NAV_COLUMNS = [
    "symbol",
    "ann_date",
    "nav_date",
    "unit_nav",
    "accum_nav",
    "accum_div",
    "net_asset",
    "total_netasset",
    "adj_nav",
    "update_flag",
]
```

Implement `map_tushare_fund_nav(raw)` using the module's existing required-column, optional-date, and numeric coercion patterns. Require `ts_code`, `ann_date`, `nav_date`, and `unit_nav`; rename `ts_code` to `symbol`; add missing optional columns as null; sort by `symbol`, `nav_date`, `ann_date`, and `update_flag`.

- [ ] **Step 4: Write and run the failing adapter test**

Add a fake client assertion:

```python
def test_fetch_fund_nav_uses_bounded_request_and_maps_result() -> None:
    client = FakeTushareClient()
    adapter = TushareAdapter(client=client)

    result = adapter.fetch_fund_nav(
        "510300.SH",
        start_date="2020-01-02",
        end_date="2024-06-28",
    )

    assert client.last_fund_nav_request["ts_code"] == "510300.SH"
    assert client.last_fund_nav_request["start_date"] == "20200102"
    assert client.last_fund_nav_request["end_date"] == "20240628"
    assert result["symbol"].tolist() == ["510300.SH"]
```

Run:

```powershell
python -m pytest tests/unit/test_adapters.py -q
```

Expected: failure because `fetch_fund_nav` does not exist.

- [ ] **Step 5: Implement the adapter method and verify GREEN**

Add `fetch_fund_nav(ts_code, start_date="", end_date="", market="E")`. Request only the frozen fields, use the existing retry/call wrapper, normalize dates with the existing helper, and return `map_tushare_fund_nav(raw)`.

Run:

```powershell
python -m pytest tests/unit/test_tushare_mapping.py tests/unit/test_adapters.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the adapter slice**

```powershell
git add tests/unit/test_tushare_mapping.py tests/unit/test_adapters.py src/quant_robot/data/sources/tushare_mapping.py src/quant_robot/data/adapters/tushare_adapter.py
git commit -m "feat: add Tushare ETF NAV adapter"
```

## Task 2: Canonicalize Revisions and Compute Point-in-Time Availability

**Files:**
- Create: `tests/unit/test_tushare_fund_nav_ingest.py`
- Create: `src/quant_robot/data/ingest/tushare_fund_nav.py`

- [ ] **Step 1: Write failing tests for the request plan**

Exercise a listed ETF, a delisted ETF, and an ETF whose life does not intersect the analysis window:

```python
def test_build_request_plan_clips_each_asset_to_its_lifetime() -> None:
    universe = pd.DataFrame(
        {
            "etf_code": ["510300", "159901", "510999"],
            "market_exchange": ["SSE", "SZSE", "SSE"],
            "list_date": ["2012-05-28", "2004-12-10", "2025-01-01"],
            "delist_date": [None, "2021-06-30", None],
        }
    )

    result = build_tushare_fund_nav_request_plan(
        universe,
        start_date="2020-01-02",
        end_date="2024-06-28",
    )

    assert result["symbol"].tolist() == ["159901.SZ", "510300.SH"]
    assert result.set_index("symbol").loc["159901.SZ", "request_end"] == pd.Timestamp("2021-06-30")
```

- [ ] **Step 2: Write failing tests for revision resolution**

Prove that the later announcement wins, then the higher numeric `update_flag`, and an unresolved value conflict at the same precedence raises `ValueError`:

```python
def test_canonicalize_prefers_latest_announced_revision() -> None:
    raw = pd.DataFrame(
        {
            "symbol": ["510300.SH", "510300.SH"],
            "nav_date": pd.to_datetime(["2020-01-02", "2020-01-02"]),
            "ann_date": pd.to_datetime(["2020-01-03", "2020-01-06"]),
            "unit_nav": [4.0, 4.1],
            "update_flag": [0.0, 1.0],
        }
    )

    result = canonicalize_tushare_fund_nav(raw, SESSIONS)

    assert result.loc[0, "unit_nav"] == pytest.approx(4.1)
    assert result.loc[0, "known_from"] == pd.Timestamp("2020-01-07")
```

- [ ] **Step 3: Write failing tests for PIT availability**

Cover:

- Friday announcement becoming known on Monday.
- Announcement on a holiday becoming known on the next official session.
- `ann_date < nav_date` remaining in the canonical table but with `known_from=NaT` and `is_pit_usable=False`.
- No official later session producing an unusable row rather than guessing a calendar date.
- Canonical columns containing no return, label, signal, score, rank, or portfolio fields.

- [ ] **Step 4: Run the ingest tests and observe RED**

```powershell
python -m pytest tests/unit/test_tushare_fund_nav_ingest.py -q
```

Expected: import failure because `tushare_fund_nav.py` does not exist.

- [ ] **Step 5: Implement pure request-plan and canonicalization functions**

Create:

```python
def build_tushare_fund_nav_request_plan(
    target_universe: pd.DataFrame,
    *,
    start_date: str | pd.Timestamp,
    end_date: str | pd.Timestamp,
) -> pd.DataFrame: ...


def canonicalize_tushare_fund_nav(
    raw: pd.DataFrame,
    trading_sessions: Sequence[pd.Timestamp],
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
    source: str = "tushare_fund_nav",
) -> pd.DataFrame: ...
```

Canonical columns:

```python
CANONICAL_COLUMNS = [
    "nav_date",
    "ann_date",
    "known_from",
    "asset_id",
    "symbol",
    "exchange",
    "unit_nav",
    "accum_nav",
    "total_netasset",
    "update_flag",
    "is_pit_usable",
    "source",
]
```

Use `np.searchsorted` over sorted official sessions to locate the first session strictly after `max(nav_date, ann_date)`. Do not forward-fill or infer missing announcements.

- [ ] **Step 6: Verify the pure logic is GREEN**

```powershell
python -m pytest tests/unit/test_tushare_fund_nav_ingest.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit the PIT canonicalization slice**

```powershell
git add tests/unit/test_tushare_fund_nav_ingest.py src/quant_robot/data/ingest/tushare_fund_nav.py
git commit -m "feat: canonicalize point-in-time ETF NAV"
```

## Task 3: Add Resumable, Auditable Source Acquisition

**Files:**
- Modify: `tests/unit/test_tushare_fund_nav_ingest.py`
- Modify: `src/quant_robot/data/ingest/tushare_fund_nav.py`

- [ ] **Step 1: Write failing resume and terminal-state tests**

Use a temporary directory and a fake adapter to prove:

- completed requests are not fetched again;
- deterministic empty responses are terminal;
- retry-exhausted requests are recorded as failed;
- every target request ends in `completed`, `empty`, or `failed`;
- request and response hashes are stable;
- no secret token is written to the manifest.

Test API:

```python
result = run_tushare_fund_nav_ingest(
    adapter=fake_adapter,
    target_universe=universe,
    trading_sessions=SESSIONS,
    output_dir=tmp_path,
    start_date="2020-01-02",
    end_date="2024-06-28",
    request_sleep_seconds=0.0,
)
assert result.manifest_path.exists()
assert result.canonical_path.exists()
```

- [ ] **Step 2: Run the focused tests and observe RED**

```powershell
python -m pytest tests/unit/test_tushare_fund_nav_ingest.py -q
```

Expected: failure because the acquisition function/result type does not exist.

- [ ] **Step 3: Implement sequential resumable acquisition**

Add an immutable result dataclass and:

```python
def run_tushare_fund_nav_ingest(
    *,
    adapter: TushareAdapter,
    target_universe: pd.DataFrame,
    trading_sessions: Sequence[pd.Timestamp],
    output_dir: str | Path,
    start_date: str,
    end_date: str,
    request_sleep_seconds: float = 0.35,
) -> TushareFundNavIngestResult: ...
```

Implementation rules:

- Build one bounded request per in-window ETF.
- Fetch sequentially to respect the current access band and avoid client thread-safety ambiguity.
- Persist one provider-normalized parquet per symbol under `source/`.
- Atomically update `request_manifest.json` after every terminal request.
- Canonicalize all successful/empty partitions into `canonical/nav.parquet`.
- Persist `canonical_manifest.json` with inputs, boundaries, row counts, date ranges, content hashes, and explicit forbidden-action flags.
- Never persist the Tushare token, environment contents, account data, or order data.

- [ ] **Step 4: Verify resume behavior and run broader ingest tests**

```powershell
python -m pytest tests/unit/test_tushare_fund_nav_ingest.py tests/unit/test_public_cn_etf_fund_structure.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the acquisition slice**

```powershell
git add tests/unit/test_tushare_fund_nav_ingest.py src/quant_robot/data/ingest/tushare_fund_nav.py
git commit -m "feat: acquire resumable ETF NAV source"
```

## Task 4: Implement the Frozen Source-Readiness Gates

**Files:**
- Create: `tests/unit/test_cn_etf_tushare_nav_source_readiness.py`
- Create: `src/quant_robot/ops/cn_etf_tushare_nav_source_readiness.py`

- [ ] **Step 1: Write a ready-fixture test**

Build a compact fixture with 30 assets, five sessions, complete terminal requests, valid PIT dates, and a public-source comparison. Assert:

```python
result = evaluate_cn_etf_tushare_nav_source_readiness(
    nav=nav,
    request_manifest=request_manifest,
    public_nav=public_nav,
    official_sessions=official_sessions,
    thresholds=thresholds,
    analysis_start="2020-01-02",
    analysis_end="2020-01-08",
)

assert result["status"] == "ready"
assert result["boundaries"]["factor_generation_allowed"] is False
assert result["boundaries"]["broker_connection_allowed"] is False
```

- [ ] **Step 2: Write one failing test per frozen blocker**

Cover:

1. unresolved request state;
2. duplicate `asset_id/nav_date`;
3. out-of-window or 2026 data;
4. `ann_date >= nav_date` ratio below 99%;
5. invalid `known_from`;
6. finite positive `unit_nav` ratio below 99.9%;
7. public key intersection below 90%;
8. public asset match below 90%;
9. within-10-bp agreement below 99%;
10. severe disagreement above 0.1%;
11. fewer than 30 usable assets on 80% of official sessions;
12. forbidden analytical columns or an enabled forbidden boundary.

- [ ] **Step 3: Run the readiness tests and observe RED**

```powershell
python -m pytest tests/unit/test_cn_etf_tushare_nav_source_readiness.py -q
```

Expected: import failure because the readiness module does not exist.

- [ ] **Step 4: Implement a pure evaluator**

Expose:

```python
DEFAULT_THRESHOLDS = {
    "minimum_terminal_request_ratio": 1.0,
    "minimum_valid_announcement_ratio": 0.99,
    "minimum_positive_unit_nav_ratio": 0.999,
    "minimum_public_key_intersection_ratio": 0.90,
    "minimum_public_asset_match_ratio": 0.90,
    "minimum_within_10bp_ratio": 0.99,
    "maximum_severe_disagreement_ratio": 0.001,
    "severe_disagreement_threshold": 0.05,
    "minimum_usable_assets_per_session": 30,
    "minimum_usable_session_coverage": 0.80,
}
```

Compute agreement as `abs(tushare_unit_nav / public_unit_nav - 1)`. Return deterministic `status`, `blockers`, `warnings`, `metrics`, `thresholds`, `boundaries`, and `source_lineage`. No performance or return metric is permitted.

- [ ] **Step 5: Add deterministic report writing**

Implement:

```python
def write_cn_etf_tushare_nav_source_readiness_report(
    result: Mapping[str, Any],
    report_dir: str | Path,
) -> dict[str, Path]: ...
```

Write:

- `source_readiness.json`
- `source_readiness.md`
- `request_states.csv`
- `nav_agreement_summary.csv`
- `session_coverage.csv`

Use atomic writes for JSON/Markdown and stable sort order for CSV.

- [ ] **Step 6: Verify GREEN and commit**

```powershell
python -m pytest tests/unit/test_cn_etf_tushare_nav_source_readiness.py -q
git add tests/unit/test_cn_etf_tushare_nav_source_readiness.py src/quant_robot/ops/cn_etf_tushare_nav_source_readiness.py
git commit -m "feat: audit ETF NAV source readiness"
```

Expected: PASS, then a successful commit.

## Task 5: Add a Strict Config and CLI

**Files:**
- Create: `configs/cn_etf_tushare_nav_source_readiness_20260729.json`
- Create: `tests/unit/test_run_cn_etf_tushare_nav_source_readiness.py`
- Create: `scripts/run_cn_etf_tushare_nav_source_readiness.py`

- [ ] **Step 1: Add the frozen tracked config**

The config must record:

```json
{
  "schema_version": 1,
  "stage": "cn_etf_tushare_nav_source_readiness",
  "review_date": "2026-07-29",
  "primary_market": "CN_ETF",
  "research_family": "cn_etf_nav_premium_relative_value",
  "analysis": {
    "target_universe_path": "data/processed/cn_etf_pcf_target_universe_2020_2024/target_universe.csv",
    "public_nav_root": "data/processed/cn_etf_fund_structure_public_2020_2024",
    "bar_root": "data/processed/tushare_etf_wide_history_2023_2026",
    "trading_calendar_path": "data/processed/trading_calendars/cn_tushare_2015_2025/cn_trading_calendar.csv",
    "trading_calendar_manifest_path": "data/processed/trading_calendars/cn_tushare_2015_2025/cn_trading_calendar_manifest.json",
    "start_date": "2020-01-02",
    "end_date": "2024-06-28",
    "next_session_read_end": "2024-07-05",
    "final_holdout_start": "2026-01-01"
  },
  "outputs": {
    "data_dir": "data/processed/cn_etf_tushare_nav_2020_2024",
    "report_dir": "data/reports/cn_etf_tushare_nav_source_readiness_20260729"
  },
  "provider": {
    "endpoint": "fund_nav",
    "market": "E",
    "request_sleep_seconds": 0.35
  },
  "thresholds": {
    "minimum_terminal_request_ratio": 1.0,
    "minimum_valid_announcement_ratio": 0.99,
    "minimum_positive_unit_nav_ratio": 0.999,
    "minimum_public_key_intersection_ratio": 0.9,
    "minimum_public_asset_match_ratio": 0.9,
    "minimum_within_10bp_ratio": 0.99,
    "maximum_severe_disagreement_ratio": 0.001,
    "severe_disagreement_threshold": 0.05,
    "minimum_usable_assets_per_session": 30,
    "minimum_usable_session_coverage": 0.8
  },
  "boundaries": {
    "factor_generation_allowed": false,
    "forward_return_read": false,
    "portfolio_grid_allowed": false,
    "walk_forward_allowed": false,
    "final_holdout_allowed": false,
    "promotion_allowed": false,
    "paper_signal_allowed": false,
    "broker_connection_allowed": false,
    "account_read_allowed": false,
    "order_placement_allowed": false,
    "live_boundary_allowed": false
  }
}
```

- [ ] **Step 2: Write failing CLI safety tests**

Test that the CLI:

- defaults to audit-only and does not call the provider;
- requires `--execute` for acquisition;
- refuses a config with any forbidden boundary set to `true`;
- refuses a current branch of `main`;
- refuses dates at or after the sealed holdout;
- loads the Tushare token only at runtime and never writes it;
- can audit an existing local dataset without network access.

- [ ] **Step 3: Run the CLI tests and observe RED**

```powershell
python -m pytest tests/unit/test_run_cn_etf_tushare_nav_source_readiness.py -q
```

Expected: import or path failure because the script does not exist.

- [ ] **Step 4: Implement the CLI**

Required interface:

```text
python scripts/run_cn_etf_tushare_nav_source_readiness.py
python scripts/run_cn_etf_tushare_nav_source_readiness.py --execute
```

The script must:

1. load and validate the frozen config;
2. assert the current branch is not `main`;
3. validate the fingerprinted official calendar;
4. load the target/public authorities;
5. only instantiate and call Tushare when `--execute` is present;
6. otherwise audit an already complete local dataset;
7. write ignored reports;
8. print a compact JSON summary;
9. exit nonzero on acquisition errors or source blockers.

- [ ] **Step 5: Verify the CLI tests and dry-run behavior**

```powershell
python -m pytest tests/unit/test_run_cn_etf_tushare_nav_source_readiness.py -q
python scripts/run_cn_etf_tushare_nav_source_readiness.py
```

Expected: tests PASS; dry run exits nonzero with a clear local-dataset-missing message until acquisition is executed.

- [ ] **Step 6: Commit the CLI slice**

```powershell
git add configs/cn_etf_tushare_nav_source_readiness_20260729.json tests/unit/test_run_cn_etf_tushare_nav_source_readiness.py scripts/run_cn_etf_tushare_nav_source_readiness.py
git commit -m "feat: run strict ETF NAV source audit"
```

## Task 6: Execute the Real Source Audit Exactly Once

**Files:**
- Generate, do not commit: `data/processed/cn_etf_tushare_nav_2020_2024/**`
- Generate, do not commit: `data/reports/cn_etf_tushare_nav_source_readiness_20260729/**`

- [ ] **Step 1: Re-run the Quant PM startup gate**

```powershell
python scripts/run_quant_pm_startup_gate.py --machine office_desktop --task factor_review --branch codex/factor-review-cn-etf-current-access-20260728
```

Expected: gate ready for source review, with the research-family scheduler warning preserved.

- [ ] **Step 2: Execute acquisition and source audit**

```powershell
python scripts/run_cn_etf_tushare_nav_source_readiness.py --execute
```

Expected: 1,069 bounded terminal requests, resumable progress, canonical ignored data, and a deterministic readiness report. A blocker is an acceptable research outcome.

- [ ] **Step 3: Resume only if provider interruption occurred**

Run the same command again only when the first execution reports non-terminal or failed retryable requests. Confirm completed requests are not downloaded again.

- [ ] **Step 4: Re-run in local audit mode**

```powershell
python scripts/run_cn_etf_tushare_nav_source_readiness.py
```

Expected: no network call and identical metrics/hashes for the canonical source.

- [ ] **Step 5: Inspect the evidence without reading labels**

```powershell
Get-Content data\reports\cn_etf_tushare_nav_source_readiness_20260729\source_readiness.md
Get-Content data\reports\cn_etf_tushare_nav_source_readiness_20260729\source_readiness.json
```

Decision:

- `ready`: authorize Task 7's separate preregistration only.
- `blocked`: document the failing source gates and stop the NAV-premium research family. Do not relax thresholds or try another signal.

## Task 7: Record Operator Economics and the Next Research Boundary

**Files:**
- Create: `configs/cn_etf_small_capital_inputs_20260729.json`
- Create: `tests/unit/test_cn_etf_small_capital_inputs.py`
- Create: `src/quant_robot/ops/cn_etf_small_capital_inputs.py`
- Create: `docs/research/cn-etf-tushare-nav-source-readiness-20260729.md`
- Modify only if source is ready: `configs/research_family_scheduler_cn_etf.json`
- Modify only if source is ready: `tests/unit/test_research_family_scheduler.py`

- [ ] **Step 1: Write failing operator-economics tests**

Prove the exact cost arithmetic:

```python
def test_round_trip_costs_cover_no_minimum_and_minimum_fee_stress() -> None:
    inputs = SmallCapitalInputs.from_mapping(FROZEN_INPUTS)

    assert inputs.round_trip_cost_bps(3000, minimum_fee=0) == pytest.approx(21.0)
    assert inputs.round_trip_cost_bps(3000, minimum_fee=5) == pytest.approx(53.333333)
    assert inputs.round_trip_cost_bps(1000, minimum_fee=5) == pytest.approx(120.0)
```

Also reject:

- capital outside CNY 1,000–3,000;
- absolute drawdown veto above 40%;
- paper drawdown cap above 8%;
- non-positive holding period;
- any enabled broker/account/order/live boundary.

- [ ] **Step 2: Run the test and observe RED**

```powershell
python -m pytest tests/unit/test_cn_etf_small_capital_inputs.py -q
```

Expected: import failure because the validation module does not exist.

- [ ] **Step 3: Implement and persist the frozen inputs**

Tracked JSON:

```json
{
  "schema_version": 1,
  "as_of_date": "2026-07-29",
  "capital_cny": {"minimum": 1000, "maximum": 3000},
  "commission_bps_per_side": 0.5,
  "slippage_bps_per_side": 10.0,
  "minimum_commission_cny_stress": 5.0,
  "absolute_max_drawdown": 0.4,
  "paper_promotion_max_drawdown": 0.08,
  "max_holding_sessions": 252,
  "max_single_position_cny": 1000,
  "max_daily_loss_cny": 60,
  "max_one_way_adv_participation": 0.01,
  "minimum_paper_days": 20,
  "minimum_paper_fills": 30,
  "minimum_market_regimes": 2,
  "boundaries": {
    "broker_connection_allowed": false,
    "account_read_allowed": false,
    "order_placement_allowed": false,
    "live_boundary_allowed": false
  }
}
```

Implement a frozen dataclass, strict validation, and `round_trip_cost_bps(notional_cny, minimum_fee)` where commission per side is `max(notional * commission_bps / 10_000, minimum_fee)`.

- [ ] **Step 4: Verify the operator inputs**

```powershell
python -m pytest tests/unit/test_cn_etf_small_capital_inputs.py -q
```

Expected: PASS.

- [ ] **Step 5: Write the evidence-backed research decision**

The lightweight report must state:

- source row/asset/session/date counts;
- each frozen gate and result;
- whether a separate candidate preregistration is authorized;
- no source-readiness performance claim;
- 21 bp base round-trip cost before minimum fee;
- 53.33–120 bp minimum-fee stress across CNY 3,000–1,000 notionals;
- 20 paper days, 30 fills, two regimes, and 8% paper drawdown remain physically uncompleted until elapsed observation exists;
- the broker adapter contract is schema-only and remains disabled until research and paper gates pass.

- [ ] **Step 6: Update scheduler only when the source is ready**

If and only if the report status is `ready`, add a single `source_ready_preregistration_required` state for `cn_etf_nav_premium_relative_value`. This state must authorize no factor run by itself. If blocked, record the family as `source_stop_loss` and do not add a candidate.

- [ ] **Step 7: Commit the governance slice**

```powershell
git add configs/cn_etf_small_capital_inputs_20260729.json tests/unit/test_cn_etf_small_capital_inputs.py src/quant_robot/ops/cn_etf_small_capital_inputs.py docs/research/cn-etf-tushare-nav-source-readiness-20260729.md
git add configs/research_family_scheduler_cn_etf.json tests/unit/test_research_family_scheduler.py
git commit -m "docs: record ETF NAV source decision"
```

When the source is blocked and scheduler files are unchanged, omit the second `git add` command.

## Task 8: Pre-register and Run One Candidate Only If Authorized

**Files:**
- Create only when Task 6 status is `ready`: `configs/cn_etf_delayed_nav_premium_innovation_reversal_60_20260729.json`
- Create only when ready: `tests/unit/test_cn_etf_delayed_nav_premium_prescreen.py`
- Create only when ready: `tests/unit/test_run_cn_etf_delayed_nav_premium_prescreen.py`
- Create only when ready: `src/quant_robot/ops/cn_etf_delayed_nav_premium_prescreen.py`
- Create only when ready: `scripts/run_cn_etf_delayed_nav_premium_prescreen.py`
- Generate, do not commit: ignored prescreen data/reports

- [ ] **Step 1: Freeze the one permitted candidate before reading returns**

Candidate:

- family: `cn_etf_nav_premium_relative_value`
- name: `etf_delayed_nav_premium_innovation_reversal_60`
- observation: close divided by the latest `unit_nav` with `known_from <= signal_date`, minus one
- innovation: current premium minus its 60-session rolling median using only prior/known observations
- direction: negative innovation
- primary horizon: H1
- diagnostic horizon: H5
- rebalance: daily
- neutralization: exchange and broad product class only when those PIT-safe fields already exist
- costs: 10 bp per side slippage plus 0.5 bp per side commission; separately report CNY 5 minimum-fee stress
- no parameter alternatives, no broad grid, no final holdout.

- [ ] **Step 2: Write failing PIT and preregistration tests**

Tests must prove:

- no NAV row is available before `known_from`;
- the rolling median excludes the current date;
- no backfilled current-name product mapping is used;
- the CLI refuses a changed config hash;
- H1 is the only promotion horizon;
- no second factor or parameter variant can be emitted.

- [ ] **Step 3: Implement only the preregistered signal**

Reuse the existing one-shot prescreen/walk-forward infrastructure. Do not implement a generic NAV factor catalog.

- [ ] **Step 4: Re-run the Quant PM gate, then execute once**

```powershell
python scripts/run_quant_pm_startup_gate.py --machine office_desktop --task factor_review --branch codex/factor-review-cn-etf-current-access-20260728
python scripts/run_cn_etf_delayed_nav_premium_prescreen.py --execute
```

The first strict execution consumes the family budget. Do not rescue, retune, or rerun against alternative windows.

- [ ] **Step 5: Decide strictly**

- Pass all frozen OOS/PIT/cost/capacity/stability gates: prepare the existing manual paper-observation package with broker actions still disabled.
- Fail any hard gate: close the family and preserve the rejection evidence.

- [ ] **Step 6: Commit only code, config, tests, and lightweight summary**

Never commit generated data, large reports, provider responses, logs, tokens, account data, broker credentials, or orders.

## Task 9: Verify, Review, Integrate, and Push

**Files:**
- Verify all tracked changes
- Do not commit ignored generated data/reports

- [ ] **Step 1: Run focused tests**

```powershell
python -m pytest tests/unit/test_tushare_mapping.py tests/unit/test_adapters.py tests/unit/test_tushare_fund_nav_ingest.py tests/unit/test_cn_etf_tushare_nav_source_readiness.py tests/unit/test_run_cn_etf_tushare_nav_source_readiness.py tests/unit/test_cn_etf_small_capital_inputs.py -q
```

- [ ] **Step 2: Run repository safety and unit checks**

```powershell
python scripts/run_checks.py --profile safety
python -m pytest tests/unit -q
```

- [ ] **Step 3: Audit the Git payload**

```powershell
git status --short
git diff --check
git diff --stat origin/main...HEAD
git diff --name-only origin/main...HEAD
```

Confirm there are no paths under `data/raw`, `data/processed`, `data/reports`, no logs, tokens, credentials, account data, order data, or large outputs.

- [ ] **Step 4: Review branch history and final evidence**

```powershell
git log --oneline origin/main..HEAD
git status --short --branch
```

Use the verification-before-completion and finishing-a-development-branch workflows. Fix any relevant defect and rerun affected tests.

- [ ] **Step 5: Push the topic branch**

```powershell
git push -u origin codex/factor-review-cn-etf-current-access-20260728
```

Expected: successful push of safe tracked evidence only. Keep `main` stable unless a later explicit integration step is supported by passing checks and branch policy.

## Completion Criteria

This 24-hour tranche is complete only when:

1. the Tushare NAV source has a deterministic `ready` or `blocked` result;
2. PIT availability, revision handling, resume behavior, and all frozen gates have tests;
3. the small-capital cost/risk inputs are tracked and validated;
4. a ready source has either one preregistered strict candidate result or a documented reason that the one-shot run cannot safely begin;
5. a rejected source/factor is closed without threshold relaxation;
6. paper and broker-readiness status clearly distinguishes code/config readiness from the physically incomplete 20-day/30-fill/two-regime observation gate;
7. no broker connection, account read, order placement, or live-trading action occurred;
8. all safe code/config/tests/lightweight reports are committed and pushed.
