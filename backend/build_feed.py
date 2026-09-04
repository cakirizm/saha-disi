"""Build the live app feed from curated seed + verified public candidates."""
import json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'backend'
seed = json.loads((ROOT / 'data/seed.json').read_text())
candidates = json.loads((B / 'candidates.json').read_text()) if (B / 'candidates.json').exists() else []

# Prefer actual spoken/written wording over editorial labels when a source card used
# "X yorumladı: ..." / "X eleştirdi: ...".
def clean_summary(value: str) -> str:
    value = ' '.join(value.split()).strip()
    if ':' in value:
        left, right = value.split(':', 1)
        generic = ('yorumladı','eleştirdi','övdü','değerlendirdi','açıkladı','konuştu','dedi')
        if any(x in left.casefold() for x in generic) and len(right.strip()) >= 20:
            return right.strip()[:320]
    return value[:320]

for s in seed.get('statements', []):
    s['summary'] = clean_summary(s.get('summary',''))

# Merge official TFF weekly fixture. Existing curated match IDs/dates win so old
# statement links do not break; TFF scores fill missing fields.
tff_path = B / 'tff_matches.json'
if tff_path.exists():
    tff = json.loads(tff_path.read_text())
    old = seed.get('matches', [])
    def norm(v):
        v=v.casefold().replace('a.ş.','').replace('fk','').strip()
        aliases={'arca çorum':'çorum','çorum':'çorum','gaziantep futbol kulübü':'gaziantep','gaziantep':'gaziantep','tümosan konyaspor':'konyaspor','çaykur rizespor':'rizespor','istanbul başakşehir':'başakşehir','amed sportif faaliyetler':'amed'}
        return aliases.get(v,v)
    old_map={(m.get('week'),norm(m.get('home','')),norm(m.get('away',''))):m for m in old}
    merged=[]
    for tm in tff:
        key=(tm.get('week'),norm(tm.get('home','')),norm(tm.get('away','')))
        if key in old_map:
            m=dict(old_map[key])
            if tm.get('home_score') is not None: m['home_score']=tm['home_score']
            if tm.get('away_score') is not None: m['away_score']=tm['away_score']
            m['league']=tm.get('league',m.get('league','Trendyol Süper Lig'))
            m.setdefault('image_url',tm.get('image_url'))
            merged.append(m)
        else:
            merged.append(tm)
    seed['matches']=merged

# Most recent usable editorial image per commentator. Images stay remote and retain
# the source URL; initials remain the fallback in the app.
photo_by_commentator={}
for c in sorted(candidates,key=lambda x:x.get('discovered_at',''),reverse=True):
    img=c.get('image_url')
    if img and str(img).startswith(('http://','https://')) and c.get('commentator') not in photo_by_commentator:
        photo_by_commentator[c['commentator']]=img

roster_path = B / 'commentator_roster.json'
if roster_path.exists():
    roster = json.loads(roster_path.read_text())
    existing = {c['id']: c for c in seed.get('commentators', [])}
    def initials(name: str) -> str:
        parts=[x for x in name.replace('-',' ').split() if x]
        return ''.join(x[0].upper() for x in parts[:3]) or '?'
    merged=[]
    for cid,name,groups in roster:
        if cid in existing: row=dict(existing[cid])
        else:
            club_groups=[g for g in groups if g!='Genel']
            if len(club_groups)==1:
                role=f"{club_groups[0]} muhabiri / yorumcu"; source=f"{club_groups[0]} kaynak taraması"
            elif len(club_groups)>1:
                role='Futbol yorumcusu / muhabir'; source='Çoklu kulüp kaynak taraması'
            else:
                role='Futbol yorumcusu / muhabir'; source='Genel futbol kaynak taraması'
            row={'id':cid,'name':name,'role':role,'primarySource':source,'avatar':initials(name)}
        row['focusTeams']=groups
        if cid in photo_by_commentator: row['photoURL']=photo_by_commentator[cid]
        else: row.setdefault('photoURL',None)
        merged.append(row)
    seed['commentators']=merged

PAUSED_COMMENTATORS={'onder-ozen'}
known={(s['commentator'],clean_summary(s['summary'])) for s in seed.get('statements',[])}
next_id=max((s['id'] for s in seed.get('statements',[])),default=0)+1
review=[]

for c in candidates:
    if c['commentator'] in PAUSED_COMMENTATORS: continue
    if c['confidence'] < 95:
        review.append(c); continue
    summary=clean_summary(c['summary_candidate'])
    if len(summary)<20: continue
    key=(c['commentator'],summary)
    if key in known: continue
    seed['statements'].append({
        'id':next_id,'commentator':c['commentator'],'date':c['discovered_at'][:10],
        'team':c.get('team'),'players':c.get('players',[]),'topic':c.get('topic','Genel yorum'),
        'type':c.get('type','opinion'),'sentiment':c.get('sentiment','neutral'),'strength':c.get('strength',6),
        'summary':summary,'source':c.get('source','Kamuya açık kaynak'),'url':c.get('url',''),
        'confidence':c['confidence'],'status':'auto_candidate'
    })
    known.add(key); next_id+=1

seed['generated_at']=datetime.now(timezone.utc).isoformat()
(B/'feed.json').write_text(json.dumps(seed,ensure_ascii=False,indent=2))
(B/'review_queue.json').write_text(json.dumps(review,ensure_ascii=False,indent=2))
print('feed',len(seed.get('commentators',[])),'commentators',len(seed.get('statements',[])),'statements',len(seed.get('matches',[])),'matches','review',len(review))
