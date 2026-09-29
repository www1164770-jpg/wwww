import json
import sys
import unittest
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from behavior_readiness import analyze, audit_connection

class ReadinessTests(unittest.TestCase):
    def row(self, **changes):
        return dict(user_id=1,website_id=1,event_type='impression',source='personalized_recommendation',recommendation_batch_id='b',session_id='s',created_at=None,valid_resource=1,valid_user=1,metadata_json='{}',**changes)

    def test_null_time_not_zero_window(self):
        r=analyze([self.row()],exclusions_verified=True)
        self.assertEqual(r['status'],'cannot_evaluate')
        self.assertIsNone(r['partitions'][0]['windows']['7'])
        self.assertIsNone(r['partitions'][0]['historical_profiles'])

    def test_unverified_accounts_never_real_users(self):
        row=self.row();row['created_at']=datetime.now()
        r=analyze([row]);self.assertEqual(r['status'],'cannot_evaluate')
        self.assertNotIn('real_users',r)

    def test_versions_separate_and_duplicate_local(self):
        a=self.row();b=self.row();b['metadata_json']=json.dumps({'event_version':'visible-v2'})
        r=analyze([a,a,b]);self.assertEqual(len(r['partitions']),2)
        self.assertEqual([p['duplicate_impressions'] for p in r['partitions']],[1,0])

    def test_exclusions_explicit_and_missing_ids(self):
        a=self.row();a['valid_resource']=0
        r=analyze([a]);self.assertEqual(r['quality']['invalid_resource'],1)
        r=analyze([a],excluded=[1],exclusions_verified=True)
        self.assertEqual(r['rows_after_exclusion'],0)

    def test_click_missing_batch_and_time_does_not_pass(self):
        a=self.row();a.update(event_type='click',recommendation_batch_id=None)
        p=analyze([a])['partitions'][0]
        self.assertEqual(p['orphan_recommendation_clicks'],1)
        self.assertEqual(p['click_duplicate_check_unknown'],1)

    def test_read_only_transaction_rolls_back_on_failure(self):
        class Cursor:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def execute(self,sql,*args):
                statements.append(sql)
                if sql.startswith('SELECT'):raise RuntimeError('unavailable')
        class Connection:
            def cursor(self):return Cursor()
            def rollback(self):statements.append('ROLLBACK')
        statements=[]
        with self.assertRaises(RuntimeError):audit_connection(Connection())
        self.assertIn('READ ONLY',statements[0]);self.assertEqual(statements[-1],'ROLLBACK')
        self.assertFalse(any(s.startswith(('INSERT','UPDATE','DELETE','CREATE')) for s in statements))

if __name__=='__main__':unittest.main()
