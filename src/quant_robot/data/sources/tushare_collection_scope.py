"""Frozen source-only collection scope; does not grant research admission."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from quant_robot.data.sources.tushare_http import TushareSourceError, TushareSourceHttpClient


SCOPE_KEYS = {
    "schema_version", "scope_id", "purpose", "primary_market", "max_date",
    "trust_env", "max_response_bytes", "connect_timeout", "read_timeout",
    "review_evidence", "requests",
}
# The final ETF holdout remains sealed, irrespective of the current system date.
SOURCE_DATE_CEILING = "20251231"


def digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def request_identity(request: dict) -> str:
    """Ignore labels, limits and column order when detecting an identical read."""
    return digest({"api_name": request["api_name"], "params": request["params"],
        "fields": sorted(request["fields"].split(","))})


def _verify_evidence(records: object, root: Path) -> None:
    if not isinstance(records, list) or not 1 <= len(records) <= 16:
        raise ValueError("review evidence requires 1 to 16 fingerprinted files")
    for record in records:
        if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
            raise ValueError("invalid review evidence fields")
        if not isinstance(record["path"], str) or not isinstance(record["sha256"], str):
            raise ValueError("invalid review evidence types")
        path = (root / record["path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("review evidence must be an existing repository file")
        if not re.fullmatch("[0-9a-f]{64}", record["sha256"]):
            raise ValueError("invalid review evidence hash")
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("review evidence hash changed")


def make_client(scope: dict, token: str) -> TushareSourceHttpClient:
    return TushareSourceHttpClient(token=token, max_requests=len(scope["requests"]),
        **{key: scope[key] for key in ("max_date", "trust_env", "max_response_bytes", "connect_timeout", "read_timeout")})


def validate_scope(scope: dict, *, repo_root: str | Path) -> dict:
    root = Path(repo_root).resolve()
    if not isinstance(scope, dict) or set(scope) != SCOPE_KEYS:
        raise ValueError("scope fields differ from the source-only schema")
    if type(scope["schema_version"]) is not int or scope["schema_version"] != 1:
        raise ValueError("unsupported scope schema version")
    if scope["purpose"] != "source_qualification" or scope["primary_market"] != "CN_ETF":
        raise ValueError("scope must be CN_ETF source qualification only")
    if not isinstance(scope["scope_id"], str) or not re.fullmatch("[a-z0-9][a-z0-9_-]{0,79}", scope["scope_id"]):
        raise ValueError("scope_id must be a short lowercase identifier")
    requests = scope["requests"]
    if not isinstance(requests, list) or not 1 <= len(requests) <= 16:
        raise ValueError("scope requires 1 to 16 requests")
    try:
        client = make_client(scope, token="scope-validation-placeholder")
        if client.max_date > SOURCE_DATE_CEILING or client.max_response_bytes > 2_000_000:
            raise ValueError("scope exceeds frozen date or response budget")
        if max(client.timeout) > 30:
            raise ValueError("each connection/read timeout must be at most 30 seconds")
        identities = []
        for request in requests:
            if not isinstance(request, dict) or set(request) != {"api_name", "fields", "max_rows", "params"}:
                raise ValueError("invalid request fields")
            if not isinstance(request["params"], dict):
                raise ValueError("request params must be an object")
            client.validate_query(request["api_name"], fields=request["fields"],
                max_rows=request["max_rows"], **request["params"])
            if request["max_rows"] > 10_000:
                raise ValueError("request row budget exceeds 10000")
            identities.append(request_identity(request))
        if len(set(identities)) != len(identities):
            raise ValueError("duplicate source requests in frozen scope")
    except (TushareSourceError, TypeError, OverflowError) as exc:
        raise ValueError("invalid source request or transport limits") from exc
    _verify_evidence(scope["review_evidence"], root)
    return {"scope_sha256": digest(scope), "request_identities": identities,
        "request_count": len(requests), "source_date_ceiling": SOURCE_DATE_CEILING}
