"""Build the live app feed from verified public-source material.

Only actual/direct commentator words enter the live feed. Current fixture overrides are
merged on top of the automated TFF cache so the app never shows a known-wrong current score.
"""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
seed=json.loads((ROOT/'data/seed.json').read_text())
candidates=json.loads((B/'candidates.json').read_text()) if (B/'candidates.json').exists() else []

PARAPHRASE_MARKERS=('düşünüyor','değerlendiriyor','savunuyor','belirtiyor','söylüyor','ifade ediyor','eleştirdi','övdü','değerlendirdi','açıkladı','yorumladı','iddia etti','vurguladı','yönündeki iddia','olarak görüyor','olarak değerlendiriyor')
CANON={
 'galatasaray a.ş.':'Galatasaray','galatasaray':'Galatasaray','fenerbahçe a.ş.':'Fenerbahçe','fenerbahçe':'Fenerbahçe',
 'beşiktaş a.ş.':'Beşiktaş','beşiktaş':'Beşiktaş','trabzonspor a.ş.':'Trabzonspor','trabzonspor':'Trabzonspor',
 'samsunspor a.ş.':'Samsunspor','samsunspor':'Samsunspor','göztepe a.ş.':'Göztepe','göztepe':'Göztepe',
 'tümosan konyaspor':'Konyaspor','konyaspor':'Konyaspor','çaykur rizespor a.ş.':'Rizespor','çaykur rizespor':'Rizespor','ç. rizespor':'Rizespor','rizespor':'Rizespor',
 'kocaelispor':'Kocaelispor','gençlerbirliği':'Gençlerbirliği','arca çorum fk':'Çorum FK','çorum fk':'Çorum FK','çorum':'Çorum FK',
 'eyüpspor':'Eyüpspor','gaziantep futbol kulübü a.ş.':'Gaziantep FK','gaziantep futbol kulübü':'Gaziantep FK','gaziantep fk':'Gaziantep FK','gaziantep':'Gaziantep FK',
 'corendon alanyaspor':'Alanyaspor','alanyaspor':'Alanyaspor','istanbul başakşehir fk':'Başakşehir','istanbul başakşehir':'Başakşehir','başakşehir':'Başakşehir',
 'kasımpaşa a.ş.':'Kasımpaşa','kasımpaşa':'Kasımpaşa','amed sportif faaliyetler':'Amed SK','amed sk':'Amed SK','amed':'Amed SK','erzurumspor fk':'Erzurumspor','erzurumspor':'Erzurumspor'}

def canonical(v):
    raw=' '.join((v or '').split()).strip()
    return CANON.get(raw.casefold(),raw)

def clean_summary(value):
    value=' '.join((value or '').split()).strip(' “”-')
    if ':' in value:
        left,right=value.split(':',1)
        generic=('yorumladı','eleştirdi','övdü','değerlendirdi','açıkladı','konuştu','dedi')
        if any(x in left.casefold() for x in generic) and len(right.strip())>=20:value=right.strip(' “”-')
    value=re.sub(r"^['\"]?den\s+",'',value,flags=re.I)
    return value[:420]

def looks_paraphrased(value):
    low=clean_summary(value).casefold()
    return any(x in low for x in PARAPHRASE_MARKERS)

def fixture_key(m):return (int(m.get('week') or 0),canonical(m.get('home')),canonical(m.get('away')))

legacy=[]
for s in seed.get('statements',[]):
    summary=clean_summary(s.get('summary',''))
    if len(summary)>=20 and s.get('verbatim') is True:
        row=dict(s);row['summary']=summary;row['team']=canonical(row.get('team')) if row.get('team') else None;row['verbatim']=True;legacy.append(row)
seed['statements']=legacy

tff=[]
try:tff=json.loads((B/'tff_matches.json').read_text())
except Exception:pass
matches={}
for m in seed.get('matches',[]):
    row=dict(m);row['home']=canonical(row.get('home'));row['away']=canonical(row.get('away'));matches[fixture_key(row)]=row
for m in tff:
    row=dict(m);row['home']=canonical(row.get('home'));row['away']=canonical(row.get('away'));key=fixture_key(row)
    base=dict(matches.get(key,{}));base.update({k:v for k,v in row.items() if v not in ('',None)});base.setdefault('home_score',None);base.setdefault('away_score',None);matches[key]=base

overrides=[]
try:overrides=json.loads((B/'fixture_overrides.json').read_text())
except Exception:pass
for m in overrides:
    row=dict(m);row['home']=canonical(row.get('home'));row['away']=canonical(row.get('away'));key=fixture_key(row)
    base=dict(matches.get(key,{}));base.update(row);base.setdefault('image_url',None);matches[key]=base
seed['matches']=sorted(matches.values(),key=lambda x:(int(x.get('week') or 0),x.get('kickoff',''),x.get('home','')))

logos={}
try:logos=json.loads((B/'team_logos.json').read_text())
except Exception:pass
for m in seed.get('matches',[]):
    m['home_logo_url']=logos.get(m.get('home'))
    m['away_logo_url']=logos.get(m.get('away'))

photo_by_commentator={}
try:
    pdata=json.loads((B/'commentator_photos.json').read_text()).get('photos',{})
    for cid,row in pdata.items():
        if row.get('verified_identity') and row.get('photoURL'):photo_by_commentator[cid]=row['photoURL']
except Exception:pass

roster_path=B/'commentator_roster.json'
if roster_path.exists():
    roster=json.loads(roster_path.read_text());existing={c['id']:c for c in seed.get('commentators',[])}
    def initials(name):
        parts=[x for x in name.replace('-',' ').split() if x];return ''.join(x[0].upper() for x in parts[:3]) or '?'
    merged=[]
    for cid,name,groups in roster:
        if cid in existing:row=dict(existing[cid])
        else:
            clubs=[g for g in groups if g!='Genel']
            if len(clubs)==1:role=f'{clubs[0]} muhabiri / yorumcu';source=f'{clubs[0]} kaynak taraması'
            elif len(clubs)>1:role='Futbol yorumcusu / muhabir';source='Çoklu kulüp kaynak taraması'
            else:role='Futbol yorumcusu / muhabir';source='Genel futbol kaynak taraması'
            row={'id':cid,'name':name,'role':role,'primarySource':source,'avatar':initials(name)}
        row['focusTeams']=groups;row['photoURL']=photo_by_commentator.get(cid);merged.append(row)
    seed['commentators']=merged

known={(s['commentator'],clean_summary(s['summary']).casefold()) for s in seed.get('statements',[]) if s.get('commentator')}
next_id=max((int(s.get('id',0)) for s in seed.get('statements',[])),default=0)+1;review=[]

manual=[]
try:manual=json.loads((B/'manual_verified.json').read_text())
except Exception:pass
for row in manual:
    summary=clean_summary(row.get('summary',''));key=(row.get('commentator'),summary.casefold())
    if not row.get('commentator') or len(summary)<20 or key in known:continue
    seed['statements'].append({'id':next_id,'commentator':row['commentator'],'date':row.get('date',''),'team':canonical(row.get('team')) if row.get('team') else None,'players':row.get('players',[]),'topic':row.get('topic','Genel yorum'),'type':row.get('type','opinion'),'sentiment':row.get('sentiment','neutral'),'strength':row.get('strength',7),'summary':summary,'source':row.get('source','Doğrulanmış kaynak'),'url':row.get('url',''),'image_url':row.get('image_url'),'confidence':row.get('confidence',100),'status':'verified_manual','verbatim':True,'match_id':row.get('match_id')})
    known.add(key);next_id+=1

for c in candidates:
    if c.get('confidence',0)<95 or not c.get('direct_quote'):
        review.append(c);continue
    summary=clean_summary(c.get('summary_candidate',''))
    if len(summary)<20 or looks_paraphrased(summary):review.append(c);continue
    key=(c.get('commentator'),summary.casefold())
    if not c.get('commentator') or key in known:continue
    seed['statements'].append({'id':next_id,'commentator':c['commentator'],'date':c.get('published_at') or c.get('discovered_at','')[:10],'team':canonical(c.get('team')) if c.get('team') else None,'players':c.get('players',[]),'topic':c.get('topic','Genel yorum'),'type':c.get('type','opinion'),'sentiment':c.get('sentiment','neutral'),'strength':c.get('strength',6),'summary':summary,'source':c.get('source','Kamuya açık kaynak'),'url':c.get('url',''),'image_url':c.get('image_url'),'confidence':c.get('confidence',95),'status':'verified_direct_quote','verbatim':True,'match_id':c.get('match_id')})
    known.add(key);next_id+=1

counts={}
for s in seed.get('statements',[]):counts[s['commentator']]=counts.get(s['commentator'],0)+1
seed['commentators']=sorted(seed.get('commentators',[]),key=lambda c:(-counts.get(c['id'],0),c['name']))
seed['generated_at']=datetime.now(timezone.utc).isoformat()
(B/'feed.json').write_text(json.dumps(seed,ensure_ascii=False,indent=2))
(B/'review_queue.json').write_text(json.dumps(review,ensure_ascii=False,indent=2))
print('feed',len(seed.get('commentators',[])),'commentators',len(seed.get('statements',[])),'statements',len(seed.get('matches',[])),'matches','review',len(review))
