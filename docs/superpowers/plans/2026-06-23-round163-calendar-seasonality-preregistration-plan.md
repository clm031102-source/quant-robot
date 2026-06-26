# Round163 Calendar Seasonality Preregistration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rotate CN-stock mining away from failed moneyflow, tradeability-event, public-technical, price-volume shock, PIT event, and regime-temperature paths by pre-registering an ex-ante calendar-seasonality factor family for Round163.

**Architecture:** Add a focused preregistration module and CLI following the existing `cn_market_regime_temperature_preregistration` pattern. The module only writes candidate specs, controls, and promotion blockers; it does not run portfolio tests or promote factors before Round164 residual prescreen evidence.

**Tech Stack:** Python dataclasses, JSON/Markdown/CSV outputs, `unittest`, existing `scripts/bootstrap.py` import path setup.

---

### Task 1: Round163 Preregistration Tests

**Files:**
- Create: `tests/unit/test_cn_calendar_seasonality_preregistration.py`
- Create: `tests/unit/test_cn_calendar_seasonality_preregistration_cli.py`

- [ ] **Step 1: Write failing module tests**

```python
result = build_cn_calendar_seasonality_preregistration()
self.assertEqual(result["summary"]["candidate_count"], 8)
self.assertGreaterEqual(result["summary"]["family_count"], 6)
self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
self.assertIn("ex_ante_calendar_state", candidate["required_controls"])
self.assertIn("no_future_holiday_gap_lookup", candidate["required_controls"])
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `python -m unittest tests.unit.test_cn_calendar_seasonality_preregistration tests.unit.test_cn_calendar_seasonality_preregistration_cli`

Expected: FAIL because `quant_robot.ops.cn_calendar_seasonality_preregistration` and its CLI do not exist yet.

### Task 2: Round163 Preregistration Implementation

**Files:**
- Create: `src/quant_robot/ops/cn_calendar_seasonality_preregistration.py`
- Create: `scripts/run_cn_calendar_seasonality_preregistration.py`

- [ ] **Step 1: Implement the minimal module**

```python
@dataclass(frozen=True)
class CNCalendarSeasonalityCandidateSpec:
    factor_name: str
    family: str
    formula_template: str
    direction: str
    windows: tuple[int, ...]
    required_fields: tuple[str, ...]
    economic_rationale: str
    public_reference_tags: tuple[str, ...]
    expected_failure_modes: tuple[str, ...]
```

- [ ] **Step 2: Register eight candidates**

Register these names exactly: `turn_of_month_reversal_liquid_5_5`, `turn_of_month_residual_momentum_20_5`, `month_end_crowding_exhaustion_10_5`, `month_start_liquidity_recovery_5_5`, `pre_holiday_liquidity_avoidance_5_3`, `post_holiday_gap_reversal_quality_3_5`, `weekday_monday_reversal_quality_5_5`, `quarter_end_liquidity_window_reversal_20_5`.

- [ ] **Step 3: Run the tests to verify GREEN**

Run: `python -m unittest tests.unit.test_cn_calendar_seasonality_preregistration tests.unit.test_cn_calendar_seasonality_preregistration_cli`

Expected: PASS.

### Task 3: Report And Startup Gate Update

**Files:**
- Create: `docs/research/cn_stock_cn_calendar_seasonality_preregistration_round163_2026-06-23.md`
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Modify: `tests/unit/test_factor_mining_startup_gate_cli.py`

- [ ] **Step 1: Generate local report output**

Run: `python scripts/run_cn_calendar_seasonality_preregistration.py --output-dir data/reports/cn_calendar_seasonality_preregistration_round163_20260623`

Expected: Summary passes with eight candidates, zero portfolio candidates, zero promotion candidates.

- [ ] **Step 2: Update startup gate**

Set `source_audit` to `docs/research/cn_stock_cn_calendar_seasonality_preregistration_round163_2026-06-23.md`, set `next_direction` to `round164_cn_calendar_seasonality_residual_prescreen`, add `calendar_seasonality` to allowed factor families, and add blockers for portfolio grids, promotion, future holiday lookup, and calendar-state tuning before residual prescreen.

- [ ] **Step 3: Verify the updated gate**

Run: `python -m unittest tests.unit.test_factor_mining_startup_gate_cli tests.unit.test_factor_mining_startup_gate`

Expected: PASS and default startup gate points to Round164 calendar-seasonality residual prescreen.

### Task 4: Final Verification

**Files:**
- Verify only, no new files.

- [ ] **Step 1: Compile and validate JSON**

Run: `python -m json.tool configs/factor_mining_startup_cn_stock.json > $null`

Run: `python -m py_compile src/quant_robot/ops/cn_calendar_seasonality_preregistration.py scripts/run_cn_calendar_seasonality_preregistration.py`

Expected: exit code 0.

- [ ] **Step 2: Re-run startup gate**

Run: `python scripts/run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --current-branch codex/factor-validation-cn-stock-long-cycle-20260618 --market CN --asset-type stock --confirm-start --output-dir data/reports/factor_mining_startup_gate_round164_calendar_recheck_20260623`

Expected: `status` is `cleared`, `next_direction` is `round164_cn_calendar_seasonality_residual_prescreen`.

- [ ] **Step 3: Confirm data policy**

Run: `git ls-files data/raw data/processed data/reports | Measure-Object`

Expected: zero tracked report/raw/processed data files.
