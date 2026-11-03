import plistlib
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
from youtube_partner import title_speaker, attributed_turn

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
        for method in ('article_explicit_speaker','official_api_author_match','columnist_byline','partner_video_title_speaker'):
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

class PartnerVideoSpeakerTests(unittest.TestCase):
    def test_title_names_a_known_commentator(self):
        cid,quote=title_speaker("Nihat Kahveci: 31 Ekim'de Fenerbahçe, havlu attı!")
        self.assertEqual(cid,'nihat-kahveci')
        self.assertTrue(quote.startswith("31 Ekim"))
        self.assertEqual(title_speaker('Nebil Evren: Mourinho gibi...')[0],None)
        self.assertEqual(title_speaker('Derbi sonrası canlı yayın')[0],None)

    def test_only_the_turn_holding_the_title_quote_is_attributed(self):
        snippets=[(0.0,'Sunucu: hoş geldiniz bugün derbiyi konuşacağız.'),(4.0,">> 31 Ekim'de Fenerbahçe havlu attı, bornoz attı."),
                  (9.0,'Şampiyonluk yarışından koptu.'),(14.0,'>> Peki hocam Galatasaray?')]
        turn=attributed_turn(snippets,"31 Ekim'de Fenerbahçe, havlu attı!")
        self.assertEqual([t for t,_ in turn],[4.0,9.0])
        self.assertNotIn('Galatasaray',' '.join(x for _,x in turn))

    def test_single_name_after_pipe_needs_a_single_voice(self):
        vole=['serdar-ali-celikler','ali-ece','metin-tekin']
        self.assertEqual(title_speaker('Kartal dönemini hangi şarkı anlatıyor? | Ali Ece',vole),('ali-ece',None))
        self.assertEqual(title_speaker('Vinicius fayda mı? | Erman Yaşar & Emre Özcan | Atıf Bey Sokak',vole),(None,None))
        # A show talking about someone names them last too; only the channel's own voices count.
        self.assertEqual(title_speaker("İbre Yerli Hocaya Mı Döndü? | Galatasaray'da Neler Oluyor? | Sergen Yalçın",['ibrahim-seten']),(None,None))
        alone=[(0.0,'Fenerbahçe bu sezon çok zorlanacak.'),(3.0,'Kadro dengesi yok.')]
        self.assertEqual(len(attributed_turn(alone,None)),2)
        self.assertIsNone(attributed_turn(alone+[(6.0,'>> Katılıyorum hocam.')],None))

    def test_block_keeps_progress_and_rests(self):
        import tempfile, json as _json, youtube_partner as yp
        from datetime import datetime, timezone
        now=datetime.now(timezone.utc).isoformat()
        videos=[{'id':'aaaaaaaaaaa','title':"Nihat Kahveci: Fenerbahçe bu sezon çok zorlanacak dostlar",'published_at':now},
                {'id':'bbbbbbbbbbb','title':"Nihat Kahveci: Beşiktaş derbide çok iyi oynadı arkadaşlar",'published_at':now}]
        caps=[([(0.0,'Fenerbahçe bu sezon çok zorlanacak dostlar, Fenerbahçe savunmada büyük hatalar yapıyor ve ligde puan kaybediyor.')],'auto')]
        def fake_captions(api,vid):
            if caps: return caps.pop()
            raise yp.Blocked('ip blocked')
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'y.json'
            with patch.object(yp,'OUT',out),patch.object(yp,'CONFIG',[{'id':'k','name':'Kontraspor','url':'u','partner':True}]),                 patch.object(yp,'channel_videos',return_value=(videos,None)),patch.object(yp,'captions',side_effect=fake_captions),                 patch.object(yp,'PAUSE',0),patch('youtube_transcript_api.YouTubeTranscriptApi'):
                yp.run()
                saved=_json.loads(out.read_text(encoding='utf-8'))
                self.assertIn('aaaaaaaaaaa',saved['seen_videos'])
                self.assertNotIn('bbbbbbbbbbb',saved['seen_videos'])
                self.assertTrue(saved['candidates'])
                self.assertTrue(saved['blocked_until'])
                with patch.object(yp,'channel_videos') as listing:
                    yp.run()
                    listing.assert_not_called()

    def test_transcript_api_keeps_only_turkish_original_captions(self):
        import youtube_partner as yp
        tr={'language':'tr','translated':False,'autoGenerated':True,'segments':[{'start':1.5,'text':'Fenerbahçe havlu attı.'}]}
        with patch.object(yp,'transcript_api',return_value=tr):
            self.assertEqual(yp.api_captions('x'),([(1.5,'Fenerbahçe havlu attı.')],'auto'))
        with patch.object(yp,'transcript_api',return_value=dict(tr,translated=True)):
            self.assertEqual(yp.api_captions('x'),(None,None))
        with patch.object(yp,'transcript_api',return_value=None):
            self.assertEqual(yp.api_captions('x'),(None,None))

    def test_transcript_api_out_of_credits_stops_the_run(self):
        import youtube_partner as yp
        from urllib.error import HTTPError
        def refuse(*a,**k): raise HTTPError('u',402,'Payment Required',{},None)
        with patch.object(yp,'urlopen',side_effect=refuse),patch.object(yp,'MIN_INTERVAL',0):
            with self.assertRaises(yp.Blocked) as ctx:
                yp.transcript_api('transcript',url='x')
        self.assertIsNotNone(ctx.exception.rest)

    def test_quote_missing_from_captions_attributes_nothing(self):
        self.assertIsNone(attributed_turn([(0.0,'Bugün hava çok güzel.')],"31 Ekim'de Fenerbahçe, havlu attı!"))

class AppResponsivenessTests(unittest.TestCase):
    def test_screens_read_the_prebuilt_index(self):
        # View bodies re-run constantly while scrolling. Scanning every statement
        # there froze the home carousel until iOS killed the app.
        app=Path(__file__).resolve().parents[1]/'ios/SahaDisi/SahaDisi'
        store=(app/'Services/AppStore.swift').read_text(encoding='utf-8')
        self.assertNotIn('payload?.statements ?? []',store)
        self.assertIn('func statements(matchID: String) -> [Statement] { index.byMatch',store)
        self.assertIn('private var featuredMatches: [Match] { store.featuredMatches }',(app/'Views/HomeView.swift').read_text(encoding='utf-8'))

class BrokenTextGateTests(unittest.TestCase):
    def test_garbled_row_is_held_back_instead_of_failing_the_feed(self):
        row={'url':'https://example.com/yazarlar/a/b','date':'2026-09-05','commentator':'x','status':'verified_manual','summary':'BeÅŸiktaÅŸ dÃ¼n gece iyi oynadÄ±.'}
        self.assertEqual(publication_problem(row),'broken_text')
        clean=dict(row,summary='Beşiktaş dün gece çok iyi oynadı.')
        self.assertIsNone(publication_problem(clean))
        self.assertEqual(publication_problem(dict(clean,evidence={'title':'Bo�uk ba�l�k'})),'broken_text')

class PrivacyDisclosureTests(unittest.TestCase):
    ROOT=Path(__file__).resolve().parents[1]
    def test_manifest_declares_user_defaults_and_no_tracking(self):
        manifest=plistlib.loads((self.ROOT/'ios/SahaDisi/SahaDisi/PrivacyInfo.xcprivacy').read_bytes())
        self.assertFalse(manifest['NSPrivacyTracking'])
        self.assertEqual(manifest['NSPrivacyCollectedDataTypes'],[])
        declared={x['NSPrivacyAccessedAPIType']:x['NSPrivacyAccessedAPITypeReasons'] for x in manifest['NSPrivacyAccessedAPITypes']}
        self.assertEqual(declared,{'NSPrivacyAccessedAPICategoryUserDefaults':['CA92.1']})
    def test_app_links_to_published_legal_documents(self):
        root=(self.ROOT/'ios/SahaDisi/SahaDisi/Views/RootView.swift').read_text(encoding='utf-8')
        for name in ('gizlilik.md','kosullar.md'):
            self.assertIn('blob/main/docs/'+name,root)
            self.assertTrue((self.ROOT/'docs'/name).exists())

if __name__=='__main__':unittest.main()
