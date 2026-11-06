"""Artificial-only dependency and physical-I/O boundaries, no financial engine."""
from copy import deepcopy
from dataclasses import asdict,replace
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import patch

from quant_robot.ops import paper_evidence_session as sessions
from quant_robot.ops import paper_source_bundle as old_bundle


def encoded(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()


def digest(raw):return sha256(raw).hexdigest()


class EvidenceSessionTests(TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve()

    def save(self,name,raw):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        return dict(path=name,sha256=digest(raw))

    def chain(self,count,*,journal='journal',event_bytes=None):
        raws=[];events=[];previous=None
        for index in range(count):
            kind='activation' if index==0 else ('decision','decision_durability','observation','observation_durability')[(index-1)%4]
            event=dict(artifact_type=sessions.EVENT_TYPE,sequence=index,kind=kind,
                previous_sha256=previous,received_at='2020-01-02T00:00:00Z',payload=dict(synthetic_only=True,padding=''))
            event['sha256']=digest(encoded(event))
            if event_bytes is not None:
                event['payload']['padding']='x'*(event_bytes-len(encoded(event)))
                unsigned={key:value for key,value in event.items() if key!='sha256'}
                event['sha256']=digest(encoded(unsigned))
            raw=encoded(event)
            if event_bytes is not None:self.assertEqual(len(raw),event_bytes)
            self.save(f'{journal}/{index:08d}.json',raw)
            raws.append(raw);events.append(event);previous=event['sha256']
        return raws,events

    def descriptor(self,raws,events,count,*,policy=sessions.SYNTHETIC_POLICY,journal='journal'):
        # Independent implementation of the written commitment format.
        root=digest(b'paper-prefix-seed-v2\0'+encoded([journal,events[0]['sha256']]))
        for index,raw in enumerate(raws[:count]):
            root=digest(b'paper-prefix-step-v2\0'+bytes.fromhex(root)+index.to_bytes(8,'big')
                        +len(raw).to_bytes(8,'big')+sha256(raw).digest())
        return dict(dependency_type=sessions.PREFIX_TYPE,policy_id=policy.policy_id,
            journal_relative_path=journal,activation_sha256=events[0]['sha256'],prefix_length=count,
            prefix_canonical_tail_sha256=events[count-1]['sha256'],prefix_raw_commitment=root,
            total_original_bytes=sum(map(len,raws[:count])))

    def operation(self,policy=sessions.SYNTHETIC_POLICY):
        return sessions.EvidenceOperation(self.root,policy=policy)

    def ordinary_stage(self,op,reference):
        with op.stage() as stage:
            child=stage.child('price');child.read_bytes(reference);ticket=child.propose({'synthetic_value':7})
            verified=stage.commit()
        return verified,ticket

    def test_only_code_owned_policy_objects_and_unchanged_ordinary_defaults(self):
        for policy in (asdict(sessions.SYNTHETIC_POLICY),replace(sessions.SYNTHETIC_POLICY),
                       sessions.SYNTHETIC_POLICY.policy_id):
            with self.subTest(policy_type=type(policy).__name__):
                with self.assertRaisesRegex(ValueError,'code_owned'):self.operation(policy)
        self.assertEqual((old_bundle.MAX_DOCUMENTS,old_bundle.MAX_TOTAL_BYTES,old_bundle.MAX_DOCUMENT_BYTES),
                         (128,16_000_000,2_000_000))
        binding=sessions.policy_binding()
        self.assertEqual(binding['policy_sha256'],digest(encoded(binding['policy'])))
        binding['policy']['ordinary_files']=999
        self.assertEqual(sessions.policy_binding()['policy']['ordinary_files'],128)

    def test_merge_prefixes_scan_each_original_twice_and_match_standalone(self):
        raws,events=self.chain(11);op=self.operation();tickets=[]
        with op.stage() as stage:
            for count in (7,3,11):
                child=stage.child(f'price_{count}');descriptor=self.descriptor(raws,events,count)
                self.assertIsNone(child.require_prefix(descriptor))
                self.assertIsNone(child.recheck())
                tickets.append(child.propose({'prefix':count,'raw_root':descriptor['prefix_raw_commitment']}))
            initial=stage.measurements()
            self.assertEqual(initial['open_attempts'],12)  # Code + eleven distinct originals.
            verified=stage.commit()
        stats=op.measurements()['stages'][0]
        self.assertEqual(stats['unique_original_files'],11)
        self.assertEqual(stats['open_attempts'],24)
        self.assertEqual(stats['io_bytes_returned'],2*(sum(map(len,raws))+Path(sessions.__file__).stat().st_size))
        self.assertTrue(all(row['opens']==2 for row in stats['per_path'].values()))
        for count,ticket in zip((7,3,11),tickets):
            separate=self.operation()
            with separate.stage() as stage:
                child=stage.child('price');desc=self.descriptor(raws,events,count)
                child.require_prefix(desc);single=child.propose({'prefix':count,'raw_root':desc['prefix_raw_commitment']})
                other=stage.commit()
            self.assertEqual(verified.result(ticket),other.result(single))

    def test_child_result_cannot_escape_finalization_and_input_value_is_copied(self):
        ref=self.save('input',b'value');op=self.operation()
        with op.stage() as stage:
            child=stage.child('price');child.read_bytes(ref);value={'number':1}
            ticket=child.propose(value);value['number']=99
            self.assertFalse(hasattr(ticket,'payload'));self.assertFalse(hasattr(ticket,'success'))
            with self.assertRaisesRegex(ValueError,'not_finalized'):ticket.result()
            self.assertIsNone(child.recheck())
            verified=stage.commit()
        self.assertEqual(verified.result(ticket),{'number':1})
        copy=verified.result(ticket);copy['number']=88
        self.assertEqual(verified.result(ticket),{'number':1})
        with self.assertRaisesRegex(ValueError,'session_not_open'):child.read_bytes(ref)
        op.close()
        with self.assertRaisesRegex(ValueError,'operation_not_open'):op.stage()

    def test_empty_child_cannot_borrow_another_childs_obligations(self):
        raws,events=self.chain(1);op=self.operation()
        with self.assertRaisesRegex(ValueError,'originals_required'):
            with op.stage() as stage:
                stage.child('owner').require_prefix(self.descriptor(raws,events,1))
                stage.child('empty').propose({'pretend':'verified'})
        self.assertEqual(op.measurements()['state'],'failed')

    def test_every_prefix_original_is_rechecked_after_parsing(self):
        raws,events=self.chain(3);desc=self.descriptor(raws,events,3)
        for index in range(3):
            with self.subTest(index=index):
                op=self.operation();path=self.root/f'journal/{index:08d}.json'
                with self.assertRaisesRegex(ValueError,'original_changed_at_final_read'):
                    with op.stage() as stage:
                        child=stage.child('price');child.require_prefix(desc);ticket=child.propose({'x':1})
                        path.write_bytes(raws[index]+b' ');stage.commit()
                path.write_bytes(raws[index])
                with self.assertRaises(ValueError):ticket.result()
                with self.assertRaisesRegex(ValueError,'operation_not_open'):op.stage()

    def test_legal_append_and_transient_restore_are_not_overclaimed(self):
        raws,events=self.chain(3);desc=self.descriptor(raws,events,3);op=self.operation()
        with op.stage() as stage:
            child=stage.child('price');child.require_prefix(desc);ticket=child.propose({'at_boundary':True})
            tail=dict(artifact_type=sessions.EVENT_TYPE,sequence=3,kind='observation',
                previous_sha256=events[2]['sha256'],received_at='2020-01-02T00:00:00Z',
                payload=dict(synthetic_only=True))
            tail['sha256']=digest(encoded(tail))
            self.save('journal/00000003.json',encoded(tail))
            path=self.root/'journal/00000001.json';path.write_bytes(b'transient edit');path.write_bytes(raws[1])
            verified=stage.commit()
        receipt=verified.receipt()
        self.assertFalse(receipt['transient_change_detection_claimed'])
        self.assertFalse(receipt['post_boundary_integrity_guaranteed'])
        self.assertNotIn('journal/00000003.json',op.measurements()['stages'][0]['per_path'])
        path.write_bytes(b'post-boundary change')
        self.assertEqual(verified.result(ticket),{'at_boundary':True})
        fresh=self.operation()
        with self.assertRaises(ValueError):
            with fresh.stage() as stage:stage.child('price').require_prefix(desc)

    def test_path_aliases_deduplicate_but_equal_content_paths_are_distinct(self):
        first=self.save('a.bin',b'same');second=self.save('b.bin',b'same');op=self.operation()
        os.link(self.root/'a.bin',self.root/'linked-copy.bin')
        hard_link=dict(path='linked-copy.bin',sha256=first['sha256'])
        with op.stage() as stage:
            child=stage.child('price');child.read_bytes(first);child.read_bytes(first);child.read_bytes(second)
            child.read_bytes(hard_link)
            ticket=child.propose({'paths':3});verified=stage.commit()
        stats=verified.receipt()['measurements']
        self.assertEqual(stats['unique_original_files'],3)
        self.assertEqual(stats['per_path']['a.bin']['opens'],2)
        self.assertEqual(stats['per_path']['b.bin']['opens'],2)
        self.assertEqual(stats['per_path']['linked-copy.bin']['opens'],2)
        self.assertEqual(verified.result(ticket),{'paths':3})

    def test_conflicting_expected_sha_poisoned_without_second_original_read(self):
        ref=self.save('a.bin',b'same');op=self.operation()
        with self.assertRaisesRegex(ValueError,'expected_sha_conflict'):
            with op.stage() as stage:
                child=stage.child('price');child.read_bytes(ref)
                stage.child('other').read_bytes({**ref,'sha256':'0'*64})
        self.assertEqual(op.measurements()['stages'][0]['per_path']['a.bin']['opens'],1)

    def test_prefix_policy_and_exact_original_commitment_fail_closed(self):
        raws,events=self.chain(3);good=self.descriptor(raws,events,3)
        mutations=[{**good,'budget':999999},{**good,'policy_id':'unreviewed'},
                   {**good,'prefix_raw_commitment':'0'*64},{**good,'prefix_length':True}]
        for desc in mutations:
            with self.subTest(fields=tuple(desc)):
                op=self.operation()
                with self.assertRaises(ValueError):
                    with op.stage() as stage:stage.child('price').require_prefix(desc)
                self.assertEqual(op.measurements()['state'],'failed')

    def test_matching_raw_commitment_cannot_hide_invalid_chain_or_clock(self):
        for mutation in ('chain','clock'):
            with self.subTest(mutation=mutation):
                raws,events=self.chain(2)
                if mutation=='chain':events[1]['previous_sha256']='0'*64
                else:events[1]['received_at']='2020-01-01T00:00:00Z'
                events[1].pop('sha256');events[1]['sha256']=digest(encoded(events[1]))
                raws[1]=encoded(events[1]);self.save('journal/00000001.json',raws[1])
                op=self.operation()
                with self.assertRaisesRegex(ValueError,'journal_hash_chain_invalid|journal_clock_regressed'):
                    with op.stage() as stage:stage.child('price').require_prefix(self.descriptor(raws,events,2))

    def test_foreign_root_missing_original_and_symlink_are_rejected(self):
        raws,events=self.chain(3);good=self.descriptor(raws,events,3)
        outside=self.root/'different-root';outside.mkdir()
        op=sessions.EvidenceOperation(outside)
        with self.assertRaises(OSError):
            with op.stage() as stage:stage.child('price').require_prefix(good)
        self.assertEqual(op.measurements()['open_attempts'],2)  # Code plus failed original open.
        op=self.operation()
        with self.assertRaises(ValueError):
            with op.stage() as stage:stage.child('price').require_prefix({**good,'journal_relative_path':'../journal'})
        link=self.root/'linked'
        try:link.symlink_to(self.root/'journal',target_is_directory=True)
        except OSError:self.skipTest('Host cannot create the artificial symlink')
        linked={**good,'journal_relative_path':'linked'};op=self.operation()
        with self.assertRaisesRegex(ValueError,'original_link_forbidden'):
            with op.stage() as stage:stage.child('price').require_prefix(linked)

    def test_real_ordinary_128_file_and_16mb_limits_are_preserved(self):
        refs=[self.save(f'small/{i}',b'x') for i in range(129)]
        op=self.operation()
        with op.stage() as stage:
            child=stage.child('price')
            for ref in refs[:128]:child.read_bytes(ref)
            child.propose({'count':128});stage.commit()
        op=self.operation()
        with self.assertRaisesRegex(ValueError,'ordinary_file_budget_exceeded'):
            with op.stage() as stage:
                child=stage.child('price')
                for ref in refs:child.read_bytes(ref)
        large=[self.save(f'large/{i}',b'z'*2_000_000) for i in range(8)]
        op=self.operation()
        with op.stage() as stage:
            child=stage.child('price')
            for ref in large:child.read_bytes(ref)
            child.propose({'bytes':16_000_000});stage.commit()
        op=self.operation()
        with self.assertRaisesRegex(ValueError,'ordinary_byte_budget_exceeded'):
            with op.stage() as stage:
                child=stage.child('price')
                for ref in large:child.read_bytes(ref)
                child.read_bytes(refs[0])

    def test_prefix_count_byte_and_per_document_hard_stops(self):
        policy=sessions._SMALL_POLICY;raws,events=self.chain(9)
        op=self.operation(policy)
        with op.stage() as stage:
            child=stage.child('price');child.require_prefix(self.descriptor(raws,events,8,policy=policy))
            child.propose({'events':8});stage.commit()
        op=self.operation(policy)
        with self.assertRaisesRegex(ValueError,'prefix_budget'):
            with op.stage() as stage:stage.child('price').require_prefix(self.descriptor(raws,events,9,policy=policy))
        raws,events=self.chain(3,event_bytes=2048)
        op=self.operation(policy)
        with op.stage() as stage:
            child=stage.child('price');child.require_prefix(self.descriptor(raws,events,2,policy=policy))
            child.propose({'bytes':4096});stage.commit()
        forged={**self.descriptor(raws,events,3,policy=policy),'total_original_bytes':4096}
        op=self.operation(policy)
        with self.assertRaisesRegex(ValueError,'prefix_raw_byte_budget_exceeded'):
            with op.stage() as stage:stage.child('price').require_prefix(forged)
        ref=self.save('oversized',b'x'*2049);op=self.operation(policy)
        with self.assertRaisesRegex(ValueError,'document_byte_budget_exceeded'):
            with op.stage() as stage:stage.child('price').read_bytes(ref)
        self.assertEqual(op.measurements()['stages'][0]['per_path']['oversized']['bytes'],0)

    def test_union_caps_apply_across_children(self):
        refs=[self.save(f'union/{i}',b'x') for i in range(11)];op=self.operation(sessions._SMALL_POLICY)
        with self.assertRaisesRegex(ValueError,'union_file_budget_exceeded'):
            with op.stage() as stage:
                for index,ref in enumerate(refs):stage.child(f'c{index}').read_bytes(ref)
        op=self.operation(sessions._UNION_POLICY);ref=self.save('union_bytes',b'x'*128)
        with op.stage() as stage:
            child=stage.child('price');child.read_bytes(ref);child.propose({'bytes':128});stage.commit()
        op=self.operation(sessions._UNION_POLICY)
        with self.assertRaisesRegex(ValueError,'union_byte_budget_exceeded'):
            with op.stage() as stage:
                stage.child('a').read_bytes(ref);stage.child('b').read_bytes(refs[0])

    def test_physical_stage_budget_matches_independent_os_read_counts(self):
        code_bytes=Path(sessions.__file__).stat().st_size
        payload=(sessions._IO_POLICY.stage_io_bytes-2*code_bytes)//2
        self.assertGreater(payload,0)
        original_open,original_read=os.open,os.read;opens=[];read_sizes=[]
        def tracked_open(*args,**kwargs):opens.append(str(args[0]));return original_open(*args,**kwargs)
        def tracked_read(*args):
            raw=original_read(*args);read_sizes.append(len(raw));return raw
        ref=self.save('exact_io',b'x'*payload);op=self.operation(sessions._IO_POLICY)
        with patch.object(os,'open',side_effect=tracked_open),patch.object(os,'read',side_effect=tracked_read):
            self.ordinary_stage(op,ref)
        self.assertEqual(op.measurements()['io_bytes_returned'],128_000)
        self.assertEqual(sum(read_sizes),128_000)
        self.assertEqual(len(opens),op.measurements()['open_attempts'])
        ref=self.save('over_io',b'x'*(payload+1));op=self.operation(sessions._IO_POLICY)
        with self.assertRaisesRegex(ValueError,'physical_io_byte_budget_exceeded'):self.ordinary_stage(op,ref)
        self.assertEqual(op.measurements()['io_bytes_returned'],128_000)

    def test_failed_reads_remain_charged_and_failed_operation_cannot_resume(self):
        ref=self.save('read_failure',b'x'*100_000);op=self.operation();real_read=os.read;calls=0
        def fail_second_data_read(fd,size):
            nonlocal calls
            if os.fstat(fd).st_size==100_000:
                calls+=1
                if calls==2:raise OSError('synthetic read failure')
            return real_read(fd,size)
        with patch.object(os,'read',side_effect=fail_second_data_read):
            with self.assertRaises(OSError):self.ordinary_stage(op,ref)
        stats=op.measurements();row=stats['stages'][0]['per_path']['read_failure']
        self.assertEqual(row,dict(opens=1,bytes=65536,reads=2))
        self.assertEqual(stats['io_bytes_returned'],65536+Path(sessions.__file__).stat().st_size)
        before=stats['open_attempts']
        with self.assertRaises(ValueError):op.stage()
        self.assertEqual(op.measurements()['open_attempts'],before)

    def test_open_attempts_and_total_operation_io_never_reset_between_stages(self):
        ref=self.save('one',b'x');op=self.operation(sessions._OPEN_POLICY)
        self.ordinary_stage(op,ref);self.ordinary_stage(op,ref)
        with self.assertRaisesRegex(ValueError,'operation_open_budget_exceeded'):op.stage()
        self.assertEqual(op.measurements()['open_attempts'],8)
        code_bytes=Path(sessions.__file__).stat().st_size
        ref=self.save('io',b'x'*((128_000-2*code_bytes)//2));op=self.operation(sessions._IO_POLICY)
        self.ordinary_stage(op,ref);self.ordinary_stage(op,ref)
        with self.assertRaisesRegex(ValueError,'physical_io_byte_budget_exceeded'):op.stage()
        self.assertEqual(op.measurements()['io_bytes_returned'],256_000)

    def test_stage_open_limit_blocks_before_fifth_open(self):
        refs=[self.save(f'stage_open_{i}',b'x') for i in range(2)]
        op=self.operation(sessions._OPEN_POLICY)
        with self.assertRaisesRegex(ValueError,'stage_open_budget_exceeded'):
            with op.stage() as stage:
                child=stage.child('price')
                for ref in refs:child.read_bytes(ref)
                child.propose({'x':1});stage.commit()
        self.assertEqual(op.measurements()['open_attempts'],4)

    def test_four_stage_ceiling_abandonment_and_nested_stage_hard_stop(self):
        ref=self.save('one',b'x');op=self.operation()
        for _ in range(4):self.ordinary_stage(op,ref)
        before=op.measurements()['open_attempts']
        with self.assertRaisesRegex(ValueError,'operation_stage_budget_exceeded'):op.stage()
        self.assertEqual(op.measurements()['open_attempts'],before)
        op=self.operation()
        with op.stage() as stage:
            child=stage.child('price');child.read_bytes(ref);ticket=child.propose({'abandoned':True})
        self.assertEqual(op.measurements()['state'],'failed')
        with self.assertRaises(ValueError):ticket.result()
        op=self.operation()
        with self.assertRaisesRegex(ValueError,'nested_stage_forbidden'):
            with op.stage():op.stage()
        self.assertEqual(op.measurements()['state'],'failed')

    def test_implementation_bytes_participate_in_final_read_and_binding(self):
        code=self.root/'artificial_code.py';code.write_bytes(b'artificial initial code')
        ref=self.save('one',b'x');op=self.operation()
        with patch.object(sessions,'__file__',str(code)):
            with self.assertRaisesRegex(ValueError,'implementation_or_policy_changed'):
                with op.stage() as stage:
                    child=stage.child('price');child.read_bytes(ref);child.propose({'x':1})
                    code.write_bytes(b'artificial changed code');stage.commit()
        counts=op.measurements()['stages'][0]['per_path']['@implementation/paper_evidence_session.py']
        self.assertEqual(counts['opens'],2)
        self.assertEqual(counts['bytes'],len(b'artificial initial code')+len(b'artificial changed code'))
