# CN ETF Skip-Momentum Prescreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a preregistered, point-in-time CN ETF skip-momentum statistical prescreen that either freezes a non-duplicate research lead or closes the remaining price-rotation subspace.

**Architecture:** Keep historical eligibility, factor construction, and statistical decision logic in separate focused modules. The CLI loads the existing wide Tushare ETF root, computes factors and forward labels only through 2024-06-28, applies Newey-West/FDR/year-stability/duplicate gates, and writes local evidence without opening any portfolio or live path.

**Tech Stack:** Python 3.12, pandas, existing `DatasetStore`/processed-bars loader, existing forward-return labels, existing Newey-West and Benjamini-Hochberg utilities, unittest/pytest.

---

## File Map

- Create `src/quant_robot/data/etf_point_in_time_universe.py`: official ETF lifecycle loading and trailing-only signal-date eligibility.
- Create `src/quant_robot/factors/etf_skip_momentum.py`: two pure skip-return factors, the frozen FIP diagnostic, and historical reference exposures.
- Create `src/quant_robot/ops/cn_etf_skip_momentum_prescreen.py`: data assembly, IC/shape/year/correlation gates, rendering, and artifact writing.
- Create `scripts/run_cn_etf_skip_momentum_prescreen.py`: callable CLI with frozen defaults.
- Create `configs/cn_etf_skip_momentum_prescreen_20260716.json`: auditable frozen inputs and thresholds.
- Create `tests/unit/test_etf_point_in_time_universe.py`: lifecycle and trailing eligibility tests.
- Create `tests/unit/test_etf_skip_momentum_factors.py`: formula, causality, and FIP parity tests.
- Create `tests/unit/test_cn_etf_skip_momentum_prescreen.py`: statistical and duplicate gate tests.
- Create `tests/unit/test_cn_etf_skip_momentum_prescreen_cli.py`: end-to-end local artifact test and holdout exclusion.
- Modify `docs/research/CURRENT_RESEARCH_INDEX.md`: final result and next scheduler action only after the real run.
- Create `docs/research/cn_etf_skip_momentum_prescreen_2026-07-16.md`: concise real-evidence report.

### Task 1: Point-In-Time ETF Eligibility

**Files:**
- Create: `tests/unit/test_etf_point_in_time_universe.py`
- Create: `src/quant_robot/data/etf_point_in_time_universe.py`

- [ ] **Step 1: Write the failing lifecycle and trailing-data tests**

Create synthetic bars for listed, future-listed, delisted, stale, short-history, and liquid assets. Assert the wished-for API:

```python
from quant_robot.data.etf_point_in_time_universe import (
    EtfEligibilityPolicy,
    build_point_in_time_etf_eligibility,
)

eligible = build_point_in_time_etf_eligibility(
    bars,
    lifecycle,
    policy=EtfEligibilityPolicy(
        min_prior_observations=3,
        liquidity_window=3,
        min_trailing_median_amount=5_000_000,
        max_stale_rate=0.05,
        max_abs_return=0.20,
    ),
)

assert eligible.loc[key("listed_liquid", "2024-01-05"), "eligible"]
assert not eligible.loc[key("future_listed", "2024-01-05"), "eligible"]
assert not eligible.loc[key("delisted", "2024-01-08"), "eligible"]
assert not eligible.loc[key("short_history", "2024-01-05"), "eligible"]
```

Also append a future row with an extreme amount and assert that eligibility on every earlier date is unchanged.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_etf_point_in_time_universe.py -q
```

Expected: collection fails because `quant_robot.data.etf_point_in_time_universe` does not exist.

- [ ] **Step 3: Implement the minimal eligibility module**

Implement:

```python
@dataclass(frozen=True)
class EtfEligibilityPolicy:
    min_prior_observations: int = 252
    liquidity_window: int = 20
    min_trailing_median_amount: float = 5_000_000.0
    max_stale_rate: float = 0.05
    max_abs_return: float = 0.20

def load_official_etf_lifecycle(metadata_root: str | Path) -> pd.DataFrame:
    ...

def build_point_in_time_etf_eligibility(
    bars: pd.DataFrame,
    lifecycle: pd.DataFrame,
    *,
    policy: EtfEligibilityPolicy = EtfEligibilityPolicy(),
) -> pd.DataFrame:
    ...
```

Requirements:

- Fail on missing or duplicated lifecycle symbols.
- Keep official `is_etf=True` only.
- Parse list/delist dates and reject reversed lifecycles.
- Compute `prior_observations` with cumulative count shifted by one session.
- Compute trailing median amount and stale rate with current and past rows only.
- Emit one row per input bar with `eligible` and explicit reason booleans.

- [ ] **Step 4: Run the tests and verify GREEN**

Run the Task 1 test file. Expected: all tests pass.

- [ ] **Step 5: Commit Task 1**

```powershell
git add src/quant_robot/data/etf_point_in_time_universe.py tests/unit/test_etf_point_in_time_universe.py
git commit -m "feat: add point-in-time ETF eligibility"
```

### Task 2: Frozen Skip-Momentum Factors

**Files:**
- Create: `tests/unit/test_etf_skip_momentum_factors.py`
- Create: `src/quant_robot/factors/etf_skip_momentum.py`

- [ ] **Step 1: Write failing formula, causality, and parity tests**

Assert exact names:

```python
ETF_SKIP_MOMENTUM_FACTOR_NAMES = (
    "etf_skip5_momentum_60",
    "etf_skip20_momentum_120",
    "fip_smooth_momentum_skip5_60",
)
```

For one asset, verify the pure formulas against direct price ratios. Append a future price spike and assert every earlier factor row is unchanged. On a small multi-asset sample, compare the new FIP diagnostic against:

```python
compute_information_discreteness_factors(
    bars,
    factor_names=("fip_smooth_momentum_skip5_60",),
)
```

Assert matching non-null values within numerical tolerance.

- [ ] **Step 2: Run the tests and verify RED**

Expected: missing module or missing function failure.

- [ ] **Step 3: Implement frozen candidates and references**

Implement:

```python
def compute_etf_skip_momentum_factors(
    bars: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    ...

def compute_etf_price_rotation_reference_factors(bars: pd.DataFrame) -> pd.DataFrame:
    ...
```

Pure candidate formulas are immutable:

```python
skip5_60 = price.shift(5) / price.shift(65) - 1.0
skip20_120 = price.shift(20) / price.shift(140) - 1.0
```

Reference output must contain only the eight preregistered names. Compute market-relative strength as same-date momentum minus the market median; do not call the full technical-factor expansion.

- [ ] **Step 4: Run factor tests and existing information-discreteness tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_etf_skip_momentum_factors.py tests\unit\test_information_discreteness_factors.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 2**

```powershell
git add src/quant_robot/factors/etf_skip_momentum.py tests/unit/test_etf_skip_momentum_factors.py
git commit -m "feat: add frozen ETF skip-momentum factors"
```

### Task 3: Statistical Prescreen And Duplicate Gate

**Files:**
- Create: `tests/unit/test_cn_etf_skip_momentum_prescreen.py`
- Create: `src/quant_robot/ops/cn_etf_skip_momentum_prescreen.py`
- Create: `configs/cn_etf_skip_momentum_prescreen_20260716.json`

- [ ] **Step 1: Write failing statistical gate tests**

Build synthetic factor/label/reference frames and assert:

```python
result = summarize_cn_etf_skip_momentum_prescreen(
    factors,
    labels,
    references,
    horizons=(5,),
    min_cross_section=20,
    min_ic_observations=20,
    min_usable_years=3,
)
```

Cases:

- A stable independent signal passes IC, Newey-West, FDR, quintile, year, and duplicate gates.
- A rank-equivalent signal with correlation 1.0 is blocked as `historical_reference_duplicate`.
- A one-year-only signal is blocked as `usable_years_below_threshold`.
- A non-significant signal remains rejected after FDR.
- Every output row has `promotion_allowed=False` and the packet has `portfolio_grid_allowed=False`.

- [ ] **Step 2: Run the tests and verify RED**

Expected: missing prescreen module.

- [ ] **Step 3: Implement summary and decision logic**

Use existing utilities:

```python
from quant_robot.ops.factor_statistical_reality_check import benjamini_hochberg
from quant_robot.research.overlap import newey_west_mean_test
```

For each candidate and horizon:

1. Merge by `date`, `asset_id`, and `market`.
2. Require the frozen minimum cross-section.
3. Compute daily Spearman IC and quintile means.
4. Apply Newey-West lag `horizon - 1` to daily IC.
5. Compute yearly IC rows and year-positive rate.
6. Compute top-quintile turnover.
7. Apply BH FDR across all result rows.
8. Add mean daily cross-sectional correlation against each historical reference.
9. Apply every threshold from the design without fallback or rescue behavior.

The packet must include:

```python
{
    "stage": "cn_etf_skip_momentum_prescreen",
    "historical_stop_loss_review": {...},
    "data_window": {...},
    "holdout_policy": {"final_holdout_included": False, ...},
    "results": [...],
    "decision": {
        "research_lead_count": ...,
        "walk_forward_allowed": ...,
        "portfolio_grid_allowed": False,
        "promotion_allowed": False,
        "next_action": ...,
    },
    "live_boundary_allowed": False,
}
```

- [ ] **Step 4: Implement real-data assembly**

`build_cn_etf_skip_momentum_prescreen` must:

- Load `CN_ETF` bars through `load_processed_bars`.
- Reject `analysis_end_date >= 2026-01-01` unconditionally.
- Load official fund metadata from the same data root.
- Build factors and labels on the complete pre-filter history.
- Apply point-in-time eligibility only when selecting signal rows.
- Preserve exact factor, label, eligibility, and metadata row counts.

- [ ] **Step 5: Add the frozen JSON config**

The config must contain exact candidate names, references, dates, horizons, lag, eligibility policy, statistical thresholds, output directory, `primary_market=CN_ETF`, and all live boundaries set false.

- [ ] **Step 6: Run prescreen tests and JSON validation**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_cn_etf_skip_momentum_prescreen.py -q
.venv\Scripts\python.exe -m json.tool configs\cn_etf_skip_momentum_prescreen_20260716.json
```

Expected: all tests pass and JSON is valid.

- [ ] **Step 7: Commit Task 3**

```powershell
git add src/quant_robot/ops/cn_etf_skip_momentum_prescreen.py tests/unit/test_cn_etf_skip_momentum_prescreen.py configs/cn_etf_skip_momentum_prescreen_20260716.json
git commit -m "feat: add CN ETF skip-momentum prescreen"
```

### Task 4: CLI And Artifact Contract

**Files:**
- Create: `tests/unit/test_cn_etf_skip_momentum_prescreen_cli.py`
- Create: `scripts/run_cn_etf_skip_momentum_prescreen.py`

- [ ] **Step 1: Write failing CLI test**

Write a temporary processed-bars root plus official fund-basic Parquet. Call the Python CLI function with shortened thresholds and assert it writes:

- `cn_etf_skip_momentum_prescreen.json`
- `cn_etf_skip_momentum_prescreen.md`
- `cn_etf_skip_momentum_prescreen_results.csv`
- `cn_etf_skip_momentum_ic_observations.csv`
- `cn_etf_skip_momentum_yearly_ic.csv`
- `cn_etf_skip_momentum_reference_correlations.csv`

Include synthetic 2026 bars and assert no 2026 signal date appears in any output.

- [ ] **Step 2: Run the CLI test and verify RED**

Expected: missing script/function failure.

- [ ] **Step 3: Implement CLI and artifact writers**

Follow the repository bootstrap pattern and expose:

```python
def run_cn_etf_skip_momentum_prescreen_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    ...
```

The command prints only a compact JSON summary. It must not expose any flag that enables the 2026 holdout, portfolio grid, promotion, paper signal, broker, account, or order paths.

- [ ] **Step 4: Run CLI and focused tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_etf_point_in_time_universe.py tests\unit\test_etf_skip_momentum_factors.py tests\unit\test_cn_etf_skip_momentum_prescreen.py tests\unit\test_cn_etf_skip_momentum_prescreen_cli.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 4**

```powershell
git add scripts/run_cn_etf_skip_momentum_prescreen.py tests/unit/test_cn_etf_skip_momentum_prescreen_cli.py
git commit -m "feat: add CN ETF skip-momentum CLI"
```

### Task 5: Real Prescreen And Evidence Decision

**Files:**
- Create local ignored artifacts under `data/reports/cn_etf_skip_momentum_prescreen_20260716`
- Create `docs/research/cn_etf_skip_momentum_prescreen_2026-07-16.md`
- Modify `docs/research/CURRENT_RESEARCH_INDEX.md`
- Modify `configs/research_family_scheduler_cn_etf.json` only under the zero-lead decision rule below

- [ ] **Step 1: Re-run the startup gate on the active branch**

```powershell
.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-etf-price-rotation-20260716
```

Expected: `status=ready`, `primary_market=CN_ETF`, no blockers.

- [ ] **Step 2: Run the frozen real prescreen**

```powershell
.venv\Scripts\python.exe scripts\run_cn_etf_skip_momentum_prescreen.py --config configs\cn_etf_skip_momentum_prescreen_20260716.json
```

Expected: completed or rejected evidence packet, never a promotion packet.

- [ ] **Step 3: Audit result integrity**

Confirm:

- Data ends no later than 2024-06-28.
- Final holdout included is false.
- Candidate count is exactly 3 and test count exactly 6.
- No candidate or threshold changed from the config.
- All duplicate correlations, yearly rows, and FDR values are present.

- [ ] **Step 4: Apply the preregistered decision**

If zero leads:

- Mark `cn_etf_price_rotation` `stop_lossed` with budget 0.
- Reallocate the closed family's 0.30 budget exactly: `cn_etf_liquidity_capacity` from 0.25 to 0.35, `cn_etf_volatility_regime` from 0.20 to 0.30, `cn_etf_flow_breadth_aggregation` from 0.15 to 0.20, and `cn_etf_fund_structure` from 0.10 to 0.15.
- Record that no retry, parameter rescue, portfolio grid, or walk-forward is allowed.

If leads exist:

- Freeze the smallest non-duplicate lead set and its SHA-256.
- Do not run walk-forward yet.
- Set the next action to 2024-H2 through 2025 data backfill and freshness audit.

- [ ] **Step 5: Write the real evidence report and index update**

The report must state exact metrics, rejected rows, duplicate blockers, data staleness, and the next scheduler action. It must not claim profitability.

- [ ] **Step 6: Commit Task 5**

```powershell
git add docs/research/cn_etf_skip_momentum_prescreen_2026-07-16.md docs/research/CURRENT_RESEARCH_INDEX.md configs/research_family_scheduler_cn_etf.json
git commit -m "docs: close CN ETF skip-momentum prescreen"
```

Only include the scheduler path when it actually changed.

### Task 6: Final Verification

**Files:**
- Verify all modified files

- [ ] **Step 1: Run focused and related suites**

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_etf_point_in_time_universe.py tests\unit\test_etf_skip_momentum_factors.py tests\unit\test_cn_etf_skip_momentum_prescreen.py tests\unit\test_cn_etf_skip_momentum_prescreen_cli.py tests\unit\test_information_discreteness_factors.py tests\unit\test_quant_pm_startup_gate.py -q
```

- [ ] **Step 2: Run complete repository regression**

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
```

- [ ] **Step 3: Run repository gates**

```powershell
.venv\Scripts\python.exe -m compileall -q src scripts tests
.venv\Scripts\python.exe scripts\run_project_audit.py --json
.venv\Scripts\python.exe scripts\run_maintainability_audit.py --fail-on-regression
git diff --check
git status --short --branch
```

Expected: tests, compilation, project audit, and maintainability baseline pass; worktree is clean after the final commit.

- [ ] **Step 4: Preserve branch without push**

Office policy forbids push. Keep `codex/factor-batch-cn-etf-price-rotation-20260716` locally for later laptop integration.
