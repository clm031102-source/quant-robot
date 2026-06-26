# Round103 Bollinger Lead Dedup Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repeatable Round103 audit that de-duplicates the Round102 `bollinger_reversal_lowvol_liquid_20` research lead before any heavier portfolio walk-forward work.

**Architecture:** A focused ops module computes lead-versus-candidate daily cross-sectional Spearman correlations from the existing capacity-safe price-volume factor frame and consumes the Round102 prescreen report as lead evidence. A thin CLI writes JSON, Markdown, and CSV outputs. Research docs and the startup gate record the three-round review and next direction.

**Tech Stack:** Python, pandas, unittest, existing `capacity_safe_price_volume_prescreen` loaders and factor formulas.

---

### Task 1: Lead Dedup Unit Tests

**Files:**
- Create: `tests/unit/test_capacity_safe_price_volume_lead_dedup.py`
- Create: `src/quant_robot/ops/capacity_safe_price_volume_lead_dedup.py`

- [ ] **Step 1: Write the failing summarizer test**

```python
def test_summarizes_lead_correlations_and_classifies_redundancy(self) -> None:
    dates = pd.bdate_range("2025-01-02", periods=6)
    rows = []
    for date in dates:
        for asset_idx in range(40):
            asset_id = f"{asset_idx:06d}.SZ"
            lead = float(asset_idx)
            rows.append({"date": date, "asset_id": asset_id, "market": "CN", "factor_name": "lead", "factor_value": lead, "amount": 1.0, "adv20_amount": 1.0})
            rows.append({"date": date, "asset_id": asset_id, "market": "CN", "factor_name": "duplicate", "factor_value": lead * 2.0, "amount": 1.0, "adv20_amount": 1.0})
            rows.append({"date": date, "asset_id": asset_id, "market": "CN", "factor_name": "independent", "factor_value": float((asset_idx * 7) % 40), "amount": 1.0, "adv20_amount": 1.0})
    result = summarize_capacity_safe_price_volume_lead_dedup(pd.DataFrame(rows), lead_factor_name="lead", min_cross_section=20)
    classifications = {row["factor_name"]: row["redundancy_class"] for row in result["correlations"]}
    self.assertEqual(classifications["duplicate"], "highly_redundant")
    self.assertEqual(classifications["independent"], "unique")
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.unit.test_capacity_safe_price_volume_lead_dedup`

Expected: import failure because `capacity_safe_price_volume_lead_dedup` does not exist.

- [ ] **Step 3: Implement minimal summarizer**

Create `summarize_capacity_safe_price_volume_lead_dedup()` with date normalization, lead frame extraction, per-candidate date-by-date Spearman correlation, redundancy classification, summary counts, promotion policy blocking, and Markdown rendering.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.unit.test_capacity_safe_price_volume_lead_dedup`

Expected: test passes.

### Task 2: Build Function and Prescreen Evidence Guard

**Files:**
- Modify: `tests/unit/test_capacity_safe_price_volume_lead_dedup.py`
- Modify: `src/quant_robot/ops/capacity_safe_price_volume_lead_dedup.py`

- [ ] **Step 1: Write the failing build test**

```python
def test_build_confirms_prescreen_lead_and_blocks_promotion(self) -> None:
    bars = _synthetic_bars(days=90, assets=40, include_holdout=True)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "processed"
        DatasetStore(root).write_frame(bars[bars["date"].dt.year == 2025], "bars", {"frequency": "1d", "market": "CN", "year": "2025"})
        DatasetStore(root).write_frame(bars[bars["date"].dt.year == 2026], "bars", {"frequency": "1d", "market": "CN", "year": "2026"})
        prescreen = {"results": [{"factor_name": "bollinger_reversal_lowvol_liquid_20", "horizon": 20, "research_lead": True}], "summary": {"research_lead_count": 1}}
        result = build_capacity_safe_price_volume_lead_dedup(bars_roots=[root], prescreen_report=prescreen, analysis_end_date="2025-12-31", sample_every_n_dates=2, min_cross_section=20)
    self.assertTrue(result["lead_evidence"]["prescreen_research_lead"])
    self.assertFalse(result["promotion_policy"]["promotion_allowed"])
    self.assertFalse(result["holdout_policy"]["final_holdout_included"])
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.unit.test_capacity_safe_price_volume_lead_dedup`

Expected: failure because the build function is missing.

- [ ] **Step 3: Implement minimal build function**

Use `load_capacity_safe_bars()` and `compute_capacity_safe_price_volume_factors()` from the prescreen module. Filter the factor frame to sampled dates after factor computation. Attach data window and holdout policy.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.unit.test_capacity_safe_price_volume_lead_dedup`

Expected: both tests pass.

### Task 3: CLI Tests and Script

**Files:**
- Create: `tests/unit/test_capacity_safe_price_volume_lead_dedup_cli.py`
- Create: `scripts/run_capacity_safe_price_volume_lead_dedup.py`

- [ ] **Step 1: Write the failing CLI test**

```python
def test_cli_writes_json_markdown_and_correlation_csv(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "processed"
        output = Path(tmp) / "output"
        prescreen_path = Path(tmp) / "prescreen.json"
        DatasetStore(root).write_frame(_synthetic_bars(), "bars", {"frequency": "1d", "market": "CN", "year": "2025"})
        prescreen_path.write_text(json.dumps({"results": [{"factor_name": "bollinger_reversal_lowvol_liquid_20", "horizon": 20, "research_lead": True}]}), encoding="utf-8")
        result = run_capacity_safe_price_volume_lead_dedup_cli(bars_roots=[root], prescreen_report=prescreen_path, output_dir=output, analysis_end_date="2025-12-31", sample_every_n_dates=2, min_cross_section=20)
    self.assertEqual(result["stage"], "capacity_safe_price_volume_lead_dedup")
    self.assertTrue((output / "capacity_safe_price_volume_lead_dedup.json").exists())
    self.assertTrue((output / "capacity_safe_price_volume_lead_dedup.md").exists())
    self.assertTrue((output / "capacity_safe_price_volume_lead_correlations.csv").exists())
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.unit.test_capacity_safe_price_volume_lead_dedup_cli`

Expected: import failure because the CLI script does not exist.

- [ ] **Step 3: Implement the CLI**

Follow the existing prescreen CLI pattern. Accept repeated `--bars-root`, `--prescreen-report`, `--output-dir`, `--analysis-start-date`, `--analysis-end-date`, `--lead-factor-name`, `--lead-horizon`, `--sample-every-n-dates`, `--min-cross-section`, and `--min-signal-date-amount`.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.unit.test_capacity_safe_price_volume_lead_dedup_cli`

Expected: test passes.

### Task 4: Real Round103 Run and Research Docs

**Files:**
- Create: `docs/research/cn_stock_capacity_safe_price_volume_lead_dedup_round103_2026-06-22.md`
- Create: `docs/research/cn_stock_round101_103_three_round_review_2026-06-22.md`

- [ ] **Step 1: Run real long-cycle audit**

Run:

```powershell
python scripts\run_capacity_safe_price_volume_lead_dedup.py --bars-root data\processed\cn_stock_long_history_2015_202306 --bars-root data\processed\office_desktop_20260616_combined_research --prescreen-report data\reports\capacity_safe_price_volume_prescreen_round102_20260622\capacity_safe_price_volume_prescreen.json --output-dir data\reports\capacity_safe_price_volume_lead_dedup_round103_20260622 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --sample-every-n-dates 5 --min-cross-section 30 --min-signal-date-amount 10000000
```

- [ ] **Step 2: Inspect JSON and Markdown output**

Check `summary`, `lead_evidence`, `next_direction`, and `holdout_policy`.

- [ ] **Step 3: Write research docs**

Record real output counts, redundancy verdict, blocker histogram, and Round104 direction.

### Task 5: Startup Gate and Verification

**Files:**
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Update startup config**

Set `source_audit` to the Round103 research doc, set `next_direction` from the Round103 JSON, and add confirmations for `round103_bollinger_lead_dedup_read` and `round101_103_three_round_review_read`.

- [ ] **Step 2: Update startup gate unit expectation**

Adjust expected source audit and next direction in `tests/unit/test_factor_mining_startup_gate_cli.py`.

- [ ] **Step 3: Run verification commands**

Run:

```powershell
python -m unittest tests.unit.test_capacity_safe_price_volume_preregistration tests.unit.test_capacity_safe_price_volume_preregistration_cli tests.unit.test_capacity_safe_price_volume_prescreen tests.unit.test_capacity_safe_price_volume_prescreen_cli tests.unit.test_capacity_safe_price_volume_lead_dedup tests.unit.test_capacity_safe_price_volume_lead_dedup_cli tests.unit.test_factor_mining_startup_gate_cli
python -m json.tool configs\factor_mining_startup_cn_stock.json > $null
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --confirm-start
python scripts\run_project_audit.py --json
python -m py_compile src\quant_robot\ops\capacity_safe_price_volume_lead_dedup.py scripts\run_capacity_safe_price_volume_lead_dedup.py
git diff --check
```

Expected: unit tests pass, startup gate clears, project audit passes, py_compile exits 0, and `git diff --check` has no actionable whitespace errors beyond existing CRLF warnings.
