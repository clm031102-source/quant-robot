import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from quant_robot.execution.offline_supervisor import launch_owned_python
from quant_robot.research.monthly_diagnostic_registration import DIRECTORY, build_registration, runtime_environment, sha256
from quant_robot.research.monthly_diagnostic_execution import execute_registration
from tests.unit.test_monthly_diagnostic_execution import execution_fixture, REPO
from tests.unit.test_monthly_diagnostic_registration import scheduler_fixture


class MonthlyDiagnosticProcessTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.packet,self.scheduler,self.gate=execution_fixture(self.root)
        (self.root/'process-context.json').write_text(json.dumps({'scheduler':self.scheduler,'gate':self.gate}))
        self.children=[]
        self.addCleanup(self.stop_children)

    def stop_children(self):
        for child in self.children:
            if child.poll() is None:child.kill()
            child.wait(timeout=5)

    def launch(self, after_claim):
        source="""
import json,os,sys,time
from pathlib import Path
from quant_robot.research.monthly_diagnostic_execution import execute_registration
root=Path(sys.argv[1]);context=json.loads((root/'process-context.json').read_text())
def after_claim(receipt):
    AFTER_CLAIM
try:
    execute_registration(root=root,registration_path='registration.json',scheduler=context['scheduler'],
        gate_supplier=lambda:context['gate'],environment={'python':'fixture'},on_claim=after_claim)
except ValueError as exc:
    if 'already claimed' in str(exc):sys.exit(3)
    raise
""".replace('AFTER_CLAIM',after_claim)
        child=launch_owned_python(['-c',source,str(self.root)],cwd=REPO,stderr=subprocess.PIPE)
        self.children.append(child);return child

    def test_hard_exit_keeps_claim_and_cannot_restart_as_new_attempt(self):
        child=self.launch('os._exit(23)');_,errors=child.communicate(timeout=15)
        self.assertEqual(child.returncode,23,errors.decode(errors='replace'))
        claim=json.loads((self.root/self.packet['ledger_path']).read_text())
        self.assertEqual(claim['status'],'claimed_before_signal_or_label_read')
        self.assertFalse((self.root/DIRECTORY/'outcome.json').exists())
        self.assertFalse((self.root/DIRECTORY/'result.json').exists())
        with self.assertRaisesRegex(ValueError,'already claimed'):
            execute_registration(root=self.root,registration_path='registration.json',scheduler=self.scheduler,
                gate_supplier=lambda:self.gate,environment={'python':'fixture'})

    def test_two_real_processes_cannot_consume_one_study_twice(self):
        children=[self.launch('time.sleep(.2)') for _ in range(2)]
        errors=[]
        for child in children:
            _,error=child.communicate(timeout=20);errors.append(error.decode(errors='replace'))
        self.assertEqual(sorted(child.returncode for child in children),[0,3],errors)
        claim=json.loads((self.root/self.packet['ledger_path']).read_text())
        result=json.loads((self.root/DIRECTORY/'result.json').read_text())
        self.assertEqual(result['attempt_id'],claim['attempt_id'])
        self.assertEqual(result['diagnostic']['interval_count'],53)
        self.assertEqual(result['counts_as_forward_paper_days'],0)

    def test_actual_cli_checks_real_pm_gate_then_runs_fixture_exactly_once(self):
        packet=build_registration(inputs=self.packet['inputs'],code_files=self.packet['code_files'],
            environment=runtime_environment(),source_origin='synthetic_fixture',branch=self.packet['branch'])
        path=self.root/DIRECTORY/'registration.json';path.parent.mkdir(parents=True);path.write_text(json.dumps(packet,sort_keys=True))
        family=json.loads((REPO/'configs/research_family_scheduler_cn_etf.json').read_text())
        decision=scheduler_fixture(packet)['monthly_diagnostic_decision']
        decision.update(registration_path=DIRECTORY+'/registration.json',registration_sha256=sha256(path.read_bytes()))
        family['monthly_diagnostic_decision']=decision
        config=json.loads((REPO/'configs/quant_pm_startup_gate_cn_etf.json').read_text())
        for row in config['required_reading']:
            target=self.root/row['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_text('fixture protocol')
        for name in ('workstations.json','quant_pm_startup_gate_cn_etf.json'):
            (self.root/'configs'/name).write_bytes((REPO/'configs'/name).read_bytes())
        (self.root/'configs/research_family_scheduler_cn_etf.json').write_text(json.dumps(family))
        subprocess.run(['git','init','--quiet','--initial-branch='+packet['branch']],cwd=self.root,check=True,capture_output=True)
        def cli(*extra):
            child=launch_owned_python([str(REPO/'scripts/run_cn_etf_policy_uncertainty_diagnostic.py'),'--root',str(self.root),*extra],
                cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.children.append(child)
            output,errors=child.communicate(timeout=20)
            return child.returncode,output.decode(),errors.decode(errors='replace')
        code,output,errors=cli();self.assertEqual(code,0,errors)
        self.assertEqual(json.loads(output)['status'],'ready_unconsumed')
        self.assertFalse((self.root/packet['ledger_path']).exists())
        code,output,errors=cli('--execute');self.assertEqual(code,0,errors)
        self.assertEqual(json.loads(output)['status'],'completed')
        self.assertEqual(json.loads(output)['source_origin'],'synthetic_fixture')
        code,_,errors=cli('--execute');self.assertNotEqual(code,0)
        self.assertIn('already claimed',errors)


if __name__=='__main__':unittest.main()
