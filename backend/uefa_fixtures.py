"""Fetch Turkish clubs' European fixtures and the national team's Nations League
fixtures from UEFA's public match service.

No club list is hard-coded: every match with a Turkish side (country code TUR)
is kept, so a club that qualifies or is knocked out appears or drops by itself.
Like the TFF reader, a failed or implausible fetch never replaces the last good
cache.
"""
from __future__ import annotations
import json, re, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
OUT=B/'uefa_matches.json'; HEALTH=B/'uefa_health.json'
API='https://match.uefa.com/v5/matches'
UA='Mozilla/5.0 (compatible; SahaDisi/1.5; official-fixture-reader)'
PAGE=200

# code, Turkish label, candidate UEFA competition ids, word the returned
# competition name must contain (guards against a wrong id silently importing
# another tournament).
COMPETITIONS=[
 ('ucl','UEFA Şampiyonlar Ligi',(1,),'champions league'),
 ('uel','UEFA Avrupa Ligi',(14,),'europa league'),
 ('uecl','UEFA Konferans Ligi',(2019,),'conference league'),
 ('unl','UEFA Uluslar Ligi',(9,2014,2008),'nations league'),
]

TURKISH={
 'galatasaray':'Galatasaray','fenerbahce':'Fenerbahçe','besiktas':'Beşiktaş','trabzonspor':'Trabzonspor',
 'samsunspor':'Samsunspor','goztepe':'Göztepe','konyaspor':'Konyaspor','rizespor':'Rizespor','caykur rizespor':'Rizespor',
 'kocaelispor':'Kocaelispor','genclerbirligi':'Gençlerbirliği','corum':'Çorum FK','corum fk':'Çorum FK','eyupspor':'Eyüpspor',
 'gaziantep':'Gaziantep FK','gaziantep fk':'Gaziantep FK','alanyaspor':'Alanyaspor','basaksehir':'Başakşehir',
 'istanbul basaksehir':'Başakşehir','basaksehir fk':'Başakşehir','kasimpasa':'Kasımpaşa','amed':'Amed SK','amedspor':'Amed SK',
 'erzurumspor':'Erzurumspor','sivasspor':'Sivasspor','antalyaspor':'Antalyaspor','kayserispor':'Kayserispor',
 'turkiye':'Türkiye','turkey':'Türkiye',
}

# Opponents keep UEFA's international name; national teams read better in Turkish.
COUNTRIES_TR={
 'Albania':'Arnavutluk','Andorra':'Andorra','Armenia':'Ermenistan','Austria':'Avusturya','Azerbaijan':'Azerbaycan',
 'Belarus':'Belarus','Belgium':'Belçika','Bosnia and Herzegovina':'Bosna-Hersek','Bulgaria':'Bulgaristan','Croatia':'Hırvatistan',
 'Cyprus':'Kıbrıs Rum Kesimi','Czechia':'Çekya','Czech Republic':'Çekya','Denmark':'Danimarka','England':'İngiltere','Estonia':'Estonya',
 'Faroe Islands':'Faroe Adaları','Finland':'Finlandiya','France':'Fransa','Georgia':'Gürcistan','Germany':'Almanya','Gibraltar':'Cebelitarık',
 'Greece':'Yunanistan','Hungary':'Macaristan','Iceland':'İzlanda','Israel':'İsrail','Italy':'İtalya','Kazakhstan':'Kazakistan','Kosovo':'Kosova',
 'Latvia':'Letonya','Liechtenstein':'Lihtenştayn','Lithuania':'Litvanya','Luxembourg':'Lüksemburg','Malta':'Malta','Moldova':'Moldova',
 'Montenegro':'Karadağ','Netherlands':'Hollanda','North Macedonia':'Kuzey Makedonya','Northern Ireland':'Kuzey İrlanda','Norway':'Norveç',
 'Poland':'Polonya','Portugal':'Portekiz','Republic of Ireland':'İrlanda','Romania':'Romanya','Russia':'Rusya','San Marino':'San Marino',
 'Scotland':'İskoçya','Serbia':'Sırbistan','Slovakia':'Slovakya','Slovenia':'Slovenya','Spain':'İspanya','Sweden':'İsveç',
 'Switzerland':'İsviçre','Ukraine':'Ukrayna','Wales':'Galler',
}

ROUNDS=[
 ('final','Final'),('semi','Yarı Final'),('quarter','Çeyrek Final'),('round of 16','Son 16'),('last 16','Son 16'),
 ('knockout round play','Play-off Turu'),('play-off','Play-off'),('playoff','Play-off'),('league phase','Lig Aşaması'),
 ('league path','Lig Aşaması'),('group','Grup Aşaması'),('third qualifying','3. Ön Eleme'),('second qualifying','2. Ön Eleme'),
 ('first qualifying','1. Ön Eleme'),('qualifying','Ön Eleme'),('relegation','Küme Düşme Play-off'),('promotion','Play-off'),
]
STATUS={'FINISHED':'finished','LIVE':'live','POSTPONED':'postponed','CANCELLED':'cancelled','ABANDONED':'suspended','SUSPENDED':'suspended'}

def norm(s):
    s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().casefold()
    return re.sub(r'[^a-z0-9]+',' ',s).strip()

def slug(s):return norm(s).replace(' ','-')

def season_year(now=None):
    """UEFA names a season by the year it ends in: 2026-27 is 2027."""
    now=now or datetime.now(timezone.utc)
    return now.year+1 if now.month>=7 else now.year

def fetch_json(params):
    req=Request(f'{API}?{urlencode(params)}',headers={'User-Agent':UA,'Accept':'application/json'})
    with urlopen(req,timeout=30) as r:return json.loads(r.read().decode('utf-8'))

def fetch_competition(cid,year,fetch=fetch_json):
    rows=[];offset=0
    while True:
        page=fetch({'competitionId':cid,'seasonYear':year,'limit':PAGE,'offset':offset,'order':'ASC'})
        if not isinstance(page,list):raise ValueError(f'unexpected payload for competition {cid}')
        rows+=page
        if len(page)<PAGE or offset>4000:return rows
        offset+=PAGE

def dig(d,*path):
    for p in path:
        if not isinstance(d,dict):return None
        d=d.get(p)
    return d

def team_name(team):
    raw=(team.get('internationalName') or dig(team,'translations','displayName','EN') or '').strip()
    key=norm(raw)
    if key in TURKISH:return TURKISH[key]
    if team.get('countryCode')=='TUR':
        # "Fenerbahçe SK", "Beşiktaş JK": the club word decides once the side is Turkish.
        for word in key.split(' '):
            if word in TURKISH:return TURKISH[word]
    # No club carries a bare country name, so an exact match is a national team.
    return COUNTRIES_TR.get(raw) or dig(team,'translations','displayName','TR') or raw

def team_logo(team):
    url=team.get('mediumLogoUrl') or team.get('logoUrl') or team.get('bigLogoUrl')
    if not url and team.get('id'):url=f"https://img.uefa.com/imgml/TP/teams/logos/240x240/{team['id']}.png"
    return url

def round_label(m):
    name=(dig(m,'round','metaData','name') or dig(m,'round','translations','name','EN') or '')
    low=name.casefold()
    label=next((tr for key,tr in ROUNDS if key in low),name)
    group=dig(m,'group','metaData','groupName') or dig(m,'group','translations','name','EN')
    if group:
        g=re.sub(r'(?i)^league\s+([A-D])\s*,?\s*group\s*(\d+)$',r'\1 Ligi \2. Grup',group)
        g=re.sub(r'(?i)^group\s+(\w+)$',r'\1 Grubu',g)
        label=f'{label} · {g}' if label else g
    day=dig(m,'matchday','name') or dig(m,'matchday','longName')
    md=re.search(r'(\d+)',day or '')
    if md and 'Lig Aşaması' in label:label=f'{label} · {md.group(1)}. Maç'
    leg=m.get('leg') or {}
    if isinstance(leg,dict) and leg.get('number') in (1,2) and 'Lig Aşaması' not in label:
        label=f"{label} · {'İlk' if leg['number']==1 else 'Rövanş'} Maç"
    return label

def parse(raw,code,label):
    out=[]
    for m in raw:
        home,away=m.get('homeTeam') or {},m.get('awayTeam') or {}
        if 'TUR' not in (home.get('countryCode'),away.get('countryCode')):continue
        h,a=team_name(home),team_name(away)
        kickoff=dig(m,'kickOffTime','dateTime') or ''
        if not h or not a or h==a:continue
        total=dig(m,'score','total') or {}
        status=STATUS.get(str(m.get('status','')).upper())
        hs,as_=total.get('home'),total.get('away')
        if status not in ('finished','live'):hs=as_=None
        pen=dig(m,'score','penalty') or {}
        row={'id':f"{code}-{m.get('seasonYear') or ''}-{m.get('id') or slug(h+'-'+a+'-'+kickoff[:10])}",
             'competition':code,'league':label,'round':round_label(m),'home':h,'away':a,
             'kickoff':kickoff.replace('Z','+00:00'),'home_score':hs,'away_score':as_,
             'home_logo_url':team_logo(home),'away_logo_url':team_logo(away),'image_url':None,
             'source':'UEFA','source_url':f"https://www.uefa.com/match/{m.get('id')}/" if m.get('id') else 'https://www.uefa.com/'}
        if pen.get('home') is not None and pen.get('away') is not None:row['penalties']=f"{pen['home']}-{pen['away']}"
        venue=dig(m,'stadium','translations','officialName','EN') or dig(m,'stadium','translations','name','EN')
        if venue:row['venue']=venue
        if status:row['status']=status
        out.append(row)
    return out

def competition_name(raw):
    for m in raw[:5]:
        name=dig(m,'competition','metaData','name') or dig(m,'competition','translations','name','EN')
        if name:return name
    return ''

def healthy(rows):
    return all(r.get('home') and r.get('away') and re.match(r'\d{4}-\d{2}-\d{2}T',r.get('kickoff') or '') for r in rows)

def collect(year=None,fetch=fetch_json):
    year=year or season_year();rows=[];report={}
    for code,label,ids,must in COMPETITIONS:
        report[code]={'ok':False,'matches':0}
        for cid in ids:
            try:raw=fetch_competition(cid,year,fetch)
            except Exception as e:report[code]['error']=str(e)[:120];continue
            name=competition_name(raw)
            if raw and must not in name.casefold():
                report[code]['error']=f'id {cid} returned {name!r}';continue
            parsed=parse(raw,code,label)
            report[code]={'ok':True,'competition_id':cid,'season_year':year,'all_matches':len(raw),'matches':len(parsed)}
            rows+=parsed;break
    return rows,report

def main():
    old=[]
    if OUT.exists():
        try:old=json.loads(OUT.read_text(encoding='utf-8'))
        except Exception:pass
    rows,report=collect()
    ok=any(v['ok'] for v in report.values()) and healthy(rows)
    if ok:
        # A competition that failed this run keeps its previous rows instead of vanishing.
        failed={code for code,v in report.items() if not v['ok']}
        rows+=[r for r in old if r.get('competition') in failed]
    else:rows=old
    rows=sorted({r['id']:r for r in rows}.values(),key=lambda r:(r.get('kickoff',''),r['id']))
    HEALTH.write_text(json.dumps({'checked_at':datetime.now(timezone.utc).isoformat(),'source':'UEFA','ok':ok,'using_cache':not ok,'competitions':report},ensure_ascii=False,indent=2),encoding='utf-8')
    OUT.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print('uefa matches',len(rows),'ok',ok,json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
