# CN ETF Liquidity-Capacity Prescreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a preregistered, point-in-time CN ETF liquidity-persistence prescreen that either freezes a statistically independent and capacity-feasible research lead or closes the liquidity-capacity family.

**Architecture:** Extract the existing pure cross-sectional statistics into one shared research engine while preserving the skip-momentum output contract. Add a focused factor module for three frozen liquidity mechanisms and a thin family wrapper that attaches historical stop-loss evidence, causal ADV20 capacity metrics, and scheduler decisions.

**Tech Stack:** Python 3.12, pandas, NumPy, existing processed-bars and ETF lifecycle loaders, existing forward-return labels, Newey-West and Benjamini-Hochberg utilities, unittest/pytest.

---

## File Map

- Create `src/quant_robot/research/cross_sectional_factor_prescreen.py`: shared IC, shape, yearly, FDR, turnover, and duplicate-correlation engine.
- Create `tests/unit/test_cross_sectional_factor_prescreen.py`: engine contract and duplicate/missing-reference tests.
- Modify `src/quant_robot/ops/cn_etf_skip_momentum_prescreen.py`: delegate pure statistics while preserving its public result.
- Modify `tests/unit/test_cn_etf_skip_momentum_prescreen.py`: parity guard for the delegated result.
- Create `src/quant_robot/factors/etf_liquidity_capacity.py`: frozen candidates, references, and ADV20.
- Create `tests/unit/test_etf_liquidity_capacity_factors.py`: exact formula and causality tests.
- Create `src/quant_robot/ops/cn_etf_liquidity_capacity_prescreen.py`: real-data assembly, capacity gate, family decision, artifacts, and Markdown.
- Create `tests/unit/test_cn_etf_liquidity_capacity_prescreen.py`: statistical plus capacity decisions.
- Create `scripts/run_cn_etf_liquidity_capacity_prescreen.py`: config-driven command entrypoint.
- Create `tests/unit/test_cn_etf_liquidity_capacity_prescreen_cli.py`: complete local artifact and holdout-boundary test.
- Create `configs/cn_etf_liquidity_capacity_prescreen_20260716.json`: frozen formulas, references, thresholds, capacity assumptions, and boundaries.
- Create `docs/research/cn_etf_liquidity_capacity_prescreen_2026-07-16.md`: real-evidence report.
- Modify `docs/research/CURRENT_RESEARCH_INDEX.md`: current decision and superseded legacy promotion note.
- Modify `configs/research_family_scheduler_cn_etf.json` only if the preregistered real-data decision requires it.

### Task 1: Shared Cross-Sectional Engine

**Files:**
- Create: `tests/unit/test_cross_sectional_factor_prescreen.py`
- Create: `src/quant_robot/research/cross_sectional_factor_prescreen.py`
- Modify: `src/quant_robot/ops/cn_etf_skip_momentum_prescreen.py`
- Modify: `tests/unit/test_cn_etf_skip_momentum_prescreen.py`

- [ ] **Step 1: Write the failing engine contract tests**

Use deterministic three-year synthetic frames and assert this interface:

```python
from quant_robot.research.cross_sectional_factor_prescreen import (
    CrossSectionalPrescreenThresholds,
    summarize_cross_sectional_factor_prescreen,
)

result = summarize_cross_sectional_factor_prescreen(
    factors,
    labels,
    references,
    candidate_names=("candidate",),
    reference_names=("reference",),
    horizons=(5,),
    thresholds=CrossSectionalPrescreenThresholds(
        min_cross_section=20,
        min_ic_observations=15,
        min_year_ic_observations=5,
        min_usable_years=3,
    ),
)
assert result["results"][0]["research_lead"]
```

Also assert rank-equivalent references add `historical_reference_duplicate`, missing named references add `historical_reference_evidence_incomplete`, and duplicate factor rows raise `ValueError`.

- [ ] **Step 2: Run the new test and verify RED**

Run `.venv\Scripts\python.exe -m pytest tests\unit\test_cross_sectional_factor_prescreen.py -q`.

Expected: import failure because the shared module does not exist.

- [ ] **Step 3: Implement the immutable threshold object and engine**

Define:

```python
@dataclass(frozen=True)
class CrossSectionalPrescreenThresholds:
    min_cross_section: int = 30
    min_ic_observations: int = 20
    min_year_ic_observations: int = 20
    min_usable_years: int = 3
    alpha: float = 0.05
    min_mean_rank_ic: float = 0.02
    min_icir: float = 0.30
    min_positive_ic_rate: float = 0.55
    min_quantile_monotonicity: float = 0.70
    max_top_quantile_turnover: float = 0.90
    min_positive_year_rate: float = 0.60
    max_abs_reference_correlation: float = 0.85
```

Move the existing normalization, daily Rank IC, quintile, Newey-West, year, turnover, reference-correlation, blocker, and sanitization-neutral calculations into `summarize_cross_sectional_factor_prescreen`. Return candidate/reference names, thresholds, summary counts, result rows, IC observations, yearly IC, reference correlations, and multiple-testing policy. Keep family names, Markdown, artifacts, safety text, and next actions outside this module.

- [ ] **Step 4: Delegate skip momentum to the shared engine**

Replace its internal statistical loop with:

```python
core = summarize_cross_sectional_factor_prescreen(
    factors,
    labels,
    references,
    candidate_names=candidate_names,
    reference_names=reference_names,
    horizons=horizons,
    thresholds=CrossSectionalPrescreenThresholds(
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_year_ic_observations=min_year_ic_observations,
        min_usable_years=min_usable_years,
        alpha=alpha,
        min_mean_rank_ic=min_mean_rank_ic,
        min_icir=min_icir,
        min_positive_ic_rate=min_positive_ic_rate,
        min_quantile_monotonicity=min_quantile_monotonicity,
        max_top_quantile_turnover=max_top_quantile_turnover,
        min_positive_year_rate=min_positive_year_rate,
        max_abs_reference_correlation=max_abs_reference_correlation,
    ),
)
```

Reattach the existing stage, historical review, decision names, safety boundaries, and Markdown without changing the JSON contract.

- [ ] **Step 5: Run shared and skip parity tests**

Run `.venv\Scripts\python.exe -m pytest tests\unit\test_cross_sectional_factor_prescreen.py tests\unit\test_cn_etf_skip_momentum_prescreen.py tests\unit\test_cn_etf_skip_momentum_prescreen_cli.py -q`.

Expected: all tests pass and skip momentum still blocks promotion and portfolio grids.

- [ ] **Step 6: Commit the shared engine**

Commit message: `refactor: share cross-sectional factor prescreen`.

### Task 2: Frozen Liquidity-Capacity Factors

**Files:**
- Create: `tests/unit/test_etf_liquidity_capacity_factors.py`
- Create: `src/quant_robot/factors/etf_liquidity_capacity.py`

- [ ] **Step 1: Write failing exact-formula tests**

Assert exact constants:

```python
ETF_LIQUIDITY_CAPACITY_FACTOR_NAMES = (
    "etf_amihud_improvement_5_60",
    "etf_amount_participation_breadth_20_60",
    "etf_amount_distribution_quality_20",
)
```

For one synthetic asset, calculate every terminal value directly from the design formulas and compare numerically. Append future extreme returns and amounts and assert all earlier factor and ADV20 rows remain byte-for-byte unchanged. Assert non-positive amount produces missing values rather than infinity.

- [ ] **Step 2: Run factor tests and verify RED**

Run `.venv\Scripts\python.exe -m pytest tests\unit\test_etf_liquidity_capacity_factors.py -q`.

Expected: missing module failure.

- [ ] **Step 3: Implement frozen candidates**

Expose three functions with the same keyword-only eligibility contract: `compute_etf_liquidity_capacity_factors(bars, *, eligible_keys=None)`, `compute_etf_liquidity_reference_factors(bars, *, eligible_keys=None)`, and `compute_etf_adv20(bars, *, eligible_keys=None)`. Each returns a `pd.DataFrame`; the first two use canonical factor columns, while ADV20 returns `date`, `asset_id`, `market`, and `adv20`.

Normalize required columns, sort by asset/date, compute each rolling series within assets, select eligible keys only after all trailing calculations, and emit canonical factor columns. Build the 13 exact references through `compute_basic_factors` with a direct requested subset.

- [ ] **Step 4: Run new and technical factor tests**

Run `.venv\Scripts\python.exe -m pytest tests\unit\test_etf_liquidity_capacity_factors.py tests\unit\test_factors.py -q`.

Expected: all tests pass.

- [ ] **Step 5: Commit frozen factors**

Commit message: `feat: add frozen ETF liquidity-capacity factors`.

### Task 3: Family Prescreen And Capacity Gate

**Files:**
- Create: `tests/unit/test_cn_etf_liquidity_capacity_prescreen.py`
- Create: `src/quant_robot/ops/cn_etf_liquidity_capacity_prescreen.py`
- Create: `configs/cn_etf_liquidity_capacity_prescreen_20260716.json`

- [ ] **Step 1: Write failing decision tests**

Build stable synthetic factor/label/reference frames plus ADV20. Assert an independent signal with top-quintile ADV20 above CNY 10 million passes only the research-lead gate. Assert the same signal is blocked with `top_quantile_capacity_below_threshold` when tenth-percentile ADV20 is below CNY 10 million, and with `top_quantile_capacity_evidence_missing` when capacity rows are absent. Assert every result keeps `promotion_allowed=False` and the packet keeps walk-forward, portfolio, paper, and live boundaries false.

- [ ] **Step 2: Run prescreen tests and verify RED**

Run `.venv\Scripts\python.exe -m pytest tests\unit\test_cn_etf_liquidity_capacity_prescreen.py -q`.

Expected: missing family prescreen module failure.

- [ ] **Step 3: Implement family summary and capacity attachment**

Call the shared engine, then merge each factor-horizon with labels and causal ADV20. Recreate valid daily quintiles using the same cross-section minimum, pool top-quintile ADV20 observations, and attach:

```python
{
    "top_quantile_adv20_observations": int(len(top_adv20)),
    "top_quantile_adv20_median_cny": float(top_adv20.median()),
    "top_quantile_adv20_p10_cny": float(top_adv20.quantile(0.10)),
    "position_notional_cny": 100000.0,
    "p10_one_way_participation_rate": float(100000.0 / top_adv20.quantile(0.10)),
    "max_one_way_participation_rate": 0.01,
}
```

Recompute `research_lead` after capacity blockers. Set `next_action` to `backfill_2024h2_2025_then_freeze_walk_forward` only when leads exist, otherwise `stop_loss_liquidity_capacity_and_rotate_scheduler`.

- [ ] **Step 4: Implement real-data assembly**

Load CN ETF bars and official lifecycle, fail for `analysis_end_date >= 2026-01-01`, build point-in-time eligibility, compute factors/references/ADV20 on full pre-end history, create lag-one forward returns, then summarize only the frozen analysis dates. Record data, eligibility, source, holdout, and legacy-quarantine evidence.

- [ ] **Step 5: Add frozen config and validate it**

The JSON must specify the three candidate names, 13 references, dates, horizons, lag, eligibility policy, all statistical thresholds, CNY 1 million portfolio, 10 positions, 1% maximum participation, exact zero-lead reallocation, output path, `primary_market=CN_ETF`, and every live permission false.

Run `.venv\Scripts\python.exe -m json.tool configs\cn_etf_liquidity_capacity_prescreen_20260716.json`.

Expected: valid JSON.

- [ ] **Step 6: Run family tests**

Run `.venv\Scripts\python.exe -m pytest tests\unit\test_cross_sectional_factor_prescreen.py tests\unit\test_etf_liquidity_capacity_factors.py tests\unit\test_cn_etf_liquidity_capacity_prescreen.py -q`.

Expected: all tests pass.

- [ ] **Step 7: Commit family prescreen**

Commit message: `feat: add CN ETF liquidity-capacity prescreen`.

### Task 4: Command And Artifact Contract

**Files:**
- Create: `tests/unit/test_cn_etf_liquidity_capacity_prescreen_cli.py`
- Create: `scripts/run_cn_etf_liquidity_capacity_prescreen.py`

- [ ] **Step 1: Write failing CLI test**

Create temporary processed CN ETF bars and official metadata, run a shortened config, and assert JSON, Markdown, result, IC, yearly IC, reference-correlation, and capacity CSV artifacts. Include 2026 input rows and assert no 2026 signal date or label observation appears. Assert an end date in 2026 raises `ValueError`.

- [ ] **Step 2: Run CLI test and verify RED**

Run `.venv\Scripts\python.exe -m pytest tests\unit\test_cn_etf_liquidity_capacity_prescreen_cli.py -q`.

Expected: missing script/function failure.

- [ ] **Step 3: Implement the config-driven command**

Expose `run_cn_etf_liquidity_capacity_prescreen_cli(config_path, output_dir=None)`. Follow the repository bootstrap pattern, map every config field explicitly, write artifacts through the ops module, and print only compact status/count/path JSON. Do not add flags for holdout, portfolios, paper, broker, accounts, orders, or live behavior.

- [ ] **Step 4: Run all focused tests**

Run `.venv\Scripts\python.exe -m pytest tests\unit\test_cross_sectional_factor_prescreen.py tests\unit\test_etf_liquidity_capacity_factors.py tests\unit\test_cn_etf_liquidity_capacity_prescreen.py tests\unit\test_cn_etf_liquidity_capacity_prescreen_cli.py tests\unit\test_cn_etf_skip_momentum_prescreen.py tests\unit\test_cn_etf_skip_momentum_prescreen_cli.py -q`.

Expected: all tests pass.

- [ ] **Step 5: Commit the command**

Commit message: `feat: add CN ETF liquidity-capacity CLI`.

### Task 5: Real Prescreen And Preregistered Decision

**Files:**
- Create ignored artifacts under `data/reports/cn_etf_liquidity_capacity_prescreen_20260716`.
- Create `docs/research/cn_etf_liquidity_capacity_prescreen_2026-07-16.md`.
- Modify `docs/research/CURRENT_RESEARCH_INDEX.md`.
- Modify `configs/research_family_scheduler_cn_etf.json` only when dictated by the frozen decision.

- [ ] **Step 1: Re-run the Quant PM startup gate**

Run `.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-batch-cn-etf-liquidity-capacity-20260716`.

Expected: ready, primary market CN_ETF, no blockers.

- [ ] **Step 2: Run the frozen real-data command**

Run `.venv\Scripts\python.exe scripts\run_cn_etf_liquidity_capacity_prescreen.py --config configs\cn_etf_liquidity_capacity_prescreen_20260716.json`.

Expected: a completed evidence packet with exactly three candidates, six tests, 13 references, capacity rows, and no promotion authorization.

- [ ] **Step 3: Audit evidence integrity**

Verify the source and analysis end no later than 2024-06-28, 2026 holdout absent, all frozen candidates/references present, FDR test count six, yearly rows present, capacity P10 present, and config hash recorded. Compare the current canonical legacy promotion report and record 270 blocked and zero paper-ready.

- [ ] **Step 4: Apply the frozen result rule**

For zero leads, stop-loss `cn_etf_liquidity_capacity`, set budget 0, add its failure blockers and forbidden rescue actions, and set active budgets exactly to volatility 0.35, flow breadth 0.35, fund structure 0.30. For one or more leads, leave scheduler budgets unchanged, freeze the smallest non-duplicate lead set, and require audited 2024-H2 through 2025 backfill before walk-forward.

- [ ] **Step 5: Write durable evidence**

The research report must contain exact metrics, capacity values, blockers, duplicate correlations, stale endpoint, legacy quarantine, scheduler action, and safety boundary. Update the current index with the superseding decision; do not rewrite historical reports.

- [ ] **Step 6: Commit real evidence**

Commit message: `docs: close CN ETF liquidity-capacity prescreen` for zero leads or `docs: freeze CN ETF liquidity-capacity leads` when leads exist.

### Task 6: Verification And Local Closeout

**Files:**
- Verify all modified files.

- [ ] **Step 1: Run focused and related tests**

Run all new tests plus ETF eligibility, skip momentum, technical factors, scheduler, startup-gate, and promotion-report tests.

- [ ] **Step 2: Run complete regression**

Run `.venv\Scripts\python.exe -m unittest discover -s tests`.

Expected: the complete suite passes.

- [ ] **Step 3: Run project gates**

Run compileall, `scripts\run_project_audit.py --json`, `scripts\run_maintainability_audit.py --fail-on-regression`, `git diff --check`, and inspect repository status.

Expected: compilation and both audits pass with no maintainability regression.

- [ ] **Step 4: Preserve the local branch**

Commit any final tracked evidence. Do not push from the office desktop. The worktree must be clean and the final response must report exact test/audit outcomes plus a next-conversation startup prompt aligned to the resulting scheduler direction.
