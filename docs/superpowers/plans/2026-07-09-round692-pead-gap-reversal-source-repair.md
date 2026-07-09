# Round692 PEAD Gap Reversal Source Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pre-register and, if the gate clears, run a source-repair audit for PEAD gap-overreaction reversal on the expanded Round690 statement source without parameter or portfolio-grid expansion.

**Architecture:** Keep the research definition in a candidate-plan JSON first. If code is needed, add a narrow statement-source adapter that converts statement rows into the existing PEAD event-reaction input shape instead of rewriting the residual IC engine.

**Tech Stack:** Python, pandas, pytest, existing `quant_robot.ops.financial_pit_post_announcement_*` modules, existing CN stock candidate-plan gate.

---

## File Structure

- Create `configs/factor_mining_candidate_plan_round692_pead_gap_reversal_source_repair_20260709.json`: preregister source-repair candidates and controls.
- Create `docs/research/cn_stock_round692_pead_gap_reversal_source_repair_candidate_plan_gate_2026-07-09.md`: lightweight gate report.
- Modify `docs/research/CURRENT_RESEARCH_INDEX.md`: append Round692 candidate-plan evidence.
- Test `tests/unit/test_financial_pit_post_announcement_gap_reversal_statement_source.py`: prove statement rows can be adapted without same-day event trading.
- Modify `src/quant_robot/ops/financial_pit_post_announcement_drift_preregistration.py`: add optional statement-source loading helper only if the existing `fina_indicator` loader cannot read statement roots.
- Modify `src/quant_robot/ops/financial_pit_post_announcement_drift_matrix_label_smoke.py`: reuse the adapted financial frame for factor matrix construction.
- Modify `scripts/run_financial_pit_post_announcement_gap_reversal_residual_prescreen.py`: add a CLI flag such as `--financial-input-kind statement` only after tests fail for the missing behavior.

## Task 1: Candidate Plan Gate

**Files:**
- Create: `configs/factor_mining_candidate_plan_round692_pead_gap_reversal_source_repair_20260709.json`
- Create: `docs/research/cn_stock_round692_pead_gap_reversal_source_repair_candidate_plan_gate_2026-07-09.md`
- Modify: `docs/research/CURRENT_RESEARCH_INDEX.md`

- [x] **Step 1: Write the candidate plan JSON**

Use five preregistered `stmt_pead_*` candidates. Set every candidate's `portfolio_backtest_allowed` and `promotion_allowed` to `false`. Include Round223/Round225 as prior evidence and Round690/Round691 as current source and failure context.

- [x] **Step 2: Run the candidate plan gate**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round692_pead_gap_reversal_source_repair_20260709.json --output-dir data\reports\round692_pead_gap_reversal_source_repair_candidate_plan_gate_20260709
```

Expected: `status` is `research_ready`, `candidate_plan_gate_cleared` is `true`, `portfolio_grid_allowed` is `false`, and `promotion_allowed` is `false`.

- [x] **Step 3: Document the gate result**

Write a concise report with startup gate status, manifest warnings, candidate count, complete control areas, and the explicit blocked actions.

- [ ] **Step 4: Commit candidate-plan artifacts**

Run:

```powershell
git add configs\factor_mining_candidate_plan_round692_pead_gap_reversal_source_repair_20260709.json docs\research\cn_stock_round692_pead_gap_reversal_source_repair_candidate_plan_gate_2026-07-09.md docs\research\CURRENT_RESEARCH_INDEX.md docs\superpowers\plans\2026-07-09-round692-pead-gap-reversal-source-repair.md
git commit -m "Register Round692 PEAD gap reversal source repair"
```

## Task 2: Statement Source Adapter Test

**Files:**
- Create: `tests/unit/test_financial_pit_post_announcement_gap_reversal_statement_source.py`
- Modify after failing test: `src/quant_robot/ops/financial_pit_post_announcement_drift_preregistration.py`
- Modify after failing test: `src/quant_robot/ops/financial_pit_post_announcement_drift_matrix_label_smoke.py`

- [ ] **Step 1: Write the failing test**

Create a test that writes `processed/financial_statement_inputs` rows with `ann_date`, `end_date`, and `netprofit`, then calls the adapter expected by the implementation:

```python
def test_statement_source_adapter_creates_reaction_available_rows() -> None:
    frame = build_pead_statement_financial_frame(statement_rows, bars)
    assert not frame.empty
    assert {"ann_date", "end_date", "signal_date", "netprofit_yoy"}.issubset(frame.columns)
    assert (pd.to_datetime(frame["signal_date"]) > pd.to_datetime(frame["ann_date"])).all()
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_financial_pit_post_announcement_gap_reversal_statement_source.py -q
```

Expected: failure because `build_pead_statement_financial_frame` does not exist.

- [ ] **Step 3: Implement the minimal adapter**

Add `build_pead_statement_financial_frame(statement: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame`. It should:

- normalize dates and `asset_id`;
- derive `signal_date` as the first trade date strictly after `ann_date`;
- derive `available_date = signal_date`;
- derive `netprofit_yoy` from same-quarter year-over-year `netprofit` when enough history exists;
- drop rows without `ann_date`, `end_date`, `asset_id`, or valid `signal_date`.

- [ ] **Step 4: Run the focused test and confirm pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_financial_pit_post_announcement_gap_reversal_statement_source.py -q
```

Expected: pass.

## Task 3: CLI Wiring Test

**Files:**
- Modify: `scripts/run_financial_pit_post_announcement_gap_reversal_residual_prescreen.py`
- Test: `tests/unit/test_financial_pit_post_announcement_gap_reversal_statement_source.py`

- [ ] **Step 1: Add a failing CLI-level test**

Extend the test file so the CLI helper is called with `financial_input_kind="statement"` and a statement-root fixture.

- [ ] **Step 2: Run the focused CLI test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_financial_pit_post_announcement_gap_reversal_statement_source.py -q
```

Expected: failure because the CLI helper does not accept `financial_input_kind`.

- [ ] **Step 3: Add CLI support**

Add `--financial-input-kind` with choices `fina_indicator` and `statement`. Default remains `fina_indicator` so Round222/223 behavior stays unchanged.

- [ ] **Step 4: Run the focused CLI test and existing PEAD tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_financial_pit_post_announcement_gap_reversal_residual_prescreen.py tests\unit\test_financial_pit_post_announcement_gap_reversal_matrix_label_smoke.py tests\unit\test_financial_pit_post_announcement_gap_reversal_statement_source.py -q
```

Expected: all pass.

## Task 4: Real Round692 Prescreen

**Files:**
- Create: `docs/research/cn_stock_round692_pead_gap_reversal_source_repair_prescreen_2026-07-09.md`
- Modify: `docs/research/CURRENT_RESEARCH_INDEX.md`

- [ ] **Step 1: Run matrix/label smoke on the expanded statement source**

Run the statement-source path with final holdout excluded and output under `data\reports\round692_pead_gap_reversal_source_repair_matrix_label_smoke_20260709`.

Expected: no alignment violations; no final-holdout dates; label coverage above the configured threshold.

- [ ] **Step 2: Run residual IC prescreen only if smoke passes**

Run the residual prescreen with frozen 5-day horizon and output under `data\reports\round692_pead_gap_reversal_source_repair_residual_prescreen_20260709`.

Expected: report writes successfully. Promotion remains disabled even if research leads appear.

- [ ] **Step 3: Write the research report**

Record factor rows, aligned rows, test count, FDR lead count, neutral-gate pass count, research lead count, promotion allowed count, PIT alignment proof, and a decision. Carry forward manifest warnings.

- [ ] **Step 4: Commit implementation and report**

Run:

```powershell
git add src\quant_robot\ops\financial_pit_post_announcement_drift_preregistration.py src\quant_robot\ops\financial_pit_post_announcement_drift_matrix_label_smoke.py scripts\run_financial_pit_post_announcement_gap_reversal_residual_prescreen.py tests\unit\test_financial_pit_post_announcement_gap_reversal_statement_source.py docs\research\cn_stock_round692_pead_gap_reversal_source_repair_prescreen_2026-07-09.md docs\research\CURRENT_RESEARCH_INDEX.md
git commit -m "Add Round692 PEAD gap reversal statement-source prescreen"
```

## Task 5: Verification

**Files:**
- No new files.

- [ ] **Step 1: Run targeted tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_financial_pit_post_announcement_gap_reversal_residual_prescreen.py tests\unit\test_financial_pit_post_announcement_gap_reversal_matrix_label_smoke.py tests\unit\test_financial_pit_post_announcement_gap_reversal_statement_source.py -q
```

- [ ] **Step 2: Validate JSON and ignored outputs**

Run:

```powershell
.\.venv\Scripts\python.exe -m json.tool configs\factor_mining_candidate_plan_round692_pead_gap_reversal_source_repair_20260709.json > $null
git check-ignore -v data\reports\round692_pead_gap_reversal_source_repair_candidate_plan_gate_20260709\factor_mining_candidate_plan_gate.json
git check-ignore -v data\reports\round692_pead_gap_reversal_source_repair_residual_prescreen_20260709\financial_pit_post_announcement_gap_reversal_residual_prescreen.json
```

- [ ] **Step 3: Run git whitespace checks**

Run:

```powershell
git diff --check
git diff --cached --check
```

Expected: no whitespace errors.

## Self-Review

- Spec coverage: candidate-plan gate, source-repair boundary, statement-source adapter, prescreen, reporting, and verification are covered.
- Placeholder scan: no deferred sections or undefined follow-up work remain.
- Type consistency: candidate names, paths, and CLI flags are consistent across tasks.
