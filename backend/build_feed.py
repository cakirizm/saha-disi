"""Build the live app feed from verified public-source material.

Policy: the app should display the commentator's actual words, not editorial paraphrases.
Only manual verbatim rows and automatically extracted direct quotes enter the live feed.
"""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
seed=json.loads((ROOT/'data/seed.json').read_text())
candidates=json.loads((B/'candidates.json').read_text()) if (B/'candidates.json').exists() else []

PARAPHRASE_MARKERS=(
    'düşünüyor','değerlendiriyor','savunuyor','belirtiyor','söylüyor','ifade ediyor',
    'eleştirdi','övdü','değerlendirdi','açıkladı','yorumladı','iddia etti','vurguladı',
    'yönündeki iddia','olarak görüyor','olarak değerlendiriyor'
)

def clean_summary(value):
    value=' '.join((value or '').split()).strip(' “”-')
    if ':' in value:
        left,right=value.split(':',1)
        generic=('yorumladı','eleştirdi','övdü','değerlendirdi','açıkladı','konuştu','dedi')
        if any(x in left.casefold() for x in generic) and len(right.strip())>=20:
            value=right.strip(' “”-')
    return value[:360]

def looks_paraphrased(value):
    low=clean_summary(value).casefold()
    return any(x in low for x in PARAPHRASE_MARKERS)

def norm(v):
    v=(v or '').casefold().replace('a.ş.','').replace('fk','').strip()
    aliases={'arca çorum':'çorum','çorum':'çorum','gaziantep futbol kulübü':'gaziantep','gaziantep':'gaziantep','tümosan konyaspor':'konyaspor','çaykur rizespor':'rizespor','istanbul başakşehir':'başakşehir','amed sportif faaliyetler':'amed','amed sk':'amed'}
    return aliases.get(v,v)

# Legacy seed summaries were editorial paraphrases. Do not show them as quotations.
# Only rows explicitly marked verbatim survive; verified manual/direct-quote rows are appended below.
legacy=[]
for s in seed.get('statements',[]):
    summary=clean_summary(s.get('summary',''))
    if len(summary)>=20 and s.get('verbatim') is True:
        row=dict(s); row['summary']=summary; row['verbatim']=True; legacy.append(row)
seed['statements']=legacy

# Official TFF fixture: use the full weekly schedule when available.
tff_path=B/'tff_matches.json'
if tff_path.exists():
    try:tff=json.loads(tff_path.read_text())
    except Exception:tff=[]
    old=seed.get('matches',[])
    old_map={(m.get('week'),norm(m.get('home')),norm(m.get('away'))):m for m in old}
    merged=[]
    for tm in tff:
        key=(tm.get('week'),norm(tm.get('home')),norm(tm.get('away')))
        if key in old_map:
            m=dict(old_map[key])
            for k in ('home_score','away_score','kickoff','league','image_url'):
                if tm.get(k) not in (None,''):m[k]=tm[k]
            merged.append(m)
        else: merged.append(tm)
    if merged: seed['matches']=merged

# Club crests: resolved from exact club pages only.
logos={}
logo_path=B/'team_logos.json'
if logo_path.exists():
    try:logos=json.loads(logo_path.read_text())
    except Exception:logos={}
for m in seed.get('matches',[]):
    m['home_logo_url']=logos.get(m.get('home')) or logos.get('Çorum' if norm(m.get('home'))=='çorum' else m.get('home'))
    m['away_logo_url']=logos.get(m.get('away')) or logos.get('Çorum' if norm(m.get('away'))=='çorum' else m.get('away'))

# Portraits: only identity-validated resolver output. Never use arbitrary article images as avatars.
photo_by_commentator={}
photo_path=B/'commentator_photos.json'
if photo_path.exists():
    try:
        pdata=json.loads(photo_path.read_text()).get('photos',{})
        for cid,row in pdata.items():
            if row.get('verified_identity') and row.get('photoURL'):
                photo_by_commentator[cid]=row['photoURL']
    except Exception: pass

roster_path=B/'commentator_roster.json'
if roster_path.exists():
    roster=json.loads(roster_path.read_text()); existing={c['id']:c for c in seed.get('commentators',[])}
    def initials(name):
        parts=[x for x in name.replace('-',' ').split() if x]; return ''.join(x[0].upper() for x in parts[:3]) or '?'
    merged=[]
    for cid,name,groups in roster:
        if cid in existing: row=dict(existing[cid])
        else:
            clubs=[g for g in groups if g!='Genel']
            if len(clubs)==1: role=f'{clubs[0]} muhabiri / yorumcu'; source=f'{clubs[0]} kaynak taraması'
            elif len(clubs)>1: role='Futbol yorumcusu / muhabir'; source='Çoklu kulüp kaynak taraması'
            else: role='Futbol yorumcusu / muhabir'; source='Genel futbol kaynak taraması'
            row={'id':cid,'name':name,'role':role,'primarySource':source,'avatar':initials(name)}
        row['focusTeams']=groups
        row['photoURL']=photo_by_commentator.get(cid)
        merged.append(row)
    seed['commentators']=merged

known={(s['commentator'],clean_summary(s['summary']).casefold()) for s in seed.get('statements',[]) if s.get('commentator')}
next_id=max((int(s.get('id',0)) for s in seed.get('statements',[])),default=0)+1
review=[]

manual_path=B/'manual_verified.json'
if manual_path.exists():
    try: manual=json.loads(manual_path.read_text())
    except Exception: manual=[]
    for row in manual:
        summary=clean_summary(row.get('summary','')); key=(row.get('commentator'),summary.casefold())
        if not row.get('commentator') or len(summary)<20 or key in known: continue
        seed['statements'].append({
            'id':next_id,'commentator':row['commentator'],'date':row.get('date',''),'team':row.get('team'),
            'players':row.get('players',[]),'topic':row.get('topic','Genel yorum'),'type':row.get('type','opinion'),
            'sentiment':row.get('sentiment','neutral'),'strength':row.get('strength',7),'summary':summary,
            'source':row.get('source','Doğrulanmış kaynak'),'url':row.get('url',''),'image_url':row.get('image_url'),
            'confidence':row.get('confidence',100),'status':'verified_manual','verbatim':True,
            'match_id':row.get('match_id')
        })
        known.add(key); next_id+=1

for c in candidates:
    # Automatic feed admission requires an actual quote extracted from the source text.
    if c.get('confidence',0)<95 or not c.get('direct_quote'):
        review.append(c); continue
    summary=clean_summary(c.get('summary_candidate',''))
    if len(summary)<20 or looks_paraphrased(summary):
        review.append(c); continue
    key=(c.get('commentator'),summary.casefold())
    if not c.get('commentator') or key in known: continue
    seed['statements'].append({
        'id':next_id,'commentator':c['commentator'],'date':c.get('discovered_at','')[:10],
        'team':c.get('team'),'players':c.get('players',[]),'topic':c.get('topic','Genel yorum'),
        'type':c.get('type','opinion'),'sentiment':c.get('sentiment','neutral'),'strength':c.get('strength',6),
        'summary':summary,'source':c.get('source','Kamuya açık kaynak'),'url':c.get('url',''),
        'image_url':c.get('image_url'),'confidence':c.get('confidence',95),'status':'verified_direct_quote',
        'verbatim':True,'match_id':c.get('match_id')
    })
    known.add(key); next_id+=1

counts={}
for s in seed.get('statements',[]): counts[s['commentator']]=counts.get(s['commentator'],0)+1
seed['commentators']=sorted(seed.get('commentators',[]),key=lambda c:(-counts.get(c['id'],0),c['name']))
seed['generated_at']=datetime.now(timezone.utc).isoformat()
(B/'feed.json').write_text(json.dumps(seed,ensure_ascii=False,indent=2))
(B/'review_queue.json').write_text(json.dumps(review,ensure_ascii=False,indent=2))
print('feed',len(seed.get('commentators',[])),'commentators',len(seed.get('statements',[])),'statements',len(seed.get('matches',[])),'matches','review',len(review))
