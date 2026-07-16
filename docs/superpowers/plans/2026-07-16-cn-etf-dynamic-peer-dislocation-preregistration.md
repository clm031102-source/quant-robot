# CN ETF Dynamic Peer Dislocation Preregistration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a deterministic, source-hash-bound preregistration for one CN ETF dynamic-peer residual-dislocation candidate and authorize exactly one later prescreen without reading labels in this task.

**Architecture:** Keep preregistration semantics in a small pure operation, one-time authorization and ledger logic in a reusable validation module, and file/config orchestration in a strict CLI. Extend the existing Quant PM restricted-mode gate only after real preregistration hashes exist, so the scheduler can expose one scoped `factor_batch` exception without allocating research budget or opening portfolio/live boundaries.

**Tech Stack:** Python 3.12, standard-library JSON/hash/file locking, pandas for candidate CSV output, unittest, existing atomic storage and Quant PM scheduler utilities.

---

### Task 1: Build The Pure Preregistration Packet

**Files:**
- Create: `src/quant_robot/ops/cn_etf_dynamic_peer_dislocation_preregistration.py`
- Create: `tests/unit/test_cn_etf_dynamic_peer_dislocation_preregistration.py`

- [ ] **Step 1: Write failing ready, source-blocked, and boundary tests**

Create a compact frozen config fixture and source packet fixture. The ready test must assert one candidate, two counted hypotheses, no label access, and no execution permission:

```python
result = build_cn_etf_dynamic_peer_dislocation_preregistration(
    config=_config(),
    source_readiness=_source_readiness(),
    evidence_hashes=_evidence_hashes(),
    config_sha256="a" * 64,
)
self.assertEqual(result["status"], "preregistered_single_prescreen")
self.assertEqual(result["summary"]["candidate_count"], 1)
self.assertEqual(result["summary"]["hypothesis_count"], 2)
self.assertFalse(result["factor_generation_allowed"])
self.assertFalse(result["forward_return_read_allowed"])
self.assertFalse(result["prescreen_execution_allowed"])
```

Add separate tests that change source status to `blocked`, enable `factor_values_calculated`, or mismatch the source result hash and assert `status == "blocked"` with exact blocker names.

- [ ] **Step 2: Run the new test and verify import failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_cn_etf_dynamic_peer_dislocation_preregistration
```

Expected: import error because the operation does not exist.

- [ ] **Step 3: Implement the packet contract and fail-closed blockers**

Define the operation around this public interface:

```python
STAGE = "cn_etf_dynamic_peer_dislocation_preregistration"
STATUS_READY = "preregistered_single_prescreen"


def build_cn_etf_dynamic_peer_dislocation_preregistration(
    *,
    config: dict[str, Any],
    source_readiness: dict[str, Any],
    evidence_hashes: dict[str, str],
    config_sha256: str,
) -> dict[str, Any]:
    blockers = _preregistration_blockers(
        config=config,
        source_readiness=source_readiness,
        evidence_hashes=evidence_hashes,
    )
    candidate = dict(config["candidate"])
    result = {
        "stage": STAGE,
        "registration_date": config["registration_date"],
        "status": "blocked" if blockers else STATUS_READY,
        "primary_market": "CN_ETF",
        "research_family": config["research_family"],
        "configuration": {"sha256": config_sha256},
        "source_evidence": dict(evidence_hashes),
        "candidate": candidate,
        "summary": {
            "candidate_count": 1,
            "hypothesis_count": len(config["evaluation"]["horizons"]),
            "primary_horizon": config["evaluation"]["primary_horizon"],
            "diagnostic_horizon": config["evaluation"]["diagnostic_horizon"],
            "blockers": blockers,
        },
        "evaluation": dict(config["evaluation"]),
        "reference_policy": dict(config["reference_policy"]),
        "capacity": dict(config["capacity"]),
        "costs": dict(config["costs"]),
        "stop_policy": dict(config["stop_policy"]),
        "forward_return_read_allowed": False,
        "factor_generation_allowed": False,
        "prescreen_execution_allowed": False,
        "portfolio_grid_allowed": False,
        "walk_forward_allowed": False,
        "final_holdout_allowed": False,
        "paper_signal_allowed": False,
        "live_boundary_allowed": False,
        "next_direction": "run_one_hash_bound_dynamic_peer_dislocation_prescreen",
    }
    result["markdown"] = render_cn_etf_dynamic_peer_dislocation_preregistration(result)
    return result
```

The blocker function must verify source status, `gate.cleared`, all four source-boundary false fields, exact source/config/mapping hashes, one candidate, two horizons, primary horizon five, diagnostic horizon 20, execution lag one, zero execution permissions, and the explicit no-rescue stop policy.

- [ ] **Step 4: Implement deterministic artifact writing**

Add:

```python
def write_cn_etf_dynamic_peer_dislocation_preregistration(
    output_dir: str | Path,
    result: dict[str, Any],
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    json_path = output / "cn_etf_dynamic_peer_dislocation_preregistration.json"
    markdown_path = output / "cn_etf_dynamic_peer_dislocation_preregistration.md"
    candidate_path = output / "candidate.csv"
    json_path.write_text(json.dumps(clean, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_cn_etf_dynamic_peer_dislocation_preregistration(result), encoding="utf-8")
    pd.DataFrame([result["candidate"]]).to_csv(candidate_path, index=False)
    return {"json": json_path, "markdown": markdown_path, "candidate_csv": candidate_path}
```

Exclude only the derived `markdown` key from JSON sanitization. Do not insert wall-clock timestamps.

- [ ] **Step 5: Run operation tests**

Run the Task 1 test command. Expected: all tests pass.

- [ ] **Step 6: Commit the operation**

```powershell
git add src/quant_robot/ops/cn_etf_dynamic_peer_dislocation_preregistration.py tests/unit/test_cn_etf_dynamic_peer_dislocation_preregistration.py
git commit -m "feat: build CN ETF dynamic peer preregistration"
```

### Task 2: Add Single-Prescreen Authorization And Claim Ledger

**Files:**
- Create: `src/quant_robot/validation/single_prescreen_authorization.py`
- Create: `tests/unit/test_single_prescreen_authorization.py`

- [ ] **Step 1: Write failing packet and one-time-claim tests**

Cover packet construction, candidate/config/hash mismatches, enabled holdout/live boundaries, a first successful claim, a second rejected claim, and a pre-existing lock file.

```python
packet = build_single_prescreen_authorization(
    registration_date="2026-07-16",
    candidate_name="etf_dynamic_peer_residual_dislocation_reversal_5_60",
    preregistration_config_sha256="a" * 64,
    preregistration_result_sha256="b" * 64,
    source_hashes=_source_hashes(),
)
write_single_prescreen_authorization(packet_path, packet)
receipt = claim_single_prescreen_authorization(
    packet_path=packet_path,
    ledger_path=ledger_path,
    expected_candidate_name=packet["candidate_name"],
    expected_config_sha256="a" * 64,
    expected_packet_sha256=sha256_file(packet_path),
    context="fixture prescreen",
)
self.assertTrue(receipt["execution_claim_recorded"])
with self.assertRaisesRegex(ValueError, "already consumed"):
    claim_single_prescreen_authorization(
        packet_path=packet_path,
        ledger_path=ledger_path,
        expected_candidate_name=packet["candidate_name"],
        expected_config_sha256="a" * 64,
        expected_packet_sha256=sha256_file(packet_path),
        context="fixture prescreen",
    )
```

- [ ] **Step 2: Run and verify import failure**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_single_prescreen_authorization
```

Expected: import error.

- [ ] **Step 3: Implement deterministic packet construction**

Use this contract:

```python
AUTHORIZATION_STAGE = "cn_etf_single_prescreen_authorization"
LEDGER_SCHEMA_VERSION = 1


def build_single_prescreen_authorization(
    *,
    registration_date: str,
    candidate_name: str,
    preregistration_config_sha256: str,
    preregistration_result_sha256: str,
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    identity_payload = {
        "candidate_name": candidate_name,
        "preregistration_config_sha256": preregistration_config_sha256,
        "preregistration_result_sha256": preregistration_result_sha256,
        "source_hashes": source_hashes,
    }
    authorization_id = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "stage": AUTHORIZATION_STAGE,
        "registration_date": registration_date,
        "status": "authorized_single_prescreen",
        "authorization_id": authorization_id,
        **identity_payload,
        "allowed_task": "factor_batch",
        "allowed_stage": "cn_etf_dynamic_peer_dislocation_prescreen",
        "max_executions": 1,
        "execution_ledger_required": True,
        "portfolio_grid_allowed": False,
        "walk_forward_allowed": False,
        "final_holdout_allowed": False,
        "promotion_allowed": False,
        "paper_signal_allowed": False,
        "live_boundary_allowed": False,
    }
```

Validate every SHA-256 as 64 lowercase hexadecimal characters and require all execution boundaries to be exactly false.

Expose these file and validation functions for the CLI and future prescreen:

```python
def write_single_prescreen_authorization(path: str | Path, packet: dict[str, Any]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
    return destination


def validate_single_prescreen_authorization(
    *,
    packet_path: str | Path,
    expected_candidate_name: str,
    expected_config_sha256: str,
    expected_packet_sha256: str,
    context: str,
) -> dict[str, Any]:
    path = Path(packet_path)
    if not path.is_file():
        raise ValueError(f"{context} single prescreen authorization is missing: {path}")
    packet_sha256 = sha256_file(path)
    if packet_sha256 != expected_packet_sha256:
        raise ValueError(f"{context} single prescreen authorization hash mismatch: {path}")
    packet = json.loads(path.read_text(encoding="utf-8"))
    if packet.get("stage") != AUTHORIZATION_STAGE:
        raise ValueError(f"{context} single prescreen authorization stage mismatch: {path}")
    if packet.get("status") != "authorized_single_prescreen":
        raise ValueError(f"{context} single prescreen is not authorized: {path}")
    if packet.get("candidate_name") != expected_candidate_name:
        raise ValueError(f"{context} single prescreen candidate mismatch: {path}")
    if packet.get("preregistration_config_sha256") != expected_config_sha256:
        raise ValueError(f"{context} single prescreen config hash mismatch: {path}")
    if packet.get("max_executions") != 1 or packet.get("execution_ledger_required") is not True:
        raise ValueError(f"{context} single prescreen execution contract mismatch: {path}")
    for key in (
        "portfolio_grid_allowed",
        "walk_forward_allowed",
        "final_holdout_allowed",
        "promotion_allowed",
        "paper_signal_allowed",
        "live_boundary_allowed",
    ):
        if packet.get(key) is not False:
            raise ValueError(f"{context} single prescreen boundary enabled: {key}")
    return {
        "packet": packet,
        "packet_path": str(path),
        "packet_sha256": packet_sha256,
        "authorization_id": str(packet["authorization_id"]),
    }


def claim_single_prescreen_authorization(
    *,
    packet_path: str | Path,
    ledger_path: str | Path,
    expected_candidate_name: str,
    expected_config_sha256: str,
    expected_packet_sha256: str,
    context: str,
) -> dict[str, Any]:
    validated = validate_single_prescreen_authorization(
        packet_path=packet_path,
        expected_candidate_name=expected_candidate_name,
        expected_config_sha256=expected_config_sha256,
        expected_packet_sha256=expected_packet_sha256,
        context=context,
    )
    ledger = Path(ledger_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger.with_suffix(ledger.suffix + ".lock")
    descriptor = _exclusive_lock(lock_path, context=context)
    try:
        payload = _load_ledger(ledger)
        claims = payload.setdefault("claims", {})
        authorization_id = validated["authorization_id"]
        if authorization_id in claims:
            raise ValueError(
                f"{context} single prescreen authorization already consumed: {authorization_id}"
            )
        receipt = {
            "authorization_id": authorization_id,
            "candidate_name": expected_candidate_name,
            "packet_sha256": validated["packet_sha256"],
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "context": context,
            "execution_claim_recorded": True,
        }
        claims[authorization_id] = receipt
        atomic_write_json(ledger, payload)
        return receipt
    finally:
        os.close(descriptor)
        lock_path.unlink(missing_ok=True)
```

`validate_single_prescreen_authorization` must load JSON, verify the packet file hash, stage, status, candidate, config hash, one-execution limit, required ledger, and every prohibited boundary before returning the packet and authorization identity. The claim function calls this validator before touching the ledger.

- [ ] **Step 4: Implement atomic one-time claim behavior**

Mirror the repository's final-holdout read-once implementation with an exclusive `.lock` file and `atomic_write_json`:

```python
claims = payload.setdefault("claims", {})
if authorization_id in claims:
    raise ValueError(f"{context} single prescreen authorization already consumed: {authorization_id}")
receipt = {
    "authorization_id": authorization_id,
    "candidate_name": expected_candidate_name,
    "packet_sha256": validated["packet_sha256"],
    "claimed_at": datetime.now(timezone.utc).isoformat(),
    "context": context,
    "execution_claim_recorded": True,
}
claims[authorization_id] = receipt
atomic_write_json(ledger, payload)
```

Always close the descriptor and remove the lock in `finally`.

- [ ] **Step 5: Run authorization tests**

Run the Task 2 test command. Expected: all tests pass.

- [ ] **Step 6: Commit authorization support**

```powershell
git add src/quant_robot/validation/single_prescreen_authorization.py tests/unit/test_single_prescreen_authorization.py
git commit -m "feat: authorize one frozen factor prescreen"
```

### Task 3: Freeze The Config And Strict CLI

**Files:**
- Create: `configs/cn_etf_dynamic_peer_dislocation_preregistration_20260716.json`
- Create: `scripts/run_cn_etf_dynamic_peer_dislocation_preregistration.py`
- Create: `tests/unit/test_run_cn_etf_dynamic_peer_dislocation_preregistration.py`

- [ ] **Step 1: Write the frozen config**

Encode every value from the design: exact source paths and hashes, candidate formula and windows, horizons and roles, eligibility, shared statistical thresholds, three closed-family reference config hashes, direct exposure challenges, capacity, 5/10 bps costs, one-run stop policy, output paths, and all execution boundaries false.

The output directory must be:

```json
"output_dir": "data/reports/cn_etf_dynamic_peer_dislocation_preregistration_20260716"
```

The future ledger path must be:

```json
"execution_ledger_path": "data/reports/cn_etf_dynamic_peer_dislocation_prescreen_execution_ledger.json"
```

- [ ] **Step 2: Write failing strict-validation and end-to-end fixture tests**

Copy the config into a temporary directory and mutate one field per subtest: source hash, formula, beta lag, primary horizon, FDR scope, reference config hash, cost stress, run limit, factor generation, final holdout, and live trading. Each mutation must raise `ValueError` containing `frozen` or the changed boundary key.

The end-to-end fixture writes source JSON and mapping bytes whose hashes are inserted into a temporary otherwise-frozen config, runs the CLI, and asserts JSON/Markdown/CSV/authorization files exist without loading bars or labels.

- [ ] **Step 3: Run and verify CLI import failure**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_run_cn_etf_dynamic_peer_dislocation_preregistration
```

Expected: import error.

- [ ] **Step 4: Implement exact config validation and source hashing**

The CLI flow must be:

```python
payload = _load_and_validate_config(config_path)
config_sha256 = sha256_file(config_path)
source_paths = _source_paths(payload)
evidence_hashes = {name: sha256_file(path) for name, path in source_paths.items()}
_validate_evidence_hashes(payload, evidence_hashes)
source_readiness = json.loads(source_paths["source_result"].read_text(encoding="utf-8"))
result = build_cn_etf_dynamic_peer_dislocation_preregistration(
    config=payload,
    source_readiness=source_readiness,
    evidence_hashes=evidence_hashes,
    config_sha256=config_sha256,
)
if result["status"] != STATUS_READY:
    raise ValueError(f"preregistration blocked: {result['summary']['blockers']}")
paths = write_cn_etf_dynamic_peer_dislocation_preregistration(destination, result)
result_sha256 = sha256_file(paths["json"])
authorization = build_single_prescreen_authorization(
    registration_date=payload["registration_date"],
    candidate_name=payload["candidate"]["factor_name"],
    preregistration_config_sha256=config_sha256,
    preregistration_result_sha256=result_sha256,
    source_hashes=evidence_hashes,
)
write_single_prescreen_authorization(destination / "single_prescreen_authorization.json", authorization)
```

The CLI prints stage, status, candidate, config/result/authorization hashes, blockers, next direction, and paths only.

- [ ] **Step 5: Run CLI tests**

Run the Task 3 test command. Expected: all tests pass.

- [ ] **Step 6: Commit config and CLI**

```powershell
git add configs/cn_etf_dynamic_peer_dislocation_preregistration_20260716.json scripts/run_cn_etf_dynamic_peer_dislocation_preregistration.py tests/unit/test_run_cn_etf_dynamic_peer_dislocation_preregistration.py
git commit -m "feat: freeze CN ETF dynamic peer prescreen plan"
```

### Task 4: Run Real Preregistration And Prove Determinism

**Files:**
- Verify ignored artifacts under `data/reports/cn_etf_dynamic_peer_dislocation_preregistration_20260716`

- [ ] **Step 1: Run the real preregistration**

```powershell
.\.venv\Scripts\python.exe scripts\run_cn_etf_dynamic_peer_dislocation_preregistration.py --config configs\cn_etf_dynamic_peer_dislocation_preregistration_20260716.json
```

Expected: `preregistered_single_prescreen`, one candidate, two hypotheses, and no source blockers.

- [ ] **Step 2: Record all artifact hashes**

```powershell
Get-ChildItem data\reports\cn_etf_dynamic_peer_dislocation_preregistration_20260716 -File | Get-FileHash -Algorithm SHA256
```

Record config, preregistration JSON, candidate CSV, Markdown, and authorization hashes.

- [ ] **Step 3: Re-run and require identical hashes**

Run the Task 4 commands again. Every hash must be identical. Any drift blocks governance updates.

### Task 5: Open Only The Hash-Bound Single Prescreen Mode

**Files:**
- Modify: `src/quant_robot/research/pm_startup_gate.py`
- Modify: `tests/unit/test_quant_pm_startup_gate.py`
- Modify: `configs/research_family_scheduler_cn_etf.json`
- Modify: `tests/unit/test_cn_etf_volatility_scheduler_closeout.py`

- [ ] **Step 1: Add a failing Quant PM single-prescreen test**

Build a scheduler fixture with last decision `prescreen_preregistered_single_batch_only`, the exact candidate, 64-character hashes, `single_prescreen_run_limit=1`, and every downstream boundary false.

Assert:

```python
self.assertEqual(factor_batch["status"], "ready")
self.assertEqual(factor_batch["mode"], "single_prescreen_only")
self.assertTrue(factor_batch["safety"]["factor_batch_allowed"])
self.assertEqual(
    factor_batch["safety"]["factor_batch_scope"]["factor_name"],
    "etf_dynamic_peer_residual_dislocation_reversal_5_60",
)
self.assertFalse(factor_batch["safety"]["portfolio_grid_allowed"])
self.assertEqual(other_factor_batch["status"], "blocked")
```

Mutate run limit to two, remove a hash, enable walk-forward, and use task `data_pipeline`; every case must remain blocked.

- [ ] **Step 2: Run and verify the new test fails**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_quant_pm_startup_gate
```

Expected: the new fixture is blocked because `single_prescreen_only` does not exist.

- [ ] **Step 3: Extend the restricted-mode contract**

Return a structured mode record rather than a bare string:

```python
restricted = _restricted_review_mode(task, resolved_family_config, family_schedule)
mode = str(restricted.get("mode", "")) if restricted else ""
```

For `prescreen_preregistered_single_batch_only`, require task `factor_batch`, exact scheduler blocker set, zero budget, candidate/config/result/authorization hashes, run limit one, and all downstream boundaries false. Set:

```python
"factor_batch_allowed": bool(not blockers and mode == "single_prescreen_only"),
"factor_batch_scope": restricted.get("scope", {}) if restricted else {},
"single_prescreen_authorization_required": mode == "single_prescreen_only",
"portfolio_grid_allowed": False,
"walk_forward_allowed": False,
"final_holdout_allowed": False,
```

Preserve existing `source_repair_only` and `preregistration_only` behavior unchanged.

- [ ] **Step 4: Update scheduler tests first, then real scheduler evidence**

The scheduler's new last decision must store the real hashes from Task 4, the candidate name, two hypotheses, run limit one, execution count zero, authorization ledger path, zero budget, and every prohibited boundary false. Move the current source-readiness decision into history without deleting older decisions.

Update the dynamic family row to:

```json
{
  "source_readiness_status": "ready_for_peer_source_preregistration",
  "preregistration_status": "preregistered_single_prescreen",
  "budget_share": 0.0,
  "single_prescreen_allowed": true,
  "factor_batch_before_preregistration_allowed": false,
  "portfolio_grid_allowed": false,
  "walk_forward_allowed": false
}
```

- [ ] **Step 5: Run governance tests and the actual startup gate**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_quant_pm_startup_gate tests.unit.test_cn_etf_volatility_scheduler_closeout
.\.venv\Scripts\python.exe scripts\run_quant_pm_startup_gate.py --machine office_desktop --task factor_batch --branch codex/factor-review-cn-etf-dynamic-peer-preregistration-20260716
```

Expected: tests pass; actual gate is ready in `single_prescreen_only`, exposes exactly one factor, and leaves portfolio/walk-forward/holdout/live false.

- [ ] **Step 6: Commit governance support**

```powershell
git add src/quant_robot/research/pm_startup_gate.py tests/unit/test_quant_pm_startup_gate.py configs/research_family_scheduler_cn_etf.json tests/unit/test_cn_etf_volatility_scheduler_closeout.py
git commit -m "feat: gate one CN ETF dynamic peer prescreen"
```

### Task 6: Record The Durable Preregistration Decision

**Files:**
- Create: `docs/research/cn_etf_dynamic_peer_dislocation_preregistration_2026-07-16.md`
- Modify: `docs/research/CURRENT_RESEARCH_INDEX.md`

- [ ] **Step 1: Write the durable report**

Report the exact candidate formula, timing, source/config/result/authorization hashes, two counted hypotheses, reference union, direct exposure challenge, 5/10 bps costs, capacity rule, stop policy, and all prohibited boundaries. State explicitly that no bars, factors, labels, IC, returns, or holdout rows were read by the preregistration operation.

- [ ] **Step 2: Update the research index**

Set the default next task to execute exactly one hash-bound prescreen on a new `factor_batch` branch. Include the required authorization packet and local claim ledger paths. Do not state that alpha or profitability exists.

- [ ] **Step 3: Run focused tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.unit.test_cn_etf_dynamic_peer_dislocation_preregistration tests.unit.test_single_prescreen_authorization tests.unit.test_run_cn_etf_dynamic_peer_dislocation_preregistration tests.unit.test_quant_pm_startup_gate tests.unit.test_cn_etf_volatility_scheduler_closeout
```

- [ ] **Step 4: Run full verification**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
.\.venv\Scripts\python.exe -m compileall -q src scripts tests
.\.venv\Scripts\python.exe scripts\run_project_audit.py --json
.\.venv\Scripts\python.exe scripts\run_maintainability_audit.py --fail-on-regression
git diff --check
.\.venv\Scripts\python.exe scripts\sync_project.py --machine office_desktop --task factor_review
```

Expected: all tests and compilation pass; project audit passes; maintainability has no baseline regression; Git and sync audits contain no forbidden files or blockers.

- [ ] **Step 5: Review and commit**

Review the complete diff for label access, threshold drift, source hash drift, accidental data artifacts, general factor-batch permission, and unsupported alpha claims. Commit locally and do not push.

```powershell
git add docs/research/cn_etf_dynamic_peer_dislocation_preregistration_2026-07-16.md docs/research/CURRENT_RESEARCH_INDEX.md
git commit -m "docs: record CN ETF dynamic peer preregistration"
```
