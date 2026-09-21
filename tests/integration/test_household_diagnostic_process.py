from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from quant_robot.execution.offline_supervisor import launch_owned_python
from quant_robot.research.household_diagnostic_registration import DIRECTORY, IMPLEMENTATION_FILES, build_registration
from quant_robot.research.monthly_diagnostic_registration import canonical, runtime_environment, sha256
from quant_robot.research.household_diagnostic_execution import execute_registration
from tests.unit.household_diagnostic_fixtures import execution_fixture
from tests.unit.test_household_diagnostic_registration import scheduler_fixture

REPO = Path(__file__).resolve().parents[2]


class HouseholdProcessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup); self.root = Path(temporary.name)
        self.packet, self.scheduler, self.gate, _ = execution_fixture(self.root)
        (self.root/'process-context.json').write_bytes(canonical({'scheduler': self.scheduler, 'gate': self.gate}))
        self.children = []; self.addCleanup(self.stop_children)

    def stop_children(self):
        for child in self.children:
            if child.poll() is None: child.kill()
            child.wait(timeout=5)

    def launch(self, after_claim):
        program = """
import json,os,sys,time
from pathlib import Path
from datetime import datetime,timezone
from quant_robot.research.household_diagnostic_execution import execute_registration
from quant_robot.research.household_diagnostic_registration import DIRECTORY
root=Path(sys.argv[1]);context=json.loads((root/'process-context.json').read_bytes())
def gate():
    context['gate']['generated_at']=datetime.now(timezone.utc).isoformat()
    return context['gate']
def after_claim(receipt):
    AFTER_CLAIM
try:
    execute_registration(root=root,registration_path=DIRECTORY+'/registration.json',scheduler=context['scheduler'],
        gate_supplier=gate,environment={'python':'fixture'},on_claim=after_claim)
except ValueError as exc:
    if 'already claimed' in str(exc):sys.exit(3)
    raise
""".replace('AFTER_CLAIM', after_claim)
        child = launch_owned_python(['-c', program, str(self.root)], cwd=REPO, stderr=subprocess.PIPE)
        self.children.append(child); return child

    def test_hard_exit_retains_claim_and_forbids_restart(self):
        child = self.launch('os._exit(23)'); _, errors = child.communicate(timeout=30)
        self.assertEqual(child.returncode, 23, errors.decode(errors='replace'))
        self.assertTrue((self.root/self.packet['ledger_path']).is_file())
        self.assertFalse((self.root/DIRECTORY/'result.json').exists())
        self.assertFalse((self.root/DIRECTORY/'outcome.json').exists())
        with self.assertRaisesRegex(ValueError, 'already claimed'):
            execute_registration(root=self.root, registration_path=DIRECTORY+'/registration.json',
                scheduler=self.scheduler, gate_supplier=lambda: self.gate, environment={'python': 'fixture'})

    def test_competing_processes_can_finish_only_one_attempt(self):
        children = [self.launch('time.sleep(.2)') for _ in range(2)]
        diagnostics = []
        for child in children:
            _, errors = child.communicate(timeout=30); diagnostics.append(errors.decode(errors='replace'))
        self.assertEqual(sorted(child.returncode for child in children), [0, 3], diagnostics)
        claim = json.loads((self.root/self.packet['ledger_path']).read_bytes())
        result = json.loads((self.root/DIRECTORY/'result.json').read_bytes())
        self.assertEqual(result['attempt_id'], claim['attempt_id'])
        self.assertEqual(result['diagnostic']['interval_count'], 17)

    def setup_cli(self):
        packet = build_registration(inputs=self.packet['inputs'], code_files=self.packet['code_files'],
            environment=runtime_environment(), source_origin='synthetic_fixture', branch=self.packet['branch'])
        (self.root/DIRECTORY/'registration.json').write_bytes(canonical(packet))
        family = json.loads((REPO/'configs/research_family_scheduler_cn_etf.json').read_bytes())
        family['household_diagnostic_decision'] = scheduler_fixture(packet)['household_diagnostic_decision']
        config = json.loads((REPO/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes())
        for row in config['required_reading']:
            target = self.root/row['path']; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('fixture protocol', encoding='utf-8')
        for name in ('workstations.json', 'quant_pm_startup_gate_cn_etf.json'):
            (self.root/'configs'/name).write_bytes((REPO/'configs'/name).read_bytes())
        (self.root/'configs/research_family_scheduler_cn_etf.json').write_bytes(canonical(family))
        subprocess.run(['git', 'init', '--quiet', '--initial-branch='+packet['branch']],
            cwd=self.root, check=True, capture_output=True)
        return packet

    def cli(self, script, *extra):
        child = launch_owned_python([str(REPO/'scripts'/script), '--root', str(self.root), *extra],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.children.append(child); output, errors = child.communicate(timeout=30)
        return child.returncode, output.decode('utf-8'), errors.decode('utf-8', errors='replace')

    def test_actual_command_checks_then_executes_fixture_once(self):
        packet = self.setup_cli()
        code, output, errors = self.cli('run_cn_etf_household_diagnostic.py')
        self.assertEqual(code, 0, errors); self.assertEqual(json.loads(output)['status'], 'ready_unconsumed')
        self.assertFalse((self.root/packet['ledger_path']).exists())
        code, output, errors = self.cli('run_cn_etf_household_diagnostic.py', '--execute')
        self.assertEqual(code, 0, errors); self.assertEqual(json.loads(output)['status'], 'completed')
        self.assertEqual(json.loads(output)['source_origin'], 'synthetic_fixture')
        code, _, errors = self.cli('run_cn_etf_household_diagnostic.py', '--execute')
        self.assertNotEqual(code, 0); self.assertIn('already claimed', errors)

    def test_prepare_does_not_relabel_unreviewed_fixture_as_real_sources(self):
        self.setup_cli()
        for relative in IMPLEMENTATION_FILES:
            path = self.root/relative; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((REPO/relative).read_bytes())
        registration = self.root/DIRECTORY/'registration.json'; before = registration.read_bytes()
        code, _, errors = self.cli('prepare_cn_etf_household_diagnostic.py')
        self.assertNotEqual(code, 0); self.assertIn('frozen household proposal', errors)
        self.assertEqual(registration.read_bytes(), before)
        self.assertFalse((self.root/self.packet['ledger_path']).exists())


if __name__ == '__main__': unittest.main()
