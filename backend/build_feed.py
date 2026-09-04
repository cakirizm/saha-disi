"""Build the live app feed from curated seed + verified public candidates."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
seed=json.loads((ROOT/'data/seed.json').read_text())
candidates=json.loads((B/'candidates.json').read_text()) if (B/'candidates.json').exists() else []

def clean_summary(value):
 value=' '.join((value or '').split()).strip()
 if ':' in value:
  left,right=value.split(':',1)
  generic=('yorumladı','eleştirdi','övdü','değerlendirdi','açıkladı','konuştu','dedi')
  if any(x in left.casefold() for x in generic) and len(right.strip())>=20:return right.strip()[:320]
 return value[:320]

for s in seed.get('statements',[]):s['summary']=clean_summary(s.get('summary',''))

# Official TFF weekly fixture. Existing curated IDs win where the same fixture already existed.
tff_path=B/'tff_matches.json'
if tff_path.exists():
 try:tff=json.loads(tff_path.read_text())
 except Exception:tff=[]
 old=seed.get('matches',[])
 def norm(v):
  v=(v or '').casefold().replace('a.ş.','').replace('fk','').strip()
  aliases={'arca çorum':'çorum','gaziantep futbol kulübü':'gaziantep','tümosan konyaspor':'konyaspor','çaykur rizespor':'rizespor','istanbul başakşehir':'başakşehir','amed sportif faaliyetler':'amed'}
  return aliases.get(v,v)
 old_map={(m.get('week'),norm(m.get('home')),norm(m.get('away'))):m for m in old}
 merged=[]
 for tm in tff:
  key=(tm.get('week'),norm(tm.get('home')),norm(tm.get('away')))
  if key in old_map:
   m=dict(old_map[key])
   for k in ('home_score','away_score','kickoff','league','image_url'):
    if tm.get(k) not in (None,''):m[k]=tm[k]
   merged.append(m)
  else:merged.append(tm)
 if merged:seed['matches']=merged

# Portraits: first prefer verified public profile-image resolver, then recent editorial image.
photo_by_commentator={}
photo_path=B/'commentator_photos.json'
if photo_path.exists():
 try:
  pdata=json.loads(photo_path.read_text()).get('photos',{})
  for cid,row in pdata.items():
   if row.get('photoURL'):photo_by_commentator[cid]=row['photoURL']
 except Exception:pass
for c in sorted(candidates,key=lambda x:x.get('discovered_at',''),reverse=True):
 img=c.get('image_url');cid=c.get('commentator')
 if cid and img and str(img).startswith(('http://','https://')) and cid not in photo_by_commentator:photo_by_commentator[cid]=img

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
  row['focusTeams']=groups;row['photoURL']=photo_by_commentator.get(cid,row.get('photoURL'))
  merged.append(row)
 seed['commentators']=merged

PAUSED_COMMENTATORS={'onder-ozen'}
known={(s['commentator'],clean_summary(s['summary']).casefold()) for s in seed.get('statements',[])}
next_id=max((s['id'] for s in seed.get('statements',[])),default=0)+1;review=[]
for c in candidates:
 if c.get('commentator') in PAUSED_COMMENTATORS:continue
 if c.get('confidence',0)<95:review.append(c);continue
 summary=clean_summary(c.get('summary_candidate',''))
 if len(summary)<20:continue
 key=(c['commentator'],summary.casefold())
 if key in known:continue
 seed['statements'].append({'id':next_id,'commentator':c['commentator'],'date':c['discovered_at'][:10],'team':c.get('team'),'players':c.get('players',[]),'topic':c.get('topic','Genel yorum'),'type':c.get('type','opinion'),'sentiment':c.get('sentiment','neutral'),'strength':c.get('strength',6),'summary':summary,'source':c.get('source','Kamuya açık kaynak'),'url':c.get('url',''),'confidence':c.get('confidence',95),'status':'auto_candidate'})
 known.add(key);next_id+=1

# Always present commentators in activity order in the payload too. Zero-comment profiles naturally sink.
counts={}
for s in seed.get('statements',[]):counts[s['commentator']]=counts.get(s['commentator'],0)+1
seed['commentators']=sorted(seed.get('commentators',[]),key=lambda c:(-counts.get(c['id'],0),c['name']))
seed['generated_at']=datetime.now(timezone.utc).isoformat()
(B/'feed.json').write_text(json.dumps(seed,ensure_ascii=False,indent=2))
(B/'review_queue.json').write_text(json.dumps(review,ensure_ascii=False,indent=2))
print('feed',len(seed.get('commentators',[])),'commentators',len(seed.get('statements',[])),'statements',len(seed.get('matches',[])),'matches','review',len(review))
