# CN ETF Fund-Structure Public-Source Readiness Implementation Plan

> **Execution:** Follow test-driven development task by task. Generated market data and reports stay outside Git.

**Goal:** Replace the inaccessible Tushare ETF share/NAV endpoint with an audited public-source path and decide, without reading labels, whether the fund-structure family is source-ready.

**Architecture:** Keep provider HTTP/parsing behavior in a small adapter, acquisition/resume and normalization in a data-ingest module, and coverage/leakage decisions in a pure readiness operation. A strict CLI binds the frozen config, bar authority, generated manifests, and output artifacts.

**Tech Stack:** Python 3.12, pandas, requests with bounded urllib3 retries, openpyxl for SZSE workbooks, standard-library JSON/hash/regex/concurrency, unittest.

---

### Task 1: Freeze Provider Parsers And Point-In-Time Normalization

**Files:**
- Create: `src/quant_robot/data/adapters/public_cn_etf_fund_structure.py`
- Create: `tests/unit/test_public_cn_etf_fund_structure_adapter.py`

- [ ] Write failing tests for SSE JSON, SZSE workbook, Eastmoney JS, malformed schemas, and bounded retry categories.
- [ ] Implement pure parsing helpers before live HTTP methods.
- [ ] Normalize six-digit symbols, dates, shares, unit NAV, source names, and response hashes.
- [ ] Require strictly dated observations and reject duplicate source rows.
- [ ] Run focused tests and commit.

### Task 2: Build Resumable Acquisition And Canonical Dataset

**Files:**
- Create: `src/quant_robot/data/ingest/public_cn_etf_fund_structure.py`
- Create: `tests/unit/test_public_cn_etf_fund_structure_ingest.py`

- [ ] Write failing resume, date-window, symbol-scope, merge, and next-session `known_from` tests.
- [ ] Implement SSE per-session, SZSE six-month-chunk, and Eastmoney per-symbol manifests.
- [ ] Join only to analysis-window bar-authority assets and closes.
- [ ] Derive scale and premium/discount only from positive finite inputs.
- [ ] Persist yearly canonical Parquet partitions plus request and quality summaries.
- [ ] Run focused tests and commit.

### Task 3: Add The Pure Readiness Gate And Strict CLI

**Files:**
- Create: `src/quant_robot/ops/cn_etf_fund_structure_source_readiness.py`
- Create: `scripts/run_cn_etf_fund_structure_source_readiness.py`
- Create: `tests/unit/test_cn_etf_fund_structure_source_readiness.py`
- Create: `tests/unit/test_run_cn_etf_fund_structure_source_readiness.py`
- Create: `configs/cn_etf_fund_structure_source_readiness_20260728.json`

- [ ] Write failing gate tests for combined/every-exchange coverage, NAV intersection, positivity, duplicate rows, PIT lag, holdout access, and every downstream boundary.
- [ ] Implement deterministic result packets and JSON/Markdown/CSV artifact writing.
- [ ] Freeze paths, dates, thresholds, provider concurrency, retries, and disabled execution boundaries in config.
- [ ] Make the CLI validate the config exactly and fail closed on drift.
- [ ] Run focused tests and commit.

### Task 4: Run The Real Backfill And Readiness Audit

- [ ] Re-run the Quant PM startup gate on the task branch.
- [ ] Execute the public-source CLI with resume enabled.
- [ ] Inspect request failures and retry only transient categories.
- [ ] Run the readiness gate on the completed normalized dataset.
- [ ] Re-run the result-only step and require deterministic result hashes.
- [ ] Record exact row, asset, session, exchange, NAV, scale, and premium/discount coverage.

### Task 5: Close Governance And Continue The Best Evidence Path

**Files:**
- Create: `docs/research/cn_etf_fund_structure_source_readiness_2026-07-28.md`
- Modify: `configs/research_family_scheduler_cn_etf.json`
- Modify: `tests/unit/test_cn_etf_volatility_scheduler_closeout.py`
- Modify: `docs/research/CURRENT_RESEARCH_INDEX.md`

- [ ] If ready, authorize only a later preregistration task with all factor/performance/live boundaries false.
- [ ] If blocked, record exact blockers, retain zero budget, and rotate to the next orthogonal source review.
- [ ] Run focused tests, full discovery, compileall, project audit, maintainability audit, Git diff check, and safe-sync audit.
- [ ] Review the entire diff for accidental data, secrets, holdout reads, or unsupported profitability claims.
- [ ] Commit and push the task branch; integrate only after merged-tree verification passes.
