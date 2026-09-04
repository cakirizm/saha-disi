"""Resolve real club crests from Wikimedia page images.
No favicons and no guessed domains: each club has an explicit canonical search title and the
resolved page title must match an allowed club token before its thumbnail is accepted.
"""
from __future__ import annotations
import json, re, unicodedata, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'; OUT=B/'team_logos.json'
UA='SahaDisi/2.0 verified-club-crest-resolver'
SEARCH={
 'Galatasaray':'Galatasaray SK','Fenerbahçe':'Fenerbahçe SK','Beşiktaş':'Beşiktaş JK','Trabzonspor':'Trabzonspor',
 'Samsunspor':'Samsunspor','Göztepe':'Göztepe SK','Konyaspor':'Konyaspor','Rizespor':'Çaykur Rizespor',
 'Kocaelispor':'Kocaelispor','Gençlerbirliği':'Gençlerbirliği SK','Çorum FK':'Çorum FK','Eyüpspor':'Eyüpspor',
 'Gaziantep FK':'Gaziantep FK','Alanyaspor':'Alanyaspor','Başakşehir':'İstanbul Başakşehir FK','Kasımpaşa':'Kasımpaşa SK',
 'Amed SK':'Amed SK','Erzurumspor':'Erzurumspor FK'
}
ALIASES={
 'İstanbul Başakşehir':'Başakşehir','İstanbul Başakşehir FK':'Başakşehir','Tümosan Konyaspor':'Konyaspor',
 'Çaykur Rizespor':'Rizespor','Çaykur Rizespor A.Ş.':'Rizespor','Arca Çorum FK':'Çorum FK','Çorum':'Çorum FK',
 'Gaziantep':'Gaziantep FK','Gaziantep Futbol Kulübü':'Gaziantep FK','Gaziantep Futbol Kulübü A.Ş.':'Gaziantep FK',
 'Amed Sportif Faaliyetler':'Amed SK','Erzurumspor FK':'Erzurumspor','Corendon Alanyaspor':'Alanyaspor',
 'Galatasaray A.Ş.':'Galatasaray','Fenerbahçe A.Ş.':'Fenerbahçe','Beşiktaş A.Ş.':'Beşiktaş','Trabzonspor A.Ş.':'Trabzonspor',
 'Samsunspor A.Ş.':'Samsunspor','Göztepe A.Ş.':'Göztepe','Kasımpaşa A.Ş.':'Kasımpaşa'
}

def norm(s):
 s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().casefold()
 return re.sub(r'[^a-z0-9]+',' ',s).strip()

def get_json(url):
 req=Request(url,headers={'User-Agent':UA,'Accept-Language':'tr-TR,tr;q=0.9'})
 with urlopen(req,timeout=18) as r:return json.loads(r.read().decode('utf-8'))

def title_ok(team,title):
 t=norm(title); q=norm(SEARCH[team]); team_n=norm(team)
 important=[x for x in team_n.split() if len(x)>=4 and x not in {'spor'}]
 return all(x in t for x in important[:1]) or all(x in t for x in q.split() if len(x)>=5) 

def resolve(team):
 q=urllib.parse.urlencode({'action':'query','generator':'search','gsrsearch':SEARCH[team],'gsrnamespace':0,'gsrlimit':6,'prop':'pageimages|info','piprop':'thumbnail|original','pithumbsize':512,'inprop':'url','format':'json','origin':'*'})
 data=get_json('https://tr.wikipedia.org/w/api.php?'+q)
 pages=list(data.get('query',{}).get('pages',{}).values())
 pages.sort(key=lambda p:int(p.get('index',999)))
 for p in pages:
  if not title_ok(team,p.get('title','')):continue
  image=(p.get('thumbnail') or {}).get('source') or (p.get('original') or {}).get('source')
  if image and image.startswith('https://upload.wikimedia.org/'):
   return image
 return None

def main():
 out={};missing=[]
 for team in SEARCH:
  try: image=resolve(team)
  except Exception: image=None
  if image:out[team]=image
  else:missing.append(team)
 for alias,canonical in ALIASES.items():
  if canonical in out:out[alias]=out[canonical]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print('verified real crests',len([t for t in SEARCH if t in out]),'missing',missing,'generated_at',datetime.now(timezone.utc).isoformat())
 if missing: raise RuntimeError('missing verified club crests: '+', '.join(missing))

if __name__=='__main__':main()
