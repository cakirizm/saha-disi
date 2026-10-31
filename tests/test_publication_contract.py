import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from article_content import article_content, attributed_quotes
from feed_quality import publication_problem, mentioned_entities
from collector_v4 import youtube_rows
from collector_v3 import extract, SENTENCE_SPLIT
from incidents import judgements, minute_of, recovered_minutes, build_incidents

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

    def test_ios_accepts_every_backend_evidence_method(self):
        # The app re-checks evidence while decoding, so a method the backend
        # publishes but the app omits is discarded on the device and the feed
        # silently looks empty. Keep the two gates identical.
        models=(Path(__file__).resolve().parents[1]/'ios/SahaDisi/SahaDisi/Models/Models.swift').read_text(encoding='utf-8')
        for method in ('article_explicit_speaker','official_api_author_match','columnist_byline'):
            row={'url':'https://example.com/yazarlar/a/b','date':'2026-09-05','commentator':'x','summary':'Beşiktaş dün gece çok iyi oynadı ve kazandı.',
                 'evidence':{'version':2,'method':method,'speaker_id':'x','url':'https://example.com/yazarlar/a/b'}}
            self.assertIsNone(publication_problem(row),method)
            self.assertIn(f'"{method}"',models,f'{method} is published but the iOS gate drops it')

class IncidentVerdictTests(unittest.TestCase):
    # Sentences below are taken from published referee columns.
    def test_missed_penalty_is_penalty_and_referee_wrong(self):
        text='76.dakikada Thalisson’un Metehan Mimaroğlu’na müdahalesinde Trabzonspor lehine penaltı kararı verilmesi gerekirdi.'
        self.assertEqual(judgements(text),[('penalty','PENALTI','hatali')])
        self.assertEqual(minute_of(text),76)

    def test_play_on_after_penalty_appeal_is_no_penalty(self):
        self.assertEqual(judgements('Hakemin maç boyunca penaltı beklenen pozisyonlardaki devam kararları ise yerindeydi.'),[('penalty','DEĞİL','dogru')])

    def test_reporting_a_card_is_not_a_verdict(self):
        self.assertEqual(judgements("87'de hakem, Mustafa Er, kırmızı kartla oyundan attı!"),[])

    def test_negated_claim_and_frankly_are_not_verdicts(self):
        self.assertEqual(judgements('Golden önce faul vardı demek ve hakemi eleştirmek mümkün değil.'),[])
        self.assertEqual(judgements("Orkun'un kazanılan penaltıyı vermesi büyük bir liderlik gösterisiydi doğrusu."),[])

    def test_minute_left_on_previous_sentence_is_recovered(self):
        rows=[{'id':1,'url':'u','summary':'Sarı kart doğruydu.48.'},{'id':2,'url':'u','summary':'Dakika: Hakemin penaltı kararı doğruydu.'}]
        self.assertEqual(recovered_minutes(rows),{2:48})

    def test_ordinals_and_club_abbreviations_do_not_split_sentences(self):
        parts=SENTENCE_SPLIT.split('Sarı kart doğruydu.48. Dakika: Penaltı doğruydu. F.Bahçe çok iyi oynadı.')
        self.assertEqual(parts,['Sarı kart doğruydu.','48. Dakika: Penaltı doğruydu.','F.Bahçe çok iyi oynadı.'])

    def test_verdicts_without_a_match_are_not_published(self):
        rows=[{'id':1,'url':'u','commentator':'deniz-coban','summary':'Fenerbahçe lehine verilen penaltı doğruydu.','match_id':None}]
        self.assertEqual(build_incidents(rows,{'hide_statement_ids':[],'verdicts':{}}),[])
        rows[0]['match_id']='m1'
        built=build_incidents(rows,{'hide_statement_ids':[],'verdicts':{}})
        self.assertEqual(built[0]['opinions'][0]['verdict'],'PENALTI')
        self.assertTrue(built[0]['opinions'][0]['expert'])

if __name__=='__main__':unittest.main()
