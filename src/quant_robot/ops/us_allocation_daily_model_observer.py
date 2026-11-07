"""Conditional after-close model observer, never certified opening execution.

Public artificial inputs are invented. A real context requires an exact release
and two reviews, but this module neither creates those nor retrieves market data.
"""
from __future__ import annotations
import copy
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D, localcontext
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

from quant_robot.ops import us_allocation_paper_journal as journal
from quant_robot.ops import us_allocation_source_contract as source
from quant_robot.research import us_monthly_rotation as kernel

SCHEMA = "us_allocation_daily_model_manifest_v1"
METHOD_SHA = "f0e37813dfa0d44b62cfef2888e9bd05ef6a5801f58f55d67e72ce396ca7aad7"
_CAPABILITY = object()
_check, _instant, _number = journal._check, journal._instant, journal._number
_bytes, _sha = journal._bytes, journal._sha
ASSETS = kernel.ASSETS
ROLES = {"primary": ("1.00", 10), "stress": ("2.50", 30)}
PRODUCTION_DATA = Path("F:/lhjqr/data/reports/us_allocation_model_20261109_20261207")


def _ref(path):
    path = Path(path).resolve(); raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def _runtime():
    return dict(files=[_ref(Path(m.__file__)) for m in (sys.modules[__name__], journal, source, kernel)],
                python=list(sys.version_info[:3]), decimal=kernel.context_record(kernel.CONTEXT))


def _write(path, value):
    expected = dict(path=str(path.resolve()), sha256=hashlib.sha256(_bytes(value)).hexdigest(), bytes=len(_bytes(value)))
    journal._publish(path, value)
    _check(_ref(path) == expected, "Exact published artifact required")
    return expected


def _bound(root, ref):
    _check(source._ref(ref), "Exact file reference required")
    path = (root/Path(ref["path"])).resolve()
    _check(path.is_relative_to(root), "Release files must stay within root")
    observed = _ref(path)
    _check(observed["sha256"] == ref["sha256"] and observed["bytes"] == ref["bytes"], "Bound file changed")
    return path, observed


@dataclass(frozen=True)
class _Context:
    kind: str
    manifest_sha256: str
    runtime_sha256: str
    bindings: tuple
    release_sha256: str | None
    normalizer_sha256: str | None
    not_before: str | None
    expires_at: str | None
    capability: object

    def __post_init__(self):
        _check(self.capability is _CAPABILITY, "Use reviewed context factories")

    @property
    def real(self): return self.kind == "conditional_forward_model"


def _manifest(manifest, kind):
    _check(manifest.get("schema") == SCHEMA and manifest.get("method_sha256") == METHOD_SHA
           and manifest.get("evidence_kind") == kind and manifest.get("assets") == list(ASSETS)
           and manifest.get("initial_cash") == "1000.00" and manifest.get("role") in ROLES, "Fixed observer identity required")
    sessions = manifest["schedule"]["sessions"]; dates = [x["date"] for x in sessions]
    _check(len(dates) >= 26 and dates == sorted(set(dates)), "Complete ordered calendar required")
    parsed = [date.fromisoformat(d) for d in dates]
    _check(all(d.isoformat() == s for d,s in zip(parsed,dates)), "Canonical calendar dates required")
    if kind == "artificial":
        _check(manifest.get("constructed_from_market_data") is False and all(2000 <= d.year <= 2004 for d in parsed), "Invented2000to2004 only")
    else:
        observed = [d for d in dates if "2026-11-09" <= d <= "2026-12-07"]
        _check(manifest.get("first_decision_date") == "2026-11-30"
               and manifest.get("last_observation_date") == "2026-12-07"
               and len(observed) == 20 and observed[0] == "2026-11-09" and observed[-1] == "2026-12-07"
               and "2026-11-26" not in dates and dates[-1] == "2026-12-08", "Fixed20session calendar required")
    first = dates.index(manifest["first_decision_date"])
    _check(first+4 < len(dates) and dates[first][:7] != dates[first+1][:7], "First decision must be a completed calendar month end")
    _check(type(manifest.get("authorities")) is dict, "External declared authorities required")


def artificial_context(manifest):
    _manifest(manifest, "artificial")
    return _Context("artificial", _sha(manifest), _sha(_runtime()), (), None, None, None, None, _CAPABILITY)


def admitted_context(root, manifest_ref, release_ref, manager_review_ref, root_review_ref):
    """Pure hash/metadata admission; no financial parser and no Boolean unlock."""
    root = Path(root).resolve(); refs = (manifest_ref, release_ref, manager_review_ref, root_review_ref)
    loaded, bound = [], []
    for ref in refs:
        path, exact = _bound(root, ref); loaded.append(json.loads(path.read_bytes())); bound.append(exact)
    manifest, release, manager, review = loaded
    _manifest(manifest, "conditional_forward_model")
    for ref in [manifest["schedule"]["source_ref"]]+[a["definition_ref"] for a in manifest["authorities"].values()]:
        _,exact = _bound(root,ref);bound.append(exact)
    role_manifests = release.get("manifests", {})
    _check(set(role_manifests) == set(ROLES) and role_manifests[manifest["role"]] == manifest_ref,
           "Both exact role manifests required")
    manifest_bindings = {}
    for role, ref in role_manifests.items():
        path, exact = _bound(root, ref); other = json.loads(path.read_bytes()); bound.append(exact)
        _manifest(other, "conditional_forward_model")
        _check(other["role"] == role and {k:v for k,v in other.items() if k != "role"}
               == {k:v for k,v in manifest.items() if k != "role"}, "Roles must share one fixed model and sources")
        manifest_bindings[role] = dict(canonical_sha256=_sha(other), file_sha256=exact["sha256"])
    normalizer = release["normalizer"]
    _check(source._ref(normalizer) and Path(normalizer["path"]).resolve() == Path(source.__file__).resolve()
           and _ref(normalizer["path"]) == normalizer, "Exact imported source normalizer required")
    bound.append(normalizer)
    binding = dict(method_sha256=METHOD_SHA, manifests=manifest_bindings, runtime_sha256=_sha(_runtime()),
                   source_authorities_sha256=_sha(manifest["authorities"]), normalizer_sha256=normalizer["sha256"])
    _check(release.get("schema") == "us_daily_model_release_v1" and release.get("role") == "root_release"
           and release.get("status") == "admitted_conditional_model" and release.get("binding") == binding
           and release.get("manager_review_sha256") == bound[2]["sha256"]
           and release.get("root_review_sha256") == bound[3]["sha256"], "Exact root release required")
    for value, role in ((manager,"manager_review"),(review,"root_review")):
        _check(value.get("schema") == "us_daily_model_review_v1" and value.get("role") == role
               and value.get("status") == "accepted" and value.get("binding") == binding, "Exact review roles required")
    now = datetime.now(timezone.utc)
    _check(_instant(release["not_before"]) <= now < _instant(release["expires_at"])
           <= _instant("2026-12-08T02:00:00Z"), "Release outside allowed window")
    return _Context("conditional_forward_model", _sha(manifest), binding["runtime_sha256"],
        tuple((x["path"],x["sha256"],x["bytes"]) for x in bound), bound[1]["sha256"], normalizer["sha256"],
        release["not_before"], release["expires_at"], _CAPABILITY)


def _guard(context, manifest):
    _check(type(context) is _Context and context.capability is _CAPABILITY
           and context.manifest_sha256 == _sha(manifest) and context.runtime_sha256 == _sha(_runtime()), "Context/runtime mismatch")
    for path, sha, size in context.bindings:
        _check(_ref(path) == dict(path=path,sha256=sha,bytes=size), "Release input changed")
    if context.real:
        now = datetime.now(timezone.utc)
        _check(_instant(context.not_before) <= now < _instant(context.expires_at), "Release expired; no automatic extension")


def _clock(context, injected):
    _check(not context.real or injected is None, "Real clock cannot be injected")
    return datetime.now(timezone.utc) if context.real else _instant(injected)


class _State:
    def __init__(self, manifest):
        self.manifest = copy.deepcopy(manifest)
        self.sessions = manifest["schedule"]["sessions"]
        self.dates = [x["date"] for x in self.sessions]
        self.account = None; self.normalized = None
        self.status = "source_waiting"; self.assessment = None; self.reason = None; self.observed = 0
        self.receipts = []; self.blocked = False

    def block(self, reason):
        self.blocked = True; self.status = "blocked_continuity_no_backfill"; self.reason = reason

    def apply(self, event, prior_ref, prior_clock):
        if self.blocked: return
        if event.get("payload_failure") is True:
            self.block("invalid_daily_payload_no_backfill"); return
        packet = event["source_evidence"]; stamp = _instant(event["recorded_at"])
        self.assessment = source.assess_source_metadata(packet, self.manifest["schedule"], authorities=self.manifest["authorities"])
        if not self.assessment["requirements_met"]:
            if self.account is not None: self.block("source_unknown_or_late")
            else: self.reason = "source_unknown_before_initialization"
            return
        i = self.dates.index(packet["session_date"])
        if packet["purpose"] == "daily_model" and packet["session_date"] > self.manifest.get("last_observation_date",self.dates[-2]):
            self.block("outside_fixed_observation_window"); return
        deadline = _instant(self.sessions[i]["open_at"] if packet["purpose"] == "warmup" else self.sessions[i+1]["open_at"])
        if not _instant(packet["received_at"]) <= stamp < deadline:
            self.block("missed_processing_deadline"); return
        if self.account is None:
            if packet["purpose"] != "warmup": self.reason = "warmup_required"; return
            if self.dates[i-1] >= self.manifest["first_decision_date"]:
                self.block("initialization_after_first_decision_not_permitted"); return
            payload = event["payload"]
            _check(payload.get("kind") == "warmup" and [r["date"] for r in payload["days"]] == packet["warmup_dates"], "Exact warmup rows required")
            bars = [None for _ in self.dates]
            for j,row in zip(range(i-20,i), payload["days"]):
                _check(set(row["prices"]) == set(ASSETS), "Four warmup assets required")
                bars[j] = {a: dict(close=_number(row["prices"][a]["close"],positive=True),
                                  volume=_number(row["prices"][a]["volume"])) for a in ASSETS}
            self.normalized = dict(dates=self.dates,bars=bars,execution=[None for _ in self.dates],
                                   dividends=[],signals={},first=i-1,terminal=len(self.dates))
            minimum,slip = ROLES[self.manifest["role"]]
            self.account = kernel._Account(SimpleNamespace(normalized=self.normalized),"fixed_quarters",minimum,slip)
            self.status = "initialized_cash_waiting_normal_month_end"; self.reason = None
        else:
            if packet["purpose"] != "daily_model" or i != self.account.i+1:
                self.block("missing_or_repeated_session"); return
            if (packet.get("previous_committed_decision_ref") != prior_ref
                or packet.get("previous_committed_decision_at") != prior_clock
                or packet.get("previous_observed_session_date") != self.dates[self.account.i]):
                self.block("prior_durable_state_not_bound"); return
            self._daily(event, i); self.observed += 1; self.status = "conditional_model_observed"
        self.receipts.append(copy.deepcopy(packet))

    def _daily(self, event, i):
        a,p = self.account,self.normalized; packet,payload = event["source_evidence"],event["payload"]
        _check(payload.get("kind") == "daily_model" and payload.get("date") == self.dates[i]
               and set(payload["prices"]) == set(ASSETS)
               and not payload.get("splits") and not payload.get("capital_gains"), "One exact supported daily payload required")
        p["bars"][i] = {s:{k:_number(payload["prices"][s][k],positive=k!="volume")
                            for k in ("open","close","volume")} for s in ASSETS}
        p["execution"][i] = {s:dict(suspended=None,buy_blocked=None,sell_blocked=None) for s in ASSETS}
        ids = {x["id"] for x in p["dividends"]}
        for item in payload.get("dividends",[]):
            _check(type(item["id"]) is str and item["id"] not in ids and item["symbol"] in ASSETS
                   and item["ex_date"] == self.dates[i], "Past/mismatched dividend cannot rewrite observations")
            ids.add(item["id"])
            p["dividends"].append(dict(id=item["id"],symbol=item["symbol"],ex_index=i,
                amount_per_share=_number(item["amount_per_share"]),
                earliest_payment_date=(date.fromisoformat(item["ex_date"])+timedelta(days=45)).isoformat()))
        a.i=i; a.reference=a.previous
        start,prior_q = a.balances(),dict(a.q)
        prior_marks = {s:p["bars"][i-1][s]["close"] for s in ASSETS}
        first_fill,first_action,first_obs = len(a.fills),len(a.actions),len(a.observations)
        a.day_active,a.triggered = bool(any(a.q.values())),False
        if a.paused and a.cooldown>=5 and not any(a.q.values()):
            a.paused,a.cooldown=False,0
            a.risks.append(dict(index=i,kind="resume_only_at_next_monthly_decision"))
        carried_risk=a.risk_due is not None and a.risk_due<=i
        entitled=a.opening_actions(); a.observe(a.marks("open"),"prior_held_open")
        if carried_risk:
            if a.pending:a.pending["status"]="cancelled_by_terminal_or_prior_risk"
            a.pending=None; a.exit_orders("risk_exit"); a.risk_due=i+1 if any(a.q.values()) else None
        elif a.pending:
            plan=a.pending
            if i==plan["sell_index"]:
                for order in plan["sell_orders"]:a.fill(order)
            if i==plan["buy_index"]:
                for order in plan["buy_orders"]:a.fill(order)
                if plan["status"]!="cancelled_increases_by_risk":plan["status"]="completed_monthly_attempt"
                a.pending=None
        if not any(a.q.values()) and a.risk_due is not None:a.risk_due=None
        marks=a.marks("close"); nav=a.observe(marks,"completed_close")
        no_increase=a.pending is None or not any(o["quantity"] for o in a.pending.get("buy_orders",[]))
        if a.paused:a.cooldown=a.cooldown+1 if not a.day_active and not a.triggered and no_increase and not any(a.q.values()) else 0
        if a.pending and i==a.pending["plan_index"]:a.plan_buys(a.pending)
        fills=a.fills[first_fill:]
        attribution=dict(carried_exposure=sum((prior_q[s]*(marks[s]-prior_marks[s]) for s in ASSETS),kernel.ZERO),
            trade_timing=sum(((f["quantity"] if f["side"]=="buy" else -f["quantity"])*(marks[f["asset"]]-f["raw_open"]) for f in fills),kernel.ZERO),
            net_dividend_entitlement=entitled,commissions=-sum((f["fee"] for f in fills),kernel.ZERO),
            sell_levies=-sum((f["sell_levy"] for f in fills),kernel.ZERO),slippage=-sum((f["slippage_cost"] for f in fills),kernel.ZERO))
        _check(sum(attribution.values(),kernel.ZERO)==nav-a.previous,"Daily NAV identity")
        for fill in fills:fill.update(model_only=True,execution_certified=False,source_received_at=packet["received_at"],
            modeled_open_at=self.sessions[i]["open_at"],volume_observation_clock="after_close_source_receipt_not_order_capacity")
        for action in a.actions[first_action:]:action.update(model_only=True,source_received_at=packet["received_at"],
            entitlement_known_before_open=False if action["kind"]=="ex_entitlement" else None)
        a.days.append(dict(index=i,date=self.dates[i],before=start,after=a.balances(),NAV=nav,PnL=nav-a.previous,
                          peak=a.peak,observed_maxDD=a.max_dd,paused=a.paused,cooldown=a.cooldown,attribution=attribution,
                          previous_marks=prior_marks,marks=marks,previous_NAV=a.previous,
                          risk_exit_due_index=a.risk_due,observation_range=[first_obs,len(a.observations)],
                          source_received_at=packet["received_at"],model_only=True))
        year=self.dates[i][:4];a.annual[year]=a.annual.get(year,kernel.ZERO)+nav-a.previous;a.previous=nav
        if self.dates[i]>=self.manifest["first_decision_date"] and i+1<len(self.dates) and self.dates[i][:7]!=self.dates[i+1][:7]:
            p["signals"][i]=dict(index=i,date=self.dates[i],model="fixed_calendar_quarters",
                weights={"fixed_quarters":dict.fromkeys(ASSETS,D(".25"))},ordinary_execution_possible=i+4<len(self.dates))
            a.decision(i)

    def snapshot(self):
        a=self.account; real=self.manifest["evidence_kind"]=="conditional_forward_model"
        ledger=None if a is None else dict(date=self.dates[a.i],balances=a.balances(),NAV=a.previous,peak=a.peak,
            maxDD=a.max_dd,previous_DD=a.previous_dd,paused=a.paused,cooldown=a.cooldown,risk_due=a.risk_due,
            pending=a.pending,FIFO=a.lots,days=a.days,fills=a.fills,actions=a.actions,risks=a.risks,
            observations=a.observations,monthly_events=a.events,intents=a.intents,rejections=a.rejections,
            unknown_execution_constraints=a.unknowns,annual=a.annual,total_commission=a.total_fee,
            total_slippage=a.total_slip,total_sell_levy=a.total_levy)
        return kernel.serial(dict(schema="us_daily_model_snapshot_v1",evidence_kind=self.manifest["evidence_kind"],
            method_sha256=METHOD_SHA,role=self.manifest["role"],currency="USD",
            minimum_commission=ROLES[self.manifest["role"]][0],slippage_bps=ROLES[self.manifest["role"]][1],
            execution_model="conditional_open_price_model",execution_certified=False,qualified=False,real_forward_days=0,
            model_forward_days=self.observed if real else 0,artificial_model_days=0 if real else self.observed,
            status=self.status,reason=self.reason,source_assessment=self.assessment,ledger=ledger,
            observation_window_end_action="stop_new_observations_without_liquidation",
            source_receipts=self.receipts,model_limitations=["Open risk cancellation is counterfactual afterclose modeling",
            "Provider finality unknown; action completeness only query snapshot; no auction execution certification"]))


def _commit(root, manifest_sha, count, last_sha, previous, clock):
    ref=_write(root/f"commit_{count:06d}.json",dict(manifest_sha256=manifest_sha,count=count,last_sha256=last_sha,
        previous_commit=previous,confirmed_at=clock))
    pointer=root/"head.next";_write(pointer,ref);os.replace(pointer,root/"head.json")
    _check((root/"head.json").read_bytes()==_bytes(ref),"Head publication changed")
    return ref


def _restore(root, context):
    _check(not (root/"head.next").exists(),"Incomplete head requires review")
    manifest=json.loads((root/"manifest.json").read_bytes());_guard(context,manifest)
    if context.real:_check(root==(PRODUCTION_DATA/"journals"/manifest["role"]).resolve(),"Fixed production journal path required")
    pointer=json.loads((root/"head.json").read_bytes())
    _check(Path(pointer["path"]).resolve().parent==root,"Head must reference this journal")
    _check(_ref(pointer["path"])==pointer,"Head target changed")
    head=json.loads(Path(pointer["path"]).read_bytes());count=head["count"]
    _check(type(count) is int and count>=0 and len(list(root.glob("input_*.json")))==count
           and len(list(root.glob("commit_*.json")))==count+1,"Journal tail count changed")
    state=_State(manifest);previous=_sha(manifest);prior_ref=None
    for i in range(count+1):
        path=root/f"commit_{i:06d}.json";current=json.loads(path.read_bytes())
        _check(current["count"]==i and current["manifest_sha256"]==_sha(manifest)
               and current["previous_commit"]==prior_ref,"Commit chain changed")
        if i:
            record=json.loads((root/f"input_{i:06d}.json").read_bytes())
            _check(record["previous_commit"]==prior_ref,"Input causality anchor changed")
            state.apply(record["event"],prior_ref,prior_clock)
            _check(record["snapshot_sha256"]==_sha(state.snapshot()),"Replay differs")
            previous=_sha(record)
        _check(current["last_sha256"]==previous,"Input bytes changed")
        prior_ref=_ref(path);prior_clock=current["confirmed_at"]
    _check(prior_ref==pointer,"Head does not refer to final commit")
    return state,pointer,head


def create(directory, manifest, *, context, injected_at=None):
    with localcontext(kernel.CONTEXT):
        _guard(context,manifest);_manifest(manifest,context.kind)
        clock=_clock(context,injected_at).isoformat();root=Path(directory).resolve()
        if context.real:_check(root==(PRODUCTION_DATA/"journals"/manifest["role"]).resolve(),"Fixed production journal path required")
        root.mkdir(parents=True,exist_ok=False)
        _write(root/"manifest.json",manifest)
        ref=_commit(root,_sha(manifest),0,_sha(manifest),None,clock)
        return dict(_State(manifest).snapshot(),committed_ref=ref,committed_at=clock)


def status(directory, *, context):
    with localcontext(kernel.CONTEXT):
        root=Path(directory).resolve();_check(not (root/"writer.lock").exists(),"Unfinished writer requires review")
        state,ref,head=_restore(root,context)
        return dict(state.snapshot(),committed_ref=ref,committed_at=head["confirmed_at"])


def advance(directory, source_evidence, payload, *, context, injected_at=None):
    """A missed/unknown active day is persisted blocked; it is never backfilled."""
    root=Path(directory).resolve();lock=root/"writer.lock"
    with lock.open("xb"):pass
    completed=False;published=False
    try:
        with localcontext(kernel.CONTEXT):
            state,prior,head=_restore(root,context)
            _check(not state.blocked,"Blocked observer cannot resume automatically")
            clock=_clock(context,injected_at)
            _check(clock>_instant(head["confirmed_at"]),"Monotonic journal clock required")
            if context.real:
                provenance=payload.get("normalization",{})
                body={k:v for k,v in payload.items() if k!="normalization"}
                _check(provenance.get("normalizer_sha256")==context.normalizer_sha256
                       and provenance.get("payload_sha256")==_sha(body),"Admitted normalizer and payload binding required")
                expected=[source_evidence["source_ref"]]+[source_evidence["records"][s]["source_ref"] for s in ASSETS]
                _check(provenance.get("source_refs")==expected,"Source provenance differs")
                for ref in expected:
                    _check(_ref(ref["path"])==ref,"Bound source artifact changed")
            event=dict(source_evidence=source_evidence,payload=payload,recorded_at=clock.isoformat(),
                       release_sha256=context.release_sha256,clock_kind="physical_UTC" if context.real else "injected_artificial")
            try:state.apply(event,prior,head["confirmed_at"])
            except (ValueError,KeyError,TypeError,ArithmeticError):
                # Invalid financial/action packets cannot partially mutate the account.
                state,prior,head=_restore(root,context);state.block("invalid_daily_payload_no_backfill")
                event["payload_failure"]=True
            record=dict(previous_commit=prior,event=event,snapshot_sha256=_sha(state.snapshot()))
            # A failed payload has a separate deterministic replay transition.
            count=head["count"]+1
            _write(root/f"input_{count:06d}.json",record);published=True
            actual=_clock(context,injected_at).isoformat()
            ref=_commit(root,context.manifest_sha256,count,_sha(record),prior,actual)
            if context.real and not state.blocked and state.account is not None:
                next_index=state.account.i+1
                _check(next_index<len(state.sessions) and datetime.now(timezone.utc)<_instant(state.sessions[next_index]["open_at"]),
                       "Publication missed next open; leave unfinished lock")
            restored,_,_=_restore(root,context)
            _check(_sha(restored.snapshot())==_sha(state.snapshot()),"Published state differs")
            _guard(context,state.manifest);completed=True
            return dict(state.snapshot(),committed_ref=ref,committed_at=actual)
    finally:
        if completed or not published:lock.unlink()


def advance_normalized(directory, normalized, *, context, injected_at=None):
    """Consume one bound normalizer result; share raw values across both roles.

Only the prior-journal pointer differs per role. Provider dates/clocks and values
are copied unchanged. This function does not parse or retrieve a raw source.
"""
    _check(normalized.get("schema") == "us_source_normalized_packet_v1"
           and normalized.get("numeric_decode_marker") is not None, "Bound normalized packet required")
    expected="conditional_provider_observation" if context.real else "artificial_source_values"
    _check(normalized.get("evidence_kind")==expected, "Normalized evidence cannot be relabeled")
    packet=copy.deepcopy(normalized["source_metadata"])
    if context.real:
        identity=normalized.get("context_identity",{})
        refs={s:packet["records"][s]["source_ref"] for s in ASSETS}
        _check(identity.get("purpose")==packet["purpose"] and identity.get("test_values") is False
               and identity.get("evidence_kind")==expected and identity.get("release_sha256")==context.release_sha256
               and identity.get("packet_sha256")==source._digest(packet)
               and identity.get("source_refs_sha256")==source._digest(refs)
               and normalized.get("source_refs")==refs,"Normalizer context/source binding differs")
        marker=normalized["numeric_decode_marker"]
        _check(source._ref(marker) and _ref(marker["path"])==marker,"Exact numeric decode marker required")
    saved=status(directory,context=context)
    if packet["purpose"]=="daily_model":
        _check(len(normalized["days"])==1 and normalized["days"][0]["date"]==packet["session_date"],"One exact daily row")
        packet["previous_committed_decision_ref"]=saved["committed_ref"]
        packet["previous_committed_decision_at"]=saved["committed_at"]
        _check(saved["ledger"] is not None,"Initialize before model observation")
        packet["previous_observed_session_date"]=saved["ledger"]["date"]
        payload=dict(kind="daily_model",date=packet["session_date"],prices=copy.deepcopy(normalized["days"][0]["prices"]),
                     dividends=copy.deepcopy(normalized["dividends"]))
    else:
        _check(packet["purpose"]=="warmup","No strict-open route through model observer")
        _check(not normalized["dividends"],"Warmup dividend rights are not inherited")
        payload=dict(kind="warmup",days=copy.deepcopy(normalized["days"]))
    payload["normalization"]=dict(normalizer_sha256=context.normalizer_sha256,
        payload_sha256=_sha(payload),source_refs=[packet["source_ref"]]+[packet["records"][s]["source_ref"] for s in ASSETS],
        numeric_decode_marker=normalized["numeric_decode_marker"],original_packet_sha256=_sha(normalized["source_metadata"]))
    payload["normalization"]["context_identity"]=copy.deepcopy(normalized.get("context_identity"))
    return advance(directory,packet,payload,context=context,injected_at=injected_at)
