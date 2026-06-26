# Round88 Tushare Financial Profitability PIT Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repeatable readiness audit that blocks true profitability-factor mining unless local Tushare financial statement / financial-indicator inputs exist with point-in-time date fields.

**Architecture:** Create a small ops module that inspects configured local roots and reports whether financial datasets and required PIT columns are available. Add a CLI wrapper and a Round88 research report; do not build profitability factors until this audit passes.

**Tech Stack:** Python, pandas, pathlib, unittest, existing repository script bootstrap pattern, Markdown research documentation.

---

### Task 1: Readiness Audit Module

**Files:**
- Create: `src/quant_robot/ops/tushare_financial_pit_readiness.py`
- Test: `tests/unit/test_tushare_financial_pit_readiness.py`

- [ ] **Step 1: Write failing tests**

Create tests for:

```python
def test_blocks_when_only_daily_basic_columns_exist():
    result = audit_tushare_financial_pit_readiness([daily_basic_root])
    assert result["summary"]["passes"] is False
    assert "missing_financial_statement_or_indicator_dataset" in result["summary"]["blockers"]
```

```python
def test_passes_when_financial_dataset_has_pit_dates_and_profitability_fields():
    result = audit_tushare_financial_pit_readiness([root_with_financial_indicator])
    assert result["summary"]["passes"] is True
    assert result["summary"]["pit_ready_datasets"] == 1
```

Expected red run:

```powershell
python -m unittest tests.unit.test_tushare_financial_pit_readiness
```

Expected: import failure or missing function failure.

- [ ] **Step 2: Implement minimal audit module**

The module should expose:

```python
FINANCIAL_DATASET_HINTS = ("fina", "financial", "indicator", "income", "balancesheet", "cashflow", "profit")
PIT_DATE_COLUMNS = ("ann_date", "f_ann_date", "end_date", "report_date")
PROFITABILITY_COLUMNS = ("roe", "roa", "grossprofit_margin", "netprofit_margin", "netprofit_yoy", "or_yoy", "ocfps", "cfps")

def audit_tushare_financial_pit_readiness(roots: Iterable[str | Path]) -> dict[str, Any]:
    ...

def render_tushare_financial_pit_readiness_markdown(result: dict[str, Any]) -> str:
    ...

def write_tushare_financial_pit_readiness(output_dir: str | Path, result: dict[str, Any]) -> None:
    ...
```

The audit passes only when at least one dataset-like path has both a PIT date column and at least one profitability column.

- [ ] **Step 3: Run unit tests green**

```powershell
python -m unittest tests.unit.test_tushare_financial_pit_readiness
```

Expected: all tests pass.

### Task 2: CLI Wrapper

**Files:**
- Create: `scripts/run_tushare_financial_pit_readiness.py`
- Test: `tests/unit/test_tushare_financial_pit_readiness_cli.py`

- [ ] **Step 1: Write failing CLI test**

Test that the CLI reads two roots, writes JSON and Markdown, and returns a failed readiness packet for daily-basic-only roots.

- [ ] **Step 2: Implement CLI**

Use repository bootstrap style:

```python
try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()
```

Arguments:

- `--root`, repeatable;
- `--output-dir`, default `data/reports/tushare_financial_pit_readiness`;
- `--allow-not-ready`, so the research workflow can write a blocking report without failing the whole session.

- [ ] **Step 3: Run CLI tests green**

```powershell
python -m unittest tests.unit.test_tushare_financial_pit_readiness_cli
```

Expected: all tests pass.

### Task 3: Run Round88 Audit And Report

**Files:**
- Create: `docs/research/cn_stock_tushare_financial_profitability_pit_readiness_round88_2026-06-21.md`
- Generated ignored output: `data/reports/tushare_financial_pit_readiness_round88_20260621`

- [ ] **Step 1: Run audit on current authority roots**

```powershell
python scripts\run_tushare_financial_pit_readiness.py `
  --root data\processed\cn_stock_long_history_2015_202306 `
  --root data\processed\office_desktop_20260617_daily_basic_factor_inputs `
  --output-dir data\reports\tushare_financial_pit_readiness_round88_20260621 `
  --allow-not-ready
```

Expected: writes readiness JSON/Markdown. Current expected status is not ready because local roots contain bars, daily_basic factor_inputs, and moneyflow_inputs, but no financial statement / fina_indicator dataset.

- [ ] **Step 2: Write report**

Record:

- local datasets found;
- whether PIT date fields exist;
- whether profitability fields exist;
- decision on whether to mine profitability factors now;
- exact next data-ingestion work if blocked.

### Task 4: Verification

**Files:**
- Test: focused unit tests and project audit

- [ ] **Step 1: Run focused tests**

```powershell
python -m unittest tests.unit.test_tushare_financial_pit_readiness tests.unit.test_tushare_financial_pit_readiness_cli tests.unit.test_factor_mining_startup_gate_cli tests.unit.test_project_audit
```

Expected: all tests pass.

- [ ] **Step 2: Run project audit**

```powershell
python scripts\run_project_audit.py --json
```

Expected: `summary.passes=true` and no forbidden hits.

- [ ] **Step 3: Check diff hygiene**

```powershell
git diff --check
```

Expected: no whitespace errors; Windows LF/CRLF warnings are acceptable.
