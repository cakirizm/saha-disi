import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from article_content import article_content, attributed_quotes
from feed_quality import publication_problem, mentioned_entities
from collector_v4 import youtube_rows
from collector_v3 import extract

class PublicationContractTests(unittest.TestCase):
    def test_legacy_verified_flag_does_not_allow_index_headline(self):
        row={'commentator':'ibrahim-seten','summary':'Tuchel artık sahaya dokunmalı!', 'url':'https://343digital.com/kategori/video','date':'2026-09-05','status':'verified_direct_quote'}
        self.assertEqual(publication_problem(row),'index_page_not_statement')
        row['url']='https://example.com/article'
        self.assertEqual(publication_problem(row),'legacy_attribution_requires_review')

    def test_new_evidence_must_match_person_and_original_url(self):
        row={'commentator':'a','url':'https://example.com/article','date':'2026-09-05','evidence':{'version':2,'speaker_id':'b','url':'https://example.com/article','method':'article_explicit_speaker'}}
        self.assertIsNotNone(publication_problem(row))
        row['evidence']['speaker_id']='a'
        self.assertIsNone(publication_problem(row))

    def test_article_excludes_related_cards_and_page_names(self):
        doc='''<meta name="datePublished" content="2026-09-05T00:00:00+03:00"><nav>Osimhen Galatasaray</nav>
        <div class="article-body"><p>Nihat Kahveci, "Torreira çok iyi bir maç oynadı."</p><aside>Nihat Kahveci: "Başka bir haberin oyuncu sözleri."</aside></div>
        <div class="related">Nihat Kahveci: "Yanlış başlığı sakın alıntı sayma."</div>'''
        body,date=article_content(doc)
        self.assertNotIn('Osimhen',body)
        self.assertNotIn('Yanlış',body)
        self.assertNotIn('Başka',body)
        self.assertTrue(date)
        self.assertEqual(attributed_quotes(body,'Nihat Kahveci')[0][0],'Torreira çok iyi bir maç oynadı.')
        self.assertEqual(attributed_quotes(body,'Yağız Sabuncuoğlu'),[])

    def test_publication_date_never_defaults_to_crawl_date(self):
        doc='<div class="article-body">Nihat Kahveci: "Torreira çok iyi bir maç oynadı."</div>'
        with patch('collector_v3.fetch',return_value=doc):
            self.assertEqual(extract('https://example.com/article',{'cid':'nihat-kahveci','trust':95,'source':'test'}),[])

    def test_player_tags_only_contain_mentioned_names(self):
        self.assertEqual(mentioned_entities('Kenan Yıldız çok mütevazı',['Osimhen','Kenan Yıldız','Leao']),['Kenan Yıldız'])
        self.assertEqual(mentioned_entities('Leaonun başka bir kelimesi',['Leao']),[])

    def test_multi_speaker_video_is_publication_not_quote(self):
        source={'name':'Test','commentators':['nihat-kahveci','yagiz-sabuncuoglu']}
        entries=[{'id':'abc','title':'Nihat Kahveci ve Yağız Sabuncuoğlu: Osimhen','published_at':'2026-09-05T00:00:00Z'}]
        with patch('collector_v4.youtube_entries',return_value=(entries,None)),patch('collector_v4.video_document') as document:
            rows,done,health,publications=youtube_rows(source,{'abc'})
        self.assertEqual(rows,[])
        self.assertEqual(len(publications),1)
        self.assertEqual(publications[0]['players'],['Osimhen'])
        self.assertEqual(len(publications[0]['commentators']),2)
        document.assert_not_called()

if __name__=='__main__':unittest.main()
