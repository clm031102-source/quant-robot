from copy import deepcopy
from datetime import date,timedelta
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.research import us_fixed_allocation_2025_verification as V


def fixed_metadata():
    d=date(2000,12,1);dates=[]
    while d<=date(2001,2,15):
        if d.weekday()<5:dates.append(d.isoformat())
        d+=timedelta(days=1)
    first=dates.index('2000-12-29');ends=[first,dates.index('2001-01-31')]
    fixture={'schema':'us_fixed_allocation_2025_fixture_v1','evidence_kind':'artificial','assets':list(V.ledger.ASSETS),
        'days':[{'date':d,'prices':'OPAQUE_NOT_READ_FOR_SIGNAL'} for d in dates],
        'first_decision_date':dates[first],'terminal_date':dates[-1],'method_sha256':V.METHOD,
        'provenance':{'constructed_from_market_data':False}}
    signals=[{'index':i,'date':dates[i],'signal_kind':'fixed_calendar_weights_no_momentum','intended_gross':'1',
        'weights':{'fixed_quarters':dict.fromkeys(V.ledger.ASSETS,'.25')},'ordinary_execution_possible':i+4<len(dates)-1} for i in ends]
    return fixture,signals


class FixedVerificationTests(unittest.TestCase):
    def test_zero_legs_keep_declared_asset_order_after_sorted_json(self):
        fixture={'schema':'us_fixed_allocation_2025_fixture_v1','first_decision_date':'2000-12-29',
            'dividends':[],'provenance':{'split_policy_verified':True,'capital_gains_present':False,
                                     'holding_window_splits_absent':True}}
        legs=[{'decision_index':20,'date':'2000-12-29','asset':a,'target_quantity':0} for a in ('SPY','GLD')]
        account={'schema':'us_fixed_allocation_2025_account_v1','role':'primary','policy':'fixed_quarters',
            'minimum_commission':'1.00','slippage_bps':10,
            'monthly_events':[{'decision_index':20,'date':'2000-12-29',
                               'targets':{'SPY':0,'EFA':1,'IEF':2,'GLD':0},'buy_orders':[]}],
            'days':[],'zero_share_target_legs':legs,'zero_share_buy_legs':[],
            'unheld_asset_sessions':dict.fromkeys(V.ledger.ASSETS,0),'statistics':V.STATISTICS}
        saved=json.loads(json.dumps(account,sort_keys=True))
        self.assertEqual(list(saved['monthly_events'][0]['targets']),['EFA','GLD','IEF','SPY'])
        with patch.object(V.ledger,'_verify_account',return_value={}):
            self.assertEqual(V.verify_account(fixture,saved)['zero_share_target_legs'],2)
            saved['zero_share_target_legs'].reverse()
            with self.assertRaisesRegex(ValueError,'zero_targets'):
                V.verify_account(fixture,saved)
            cash=deepcopy(saved)
            cash.update(role='cash',policy='cash',minimum_commission='0.35',slippage_bps=0,
                        zero_share_target_legs=[])
            cash['monthly_events'][0]['targets']={}
            self.assertEqual(V.verify_account(fixture,cash)['zero_share_target_legs'],0)

    def test_fixed_calendar_never_reads_adjusted_or_ranking(self):
        f,s=fixed_metadata();self.assertEqual(len(V.verify_fixed_signals(f,s)),2)
        for case in ('weight','missing','rank','first'):
            with self.subTest(case=case):
                bad=deepcopy(s);fixture=deepcopy(f)
                if case=='weight':bad[0]['weights']['fixed_quarters']['SPY']='.50'
                elif case=='missing':bad.pop()
                elif case=='rank':bad[0]['ranked_positive']=['SPY']
                else:fixture['first_decision_date']=fixture['days'][19]['date']
                with self.assertRaises(ValueError):V.verify_fixed_signals(fixture,bad)

    def test_role_cost_and_legacy_defaults_remain_exact(self):
        f,_=fixed_metadata()
        a={'schema':'us_fixed_allocation_2025_account_v1','role':'cash','policy':'cash','minimum_commission':'1.00','slippage_bps':10}
        with self.assertRaisesRegex(ValueError,'role_minimum_commission'):V.verify_account(f,a)
        parameters=inspect.signature(V.ledger._verify_account).parameters
        self.assertEqual(parameters['expected_method'].default,V.ledger.METHOD)
        self.assertIs(parameters['signal_verifier'].default,V.ledger.verify_signals)
        self.assertNotEqual(V.ledger.METHOD,V.METHOD)

    def test_direct_production_fixture_requires_registration_and_marker(self):
        f,_=fixed_metadata();f['evidence_kind']='known_history_conditional';f['provenance']['registration_sha256']='a'*64
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def save(name,obj):
                b=json.dumps(obj).encode();(root/name).write_bytes(b);return {'path':name,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
            ref=save('fixture.json',f)
            with self.assertRaisesRegex(ValueError,'registration'):V.verify_recorded_accounts(root,ref,{},ref,None)
            wrappers={role:{'artifact':ref,'summary':{}} for role in V.ROLES}
            with self.assertRaisesRegex(ValueError,'completion_required'):V.verify_recorded_accounts(root,ref,wrappers,ref,'a'*64)
            wrong=save('completion.json',{'status':'complete','account_id':'wrong','registration_sha256':'a'*64,'artifact':ref})
            wrappers['primary']['completion']=wrong
            with self.assertRaisesRegex(ValueError,'completion_role'):V.verify_recorded_accounts(root,ref,wrappers,ref,'a'*64)


if __name__=='__main__':unittest.main()
