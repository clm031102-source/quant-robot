"""Run fixed fabricated raw-source monthly exercises; no historical input option."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.research.crypto_monthly_diagnostic import (
    _json, load_raw_month, run_account, run_matrix, sha, synthetic_raw_fixture,
)

REPO=Path(__file__).resolve().parents[1]
REPORT_ROOT=REPO/'data/reports/campaign_72h_20261106/manager'
IMPLEMENTATION=(
    'src/quant_robot/research/crypto_carry_model.py',
    'src/quant_robot/research/crypto_carry_policy.py',
    'src/quant_robot/research/crypto_carry_scheduler.py',
    'src/quant_robot/research/crypto_carry_driver.py',
    'src/quant_robot/research/crypto_monthly_diagnostic.py',
    'scripts/run_crypto_monthly_diagnostic_synthetic.py',
    'tests/unit/test_crypto_monthly_diagnostic.py',
)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exercise',choices=('primary31','matrix3'),default='primary31')
    parser.add_argument('--output-dir',type=Path,default=REPORT_ROOT/'crypto_monthly_synthetic_primary31')
    args=parser.parse_args()
    output=args.output_dir.resolve()
    if output==REPORT_ROOT.resolve() or not output.is_relative_to(REPORT_ROOT.resolve()):
        raise ValueError('Output must be a new child of the manager report directory')
    output.mkdir(parents=True,exist_ok=False)
    started=datetime.now(timezone.utc).isoformat()
    binding={name:sha((REPO/name).read_bytes()) for name in IMPLEMENTATION}
    raw=synthetic_raw_fixture(days=31 if args.exercise=='primary31' else 3,shock=args.exercise=='primary31')
    originals=output/'fabricated_originals'; originals.mkdir()
    for archive in raw.archives.values():
        (originals/archive.filename).write_bytes(archive.body)
        (originals/(archive.filename+'.CHECKSUM')).write_bytes(archive.checksum)
    (originals/'funding_tool_return.json').write_bytes(raw.funding_tool_return)
    data=load_raw_month(raw)
    result=run_account(data,output_dir=output/'B_5') if args.exercise=='primary31' else run_matrix(data,output_dir=output/'matrix')
    after={name:sha((REPO/name).read_bytes()) for name in IMPLEMENTATION}
    if after!=binding:
        raise ValueError('implementation_changed_during_synthetic_exercise')
    receipt={'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
        'implementation':binding,'implementation_unchanged':True,'exercise':args.exercise,
        'evidence_class':'synthetic_raw_fixture','qualified':False,'real_forward':0,
        'historical_returns_computed':False,'real_market_files_read':0,'network_requests':0,
        'source_provenance':data.provenance,'coverage':data.coverage,
        'account_summary':str(output/'B_5/summary.json') if args.exercise=='primary31' else str(output/'matrix/matrix.json')}
    (output/'execution_receipt.json').write_text(_json(receipt)+'\n',encoding='utf-8')
    if args.exercise=='primary31':
        print(json.dumps({key:result[key] for key in ('status','account_complete','economic_exercise_complete',
            'processed_minutes','fill_count','sampled_model_drawdown','per_minute_conditional_envelope','qualified')}))
        return 0 if result['account_complete'] and result['economic_exercise_complete'] else 2
    print(json.dumps({'accounts':list(result['accounts']),'cash':result['cash']['nav'],'qualified':False}))
    return 0 if all(row['account_complete'] for row in result['accounts'].values()) else 2


if __name__=='__main__':
    raise SystemExit(main())
