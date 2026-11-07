"""One pinned warmup clock exception, proved with opaque original tokens.

No source is read on import. This proof does not authorize financial decoding.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
import re
from zipfile import ZipFile

POLICY_ID="exact_retained_20180208_daily_time_exception_v1"
ADDENDUM_SHA="e2f435024008f48f0520a89e53a41853f28f0d6208c9634f4af3552f55543e36"
ROOT_REVIEW_SHA="6864582cd2dab55e14c4292c31273338d94fa997f0dd3d3d85e339422dae4a45"
NATIVE_SHA="7cb96ef96be013b31516bd6f1445cdffe57f0011aead76a7a9630fa2814bda4a"
ARCHIVE_SHA="037b2a4846cde6fb748aeb556e9dd84d964c1418097b979a2a4063fa3e9321e3"
CHECKSUM_SHA="a3119a7063e2fb04dccd4ecfd7f43b35adf18644e44def897f574196fb7b845e"
OPEN=1518048000000
NATIVE_CLOSE=1518049694788
ARCHIVE_CLOSE=1518134399999
DAY=86400000
INDICES=(1,2,3,4,5,7,8,9,10,11)
_TOKEN=object()


class IntegerToken(str):pass
class FloatToken(str):pass


def _sha(raw):return hashlib.sha256(raw).hexdigest()


def _sealed(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError("Duplicate JSON key")
            result[key]=value
        return result
    def bad(value):raise ValueError("Nonfinite JSON token")
    return json.loads(raw,parse_int=IntegerToken,parse_float=FloatToken,object_pairs_hook=pairs,parse_constant=bad)


def _same(left,right):
    if type(left) is not type(right):return False
    if isinstance(left,dict):return set(left)==set(right) and all(_same(left[k],right[k]) for k in left)
    if isinstance(left,list):return len(left)==len(right) and all(_same(a,b) for a,b in zip(left,right))
    return left==right


def _time(day):return int(datetime.combine(day,datetime.min.time(),timezone.utc).timestamp())*1000


def _native_opaque(raw):
    obj=_sealed(raw)
    if (type(obj) is not dict or set(obj)!={"content","structuredContent","isError"}
            or obj["isError"] is not False or type(obj["content"]) is not list or len(obj["content"])!=1):
        raise ValueError("Exact native shape required")
    content=obj["content"][0]
    if type(content) is not dict or set(content)!={"type","text"} or content["type"]!="text" or type(content["text"]) is not str:
        raise ValueError("Exact text mirror required")
    left,right=_sealed(content["text"]),obj["structuredContent"]
    if not _same(left,right) or type(left) is not dict or set(left)!={"result"} or type(left["result"]) is not list:
        raise ValueError("Opaque mirrors differ in type or literal spelling")
    rows=left["result"]
    if len(rows)!=364:raise ValueError("Exact364 native days required")
    selected=None
    for i,row in enumerate(rows):
        if (type(row) is not list or len(row)!=12 or any(type(row[k]) is not IntegerToken for k in (0,6,8))
                or any(type(row[k]) is not str for k in (1,2,3,4,5,7,9,10,11))
                or any(not re.fullmatch(r'[0-9]+',row[k]) for k in (0,6,8))):
            raise ValueError("Exact native row token types required")
        expected=_time(date(2018,1,2)+timedelta(days=i))
        if int(row[0])!=expected:raise ValueError("Native open dates/order changed")
        close=NATIVE_CLOSE if expected==OPEN else expected+DAY-1
        if int(row[6])!=close:raise ValueError("Unapproved native close time")
        if expected==OPEN:selected=row
    if selected is None:raise ValueError("Pinned native day absent")
    return selected


def _archive_opaque(raw,checksum):
    name=b'BTCUSDT-1d-2018-02.zip'
    match=re.fullmatch(rb'([a-fA-F0-9]{64})[ \t]+\*?'+re.escape(name)+rb'\s*',checksum)
    if not match or match[1].decode().lower()!=_sha(raw):raise ValueError("Pinned archive checksum mismatch")
    if len(raw)>16*1024*1024 or len(checksum)>4096:raise ValueError("Source bytes exceed bounds")
    selected=None
    with ZipFile(io.BytesIO(raw)) as z:
        members=z.infolist()
        if (len(members)!=1 or members[0].filename!='BTCUSDT-1d-2018-02.csv' or members[0].is_dir()
                or members[0].flag_bits&1 or not 0<members[0].file_size<=32*1024*1024):
            raise ValueError("Exact single daily CSV required")
        count=0;inflated=0
        with z.open(members[0]) as stream:
            while True:
                line=stream.readline(4097)
                if not line:break
                inflated+=len(line)
                if len(line)>4096 or inflated>32*1024*1024:raise ValueError("Daily CSV bound")
                row=line.rstrip(b'\r\n').split(b',')
                if len(row)!=12 or any(not re.fullmatch(rb'[0-9]+',row[k]) for k in (0,6)):
                    raise ValueError("Exact headerless daily schema required")
                expected=_time(date(2018,2,1)+timedelta(days=count));count+=1
                if count>28 or int(row[0])!=expected or int(row[6])!=expected+DAY-1:
                    raise ValueError("Archive date/order/full-day clock mismatch")
                if expected==OPEN:selected=row
        if count!=28 or inflated!=members[0].file_size or selected is None:
            raise ValueError("Exact28 archive dates/CRC required")
    return selected


@dataclass(frozen=True)
class ExactDailyTimeProof:
    native_sha256: str
    registration_sha256: str
    claim_sha256: str
    source_nature: str
    provenance_json: str
    _seal: object

    def __post_init__(self):
        if self._seal is not _TOKEN:raise ValueError("Only verified exact source proof")

    def validate_claim(self,claim):
        if (self._seal is not _TOKEN or not claim.active or self.registration_sha256!=claim.packet['registration_sha256']
                or self.claim_sha256!=claim.claim_hash or self.source_nature!=claim.source_nature):
            raise ValueError("Exception proof belongs to a different claim")

    def validate_source(self,raw,first,last):
        if self._seal is not _TOKEN or _sha(raw)!=self.native_sha256 or (first,last)!=('2018-01-02','2018-12-31'):
            raise ValueError("Exception proof source/range changed")

    def accepts_close(self,day,open_time,close_time):
        return self._seal is _TOKEN and day=='2018-02-08' and open_time==OPEN and close_time==NATIVE_CLOSE

    def provenance(self):return json.loads(self.provenance_json)


def _prove_bytes(native,archive,checksum,addendum,*,registration_sha256,claim_sha256,source_nature,bound_refs):
    """Pure opaque checker. Tests inject explicit artificial pins, never real rows."""
    for raw,expected in ((native,NATIVE_SHA),(archive,ARCHIVE_SHA),(checksum,CHECKSUM_SHA),(addendum,ADDENDUM_SHA)):
        if _sha(raw)!=expected:raise ValueError("Exact exception original hash mismatch")
    contract=json.loads(addendum)
    if contract['policy_id']!=POLICY_ID:raise ValueError("Wrong source policy")
    for key,raw in (('native',native),('archive',archive),('checksum',checksum)):
        if contract['authority'][key]['sha256']!=_sha(raw) or contract['authority'][key]['bytes']!=len(raw):
            raise ValueError("Exact authority identity/size mismatch")
    left,right=_native_opaque(native),_archive_opaque(archive,checksum)
    if any(left[k].encode('utf8')!=right[k] for k in INDICES):
        raise ValueError("One of ten non-time original tokens differs")
    provenance=dict(policy_id=POLICY_ID,addendum_sha256=ADDENDUM_SHA,
        root_decision=contract['authority']['root_decision'],root_review_sha256=ROOT_REVIEW_SHA,
        bound_refs=bound_refs,source_nature=source_nature,target_date='2018-02-08',role='warmup',
        original_open_time_ms=OPEN,original_native_close_time_ms=NATIVE_CLOSE,original_archive_close_time_ms=ARCHIVE_CLOSE,
        native_dates=364,archive_dates=28,native_mirrors_same_types_and_literals=True,non_time_exact_equal_count=10,
        equality_financial_numeric_conversions=0,raw_originals_rewritten=False,economic_fields_replaced=False,
        modeled_availability='nextUTCday00:02',historical_first_publication_verified=False,
        full_24h_trading_completeness_verified=False,source_disagreement_cause_known=False,
        original_phase2_status='failed_consumed',qualification_granted=False,real_forward_days_added=0)
    return ExactDailyTimeProof(NATIVE_SHA,registration_sha256,claim_sha256,source_nature,
                              json.dumps(provenance,sort_keys=True),_TOKEN)


def prepare_claimed_exception(claim):
    from quant_robot.research import spot_macd_transfer_admission as a
    if not isinstance(claim,a._Claim) or not claim.active or claim.decoding_started:
        raise ValueError("Unused active claim required for opaque exception proof")
    claim.guard('before','exact_time_exception_opaque_proof')
    policy=claim.manifest.get('source_schema_policy')
    a.validate_source_schema_policy(claim.root,claim.manifest,claim.packet['inputs'])
    if policy is None:raise ValueError("Frozen source exception policy absent")
    roles=policy['authority_roles'];refs={k:claim.packet['inputs'][v] for k,v in roles.items()}
    refs['addendum']=claim.packet['inputs'][policy['addendum_role']]
    refs['root_review']=claim.packet['inputs'][policy['root_review_role']]
    proof=_prove_bytes(claim.read(roles['native']),claim.read(roles['archive']),claim.read(roles['checksum']),
        claim.read(policy['addendum_role']),registration_sha256=claim.packet['registration_sha256'],
        claim_sha256=claim.claim_hash,source_nature=claim.source_nature,bound_refs=refs)
    claim.guard('after','exact_time_exception_opaque_proof')
    return proof
