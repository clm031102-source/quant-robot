# Round143 CN Stock Tradeability Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable A-share tradeability gate that turns bars plus `stock_basic` metadata into buy/sell eligibility flags before factor mining or promotion.

**Architecture:** Add one focused ops module that computes deterministic flags from existing local data: zero-volume/suspended proxy, limit-up/limit-down proxy, ST/name risk, new-listing age, inactive/delist risk, and board-permission blocks. Add a small CLI to write a JSON/Markdown report, then update the Round142 quality gate evidence without claiming that proxy-only controls equal official exchange feeds.

**Tech Stack:** Python stdlib, pandas, existing `unittest`, JSON/Markdown artifacts.

---

### Task 1: Unit Tests First

**Files:**
- Create: `tests/unit/test_cn_stock_tradeability_gate.py`
- Create: `tests/unit/test_cn_stock_tradeability_gate_cli.py`

- [ ] **Step 1: Write tests**

The tests must prove:

- ST names are blocked by `st_flag_filter`.
- New listings younger than the configured age are blocked.
- BSE/STAR/ChiNext names are blocked unless permission flags allow them.
- Limit-up-like execution bars block buys but not sells.
- Limit-down-like execution bars block sells but not buys.
- Zero-volume or zero-amount rows are treated as suspended/invalid execution rows.
- The CLI writes `cn_stock_tradeability_gate.json` and `.md`.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m unittest tests.unit.test_cn_stock_tradeability_gate tests.unit.test_cn_stock_tradeability_gate_cli`

Expected: import errors because the module and CLI do not exist.

### Task 2: Module And CLI

**Files:**
- Create: `src/quant_robot/ops/cn_stock_tradeability_gate.py`
- Create: `scripts/run_cn_stock_tradeability_gate.py`

- [ ] **Step 1: Implement policy and flag builder**

Expose:

- `CNStockTradeabilityPolicy`
- `build_cn_stock_tradeability_frame(bars, stock_basic=None, policy=None)`
- `build_cn_stock_tradeability_report(bars, stock_basic=None, policy=None)`
- `render_markdown(report)`

- [ ] **Step 2: Implement CLI**

The CLI should read CSV or Parquet bars and metadata, run the report, and write JSON/Markdown artifacts.

- [ ] **Step 3: Verify GREEN**

Run the two new tests and `py_compile`.

### Task 3: Quality Gate Evidence Update

**Files:**
- Modify: `configs/factor_mining_quality_gate_cn_stock.json`
- Modify: `docs/research/cn_stock_factor_mining_quality_gate_round142_2026-06-22.md` or create a Round143 report.

- [ ] **Step 1: Update control statuses conservatively**

Mark metadata-backed controls as implemented only when the new module covers them directly. Keep proxy-only controls partial.

- [ ] **Step 2: Generate a local sample report**

Run the CLI on a local bars shard plus stock_basic metadata and write output under `data/reports/cn_stock_tradeability_gate_round143`.

- [ ] **Step 3: Verify the quality gate reflects improved evidence**

Run `python scripts/run_factor_mining_quality_gate.py --config configs/factor_mining_quality_gate_cn_stock.json --output-dir data/reports/factor_mining_quality_gate_round143`.
