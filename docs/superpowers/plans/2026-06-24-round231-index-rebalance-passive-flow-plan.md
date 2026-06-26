# Round231 Index Rebalance Passive Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable Round231 research path for PIT-safe CN stock index rebalance passive-flow factors, then screen them without portfolio promotion.

**Architecture:** Convert Tushare `index_weight` snapshots into PIT-safe added/removed/weight-change events, then transform those events into sparse factor rows. Reuse the existing event PIT/IC and neutralization gates so Round231 remains comparable to earlier event studies while testing a genuinely different supply-demand mechanism.

**Tech Stack:** Python, pandas, unittest, existing `quant_robot.ops.index_rebalance_event_audit`, existing `quant_robot.ops.event_factor_pit_ic_prescreen`, Tushare data under local ignored `data/` paths.

---

### Task 1: Index Rebalance Factor Frame

**Files:**
- Create: `src/quant_robot/ops/index_rebalance_passive_flow_prescreen.py`
- Test: `tests/unit/test_index_rebalance_passive_flow_prescreen.py`

- [x] **Step 1: Write the failing test**

```python
def test_build_index_rebalance_factor_frame_creates_pit_sparse_factors(self):
    events = pd.DataFrame(
        [
            {
                "available_date": "2024-01-03",
                "event_date": "2024-01-02",
                "asset_id": "CN_000001",
                "event_type": "added",
                "prior_weight": 0.0,
                "current_weight": 0.8,
                "weight_delta": 0.8,
                "index_code": "000300.SH",
            },
            {
                "available_date": "2024-01-03",
                "event_date": "2024-01-02",
                "asset_id": "CN_000002",
                "event_type": "removed",
                "prior_weight": 0.7,
                "current_weight": 0.0,
                "weight_delta": -0.7,
                "index_code": "000300.SH",
            },
        ]
    )
    bars = _bars()
    factors = build_index_rebalance_passive_flow_factor_frame(events, bars)
    self.assertEqual(
        set(factors["factor_name"]),
        {
            "index_rebalance_add_pressure_1d",
            "index_rebalance_remove_pressure_1d",
            "index_rebalance_weight_up_pressure_1d",
            "index_rebalance_weight_down_pressure_1d",
            "index_rebalance_abs_flow_pressure_1d",
        },
    )
    self.assertTrue((factors["date"] == pd.Timestamp("2024-01-03")).all())
```

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.unit.test_index_rebalance_passive_flow_prescreen
```

Expected: `ModuleNotFoundError` for `quant_robot.ops.index_rebalance_passive_flow_prescreen`.

- [x] **Step 3: Write minimal implementation**

Create `build_index_rebalance_passive_flow_factor_frame(events, bars)` that emits five fixed factor names:

```python
INDEX_REBALANCE_PASSIVE_FLOW_FACTOR_NAMES = (
    "index_rebalance_add_pressure_1d",
    "index_rebalance_remove_pressure_1d",
    "index_rebalance_weight_up_pressure_1d",
    "index_rebalance_weight_down_pressure_1d",
    "index_rebalance_abs_flow_pressure_1d",
)
```

Use `available_date` as `date`; never use same-day event trade dates. Join `amount`, `adv20_amount`, and `log_adv20` from bars on `date`, `asset_id`, and `market`.

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest tests.unit.test_index_rebalance_passive_flow_prescreen
```

Expected: all tests pass.

### Task 2: Prescreen Builder And Writer

**Files:**
- Modify: `src/quant_robot/ops/index_rebalance_passive_flow_prescreen.py`
- Create: `scripts/run_index_rebalance_passive_flow_prescreen.py`
- Test: `tests/unit/test_index_rebalance_passive_flow_prescreen_cli.py`

- [x] **Step 1: Write the failing tests**

```python
def test_build_index_rebalance_passive_flow_prescreen_blocks_promotion(self):
    result = build_index_rebalance_passive_flow_prescreen(
        index_events=_events(),
        bars=_bars(),
        stock_basic=_stock_basic(),
        horizons=(1,),
        min_cross_section=2,
        min_ic_observations=1,
        min_neutral_rank_ic=-1.0,
        min_neutral_ic_t_stat=-1.0,
    )
    self.assertEqual(result["stage"], "index_rebalance_passive_flow_prescreen")
    self.assertFalse(result["promotion_policy"]["promotion_allowed"])
    self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
```

```python
def test_cli_writes_json_markdown_and_results(self):
    result = run_index_rebalance_passive_flow_prescreen_cli(...)
    self.assertTrue((output_dir / "index_rebalance_passive_flow_prescreen.json").exists())
    self.assertTrue((output_dir / "index_rebalance_passive_flow_prescreen.md").exists())
    self.assertTrue((output_dir / "index_rebalance_passive_flow_prescreen_results.csv").exists())
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m unittest tests.unit.test_index_rebalance_passive_flow_prescreen tests.unit.test_index_rebalance_passive_flow_prescreen_cli
```

Expected: missing builder/CLI errors.

- [x] **Step 3: Write minimal implementation**

`build_index_rebalance_passive_flow_prescreen(...)` should:
- build factor rows from index events;
- create forward-return labels via existing `make_forward_returns`;
- call `summarize_event_factor_pit_ic_prescreen`;
- retag stage, next direction, and promotion policy for Round231;
- write JSON, Markdown, results CSV, IC observations CSV, neutral observations CSV, and factor rows CSV.

- [x] **Step 4: Run tests to verify they pass**

Run:

```powershell
python -m unittest tests.unit.test_index_rebalance_passive_flow_prescreen tests.unit.test_index_rebalance_passive_flow_prescreen_cli
```

Expected: all tests pass.

### Task 3: Round231 Preregistration And Data Pull

**Files:**
- Create: `configs/factor_mining_candidate_plan_round231_index_rebalance_passive_flow_20260624.json`
- Create: `docs/research/cn_stock_round231_index_rebalance_passive_flow_preregistration_2026-06-24.md`

- [x] **Step 1: Write pre-registration**

Register five fixed factors, using these constraints:
- no same-day event trading;
- use `available_date` from the first open trade date after index-weight snapshot date;
- no portfolio grid before PIT/IC and neutral gates;
- no promotion from event IC alone;
- multiple testing counts all factor x horizon tests.

- [x] **Step 2: Pull ignored local event data**

Fetch Tushare `index_weight` rows for at least `000300.SH`, `000905.SH`, and `000852.SH` from 2015-01-01 to 2025-12-31, storing output only under `data/reports/round231_index_rebalance_passive_flow_20260624/`.

- [x] **Step 3: Run audit and prescreen**

Run the existing index audit first, then the new passive-flow prescreen. If event coverage is too sparse, stop and record a coverage-blocked report rather than tuning parameters.

### Task 4: Startup Contract Update

**Files:**
- Modify: `configs/factor_mining_startup_cn_stock.json`
- Create: `docs/research/cn_stock_round231_index_rebalance_passive_flow_prescreen_2026-06-24.md`

- [x] **Step 1: Write report**

Record candidate count, test count, IC and neutral metrics, blockers, and whether any residual/neutral research lead exists.

- [x] **Step 2: Update next direction**

If zero leads survive, set next direction to `round232_rotate_after_index_rebalance_passive_flow_failure`. If leads survive, set next direction to `round232_index_rebalance_passive_flow_reference_dedup_or_walk_forward_preflight`.

- [x] **Step 3: Verify**

Run:

```powershell
python -m json.tool configs\factor_mining_startup_cn_stock.json > $null
python -m unittest tests.unit.test_index_rebalance_passive_flow_prescreen tests.unit.test_index_rebalance_passive_flow_prescreen_cli tests.unit.test_factor_mining_startup_gate tests.unit.test_factor_mining_startup_gate_cli
python scripts\run_factor_mining_startup_gate.py --machine office_desktop --task factor_validation --branch codex/factor-validation-cn-stock-long-cycle-20260618 --confirm-start --output-dir data\reports\factor_mining_startup_gate_round232_after_index_rebalance_passive_flow_20260624
```

Expected: JSON valid, tests pass, startup gate cleared.
