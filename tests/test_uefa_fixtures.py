import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import uefa_fixtures as uf


def team(name,country,tid=1,**extra):
    return {'id':tid,'internationalName':name,'countryCode':country,**extra}


def match(mid,home,away,status='UPCOMING',total=None,comp='UEFA Champions League',**extra):
    row={'id':mid,'seasonYear':2027,'status':status,'homeTeam':home,'awayTeam':away,
         'kickOffTime':{'dateTime':'2026-11-25T20:00:00Z'},'competition':{'metaData':{'name':comp}},
         'round':{'metaData':{'name':'League phase'}},'matchday':{'name':'Matchday 5'}}
    if total:row['score']={'total':{'home':total[0],'away':total[1]}}
    row.update(extra);return row


class UefaFixtureTests(unittest.TestCase):
    def test_only_turkish_sides_are_kept(self):
        raw=[match(1,team('Galatasaray','TUR'),team('Liverpool','ENG')),
             match(2,team('Arsenal','ENG'),team('Benfica','POR'))]
        rows=uf.parse(raw,'ucl','UEFA Şampiyonlar Ligi')
        self.assertEqual([(r['home'],r['away']) for r in rows],[('Galatasaray','Liverpool')])
        self.assertEqual(rows[0]['round'],'Lig Aşaması · 5. Maç')
        self.assertEqual(rows[0]['kickoff'],'2026-11-25T20:00:00+00:00')
        self.assertIsNone(rows[0]['home_score'])

    def test_club_suffix_and_turkish_letters(self):
        raw=[match(3,team('Liverpool','ENG'),team('Fenerbahce SK','TUR'),status='FINISHED',total=(1,2))]
        row=uf.parse(raw,'uel','UEFA Avrupa Ligi')[0]
        self.assertEqual(row['away'],'Fenerbahçe')
        self.assertEqual((row['home_score'],row['away_score'],row['status']),(1,2,'finished'))

    def test_national_team_names_in_turkish(self):
        raw=[match(4,team('Türkiye','TUR'),team('Wales','WAL'),comp='UEFA Nations League',
                   group={'metaData':{'groupName':'League B, Group 4'}})]
        row=uf.parse(raw,'unl','UEFA Uluslar Ligi')[0]
        self.assertEqual((row['home'],row['away']),('Türkiye','Galler'))
        self.assertIn('B Ligi 4. Grup',row['round'])

    def test_wrong_competition_id_is_rejected(self):
        payload=[match(5,team('Galatasaray','TUR'),team('Ajax','NED'),comp='UEFA Youth League')]
        def fake(params):
            return payload if params['offset']==0 else []
        rows,report=uf.collect(2027,fetch=fake)
        self.assertEqual(rows,[])
        self.assertFalse(report['ucl']['ok'])

    def test_empty_id_falls_through_to_next_candidate(self):
        unl=[match(6,team('Türkiye','TUR'),team('Wales','WAL'),comp='UEFA Nations League')]
        def fake(params):
            if params['offset']:return []
            return unl if params['competitionId']==2014 else []
        rows,report=uf.collect(2027,fetch=fake)
        self.assertEqual(report['unl']['competition_id'],2014)
        self.assertEqual([(r['home'],r['away']) for r in rows],[('Türkiye','Galler')])

    def test_league_phase_group_label_is_dropped(self):
        raw=[match(7,team('Galatasaray','TUR'),team('Ajax','NED'),group={'metaData':{'groupName':'League'}})]
        self.assertEqual(uf.parse(raw,'ucl','UEFA Şampiyonlar Ligi')[0]['round'],'Lig Aşaması · 5. Maç')

    def test_season_year_rolls_over_in_july(self):
        from datetime import datetime,timezone
        self.assertEqual(uf.season_year(datetime(2026,11,16,tzinfo=timezone.utc)),2027)
        self.assertEqual(uf.season_year(datetime(2027,3,1,tzinfo=timezone.utc)),2027)


if __name__=='__main__':
    unittest.main()
