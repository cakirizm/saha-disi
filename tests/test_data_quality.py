import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from feed_quality import merge_fixture, match_status, statement_image, normalize_kickoff
from collector_v3 import candidate_rows, classify
from social_sources import x_posts, post_candidate, collect_social

class DataQualityTests(unittest.TestCase):
    def test_tff_date_normalizes_to_istanbul(self):
        self.assertEqual(normalize_kickoff('04.09.2026 20:00'),'2026-09-04T20:00:00+03:00')

    def test_empty_override_does_not_erase_result(self):
        row=merge_fixture({'home_score':2,'away_score':3},{'home_score':None,'away_score':None},fallback=True)
        self.assertEqual((row['home_score'],row['away_score']),(2,3))

    def test_fallback_does_not_replace_fresh_score(self):
        self.assertEqual(merge_fixture({'home_score':2},{'home_score':1},fallback=True)['home_score'],2)

    def test_zero_score_is_data(self):
        self.assertEqual(merge_fixture({'home_score':2},{'home_score':0})['home_score'],0)

    def test_missing_result_is_not_scheduled_or_finished(self):
        now=datetime(2026,9,5,tzinfo=timezone.utc)
        self.assertEqual(match_status({'kickoff':'2026-09-04T20:00:00+03:00'},now),'awaiting_result')
        self.assertEqual(match_status({'kickoff':'05.09.2026 20:00'},now),'scheduled')
        self.assertEqual(match_status({'kickoff':'not a date'},now),'unscheduled')

    def test_postponement_survives(self):
        self.assertEqual(match_status({'status':'postponed','kickoff':'2020-01-01'}),'postponed')

    def test_article_image_never_becomes_portrait(self):
        row={'commentator':'a','image_url':'https://news.example/logo.jpg'}
        self.assertIsNone(statement_image(row,{}))
        self.assertEqual(statement_image(row,{'a':'https://portraits.example/a.jpg'}),'https://portraits.example/a.jpg')

    def test_other_speakers_quote_not_attributed(self):
        src={'cid':'nihat-kahveci','source':'test','trust':95}
        rows=candidate_rows('Nihat Kahveci programda. Ali Ece: "Galatasaray bugün çok iyi futbol oynadı."',src,'https://example.com')
        self.assertEqual(rows,[])

    def test_quote_entities_exclude_navigation(self):
        src={'cid':'nihat-kahveci','source':'test','trust':80}
        rows=candidate_rows('Fenerbahçe haberleri. Nihat Kahveci: "Galatasaray bugün çok iyi futbol oynadı."',src,'https://example.com')
        self.assertTrue(rows)
        self.assertEqual(rows[0]['team'],'Galatasaray')
        self.assertEqual(rows[0]['confidence'],80)

    def test_transfer_is_not_overridden_by_hot_take(self):
        self.assertEqual(classify('Kesin transfer olacak, imza atacak')[0],'transfer')
        self.assertEqual(classify('The signing is ready, contract agreed.')[0],'transfer')

    def test_x_requires_matching_author(self):
        account={'commentator':'fabrizio-romano','username':'FabrizioRomano'}
        payload={'includes':{'users':[{'id':'123','username':'impersonator'}]},'data':[{'id':'456','author_id':'123','text':'Transfer deal agreed, here we go!','created_at':'2026-09-05T00:00:00Z'}]}
        with patch('social_sources.api_get',return_value=payload):self.assertEqual(x_posts(account,'test'),([],False))
        payload['includes']['users'][0]['username']='FabrizioRomano'
        with patch('social_sources.api_get',return_value=payload):self.assertEqual(len(x_posts(account,'test')[0]),1)

    def test_social_missing_date_or_long_post_not_truncated(self):
        account={'commentator':'a','username':'a'}
        self.assertIsNone(post_candidate(account,'transfer '*100,'https://x.com/a/status/1','2026-09-05','X'))
        self.assertIsNone(post_candidate(account,'Transfer contract agreed today','https://x.com/a/status/1',None,'X'))

    def test_missing_credentials_reported(self):
        with patch.dict('os.environ',{},clear=True):
            rows,health=collect_social()
        self.assertEqual(rows,[])
        self.assertTrue(all(x['error']=='missing_credentials' for x in health))

if __name__=='__main__':unittest.main()
