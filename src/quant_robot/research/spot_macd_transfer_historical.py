"""Claim-only native-daily/archive-minute adapter and fixed27-account replay.

Import does not open any source. Exact original dates are retained. Modeled
historical availability is distinct from the actual retained receipt clock.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import localcontext
import hashlib
import io
import json
from pathlib import Path
import re
from zipfile import ZipFile

from quant_robot.research import spot_macd_transfer_admission as admission

UTC=timezone.utc
DAY_MS=86_400_000
MINUTE_MS=60_000
FIRST=date(2018,1,1)
EXEC_FIRST=date(2019,1,2)
LAST=date(2024,1,1)
EXEC_LAST=date(2024,1,2)
ARCHIVE_COLUMNS=('open_time','open','high','low','close','volume','close_time','quote_asset_volume',
                 'number_of_trades','taker_buy_base_asset_volume','taker_buy_quote_asset_volume','ignore')


def _ms(day, minute=0):
    return int(datetime.combine(day,datetime.min.time(),UTC).timestamp())*1000+minute*MINUTE_MS


def _clock(value):
    if not isinstance(value,str): raise ValueError("Actual receipt clock must be a string")
    result=datetime.fromisoformat(value.replace("Z","+00:00"))
    if result.tzinfo is None or result.utcoffset()!=timedelta(0):
        raise ValueError("Explicit actual UTC receipt required")
    return result


def _receipt_evidence(claim, descriptor):
    path=descriptor.get("received_at_path")
    if not isinstance(path,list) or not path or any(not (isinstance(p,str) and p or type(p) is int and p>=0) for p in path):
        raise ValueError("Exact source-specific receipt-clock path required")
    clock_kind=descriptor.get("receipt_clock_kind")
    if clock_kind not in ("tool_return_received_at","http_body_received_at",
                          "source_capture_completed_at","source_capture_completed_at_upper_bound","received_or_failed_at"):
        raise ValueError("Explicit retained clock semantics required")
    raw=claim.read(descriptor["receipt_role"])
    line=descriptor.get("receipt_line_1based")
    if line is not None:
        lines=raw.splitlines()
        if type(line) is not int or not 1<=line<=len(lines): raise ValueError("Exact retained JSONL line required")
        raw=lines[line-1]
    receipt=admission._json(raw)
    value=receipt
    for key in path:
        if isinstance(key,str) and isinstance(value,dict) and key in value: value=value[key]
        elif type(key) is int and isinstance(value,list) and key<len(value): value=value[key]
        else: raise ValueError("Receipt clock path absent")
    actual=_clock(value)
    if actual>datetime.now(UTC): raise ValueError("Receipt clock is in the future")
    return dict(receipt=claim.packet["inputs"][descriptor["receipt_role"]],
        received_at_path=path, receipt_line_1based=line, retained_capture_clock=value,
        clock_kind=clock_kind, exact_body_received_at_verified=clock_kind=="http_body_received_at",
        tool_return_received_at_verified=clock_kind=="tool_return_received_at",
        local_capture_completion_upper_bound=clock_kind in ("source_capture_completed_at","source_capture_completed_at_upper_bound"),
        historical_first_publication_verified=False)


def _native_rows(raw):
    """The observed native shape has result wrappers on BOTH mirrors."""
    obj=admission._json(raw)
    if (not isinstance(obj,dict) or set(obj)!={"content","isError","structuredContent"}
            or obj["isError"] is not False or not isinstance(obj["content"],list) or len(obj["content"])!=1):
        raise ValueError("Exact native outer shape required")
    text=obj["content"][0]
    if not isinstance(text,dict) or set(text)!={"type","text"} or text["type"]!="text" or not isinstance(text["text"],str):
        raise ValueError("One native text mirror required")
    left,right=admission._json(text["text"]),obj["structuredContent"]
    if (not isinstance(left,dict) or not isinstance(right,dict) or set(left)!={"result"} or set(right)!={"result"}
            or admission.canonical(left)!=admission.canonical(right) or not isinstance(left["result"],list)):
        raise ValueError("Exact native result mirrors disagree")
    for r in left["result"]:
        if (not isinstance(r,list) or len(r)!=12 or any(type(r[k]) is not int for k in (0,6,8))
                or any(not isinstance(r[k],str) for k in (1,2,3,4,5,7,9,10,11)) or r[8]<0):
            raise ValueError("Native12-field token schema differs")
    return left["result"]


def _daily(raw, first, last, *, source_time_exception=None):
    if source_time_exception is not None:
        from quant_robot.research.spot_macd_transfer_time_exception import ExactDailyTimeProof
        if type(source_time_exception) is not ExactDailyTimeProof:raise ValueError("Verified exact source proof required")
        source_time_exception.validate_source(raw,first,last)
    from quant_robot.research import spot_macd_transfer as model
    start,end=date.fromisoformat(first),date.fromisoformat(last)
    rows=_native_rows(raw)
    if len(rows)!=(end-start).days+1: raise ValueError("Daily source coverage incomplete")
    result=[]
    with localcontext(model.context()):
        for i,r in enumerate(rows):
            day=start+timedelta(days=i)
            if r[0]!=_ms(day) or (r[6]!=_ms(day)+DAY_MS-1 and not (source_time_exception is not None
                    and source_time_exception.accepts_close(day.isoformat(),r[0],r[6]))):
                raise ValueError("Daily UTC clock or order mismatch")
            o,h,l,c=(model.number(r[k],positive=True) for k in (1,2,3,4))
            model.number(r[5])
            if l>min(o,c) or h<max(o,c) or h<l: raise ValueError("Daily OHLC invalid")
            result.append(dict(date=day.isoformat(),open=r[1],high=r[2],low=r[3],close=r[4],volume=r[5]))
    return result


def _archive_targets(raw, checksum_raw, month):
    """Check ordered month clocks/CRC and exact target coverage, not every minute.

    ZIP decompression and CSV tokenization necessarily touch other rows, but
    their financial tokens are never converted, used by the model, or emitted.
    """
    from quant_robot.research import spot_macd_transfer as model
    filename=f"BTCUSDT-1m-{month}.zip"
    match=re.fullmatch(r"([0-9a-fA-F]{64})[ \t]+\*?([^\r\n]+)\r?\n?",checksum_raw.decode("ascii"))
    if not match or match[2]!=filename or match[1].lower()!=admission.digest(raw):
        raise ValueError("Archive filename/checksum mismatch")
    if len(raw)>16*1024*1024: raise ValueError("Monthly compressed source exceeds bound")
    year,month_num=map(int,month.split("-")); first=date(year,month_num,1)
    days=calendar.monthrange(year,month_num)[1]
    expected={_ms(first+timedelta(days=i),3) for i in range(days) if EXEC_FIRST<=first+timedelta(days=i)<=EXEC_LAST}
    targets=[];seen=set();previous=None;header=False;inflated=0
    with ZipFile(io.BytesIO(raw)) as z, localcontext(model.context()):
        members=z.infolist()
        if (len(members)!=1 or members[0].filename!=filename[:-4]+".csv" or members[0].is_dir()
                or not 0<members[0].file_size<=32*1024*1024 or members[0].flag_bits&1):
            raise ValueError("Exact single bounded monthly CSV required")
        count=0
        with z.open(members[0]) as binary:
            while True:
                line=binary.readline(4097)
                if not line:break
                inflated+=len(line)
                if len(line)>4096 or inflated>32*1024*1024:raise ValueError("Monthly CSV line/inflation bound")
                body=line.rstrip(b"\r\n")
                if body==','.join(ARCHIVE_COLUMNS).encode('ascii'):
                    if header or count:raise ValueError("Repeated or misplaced archive header")
                    header=True;continue
                literal=body.partition(b',')[0]
                if body.count(b',')!=11 or not re.fullmatch(rb'[0-9]+',literal):
                    raise ValueError("Exact12-field minute clock schema required")
                stamp=int(literal)
                if not _ms(first)<=stamp<_ms(first)+days*DAY_MS or stamp%MINUTE_MS or (previous is not None and stamp<=previous):
                    raise ValueError("Monthly minute duplicate/unordered/out-of-range")
                previous=stamp;count+=1
                if stamp not in expected:continue
                row=body.split(b',')
                if not re.fullmatch(rb'[0-9]+',row[6]) or int(row[6])!=stamp+MINUTE_MS-1:
                    raise ValueError("Target close_time mismatch")
                o,v=row[1].decode('ascii'),row[5].decode('ascii')
                model.number(o,positive=True);model.number(v)
                d=datetime.fromtimestamp(stamp//1000,UTC).date().isoformat()
                targets.append(dict(date=d,open_time=d+"T00:03:00Z",close_time=d+"T00:03:59.999Z",open=o,volume=v))
                seen.add(stamp)
        if seen!=expected:raise ValueError("Exact target minute missing")
        if inflated!=members[0].file_size:raise ValueError("Archive inflation length mismatch")
    return targets,dict(month=month,rows=count,target_rows=len(targets),checksum_verified=True,CRC_read_to_EOF=True,
        numeric_fields_decoded_only=["target00:03.open","target00:03.volume"],other_financial_tokens_used=False,
        header_present=header,coverage_level="exact_target_times_only",full_month_minute_contiguity_verified=False)


@dataclass(frozen=True)
class LoadedHistory:
    fixture: dict
    provenance: dict
    digest: str

    def verify(self):
        if admission.digest(admission.canonical(dict(fixture=self.fixture,provenance=self.provenance)))!=self.digest:
            raise ValueError("Decoded in-memory evidence changed")


def load_claimed_inputs(claim, *, source_time_exception=None):
    if not isinstance(claim,admission._Claim) or not claim.active or claim.decoding_started:
        raise ValueError("Unused durable claim required to decode sources")
    if source_time_exception is not None:
        from quant_robot.research.spot_macd_transfer_time_exception import ExactDailyTimeProof
        if type(source_time_exception) is not ExactDailyTimeProof:raise ValueError("Verified exact source proof required")
        source_time_exception.validate_claim(claim)
    # All file hashes, source layout, and receipt clocks before numeric decode.
    claim.guard("before","load_metadata")
    layouts=claim.manifest["daily_sources"]+claim.manifest["minute_sources"]
    clocks=[_receipt_evidence(claim,d) for d in layouts]
    first_raw=claim.read(claim.manifest["daily_sources"][0]["role"])
    claim.begin_financial_decode()
    daily=[]; minutes=[]; monthly=[]; refs=[]; exception_carriers=0
    for index,(desc,receipt) in enumerate(zip(claim.manifest["daily_sources"],clocks)):
        raw=first_raw if index==0 else claim.read(desc["role"])
        if source_time_exception is not None and admission.digest(raw)==source_time_exception.native_sha256:
            daily.extend(_daily(raw,desc["first"],desc["last"],source_time_exception=source_time_exception))
            exception_carriers+=1
        else:daily.extend(_daily(raw,desc["first"],desc["last"]))
        refs.append(dict(kind="native_daily",source=claim.packet["inputs"][desc["role"]],**receipt))
    for desc,receipt in zip(claim.manifest["minute_sources"],clocks[len(claim.manifest["daily_sources"]):]):
        rows,coverage=_archive_targets(claim.read(desc["zip_role"]),claim.read(desc["checksum_role"]),desc["month"])
        minutes.extend(rows); monthly.append(coverage)
        refs.append(dict(kind="monthly_archive",source=claim.packet["inputs"][desc["zip_role"]],
                         checksum=claim.packet["inputs"][desc["checksum_role"]],**receipt))
    if source_time_exception is not None and exception_carriers!=1:raise ValueError("Exception carrier must occur exactly once")
    if ([r["date"] for r in daily]!=[(FIRST+timedelta(days=i)).isoformat() for i in range(2192)]
            or [r["date"] for r in minutes]!=[(EXEC_FIRST+timedelta(days=i)).isoformat() for i in range(1827)]):
        raise ValueError("Exact2192daily/1827execution coverage required")
    fixture=dict(artifact_type="claimed_spot_transfer_normalized_input_v1",asset_id="BTCUSDT",market="spot",
        source_nature=claim.source_nature,warmup_days=366,daily=daily,execution=minutes)
    provenance=dict(source_nature=claim.source_nature,registration_sha256=claim.packet["registration_sha256"],
        method_sha256=admission.METHOD_SHA,sources=refs,monthly_coverage=monthly,
        actual_original_dates_retained=True,historical_first_publication_verified=False,
        modeled_availability=dict(completed_daily="nextUTCday00:02_decision",minute_open="sameUTCday00:03_execution_only",
            minute_volume="sameUTCday00:04_expost_only"),model_assumptions=["HistoricalfeesfiltersPITunverified",
            "Dailyclose_assumed_received_before00:02", "Minuteopen_executionquote_assumption_notcertifiedfill",
            "Minutevolume_afterfill_notpretrade_capacity", "Native1000USDT_notCNYconversion"],
        source_numeric_projection=dict(daily=["open","high","low","close","volume"],minute=["open","volume"],
            outside_target_minute_numeric_values_decoded=False),qualified=False,real_forward_days_added=0)
    if source_time_exception is not None:provenance["source_time_exception"]=source_time_exception.provenance()
    loaded=LoadedHistory(fixture,provenance,admission.digest(admission.canonical(dict(fixture=fixture,provenance=provenance))))
    loaded.verify(); claim.guard("after","load_complete")
    return loaded


def _prepare(loaded):
    from quant_robot.research import spot_macd_transfer as m
    loaded.verify(); f=loaded.fixture
    if (f.get("artifact_type")!="claimed_spot_transfer_normalized_input_v1" or f.get("asset_id")!="BTCUSDT"
            or f.get("market")!="spot" or f.get("warmup_days")!=366
            or len(f["daily"])!=2192 or len(f["execution"])!=1827):
        raise ValueError("Fixed actual-calendar normalized source required")
    with localcontext(m.context()):
        daily=tuple(m.Daily(r["date"],*(m.number(r[k],positive=True) for k in ("open","high","low","close")),m.number(r["volume"])) for r in f["daily"])
        minutes=tuple(m.Minute(r["date"],m.number(r["open"],positive=True),m.number(r["volume"])) for r in f["execution"])
        frame=m.macd_frame([r["close"] for r in f["daily"]])
        states=tuple(False if m.pd.isna(v) else bool(v) for v in frame.desired)
        return m.Prepared(daily,minutes,366,states,loaded.digest,json.dumps(dict(decimal=frame.attrs["decimal_context"],
            floating=frame.attrs["float_environment"]),sort_keys=True))


def _persist(claim,path,value):
    target=admission.resolve_path(claim.root,path)
    admission.write_exclusive_json(target,value)
    return dict(path=path,sha256=admission.file_digest(target))


def run_claimed_diagnostic(claim):
    from quant_robot.research import spot_macd_transfer as m
    if "source_schema_policy" in claim.manifest:
        from quant_robot.research.spot_macd_transfer_time_exception import prepare_claimed_exception
        proof=prepare_claimed_exception(claim)
        loaded=load_claimed_inputs(claim,source_time_exception=proof)
    else:loaded=load_claimed_inputs(claim)
    folder=admission.DIRECTORY
    decoded=_persist(claim,folder+"/decoded_input.json",dict(fixture=loaded.fixture,provenance=loaded.provenance))
    prepared=_prepare(loaded)
    evidence=m._claimed_evidence(claim,loaded.digest,admission.digest(admission.canonical(loaded.provenance)))
    accounts={}; artifacts={}
    for case in m.CASES:
        for role in m.ROLES:
            key=f"fee{case[0]}_slip{case[1]}/{role}"
            claim.guard("before",key); loaded.verify()
            base=folder+"/accounts/"+key
            _persist(claim,base+"/started.json",dict(account=key,normalized_input_sha256=loaded.digest))
            try:
                result=m._run_prepared(prepared,case,role,evidence=evidence)
                claim.model_accounts_calculated+=1
                artifacts[key]=_persist(claim,base+"/complete.json",result)
                accounts[key]=result
                loaded.verify(); claim.guard("after",key)
                _persist(claim,folder+f"/account_index/{len(accounts):02}.json",dict(account=key,artifact=artifacts[key]))
            except BaseException as exc:
                _persist(claim,base+"/failed.json",dict(account=key,error_type=type(exc).__name__,resume_allowed=False))
                raise
    loaded.verify(); claim.guard("before","fixed_statistics")
    bootstrap=m.paired_bootstrap(accounts,evidence=evidence)
    statistics=_persist(claim,folder+"/statistics.json",dict(**evidence.fields("statistics"),method_sha256=m.METHOD_SHA,**bootstrap))
    checks,annual=m._conditional_checks(accounts,bootstrap)
    result=m.serial(dict(**evidence.fields("27_suite"),qualified=False,method_sha256=m.METHOD_SHA,
        account_count=27,observations=1827,full_fixed_statistics_completed=True,checks=checks,
        conditional_screen_passed=all(checks.values()),original_qualification_not_granted=True,
        primary_relative_attribution_blocks=annual,bootstrap=bootstrap,summaries={k:a["summary"] for k,a in accounts.items()},
        artifacts=artifacts,statistics_artifact=statistics,decoded_input_artifact=decoded,
        decoded_input_sha256=loaded.digest,limitations=loaded.provenance["model_assumptions"]+[
            "Holding_fixed252_oneattempt_not_uninterrupted_passive", "Dust_not_zero", "Observedrisk_not_all_paths",
            "Conditional_history_is_not_real_forward_or_qualification"]))
    loaded.verify(); verify_final_artifacts(claim,result)
    return result


def verify_final_artifacts(claim,result):
    from quant_robot.research import spot_macd_transfer as m
    expected={f"fee{f}_slip{s}/{r}" for f,s in m.CASES for r in m.ROLES}
    if set(result["artifacts"])!=expected or result["account_count"]!=27: raise ValueError("Complete27 artifacts required")
    decoded_ref=result["decoded_input_artifact"]
    if decoded_ref["path"]!=admission.DIRECTORY+"/decoded_input.json": raise ValueError("Normalized artifact path changed")
    decoded=admission._json(admission.read_bound(claim.root,decoded_ref,return_bytes=True))
    if set(decoded)!={"fixture","provenance"} or admission.digest(admission.canonical(decoded))!=result["decoded_input_sha256"]:
        raise ValueError("Normalized canonical evidence changed")
    for key,ref in result["artifacts"].items():
        if ref["path"]!=admission.DIRECTORY+"/accounts/"+key+"/complete.json": raise ValueError("Account artifact alias changed")
        admission.read_bound(claim.root,ref)
    if result["statistics_artifact"]["path"]!=admission.DIRECTORY+"/statistics.json": raise ValueError("Statistics alias changed")
    admission.read_bound(claim.root,result["statistics_artifact"])
