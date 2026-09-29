import sys,unittest
from pathlib import Path
from datetime import datetime,timedelta
from flask import Flask
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'backend/scripts'),str(ROOT)]
from recommendation_stage4 import reorder
from recommendation_feedback_routes import register
from recommend_service import rank_sites,MATCH_WEIGHTS
from stage4_fixtures import resources,PROFILES

class DiversityTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,9,26)
        self.baseline=rank_sites(resources(),PROFILES[0]['profile'],60)

    def test_frozen_weights(self):
        self.assertEqual(MATCH_WEIGHTS,{'occupation':20,'direction':30,'primary_need':35,'priority':10,'other_tags':5})

    def test_default_is_exact_baseline_no_database_access(self):
        app=Flask(__name__)
        def forbidden():raise AssertionError('disabled rollout must not access feedback DB')
        decorate=register(app,forbidden,lambda:None,lambda x:x,lambda *args:args)
        self.assertIs(decorate(self.baseline,1),self.baseline)

    def test_only_public_related_and_known_hard_conditions(self):
        result=reorder(self.baseline,now=self.now,diversity=True)
        self.assertTrue(set(s['id'] for s in result)<={1,2,3,4})
        self.assertFalse({9,10,11,12}&{s['id'] for s in result})
        self.assertTrue(all(s['match_evidence'] for s in result))

    def test_no_domain_or_name_identity_guess(self):
        rows=[{**self.baseline[0],'id':n,'canonical_site_id':n,'name':'Same','url':f'https://one.invalid/product/{n}'} for n in (21,22)]
        self.assertEqual(len(reorder(rows,now=self.now,diversity=True)),2)
        rows[1]['canonical_site_id']=21
        self.assertEqual(len(reorder(rows,now=self.now,diversity=True)),1)

    def test_scores_reasons_and_large_relevance_gaps_preserved(self):
        rows=[{**self.baseline[0],'id':21,'canonical_site_id':21,'match_score':90},
              {**self.baseline[0],'id':22,'canonical_site_id':22,'match_score':70,'tags':['extra1','extra2'],'category_id':9}]
        result=reorder(rows,now=self.now,diversity=True)
        self.assertEqual([s['id'] for s in result],[21,22])
        self.assertEqual([s['match_score'] for s in result],[90,70])
        self.assertEqual([s['reason'] for s in result],[s['reason'] for s in rows])

    def test_unknown_required_condition_never_promoted(self):
        site={**self.baseline[0],'condition_checks':[{'strength':'must','state':'unknown'}]}
        self.assertEqual(reorder([site],now=self.now,diversity=True),[])

    def test_irrelevant_is_resource_only_and_reversible(self):
        selected=reorder(self.baseline,now=self.now,diversity=True)
        sid=selected[0]['id'];pref=[{'website_id':sid,'reason':'irrelevant','expires_at':None}]
        excluded=reorder(self.baseline,pref,now=self.now,diversity=True)
        self.assertNotIn(sid,[s['id'] for s in excluded]);self.assertTrue(excluded)
        pref[0]['reason']=None
        self.assertEqual(selected,reorder(self.baseline,pref,now=self.now,diversity=True))

    def test_temporarily_suspended_expires(self):
        sid=2;pref=[{'website_id':sid,'reason':'later','expires_at':self.now+timedelta(days=30)}]
        self.assertNotIn(sid,[s['id'] for s in reorder(self.baseline,pref,now=self.now)])
        self.assertIn(sid,[s['id'] for s in reorder(self.baseline,pref,now=self.now+timedelta(days=30))])

    def test_known_deprioritized_without_global_score_change(self):
        sid=2;pref=[{'website_id':sid,'reason':'known','expires_at':self.now+timedelta(days=7)}]
        result=reorder(self.baseline,pref,now=self.now)
        self.assertGreater(next(i for i,r in enumerate(result) if r['id']==sid),0)
        self.assertEqual(next(r['match_score'] for r in result if r['id']==sid),next(r['match_score'] for r in self.baseline if r['id']==sid))

    def test_stable_and_no_filler(self):
        first=reorder(self.baseline,now=self.now,diversity=True)
        self.assertEqual(first,reorder(self.baseline,now=self.now,diversity=True))
        self.assertEqual(reorder([],now=self.now,diversity=True),[])

if __name__=='__main__':unittest.main()
