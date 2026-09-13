"""Offline, self-contained review bundles for explicitly supplied raw observations."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from quant_robot.data.analyst_forecast_events import normalize_analyst_response
from quant_robot.data.analyst_forecast_revisions import build_revision_trace


def materialize_observation_bundle(
    manifest_path: str | Path, output_dir: str | Path, *, as_of: str,
) -> dict[str, Any]:
    """Verify before writing; only result.json marks a fully written, fingerprinted bundle."""
    cutoff = _timestamp(as_of)
    manifest_path = Path(manifest_path).resolve()
    manifest_raw = _bounded_read(manifest_path, 1_000_000)
    manifest = json.loads(manifest_raw.decode('utf-8-sig'), object_pairs_hook=_unique_object)
    if (not isinstance(manifest, dict) or set(manifest) != {'schema_version', 'source', 'captures'}
            or type(manifest['schema_version']) is not int or manifest['schema_version'] != 1
            or manifest['source'] != 'tushare_report_rc'
            or not isinstance(manifest['captures'], list) or not 1 <= len(manifest['captures']) <= 128):
        raise ValueError('invalid_observation_manifest')

    captures, exported_captures, events = [], [], []
    raw_files: dict[str, bytes] = {}
    skipped, total_bytes = 0, 0
    for entry in manifest['captures']:
        if (not isinstance(entry, dict) or set(entry) != {'path', 'sha256', 'observed_at'}
                or not isinstance(entry['path'], str) or not entry['path'].strip()
                or not isinstance(entry['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', entry['sha256'])):
            raise ValueError('invalid_observation_capture')
        observed = _timestamp(entry['observed_at'])
        if observed > cutoff:
            skipped += 1
            continue
        raw = _bounded_read(manifest_path.parent / entry['path'], 8_000_000)
        total_bytes += len(raw)
        if total_bytes > 64_000_000:
            raise ValueError('observation_bundle_size_limit')
        if hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('source_sha256_mismatch')
        batch = normalize_analyst_response(raw, observed_at=observed)
        relative = f'raw/{batch.source_sha256}.json'
        raw_files[relative] = raw
        exported_captures.append({'path':relative, 'sha256':batch.source_sha256, 'observed_at':observed.isoformat()})
        eligible = [event for event in batch.events if event.available_at <= cutoff]
        events.extend(eligible)
        captures.append({
            'source_sha256':batch.source_sha256, 'observed_at':observed.isoformat(),
            'raw_rows':batch.raw_rows, 'normalized_events':len(batch.events), 'eligible_events':len(eligible),
            'provider_has_more':batch.provider_has_more, 'provider_count':batch.provider_count,
            'documented_row_cap_reached':batch.raw_rows >= 3000,
        })
    if not captures:
        raise ValueError('no_observations_at_cutoff')
    events.sort(key=lambda e: (e.available_at, e.match_key, e.version_id, e.observed_at, e.source_sha256, e.source_rows))
    transitions = build_revision_trace(events, as_of=cutoff)
    kinds = Counter(row.kind for row in transitions)
    report = {
        'schema_version':1, 'stage':'analyst_observation_review', 'as_of':cutoff.isoformat(),
        'input_manifest_sha256':hashlib.sha256(manifest_raw).hexdigest(),
        'observation_clock':'caller_supplied_unverified', 'historical_availability_verified':False,
        'source_completeness_verified':False, 'research_admitted':False,
        'captures':captures,
        'summary':{
            'captures':len(captures), 'skipped_future_captures':skipped,
            'raw_rows':sum(c['raw_rows'] for c in captures), 'eligible_events':len(events),
            'unique_versions':len({e.version_id for e in events}),
            'empty_captures':sum(c['raw_rows'] == 0 for c in captures),
            'pagination_or_cap_warnings':sum(c['provider_has_more'] is True or c['documented_row_cap_reached'] for c in captures),
            'new_report_revisions':kinds['new_report_revision'], 'transition_kinds':dict(sorted(kinds.items())),
        },
        'events':[{**asdict(event), 'target_price':event.target_price} for event in events],
        'transitions':[asdict(row) for row in transitions],
    }
    exported_manifest = {**manifest, 'captures':exported_captures}
    files = {**raw_files, 'manifest.json':_json_bytes(exported_manifest), 'review.json':_json_bytes(report)}
    result = {
        'schema_version':1, 'status':'complete',
        'files':{name:hashlib.sha256(raw).hexdigest() for name, raw in sorted(files.items())},
        'historical_availability_verified':False, 'source_completeness_verified':False,
        'research_admitted':False,
    }
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'raw').mkdir()
    for name, raw in files.items():
        (output / name).write_bytes(raw)
    for name, digest in result['files'].items():
        if hashlib.sha256((output / name).read_bytes()).hexdigest() != digest:
            raise OSError('written_bundle_fingerprint_mismatch')
    marker = output / '.result.pending'
    marker.write_bytes(_json_bytes(result))
    marker.replace(output / 'result.json')
    return result


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError('invalid_observation_timestamp')
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('observation_timezone_required')
    return result.astimezone(timezone.utc)


def _bounded_read(path: Path, limit: int) -> bytes:
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('observation_file_size_limit')
    return raw


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_manifest_key')
        result[key] = value
    return result


def _json_bytes(value: Any) -> bytes:
    def scalar(item):
        if isinstance(item, (date, datetime)):
            return item.isoformat()
        if isinstance(item, Decimal):
            return str(item)
        raise TypeError(f'unsupported_bundle_scalar:{type(item).__name__}')
    return json.dumps(value, default=scalar, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode('utf-8')
