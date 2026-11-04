"""Exact one-use geopolitical source cadence admission; no outcome roles."""
from datetime import datetime, timezone
import json

from quant_robot.data.sources.geopolitical_vintages import history_url, raw_url, select_commit
from quant_robot.research.geopolitical_cadence import MONTHS, calculate
from quant_robot.research.monthly_diagnostic_registration import (
    canonical, resolve_path, runtime_environment, sha256, write_exclusive_json,
)

DIRECTORY = "data/reports/geopolitical_cadence_20261104"
REGISTRATION = DIRECTORY + "/registration.json"
DECISION = "geopolitical_cadence_decision"
STAGE = "single_geopolitical_cadence_screen"
MODE = "single_geopolitical_cadence_only"
SOURCE = "data/reports/geopolitical_source_expansion_20261104"
PILOT_FILES = {
    "pilot_scope": ("geopolitical_source_pilot/scope.json", "867fde7d58f32c7a7d9a62765b5e3103d788a3fa87850c7f3e56ccf370a670e1"),
    "pilot_source_review": ("geopolitical_source_pilot/source_review.json", "2f6a34538713878809f5b6a884b511d92b59eec816ea5e25f4c86241d1e6fc6f"),
    "pilot_windows": ("geopolitical_source_pilot/source_windows.json", "7ab9ae563de60323a73555655483bdf7654e04336ae8fc95be3fbbc8845c816d"),
    "pilot_retrieval": ("geopolitical_source_pilot/retrieval_results.json", "8bf434374ccd14948b71ab7887aa94ddb315d1fec6d27c293b967e5468b284a7"),
    "pilot_method_review": ("geopolitical_method_bridge/method_review.json", "089e364eee2f740805788552b8aae348b94ae23120975a33c5f3a11ec0507e89"),
    "pilot_archive_review": ("geopolitical_archive_index/archive_review.json", "62df661eef1da03496beb80e2e4d9862b68294f5ff5d8076ffe7f8bc0ab750ef"),
    "pilot_metadata_review": ("geopolitical_archive_metadata/metadata_review.json", "12868f1d9e1b6ab95529f3ec8f396bd1e865333d55ea6e6f062ed239b9450135"),
}
FROZEN = {
    "proposal": dict(path="configs/cn_etf_geopolitical_gold_proposal_20260922.json", sha256="58a5f1e9ca392eadf6f2e90468d6100257a9e994e7b278eef5065d8f1d66dae4"),
    "source_summary": dict(path="configs/cn_etf_geopolitical_source_expansion_review_20261104.json", sha256="298c00dd51443c44d12f6d1e6baaeadb93959151e1deac160c86d9adf0d1338c"),
    "pilot_review": dict(path="configs/cn_etf_geopolitical_gold_pilot_review_20260922.json", sha256="b523db3ae1bd985adf17e88f58135ec93c55e935c0f18598a4499467291f9263"),
    "source_scope": dict(path=SOURCE+"/scope.json", sha256="ec6f8b9e0efcdfa3a9a81559118fe0f5c62f2404be417abc5576c767681a7f79"),
    "source_result": dict(path=SOURCE+"/source_expansion_result.json", sha256="88f5915091cf3ce6162b270c45888e7e75fa47e3328a421600c09b1f04808670"),
    "source_claim": dict(path=SOURCE+"/execution_claim.json", sha256="9b0814cc949e5578c788a41e764a806ec36052ee0baed68dbe6529acb7042db0"),
    "source_preflight_review": dict(path=SOURCE+"/preflight_independent_review.md", sha256="d367feb344c7c95c2f5b7d53200cd97f68fe3cb0178f9a9fe5881ef104e1bde8"),
    "source_result_review": dict(path=SOURCE+"/source_result_independent_review.md", sha256="d38eb9770bc716c51478c384a7b94adce0a611d130ecf4df93d2f5c976657fd2"),
    **{role: dict(path=DIRECTORY+"/pilot_authority/"+role+".json", sha256=digest)
       for role, (_, digest) in PILOT_FILES.items()},
}
PARTS = ("history", "history_claim", "history_receipt", "vintage", "vintage_claim", "vintage_receipt")
AUTHORITY_PATHS = {
    f"original_{month}_{part}": (DIRECTORY+"/pilot_authority" if month in ("202203", "202512") else SOURCE)
        + f"/{month}_{part}" + (".xls" if part == "vintage" else ".json")
    for month in MONTHS for part in PARTS
}
ROLES = set(FROZEN) | set(AUTHORITY_PATHS)
IMPLEMENTATION = (
    "src/quant_robot/research/geopolitical_cadence.py",
    "src/quant_robot/research/geopolitical_cadence_study.py",
    "src/quant_robot/data/sources/geopolitical_vintages.py",
    "src/quant_robot/research/monthly_diagnostic_registration.py",
    "src/quant_robot/research/pm_startup_gate.py", "src/quant_robot/research/family_scheduler.py",
    "scripts/run_cn_etf_geopolitical_cadence.py", "scripts/prepare_cn_etf_geopolitical_cadence.py",
    "scripts/bootstrap.py",
)


def build_registration(*, inputs, code_files, branch, environment):
    if set(inputs) != ROLES or set(code_files) != set(IMPLEMENTATION):
        raise ValueError("Exact source and implementation roles required; no outcome roles")
    for item in [*inputs.values(), *code_files.values()]:
        if set(item) != {"path", "sha256"}:
            raise ValueError("Path and SHA256 required")
        resolve_path(".", item["path"])
        digest = item["sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Lowercase SHA256 required")
    if any(inputs[role] != pin for role, pin in FROZEN.items()):
        raise ValueError("Frozen economic proposal and source evidence required")
    if any(inputs[role]["path"] != path for role, path in AUTHORITY_PATHS.items()):
        raise ValueError("Original authorities require fixed local paths")
    if any(name != item["path"] for name, item in code_files.items()):
        raise ValueError("Implementation aliases rejected")
    if not branch.startswith("codex/factor-") or not environment:
        raise ValueError("Task branch and runtime required")
    body = dict(schema_version=1, stage=STAGE, inputs=inputs, code_files=code_files,
                branch=branch, environment=environment, max_executions=1,
                source_cadence_only=True, returns_allowed=False, net_account_allowed=False,
                promotion_allowed=False, final_holdout_allowed=False, live_boundary_allowed=False)
    return dict(body, registration_id=sha256(canonical(body)))


def validate_registration(packet):
    expected = build_registration(**{k: packet[k] for k in ("inputs", "code_files", "branch", "environment")})
    if canonical(expected) != canonical(packet):
        raise ValueError("Registration changed")
    return packet


def admission(packet, raw):
    validate_registration(packet)
    return dict(status="authorized_once", registration_id=packet["registration_id"],
                registration_path=REGISTRATION, registration_sha256=sha256(raw), max_executions=1,
                execution_count=0, allowed_stage=STAGE, ledger_path=DIRECTORY+"/attempt_claim.json",
                source_cadence_only=True, returns_allowed=False, general_factor_batch_allowed=False,
                net_account_allowed=False, promotion_allowed=False,
                final_holdout_allowed=False, live_boundary_allowed=False)


def require_unused(root):
    if any(resolve_path(root, DIRECTORY+"/"+name).exists()
           for name in ("attempt_claim.json", "result.json", "outcome.json")):
        raise ValueError("Geopolitical cadence hypothesis consumed; no rerun")


def scope(task, family_config, family_schedule, *, root, branch):
    if task != "factor_batch" or family_config.get(DECISION, {}).get("status") != "authorized_once":
        return None
    if (set(family_schedule.get("blockers", [])) != {"insufficient_active_research_families"}
            or family_schedule["summary"].get("primary_budget_share") != 0
            or family_schedule["summary"].get("active_primary_families") != 0):
        return None
    try:
        raw = resolve_path(root, REGISTRATION).read_bytes()
        packet = validate_registration(json.loads(raw))
        require_unused(root)
        if packet["branch"] != branch or family_config[DECISION] != admission(packet, raw):
            return None
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return dict(mode=MODE, scope=family_config[DECISION])


def source_chain(packet, snapshots):
    summary = json.loads(snapshots["source_summary"])
    for role, key in (("proposal", "proposal"), ("source_scope", "scope"), ("source_result", "result"),
                      ("source_claim", "claim"), ("source_preflight_review", "preflight_review"),
                      ("source_result_review", "result_review")):
        if packet["inputs"][role] != summary["pins"][key]:
            raise ValueError("Reviewed source chain differs")
    result = json.loads(snapshots["source_result"])
    if (result["passed"] != 44 or result["requests"] != 88
            or result["scope_sha256"] != packet["inputs"]["source_scope"]["sha256"]
            or result.get("signal_generated") is not False or result.get("ETF_data_accessed") is not False
            or [r["month"] for r in result["results"]] != list(MONTHS[1:-1])):
        raise ValueError("Frozen pre-state complete source result required")
    pilot = json.loads(snapshots["pilot_review"])
    pilot_rows = {r["vintage_month"]: r for r in pilot["fixed_pilots"]}
    actual_rows = {r["month"]: r for r in result["results"]}
    for month in MONTHS:
        def raw(part):
            return snapshots[f"original_{month}_{part}"]

        history_receipt = json.loads(raw("history_receipt"))
        choice = select_commit(raw("history"), history_receipt, month)
        expected = pilot_rows[month] if month in pilot_rows else actual_rows[month]
        if choice["commit_sha"] != expected["commit_sha"]:
            raise ValueError("Pre-cutoff version selection differs")
        scope_role = "pilot_scope" if month in pilot_rows else "source_scope"
        scope_sha = packet["inputs"][scope_role]["sha256"]
        for part, url in (("history", history_url(month)), ("vintage", raw_url(month, choice["commit_sha"]))):
            receipt, claim = json.loads(raw(part+"_receipt")), json.loads(raw(part+"_claim"))
            if (receipt["status_code"] != 200 or receipt["url"] != url or claim["url"] != url
                    or receipt["scope_sha256"] != scope_sha or claim["scope_sha256"] != scope_sha
                    or receipt["sha256"] != sha256(raw(part)) or receipt["bytes"] != len(raw(part))
                    or receipt["started_at"] != claim["started_at"]):
                raise ValueError("Original request or byte fingerprint differs")
        if sha256(raw("vintage")) != expected["raw_sha256"]:
            raise ValueError("Reviewed vintage differs")


def preflight(root, scheduler, gate_supplier):
    raw = resolve_path(root, REGISTRATION).read_bytes()
    packet = validate_registration(json.loads(raw))
    require_unused(root)
    if scheduler.get(DECISION) != admission(packet, raw) or packet["environment"] != runtime_environment():
        raise ValueError("Exact unused cadence admission/runtime required")
    snapshots = {}
    for group in ("code_files", "inputs"):
        for role, pin in packet[group].items():
            content = resolve_path(root, pin["path"]).read_bytes()
            if sha256(content) != pin["sha256"]:
                raise ValueError("Pinned file changed: "+role)
            if group == "inputs":
                snapshots[role] = content
    source_chain(packet, snapshots)
    gate = gate_supplier()
    safety, selected = gate["safety"], gate["selected"]
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(gate["generated_at"])).total_seconds()
    if not (0 <= age <= 30 and gate["status"] == "ready" and not gate["blockers"]
            and gate["mode"] == MODE and gate["primary_market"] == "CN_ETF"
            and safety.get("geopolitical_cadence_allowed") is True
            and safety.get("geopolitical_cadence_scope") == scheduler[DECISION]
            and safety.get("factor_batch_scope") == {}
            and selected["machine"] == "office_desktop" and selected["task"] == "factor_batch"
            and selected["branch"] == packet["branch"] == selected["current_branch"]
            and all(safety.get(k) is False for k in
                    ("factor_batch_allowed", "final_holdout_allowed", "live_boundary_allowed"))):
        raise ValueError("Fresh exact geopolitical-cadence PM gate required")
    return packet, snapshots, gate


def execute(root, scheduler, gate_supplier):
    packet, snapshots, gate = preflight(root, scheduler, gate_supplier)
    receipt = dict(registration_id=packet["registration_id"], claimed_at=datetime.now(timezone.utc).isoformat(),
                   status="claimed_before_real_states")
    write_exclusive_json(resolve_path(root, DIRECTORY+"/attempt_claim.json"), receipt)
    try:
        result = dict(calculate(snapshots), registration_id=packet["registration_id"], pm_gate=gate)
        write_exclusive_json(resolve_path(root, DIRECTORY+"/result.json"), result)
        terminal = dict(status="completed", result_sha256=sha256(canonical(result)))
    except BaseException as exc:
        terminal = dict(status="failed_consumed", error_type=type(exc).__name__)
        raise
    finally:
        write_exclusive_json(resolve_path(root, DIRECTORY+"/outcome.json"),
                             dict(receipt, **terminal, finished_at=datetime.now(timezone.utc).isoformat()))
    return result
