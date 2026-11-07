"""One bounded spot transfer study. Import/preview never imports the price loader."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Context, getcontext, ROUND_HALF_EVEN, InvalidOperation, DivisionByZero, Overflow, FloatOperation
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import sys

from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, write_exclusive_json

BRANCH = "codex/factor-review-72h-campaign-20261106"
MODE = "single_campaign_spot_macd_transfer_27_account_only"
DIRECTORY = "data/reports/campaign_72h_20261106/spot_macd_transfer_accounts"
REGISTRATION, REVIEW, ROOT_REVIEW, COMPARISON = (DIRECTORY+"/"+name for name in
    ("registration.json", "independent_review.json", "root_admission_review.json", "comparison_review.json"))
ADMISSION = "configs/cn_etf_spot_macd_transfer_admission_20261107.json"
MANIFEST = "data/reports/campaign_72h_20261106/manager/external_transfer_design_20261107/historical_input_manifest.json"
MANIFEST_SHA = None  # Actual package is not authorized or frozen by engineering.
METHOD_SHA = "6ec96945600c35d7c4f8c31fcd3c4d090535517a9d41948faa6387827953b9f0"
SOURCE_SCHEMA_ID = "exact_retained_20180208_daily_time_exception_v1"
SOURCE_SCHEMA_SHA = "e2f435024008f48f0520a89e53a41853f28f0d6208c9634f4af3552f55543e36"
SOURCE_SCHEMA_REVIEW_SHA = "6864582cd2dab55e14c4292c31273338d94fa997f0dd3d3d85e339422dae4a45"
POLICY = dict(symbol="BTCUSDT", market="spot", initial_cash_USDT="1000", daily_first="2018-01-01",
    daily_last="2024-01-01", daily_rows=2192, execution_first="2019-01-02", execution_last="2024-01-02",
    execution_rows=1827, decision_UTC="00:02:00", execution_UTC="00:03:00", volume_available_UTC="00:04:00",
    strategy_accounts=9, holding_controls=9, cash_controls=9, total_accounts=27,
    cost_cases=[[f,s] for f in (5,10,20) for s in (0,10,30)], primary="fee10_slip10",
    hypotheses=1, max_executions=1, conditional_only=True, qualification_granted=False,
    final_holdout_allowed=False, live_boundary_allowed=False, ordinary_factor_budget_changed=False,
    comparison_purpose="conditional_external_spot_transfer_only", holding_control_tested=True,
    holding_policy="fixed_252_day_single_attempt_cycles", uninterrupted_passive_holding_tested=False,
    alpha_or_promotion_eligible=False, CNY_conversion_claim=False, source_year_2026_allowed=False)
PM_INPUTS = dict(campaign="configs/research_campaign_72h_20261106.json",
    pm_policy="configs/quant_pm_startup_gate_cn_etf.json", workstations="configs/workstations.json",
    family_scheduler="configs/research_family_scheduler_cn_etf.json")
CORE_ROLES = {"method", "source_plan", "source_schema_review", "method_manager_review", "method_root_review"}
IMPLEMENTATION = (
    "src/quant_robot/research/spot_macd_transfer.py", "src/quant_robot/research/spot_macd_transfer_admission.py",
    "src/quant_robot/research/spot_macd_transfer_historical.py",
    "src/quant_robot/research/spot_macd_transfer_time_exception.py",
    "src/quant_robot/research/spot_macd_transfer_verification.py",
    "src/quant_robot/research/monthly_diagnostic_registration.py", "src/quant_robot/research/pm_startup_gate.py",
    "src/quant_robot/research/account_comparison_scope.py", "src/quant_robot/research/family_scheduler.py",
    "src/quant_robot/ops/paper_evidence_session.py", "scripts/run_spot_macd_transfer_historical.py",
    "scripts/run_quant_pm_startup_gate.py", "scripts/start_task_context.py", "scripts/bootstrap.py",
    "tests/unit/test_spot_macd_transfer.py", "tests/unit/test_spot_macd_transfer_admission.py",
    "tests/unit/test_spot_macd_transfer_historical.py", "tests/unit/test_spot_macd_transfer_pm_gate.py",
    "tests/unit/test_spot_macd_transfer_verification.py", "tests/unit/test_spot_macd_transfer_time_exception.py")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json(raw):
    def pairs(items):
        result = {}
        for k,v in items:
            if k in result: raise ValueError("Duplicate JSON key")
            result[k] = v
        return result
    def invalid(value): raise ValueError("Nonfinite JSON token")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def read_bound(root, ref, *, return_bytes=False):
    if (not isinstance(ref,dict) or set(ref)!={"path","sha256"} or not isinstance(ref["sha256"],str)
            or len(ref["sha256"])!=64 or any(c not in "0123456789abcdef" for c in ref["sha256"])):
        raise ValueError("Exact path/hash reference required")
    path = resolve_path(root,ref["path"])
    cursor = Path(root)/ref["path"]
    while cursor != Path(root) and cursor != cursor.parent:
        if cursor.is_symlink(): raise ValueError("Symlink source forbidden")
        cursor = cursor.parent
    if file_digest(path)!=ref["sha256"]: raise ValueError("Bound file changed: "+ref["path"])
    if return_bytes:
        raw=path.read_bytes()
        if digest(raw)!=ref["sha256"]: raise ValueError("Bound bytes changed during read")
        return raw


def _context_record(c, *, flags=True):
    out={k:getattr(c,k) for k in ("prec","rounding","Emin","Emax","capitals","clamp")}
    out["traps"]={k.__name__:v for k,v in c.traps.items()}
    if flags: out["flags"]={k.__name__:v for k,v in c.flags.items()}
    return out


def runtime_environment():
    contexts={}
    for label,precision in (("signal",28),("finance",40)):
        c=Context(prec=precision,rounding=ROUND_HALF_EVEN,Emin=-999999,Emax=999999,capitals=1,clamp=0)
        for s in c.traps: c.traps[s]=s in (InvalidOperation,DivisionByZero,Overflow,FloatOperation)
        c.clear_flags(); contexts[label]=_context_record(c)
    return dict(python=platform.python_version(), implementation=platform.python_implementation(),
        platform=platform.platform(), executable=str(Path(sys.executable).resolve()),
        executable_sha256=file_digest(sys.executable), ambient_decimal_context=_context_record(getcontext()),
        prescribed_contexts=contexts, dependencies={name:version(name) for name in ("numpy","pandas")})


def validate_source_schema_policy(root, manifest, pins):
    # Metadata only: never import the proof helper or decode a financial source.
    if "source_schema_policy" not in manifest:return
    policy=manifest["source_schema_policy"]
    if (not isinstance(policy,dict) or set(policy)!={"policy_id","addendum_role","root_review_role","authority_roles"}
            or policy["policy_id"]!=SOURCE_SCHEMA_ID or policy["addendum_role"] not in pins
            or policy["root_review_role"] not in pins
            or pins[policy["addendum_role"]]["sha256"]!=SOURCE_SCHEMA_SHA
            or pins[policy["root_review_role"]]["sha256"]!=SOURCE_SCHEMA_REVIEW_SHA):
        raise ValueError("Exact optional source schema and root review required")
    contract=_json(read_bound(root,pins[policy["addendum_role"]],return_bytes=True))
    read_bound(root,pins[policy["root_review_role"]])
    roles=policy["authority_roles"]
    names={"economic_contract","economic_method_text","original_source_plan","root_decision","old_failed_outcome",
        "native","native_capture","native_failed_receipt","archive","checksum","archive_receipt","time_outcome",
        "time_independent_review","token_scope","token_result","token_implementation"}
    if (contract.get("policy_id")!=SOURCE_SCHEMA_ID or contract["economic_invariants"]["method_sha256"]!=METHOD_SHA
            or not isinstance(roles,dict) or set(roles)!=names or set(contract["authority"])!=names
            or any(role not in pins for role in roles.values()) or len(set(roles.values()))!=16
            or roles["native"]!=manifest["daily_sources"][1]["role"]):
        raise ValueError("Exact16 authority roles and existing native role required")
    for key,role in roles.items():
        ref=pins[role];expected=contract["authority"][key]
        if ref["sha256"]!=expected["sha256"] or resolve_path(root,ref["path"]).stat().st_size!=expected["bytes"]:
            raise ValueError("Source schema authority binding differs")
        read_bound(root,ref)


def _manifest_inputs(root, manifest, *, allow_artificial=False):
    rows=manifest.get("inputs",[])
    if (manifest.get("artifact_type")!="spot_macd_transfer_input_manifest_v1"
            or manifest.get("method_sha256")!=METHOD_SHA or manifest.get("policy")!=POLICY
            or manifest.get("source_nature") not in (("retained_official_history","artificial_protocol_fixture") if allow_artificial else ("retained_official_history",))
            or type(manifest.get("study_number")) is not int or manifest["study_number"]<=0
            or type(manifest.get("input_count")) is not int or manifest["input_count"]!=len(rows)
            or len({r["role"] for r in rows})!=len(rows) or not CORE_ROLES.issubset({r["role"] for r in rows})):
        raise ValueError("Complete exact spot manifest required")
    pins={}
    for row in rows:
        ref={"path":row["path"],"sha256":row["sha256"]}
        if type(row["bytes"]) is not int or resolve_path(root,row["path"]).stat().st_size!=row["bytes"]:
            raise ValueError("Source size changed")
        read_bound(root,ref); pins[row["role"]]=ref
    if len({v["path"] for v in pins.values()})!=len(pins) or pins["method"]["sha256"]!=METHOD_SHA:
        raise ValueError("Duplicate input or wrong method")
    validate_source_schema_policy(root,manifest,pins)
    # Layout is metadata only. The loader validates exact retained schema lazily.
    daily=manifest.get("daily_sources",[]); minute=manifest.get("minute_sources",[])
    ranges=[("2018-01-01","2018-01-01"),("2018-01-02","2018-12-31")]+[(f"{y}-01-01",f"{y}-12-31") for y in range(2019,2024)]+[("2024-01-01","2024-01-01")]
    months=[f"{y}-{m:02}" for y in range(2019,2025) for m in range(1,13) if (y,m)<=(2024,1)]
    if ([(r["first"],r["last"]) for r in daily]!=ranges or [r["month"] for r in minute]!=months
            or any(r["role"] not in pins or r["receipt_role"] not in pins for r in daily)
            or any(any(r[k] not in pins for k in ("zip_role","checksum_role","receipt_role")) for r in minute)):
        raise ValueError("Exact8daily partitions and61minute months required")
    return pins


def validate_registration(packet, root):
    if (not isinstance(packet,dict) or set(packet)!={"artifact_type","branch","input_manifest","inputs","implementation","environment","policy","registration_sha256"}
            or packet["artifact_type"]!="spot_macd_transfer_registration_v1" or packet["branch"]!=BRANCH
            or packet["policy"]!=POLICY or not isinstance(MANIFEST_SHA,str) or len(MANIFEST_SHA)!=64
            or packet["input_manifest"]!={"path":MANIFEST,"sha256":MANIFEST_SHA}
            or set(packet["implementation"])!=set(IMPLEMENTATION)
            or packet["registration_sha256"]!=digest(canonical({k:v for k,v in packet.items() if k!="registration_sha256"}))):
        raise ValueError("Exact root-frozen spot registration required")
    env=runtime_environment()
    if packet["environment"]!=env or env["python"]!="3.12.13" or env["dependencies"]!={"numpy":"2.4.6","pandas":"3.0.3"}:
        raise ValueError("Frozen full numeric runtime required")
    pins=_manifest_inputs(root,_json(read_bound(root,packet["input_manifest"],return_bytes=True)))
    if set(packet["inputs"])!=set(pins)|set(PM_INPUTS): raise ValueError("Exact input role union required")
    for role,ref in packet["inputs"].items():
        if (role in pins and ref!=pins[role]) or (role in PM_INPUTS and ref["path"]!=PM_INPUTS[role]):
            raise ValueError("Input alias changed")
        read_bound(root,ref)
    for name,ref in packet["implementation"].items():
        if ref["path"]!=name: raise ValueError("Implementation alias changed")
        read_bound(root,ref)
    campaign=_json(read_bound(root,packet["inputs"]["campaign"],return_bytes=True))
    now=datetime.now(timezone.utc)
    if (campaign.get("campaign_id")!="quant_manager_72h_20261106" or campaign.get("status")!="active"
            or campaign.get("task_branch")!=BRANCH or campaign.get("machine")!="office_desktop"
            or campaign.get("started_at")!="2026-11-06T16:21:39Z" or campaign.get("delivery_deadline")!="2026-11-09T16:21:39Z"
            or not datetime.fromisoformat(campaign["started_at"].replace("Z","+00:00"))<=now<datetime.fromisoformat(campaign["delivery_deadline"].replace("Z","+00:00"))
            or campaign.get("finite_preregistered_studies_required") is not True
            or campaign.get("old_consumed_scopes_remain_closed") is not True
            or campaign.get("holdout_unsealing_authorized") is not False or campaign.get("live_boundary_allowed") is not False):
        raise ValueError("Active fixed campaign with old/holdout/live closed required")
    return packet


def build_registration(root):
    if not isinstance(MANIFEST_SHA,str) or len(MANIFEST_SHA)!=64:
        raise ValueError("Actual manifest not frozen; financial registration unavailable")
    ref={"path":MANIFEST,"sha256":MANIFEST_SHA}
    pins=_manifest_inputs(root,_json(read_bound(root,ref,return_bytes=True)))
    pins.update({k:{"path":v,"sha256":file_digest(resolve_path(root,v))} for k,v in PM_INPUTS.items()})
    packet=dict(artifact_type="spot_macd_transfer_registration_v1",branch=BRANCH,input_manifest=ref,inputs=pins,
        implementation={p:{"path":p,"sha256":file_digest(resolve_path(root,p))} for p in IMPLEMENTATION},
        environment=runtime_environment(),policy=POLICY)
    packet["registration_sha256"]=digest(canonical(packet))
    return validate_registration(packet,root)


def require_unused(root):
    folder=resolve_path(root,DIRECTORY)
    names=("attempt_claim.json","financial_decode_started.json","decoded_input.json","outcome.json","result.json","accounts","account_index","statistics.json","guard_checks")
    if any((folder/name).exists() for name in names):
        raise ValueError("Spot study reserved or consumed; no resume")


def admitted_packet(root, *, unused=True):
    admission=_json(resolve_path(root,ADMISSION).read_bytes())
    paths=dict(registration=REGISTRATION,review=REVIEW,root_review=ROOT_REVIEW,comparison=COMPARISON)
    if (set(admission)!={"artifact_type","status","registration","review","root_review","comparison","policy"}
            or admission["artifact_type"]!="spot_macd_transfer_admission_v1" or admission["status"]!="authorized_once"
            or admission["policy"]!=POLICY or any(admission[k]["path"]!=v for k,v in paths.items())):
        raise ValueError("Separate exact spot admission required")
    packet=validate_registration(_json(read_bound(root,admission["registration"],return_bytes=True)),root)
    for key,who in (("review","quant_manager_72h"),("root_review","root")):
        r=_json(read_bound(root,admission[key],return_bytes=True))
        if (r.get("reviewer")!=who or r.get("status")!="accepted_for_one_conditional_spot_transfer"
                or r.get("registration_sha256")!=packet["registration_sha256"] or r.get("financial_execution_authorized") is not True
                or r.get("qualified") is not False or type(r.get("real_forward_days_added")) is not int or r["real_forward_days_added"]!=0):
            raise ValueError("Both exact reviews required")
    read_bound(root,admission["comparison"])
    if unused: require_unused(root)
    return packet,admission


def _scope(packet, root):
    return dict(registration_sha256=packet["registration_sha256"],admission_file_sha256=file_digest(resolve_path(root,ADMISSION)),policy=POLICY)


def scope(task, family_config, family_schedule, *, root, branch):
    if task!="factor_review" or branch!=BRANCH: return None
    if not resolve_path(root,ADMISSION).exists(): return None
    if (set(family_schedule.get("blockers",[]))!={"insufficient_active_research_families"}
            or family_schedule["summary"].get("primary_budget_share")!=0
            or family_schedule["summary"].get("active_primary_families")!=0): return None
    try: packet,_=admitted_packet(root)
    except (OSError,ValueError,KeyError,TypeError): return None
    return dict(mode=MODE,scope=_scope(packet,root))


def review_comparison(root, scope):
    packet,admission=admitted_packet(root)
    if canonical(scope)!=canonical(_scope(packet,root)): raise ValueError("Comparison scope changed")
    r=_json(read_bound(root,admission["comparison"],return_bytes=True))
    expected=dict(registration_sha256=packet["registration_sha256"],method_sha256=METHOD_SHA,
        inputs_sha256=digest(canonical(packet["inputs"])),implementation_sha256=digest(canonical(packet["implementation"])),
        environment_sha256=digest(canonical(packet["environment"])),policy=POLICY,
        holding_control_tested=True,holding_policy=POLICY["holding_policy"],uninterrupted_passive_holding_tested=False,
        comparison_purpose=POLICY["comparison_purpose"],alpha_or_promotion_eligible=False)
    if (r.get("status")!="accepted_fixed_spot_comparison" or r.get("reviewer") not in ("root","quant_manager_72h")
            or any(r.get(k)!=v for k,v in expected.items())):
        raise ValueError("Independent complete27account comparison review required")
    return dict(status="passed_specification_only",blockers=[],method=packet["inputs"]["method"],input_manifest=packet["input_manifest"],
        implementation=packet["implementation"],environment=packet["environment"],strategy_accounts=9,holding_controls=9,cash_controls=9,
        no_price_decoding_performed=True,net_positive_EV_verified=False,source_quality_verified=False,
        holding_control_tested=True,holding_policy=POLICY["holding_policy"],uninterrupted_passive_holding_tested=False,
        comparison_purpose=POLICY["comparison_purpose"],alpha_or_promotion_eligible=False)


_TOKEN=object()


class _Claim:
    def __init__(self,root,packet,admission,claim_hash,token):
        if token is not _TOKEN: raise ValueError("Durable claim handle required")
        self.root=Path(root).resolve(); self.packet=packet; self.admission=admission; self.claim_hash=claim_hash
        self.active=True; self.decoding_started=False; self.guard_count=0
        self.model_accounts_calculated=0
        self.admission_hash=file_digest(resolve_path(root,ADMISSION))
        self.manifest=_json(read_bound(root,packet["input_manifest"],return_bytes=True))
        self.source_nature=self.manifest["source_nature"]

    def guard(self,phase,identity):
        if not self.active: raise ValueError("Closed claim")
        if file_digest(resolve_path(self.root,DIRECTORY+"/attempt_claim.json"))!=self.claim_hash:
            raise ValueError("Claim changed")
        if file_digest(resolve_path(self.root,ADMISSION))!=self.admission_hash:
            raise ValueError("Admission changed")
        branch=subprocess.run(["git","symbolic-ref","--short","HEAD"],cwd=self.root,check=True,capture_output=True,text=True,timeout=10).stdout.strip()
        if branch!=BRANCH: raise ValueError("Execution branch changed")
        packet,admission=admitted_packet(self.root,unused=False)
        if canonical(packet)!=canonical(self.packet) or canonical(admission)!=canonical(self.admission):
            raise ValueError("Frozen packet changed")
        self.guard_count+=1
        write_exclusive_json(resolve_path(self.root,DIRECTORY+f"/guard_checks/{self.guard_count:03}.json"),
            dict(phase=phase,identity=identity,at=datetime.now(timezone.utc).isoformat(),all_bindings_checked=True,
                 registration_sha256=packet["registration_sha256"],fresh_initial_PM_gate_in_claim=True))

    def read(self,role):
        if not self.active: raise ValueError("Closed source access")
        return read_bound(self.root,self.packet["inputs"][role],return_bytes=True)

    def begin_financial_decode(self):
        if not self.active or self.decoding_started: raise ValueError("Decode once only")
        self.guard("before","first_numeric_parse")
        actual=self.source_nature=="retained_official_history"
        write_exclusive_json(resolve_path(self.root,DIRECTORY+"/financial_decode_started.json"),
            dict(at=datetime.now(timezone.utc).isoformat(),registration_sha256=self.packet["registration_sha256"],
                numerical_decode_started=True,financial_decode_started=actual,research_study_consumed=actual,
                study_number=self.manifest["study_number"] if actual else None,source_nature=self.source_nature,qualified=False))
        self.decoding_started=True


def execute_once(root, *, expected_registration_sha256, gate_supplier):
    packet,admission=admitted_packet(root)
    if expected_registration_sha256!=packet["registration_sha256"]: raise ValueError("Exact registration digest required")
    gate=gate_supplier(); safety=gate["safety"]
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(gate["generated_at"].replace("Z","+00:00"))).total_seconds()
    if (not 0<=age<=120 or gate["status"]!="ready" or gate["blockers"] or gate["mode"]!=MODE
            or gate["primary_market"]!="CN_ETF" or gate["selected"]!=dict(machine="office_desktop",task="factor_review",branch=BRANCH,current_branch=BRANCH)
            or safety.get("spot_macd_transfer_allowed") is not True or canonical(safety.get("spot_macd_transfer_scope"))!=canonical(_scope(packet,root))
            or any(safety.get(k) is not False for k in ("factor_batch_allowed","final_holdout_allowed","live_boundary_allowed"))):
        raise ValueError("Fresh exact spot PM gate required")
    review_comparison(root,_scope(packet,root))
    again,approval=admitted_packet(root)
    if canonical(again)!=canonical(packet) or canonical(approval)!=canonical(admission): raise ValueError("Admission changed during gate")
    folder=resolve_path(root,DIRECTORY)
    write_exclusive_json(folder/"attempt_claim.json",dict(claimed_at=datetime.now(timezone.utc).isoformat(),
        registration_sha256=expected_registration_sha256,admission_file_sha256=file_digest(resolve_path(root,ADMISSION)),
        status="claimed_before_numeric_decode",gate=gate,policy=POLICY,attempt_consumed_even_if_failed=True))
    claim=None
    outcome=dict(status="failed_consumed",qualified=False,real_forward_days_added=0,numerical_decode_started=False,
                 financial_decode_started=False,research_study_consumed=False,historical_returns_computed=False,model_accounts_completed=0)
    try:
        claim=_Claim(root,packet,admission,file_digest(folder/"attempt_claim.json"),_TOKEN)
        from quant_robot.research.spot_macd_transfer_historical import run_claimed_diagnostic, verify_final_artifacts
        result=run_claimed_diagnostic(claim)
        claim.guard("final","all27_and_statistics")
        verify_final_artifacts(claim,result)
        write_exclusive_json(folder/"result.json",result)
        outcome.update(status="completed",result_sha256=file_digest(folder/"result.json"),model_accounts_completed=27,
                       historical_returns_computed=result["historical_returns_computed"])
    except BaseException as exc:
        outcome["error_type"]=type(exc).__name__
        raise
    finally:
        started=claim is not None and claim.decoding_started
        actual=started and claim.source_nature=="retained_official_history"
        completed=len(list((folder/"account_index").glob("*.json")))
        calculated=claim.model_accounts_calculated if claim is not None else 0
        outcome.update(numerical_decode_started=started,financial_decode_started=actual,
            research_study_consumed=actual,study_number=claim.manifest["study_number"] if actual else None,
            model_accounts_completed=completed,model_accounts_calculated=calculated,
            historical_returns_computed=actual and calculated>0,
            full_fixed_27_completed=outcome["status"]=="completed",
            source_nature=claim.source_nature if claim is not None else None,registration_sha256=packet["registration_sha256"],
            finished_at=datetime.now(timezone.utc).isoformat(),guard_checks=claim.guard_count if claim is not None else 0)
        if claim is not None: claim.active=False
        write_exclusive_json(folder/"outcome.json",outcome)
    return outcome
