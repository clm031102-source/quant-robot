# CN ETF Dynamic Peer Dislocation Prescreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement, verify, and execute exactly one hash-bound CN ETF dynamic-peer residual-dislocation prescreen, then close or advance the family strictly according to the frozen primary-horizon gates.

**Architecture:** Keep point-in-time factor math in a pure factor module, supplemental cross-sectional cost/capacity diagnostics in a focused research module, analytical orchestration and deterministic writing in one operation, and hash/auth/file boundaries in a strict CLI. Build all unlabeled inputs before atomically claiming the real authorization; construct forward labels only after the claim.

**Tech Stack:** Python 3.12, pandas, NumPy, SciPy through existing prescreen utilities, unittest, existing CN ETF eligibility/storage/factor modules, atomic JSON writing, and the one-time authorization ledger.

---

### Task 1: Implement Point-In-Time Dynamic-Peer Factor Math

**Files:**
- Create: `src/quant_robot/factors/etf_dynamic_peer_dislocation.py`
- Create: `tests/unit/test_etf_dynamic_peer_dislocation.py`

- [ ] **Step 1: Write failing formula and eligibility tests**

Use compact synthetic calendars with a target and at least three peers. Assert:

- the market return is the eligible cross-sectional median;
- alpha and beta used on `t` are estimated only through `t-1`;
- five residuals are required for `E5`;
- the active mapping interval is used on each date;
- an ineligible peer is removed and fewer than three peers emits no factor;
- the peer consensus is an ordinary median; and
- zero or sub-epsilon MAD emits no factor.

- [ ] **Step 2: Write failing causality regressions**

Assert that appending future bars, changing a future mapping interval, or adding
a new peer after a historical date leaves all prior factor values unchanged.
Add a missing-dislocation test proving that the robust window is 60 prior
calendar signal dates, not 60 prior finite observations.

- [ ] **Step 3: Verify the tests fail because the module is absent**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_etf_dynamic_peer_dislocation
```

- [ ] **Step 4: Implement the pure factor builder**

Expose:

```python
def compute_etf_dynamic_peer_dislocation(
    bars: pd.DataFrame,
    mapping: pd.DataFrame,
    *,
    eligible_keys: pd.DataFrame,
    market_min_cross_section: int = 30,
    beta_window: int = 120,
    beta_min_observations: int = 80,
    beta_lag: int = 1,
    residual_sum_window: int = 5,
    minimum_daily_peers: int = 3,
    robust_scale_window: int = 60,
    robust_scale_min_observations: int = 40,
    robust_scale_epsilon: float = 1e-12,
) -> DynamicPeerDislocationResult:
    ...
```

Return candidate rows, raw diagnostics, and direct exposure rows in a frozen
dataclass. Reuse the audited mapping validator and existing market-proxy and
ADV20 conventions where they preserve the exact formula. Reject duplicate
asset-date bars, duplicate eligibility keys, an unexpected mapping method,
invalid intervals, and non-one-session beta lag.

- [ ] **Step 5: Run focused tests and commit**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_etf_dynamic_peer_dislocation
```

Commit the factor module and tests only after the focused suite passes.

### Task 2: Add Supplemental Cost, Capacity, And Exposure Diagnostics

**Files:**
- Create: `src/quant_robot/research/cross_sectional_prescreen_diagnostics.py`
- Create: `tests/unit/test_cross_sectional_prescreen_diagnostics.py`

- [ ] **Step 1: Write failing quintile and turnover tests**

Construct two dates with changing membership and assert top and bottom turnover
independently. The first date must be excluded from average transition turnover
but charged as 1.0 per side in cost-adjusted spread.

- [ ] **Step 2: Write failing cost tests**

Assert daily and mean net spread for 5 and 10 bps using:

```python
net = gross - one_way_cost * (top_turnover + bottom_turnover)
```

Cover missing labels, insufficient cross-section, ties, and a negative 10 bps
primary result.

- [ ] **Step 3: Write failing all-date capacity tests**

Assert that pooled liquidity cannot hide one unsupported date. Require complete
finite positive ADV20 coverage for every top-quintile constituent and calculate
daily P10, daily participation, minimum P10, maximum participation, and worst
date.

- [ ] **Step 4: Write failing direct-exposure correlation tests**

Calculate mean daily Spearman correlations, report every expected exposure,
and block missing, all-null, or absolute correlation greater than or equal to
0.85.

- [ ] **Step 5: Implement and verify the diagnostic helpers**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_cross_sectional_prescreen_diagnostics
```

Keep the module label/factor-frame based and independent of file I/O.

### Task 3: Build The Frozen Prescreen Operation

**Files:**
- Create: `src/quant_robot/ops/cn_etf_dynamic_peer_dislocation_prescreen.py`
- Create: `tests/unit/test_cn_etf_dynamic_peer_dislocation_prescreen.py`

- [ ] **Step 1: Write failing pass and close-family tests**

Build small precomputed factor, label, reference, exposure, and ADV fixtures.
Assert exactly two Benjamini-Hochberg rows, horizon 5 as primary, horizon 20 as
non-rescuing diagnostic, and a family decision of either `primary_passed` or
`close_family_zero_budget`.

- [ ] **Step 2: Write one failing test per supplemental blocker**

Cover reference hash/name completeness, direct exposure ceiling, per-date
capacity, 10 bps net spread, missing primary evidence, and a positive H20 row
that cannot rescue failed H5.

- [ ] **Step 3: Implement reference-union construction**

Read the three exact closed-family configs, validate their hashes, derive the
expected complete candidate-and-reference name set, and call the existing skip
momentum, liquidity/capacity, and residual-volatility builders over identical
eligible keys. Reject duplicate or missing names and all-null overlap.

- [ ] **Step 4: Implement analytical orchestration**

Reuse `summarize_cross_sectional_factor_prescreen` for the shared statistical
gate. Add the supplemental diagnostics without weakening shared blockers.
Apply frozen primary/diagnostic roles after both rows have received the same
Benjamini-Hochberg correction.

- [ ] **Step 5: Implement deterministic artifacts**

Write stable JSON, Markdown, candidate-horizon metrics, daily IC, quintile,
turnover/cost, capacity, reference-correlation, direct-exposure-correlation,
and manifest evidence. Sort every table explicitly and exclude wall-clock
fields from analytical artifacts.

- [ ] **Step 6: Run operation tests and commit**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_cn_etf_dynamic_peer_dislocation_prescreen
```

### Task 4: Implement Strict Preflight And One-Time CLI

**Files:**
- Create: `scripts/run_cn_etf_dynamic_peer_dislocation_prescreen.py`
- Create: `tests/unit/test_run_cn_etf_dynamic_peer_dislocation_prescreen.py`

- [ ] **Step 1: Write failing static-preflight tests**

Reject a changed preregistration config, source/mapping/reference hash mismatch,
authorization hash mismatch, scheduler scope mismatch, existing claim, enabled
downstream boundary, output path outside `data/reports`, and any horizon other
than 5 and 20. Assert no bar loader or label builder is called on these failures.

- [ ] **Step 2: Write failing sequencing tests**

Patch the data and authorization functions and record call order. Assert:

1. config/hash/scope validation;
2. bars, lifecycle, eligibility, mapping, factor, references, exposures, ADV20;
3. atomic authorization claim;
4. forward-label construction;
5. summary and artifact writing.

Assert a pre-claim exception leaves the fixture ledger absent and a post-claim
exception leaves the claim consumed and writes terminal failure evidence.

- [ ] **Step 3: Implement a strict, parameter-free CLI**

Support `--preflight-only` for static boundary validation and
`--execute-authorized` for the single full execution. No factor windows,
thresholds, dates, horizons, costs, paths, or rescue options are accepted from
the command line.

The full command keeps unlabeled frames in memory, claims once immediately
before `make_forward_returns`, and never retries after a claim.

- [ ] **Step 4: Verify CLI tests and existing authorization tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_run_cn_etf_dynamic_peer_dislocation_prescreen tests.unit.test_single_prescreen_authorization tests.unit.test_quant_pm_startup_gate
```

### Task 5: Prove The Pipeline Before Consuming Real Authorization

**Files:**
- Modify only if a discovered defect requires it: modules and tests from Tasks 1-4

- [ ] **Step 1: Run all new focused tests together**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_etf_dynamic_peer_dislocation tests.unit.test_cross_sectional_prescreen_diagnostics tests.unit.test_cn_etf_dynamic_peer_dislocation_prescreen tests.unit.test_run_cn_etf_dynamic_peer_dislocation_prescreen
```

- [ ] **Step 2: Run a synthetic end-to-end fixture authorization**

Use only a temporary packet and temporary ledger. Generate deterministic
artifacts twice in separate temporary directories and compare their analytical
hashes. Confirm the real ledger still does not exist.

- [ ] **Step 3: Run adjacent regression tests and compilation**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_cross_sectional_factor_prescreen tests.unit.test_cross_sectional_capacity tests.unit.test_cn_etf_market_residual_volatility_prescreen tests.unit.test_single_prescreen_authorization tests.unit.test_quant_pm_startup_gate
```

```powershell
.\.venv\Scripts\python.exe -m compileall -q src scripts tests
```

- [ ] **Step 4: Run real static preflight**

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_etf_dynamic_peer_dislocation_prescreen.py --preflight-only
```

Verify exact hashes, zero claims, and no label read. Commit the complete tested
implementation before the real run.

### Task 6: Execute Once And Close The Research Decision

**Files:**
- Modify: `configs/research_family_scheduler_cn_etf.json`
- Modify: `docs/research/CURRENT_RESEARCH_INDEX.md`
- Create: `docs/research/cn_etf_dynamic_peer_dislocation_prescreen_2026-07-16.md`
- Modify or create tests for scheduler closeout as required

- [ ] **Step 1: Re-run the Quant PM gate**

```powershell
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-etf-dynamic-peer-dislocation-20260716
```

- [ ] **Step 2: Execute the real authorized prescreen exactly once**

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_etf_dynamic_peer_dislocation_prescreen.py --execute-authorized
```

Do not rerun this command. Inspect the claim ledger, execution outcome, and
analytical report directly.

- [ ] **Step 3: Apply the frozen stop decision**

If H5 fails any required gate, record family closure with zero budget and no
rescue. If H5 passes every gate, authorize only 2024-H2 through 2025 backfill
and data-quality work; do not authorize walk-forward or holdout access yet.
Update scheduler tests first, then scheduler state.

- [ ] **Step 4: Write the durable research report and index update**

Report the exact tested sample, coverage, both horizon rows, all blockers,
reference and direct-exposure maxima, cost and capacity outcomes, artifact
hashes, authorization consumption, and next allowed direction. Make no
profitability claim beyond the evidence.

- [ ] **Step 5: Run full verification**

Run the complete unittest suite, compilation, project audit, maintainability
baseline, and safe-sync audit under `.venv`. Generated data/reports remain
ignored and must not be staged.

- [ ] **Step 6: Commit the closeout**

Commit code/config/tests/docs locally. Do not push unless the user explicitly
changes the current no-push instruction.
