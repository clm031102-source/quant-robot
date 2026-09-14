"""Review one pinned local fiscal release; no downloads, factors or returns."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct invocation
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data import mof_fiscal_release  # noqa: E402
from quant_robot.data.mof_fiscal_release import parse_mof_monthly_expenditure  # noqa: E402
from quant_robot.storage.atomic import atomic_write_json  # noqa: E402
from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--year', required=True, type=int)
    parser.add_argument('--month', required=True, type=int)
    parser.add_argument('--component-label-schema', default='central_own_local',
                        choices=['central_own_local', 'reported_legacy'])
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--machine', required=True)
    parser.add_argument('--branch', required=True)
    args = parser.parse_args(argv)
    output = None
    result = {'stage': 'mof_monthly_fiscal_source_review', 'status': 'started',
        'research_admission_granted': False, 'network_requests': 0,
        'factor_or_return_computed': False, 'started_at': datetime.now(timezone.utc).isoformat()}
    try:
        if re.fullmatch('[0-9a-f]{64}', args.source_sha256) is None:
            raise ValueError('source SHA256 must be explicit and canonical')
        source = Path(args.input).resolve()
        with source.open('rb') as handle:
            raw = handle.read(3_000_001)
        if len(raw) > 3_000_000 or hashlib.sha256(raw).hexdigest() != args.source_sha256:
            raise ValueError('source size or fingerprint differs from the reviewed input')
        destination = Path(args.output_dir).resolve()
        destination.mkdir(parents=True, exist_ok=False)
        output = destination
        result.update(source_path=str(source), source_sha256=args.source_sha256,
            expected_year=args.year, expected_month=args.month,
            component_label_schema=args.component_label_schema,
            implementation_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (Path(__file__), Path(mof_fiscal_release.__file__))})
        atomic_write_json(output / 'result.json', result)
        atomic_write_json(output / 'invocation.json', {'machine': args.machine, 'task': 'factor_review',
            'branch': args.branch, 'year': args.year, 'month': args.month,
            'component_label_schema': args.component_label_schema,
            'source_path': str(source), 'source_sha256': args.source_sha256})
        gate = run_quant_pm_startup_gate(output_dir=output / 'startup_gate', machine=args.machine,
                                        task='factor_review', branch=args.branch)
        atomic_write_json(output / 'gate.json', gate)
        result['gate_sha256'] = hashlib.sha256((output / 'gate.json').read_bytes()).hexdigest()
        if gate.get('status') != 'ready' or gate.get('primary_market') != 'CN_ETF' or gate.get('blockers') != []:
            result['status'] = 'gate_blocked'
        else:
            result['observation'] = parse_mof_monthly_expenditure(raw,
                expected_year=args.year, expected_month=args.month,
                component_label_schema=args.component_label_schema)
            result['status'] = 'parsed_source_not_admitted'
    except Exception as exc:
        result.update(status='rejected', failure_kind=type(exc).__name__)
    finally:
        result['finished_at'] = datetime.now(timezone.utc).isoformat()
        if output is not None:
            try:
                atomic_write_json(output / 'result.json', result)
            except OSError:
                result.update(status='evidence_write_failed', failure_kind='OSError')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result['status'] == 'parsed_source_not_admitted' else 1


if __name__ == '__main__':
    raise SystemExit(main())
