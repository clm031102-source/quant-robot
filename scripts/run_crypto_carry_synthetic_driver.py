"""Run one fixed fabricated 2001 two-day exercise; no market input option."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.research.crypto_carry_driver import fabricated_fixture, json_ready, run_synthetic_driver

REPO=Path(__file__).resolve().parents[1]
REPORT_ROOT=REPO/'data/reports/campaign_72h_20261106/manager'


def raw_json(value):
    return (json.dumps(json_ready(value),ensure_ascii=False,sort_keys=True)+"\n").encode('utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=REPORT_ROOT/'crypto_driver_demo')
    args=parser.parse_args()
    output=args.output_dir.resolve()
    if not output.is_relative_to(REPORT_ROOT.resolve()) or output==REPORT_ROOT.resolve():
        raise ValueError('Output must be a new child of the campaign manager report directory')
    output.mkdir(parents=True,exist_ok=False)
    started=datetime.now(timezone.utc).isoformat()
    data=fabricated_fixture()
    result=run_synthetic_driver(data)
    artifacts={}
    for name,value in (
        ('fabricated_input.json',asdict(data)),
        ('event_states.jsonl',result.get('event_states',())),
        ('minute_envelopes.jsonl',result.get('envelopes',())),
        ('journals.json',{'kernel':result.get('kernel_journal',()),'scheduler':result.get('scheduler_journal',())}),
    ):
        payload=b''.join(raw_json(row) for row in value) if name.endswith('.jsonl') else raw_json(value)
        with (output/name).open('xb') as stream: stream.write(payload)
        artifacts[name]={'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)}
    summary={key:value for key,value in result.items()
             if key not in {'event_states','envelopes','kernel_journal','scheduler_journal'}}
    summary.update(started_at_utc=started,finished_at_utc=datetime.now(timezone.utc).isoformat(),artifacts=artifacts,
        implementation={relative:hashlib.sha256((REPO/relative).read_bytes()).hexdigest() for relative in (
            'src/quant_robot/research/crypto_carry_model.py','src/quant_robot/research/crypto_carry_policy.py',
            'src/quant_robot/research/crypto_carry_scheduler.py','src/quant_robot/research/crypto_carry_driver.py',
            'scripts/run_crypto_carry_synthetic_driver.py')})
    with (output/'summary.json').open('xb') as stream: stream.write(raw_json(summary))
    print(json.dumps({key:summary[key] for key in ('status','economic_exercise_complete','processed_minutes',
        'fill_count','confirmed_transfer_count','envelope_status_counts','qualified','real_forward')},ensure_ascii=False))
    return 0 if summary['economic_exercise_complete'] else 2


if __name__=='__main__':
    raise SystemExit(main())
