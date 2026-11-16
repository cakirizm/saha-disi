import re
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import collector_v3 as c
import columnist_discovery as d

# build_feed publishes a candidate only at this confidence or above.
PUBLISH_BAR=95


class ColumnistSourceTests(unittest.TestCase):
    def test_every_byline_source_clears_the_publish_bar(self):
        # Takvim sat at 92: its columnists were collected, then all sent to review.
        for publisher in d.PUBLISHERS:
            self.assertGreaterEqual(publisher['trust'],PUBLISH_BAR,publisher['source'])
        self.assertGreaterEqual(d.TARGETED_TRUST,PUBLISH_BAR)
        for src in c.direct_sources():
            self.assertGreaterEqual(src['trust'],PUBLISH_BAR,src['url'])

    def test_targeted_authors_are_roster_commentators(self):
        for source,url,cid in d.TARGETED:
            self.assertIn(cid,c.COMMENTATORS,url)
            self.assertTrue(url.startswith('https://'),url)
        self.assertEqual(len(d.targeted_jobs()),len(d.TARGETED))

    def test_index_slugs_with_underscore_or_dot_are_tried(self):
        page=('<a href="/yazarlar/mustafa_culcu/arsiv">x</a><a href="/yazarlar/serkan.korkmaz/arsiv">y</a>'
              '<a href="/yazarlar/tum-yazarlar">z</a><a href="/yazarlar/logo.png">i</a>')
        with patch.object(c,'fetch',return_value=page):
            slugs=d.slugs_of({'index':'https://www.fotomac.com.tr/yazarlar/tum-yazarlar'})
        self.assertEqual(slugs,['mustafa_culcu','serkan.korkmaz'])

    def test_discovered_author_takes_roster_id_by_name(self):
        self.assertEqual(d.author_cid('Feyyaz Uçar','feyyazucar'),'feyyaz-ucar')
        self.assertEqual(d.author_cid('RIDVAN DİLMEN','dilmen'),'ridvan-dilmen')
        self.assertEqual(d.author_cid('Yeni Yazar','yeni_yazar'),'yeni-yazar')

    def test_validate_keeps_roster_id_and_name(self):
        job={'url':'https://beinsports.com.tr/yazarlar/feyyazucar','source':'beIN SPORTS','trust':95,'slug':'feyyazucar','cid':None}
        doc='<meta property="og:title" content="Feyyaz Uçar | beIN SPORTS">'
        with patch.object(c,'fetch',return_value=doc),patch.object(d,'football_sentences',return_value=5):
            row=d.validate(job)
        self.assertEqual(row['cid'],'feyyaz-ucar')
        self.assertEqual(row['name'],c.COMMENTATORS['feyyaz-ucar'])

    def test_validate_drops_author_without_football_columns(self):
        job=d.targeted_jobs()[0]
        with patch.object(c,'fetch',return_value=''),patch.object(d,'football_sentences',return_value=1):
            self.assertIsNone(d.validate(job))

    def test_one_commentator_keeps_a_row_per_site_and_current_trust(self):
        now=datetime(2026,11,16,tzinfo=timezone.utc)
        old=[{'cid':'abdullah-ercan','url':'https://www.takvim.com.tr/yazarlar/abdullah-ercan/arsiv','source':'Takvim','trust':92,'last_validated':'2026-11-14'}]
        found=[{'cid':'ridvan-dilmen','url':'https://www.ntvspor.net/yazarlar/ridvan-dilmen','source':'NTV Spor','trust':95,'last_validated':'2026-11-16'},
               {'cid':'ridvan-dilmen','url':'https://www.sabah.com.tr/yazarlar/dilmen/arsiv','source':'Sabah Spor','trust':95,'last_validated':'2026-11-16'}]
        rows=d.merge(old,found,now)
        self.assertEqual(len(rows),3)
        self.assertEqual({r['trust'] for r in rows},{95})

    def test_committed_columnists_clear_the_publish_bar(self):
        for row in d.load_existing():
            self.assertGreaterEqual(row.get('trust',0),PUBLISH_BAR,row['url'])


if __name__=='__main__':
    unittest.main()
