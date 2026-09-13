from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from quant_robot.gui.paper_request_identity import _json_safe
from quant_robot.storage.atomic import atomic_write


ARCHIVE_DIRECTORY = Path('data/reports/gui_paper_results')
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024


def _validate_result(result: Any) -> None:
    if not isinstance(result, dict):
        raise ValueError('paper archive requires a complete result')
    for key, kind in (('request', dict), ('metrics', dict), ('equity_curve', list), ('fills', list)):
        if not isinstance(result.get(key), kind):
            raise ValueError(f'paper archive missing result field: {key}')
    benchmark = result.get('fixed_hold_benchmark')
    if benchmark is not None:
        _validate_result(benchmark)


def _archive_path(repo_root: str | Path, archive_id: str) -> Path:
    if not isinstance(archive_id, str) or not re.fullmatch('[0-9a-f]{64}', archive_id):
        raise ValueError('invalid paper archive identifier')
    base = Path(repo_root).resolve() / ARCHIVE_DIRECTORY
    target = base / (archive_id + '.json')
    if base.resolve() != base or target.resolve() != target:
        raise ValueError('paper archive path must not redirect outside its fixed location')
    return target


def _reference(archive_id: str, size: int, recorded_at: str, *, restored: bool) -> dict[str, Any]:
    return {'archive_id': archive_id, 'sha256': archive_id, 'bytes': size,
            'recorded_at': recorded_at, 'schema_version': 1,
            'status': 'verified' if restored else 'saved', 'restored': restored,
            'source_quality_verified': False, 'profitability_verified': False,
            'new_forward_observation': False, 'executable': False}


def archive_paper_result(repo_root: str | Path, result: dict[str, Any]) -> dict[str, Any]:
    """Retain the whole server result, without treating an archive as new research evidence."""
    _validate_result(result)
    recorded_at = datetime.now(timezone.utc).isoformat()
    payload = {'schema_version': 1, 'kind': 'gui_paper_result', 'recorded_at': recorded_at,
               'result': _json_safe({k: v for k, v in result.items() if k != 'paper_archive'})}
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')
    if len(body) > MAX_ARCHIVE_BYTES:
        raise ValueError('paper archive size exceeds limit; result was not truncated')
    archive_id = hashlib.sha256(body).hexdigest()
    path = _archive_path(repo_root, archive_id)
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError('existing paper archive fingerprint mismatch')
    else:
        atomic_write(path, lambda temporary: temporary.write_bytes(body))
    return _reference(archive_id, len(body), recorded_at, restored=False)


def load_paper_result(repo_root: str | Path, archive_id: str) -> dict[str, Any]:
    path = _archive_path(repo_root, archive_id)
    with path.open('rb') as handle:
        body = handle.read(MAX_ARCHIVE_BYTES + 1)
    if len(body) > MAX_ARCHIVE_BYTES:
        raise ValueError('paper archive size exceeds limit')
    if hashlib.sha256(body).hexdigest() != archive_id:
        raise ValueError('paper archive fingerprint mismatch')
    payload = json.loads(body.decode('utf-8'))
    if not isinstance(payload, dict) or payload.get('schema_version') != 1 or payload.get('kind') != 'gui_paper_result':
        raise ValueError('unsupported paper archive format')
    result = payload.get('result')
    _validate_result(result)
    result['paper_archive'] = _reference(archive_id, len(body), payload['recorded_at'], restored=True)
    return result


def retain_paper_result(repo_root: str | Path, result: dict[str, Any]) -> None:
    try:
        result['paper_archive'] = archive_paper_result(repo_root, result)
    except (ValueError, OSError) as exc:
        result['paper_archive'] = {'status': 'failed', 'error': str(exc),
                                   'source_quality_verified': False, 'executable': False}


def operation_result_fields(result: dict[str, Any]) -> dict[str, Any]:
    fields = {'metrics': _json_safe(result.get('metrics') if isinstance(result.get('metrics'), dict) else {})}
    for key in ('account_comparison', 'paper_archive'):
        if isinstance(result.get(key), dict):
            fields[key] = _json_safe(result[key])
    return fields
