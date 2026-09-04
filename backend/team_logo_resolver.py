"""Resolve real Süper Lig club crests from identified football-team sources.
ESPN team assets are preferred. Missing clubs use explicit club-verified fallbacks only.
No generic favicons are accepted.
"""
from __future__ import annotations
import json, re, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'; OUT=B/'team_logos.json'
URL='https://site.api.espn.com/apis/site/v2/sports/soccer/tur.1/teams?limit=100'
UA='Mozilla/5.0 (compatible; SahaDisi/2.3; verified-football-crest-resolver)'
CANONICAL=['Galatasaray','Fenerbahçe','Beşiktaş','Trabzonspor','Samsunspor','Göztepe','Konyaspor','Rizespor','Kocaelispor','Gençlerbirliği','Çorum FK','Eyüpspor','Gaziantep FK','Alanyaspor','Başakşehir','Kasımpaşa','Amed SK','Erzurumspor']
VERIFIED_FALLBACKS={
 'Amed SK':'https://pbs.twimg.com/media/B8x-WXuCIAALv64.jpg',
 'Erzurumspor':'https://erzurumsporfk.org/wp-content/uploads/2025/08/erzurumsporfklogo.png'
}
ALIASES={
 'İstanbul Başakşehir':'Başakşehir','İstanbul Başakşehir FK':'Başakşehir','Tümosan Konyaspor':'Konyaspor','Çaykur Rizespor':'Rizespor','Çaykur Rizespor A.Ş.':'Rizespor',
 'Arca Çorum FK':'Çorum FK','Çorum':'Çorum FK','Gaziantep':'Gaziantep FK','Gaziantep Futbol Kulübü':'Gaziantep FK','Gaziantep Futbol Kulübü A.Ş.':'Gaziantep FK',
 'Amed Sportif Faaliyetler':'Amed SK','AMED SPORTİF FAALİYETLER':'Amed SK','Erzurumspor FK':'Erzurumspor','ERZURUMSPOR FK':'Erzurumspor',
 'Corendon Alanyaspor':'Alanyaspor','Galatasaray A.Ş.':'Galatasaray','Fenerbahçe A.Ş.':'Fenerbahçe','Beşiktaş A.Ş.':'Beşiktaş','Trabzonspor A.Ş.':'Trabzonspor',
 'Samsunspor A.Ş.':'Samsunspor','Göztepe A.Ş.':'Göztepe','Kasımpaşa A.Ş.':'Kasımpaşa'
}
NAME_ALIASES={
 'galatasaray':'Galatasaray','fenerbahce':'Fenerbahçe','besiktas':'Beşiktaş','trabzonspor':'Trabzonspor','samsunspor':'Samsunspor','goztepe':'Göztepe',
 'konyaspor':'Konyaspor','caykur rizespor':'Rizespor','rizespor':'Rizespor','kocaelispor':'Kocaelispor','genclerbirligi':'Gençlerbirliği','corum fk':'Çorum FK',
 'corum':'Çorum FK','eyupspor':'Eyüpspor','gaziantep fk':'Gaziantep FK','gaziantep':'Gaziantep FK','alanyaspor':'Alanyaspor','istanbul basaksehir':'Başakşehir',
 'basaksehir':'Başakşehir','kasimpasa':'Kasımpaşa','amed sk':'Amed SK','amedspor':'Amed SK','erzurumspor fk':'Erzurumspor','erzurumspor':'Erzurumspor'
}

def norm(s):
 s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().casefold()
 return re.sub(r'[^a-z0-9]+',' ',s).strip()

def fetch_data():
 req=Request(URL,headers={'User-Agent':UA,'Accept':'application/json'})
 with urlopen(req,timeout=18) as r:return json.loads(r.read().decode('utf-8'))

def team_rows(data):
 sports=data.get('sports') or []
 if sports:
  leagues=sports[0].get('leagues') or []
  if leagues:return leagues[0].get('teams') or []
 return data.get('teams') or []

def reachable_image(url):
 try:
  req=Request(url,headers={'User-Agent':UA,'Accept':'image/*'})
  with urlopen(req,timeout=12) as r:
   ctype=(r.headers.get('Content-Type') or '').casefold()
   return r.status==200 and ctype.startswith('image/') and len(r.read(64))>0
 except Exception:return False

def main():
 data=fetch_data();out={};seen=[]
 for wrapper in team_rows(data):
  team=wrapper.get('team',wrapper)
  names=[team.get('displayName'),team.get('shortDisplayName'),team.get('name'),team.get('slug')]
  canonical=None
  for name in names:
   key=norm(name)
   if key in NAME_ALIASES:canonical=NAME_ALIASES[key];break
  if not canonical:continue
  logos=team.get('logos') or []
  image=next((x.get('href') for x in logos if x.get('href','').startswith('https://')),None)
  if image:
   out[canonical]=image;seen.append((canonical,team.get('displayName'),'espn'))
 for team,url in VERIFIED_FALLBACKS.items():
  if not out.get(team):
   if reachable_image(url):out[team]=url;seen.append((team,'verified fallback','club-verified'))
 missing=[t for t in CANONICAL if not out.get(t)]
 for alias,canonical in ALIASES.items():
  if canonical in out:out[alias]=out[canonical]
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print('verified real crests',len(CANONICAL)-len(missing),'missing',missing,'matched',seen,'generated_at',datetime.now(timezone.utc).isoformat())
 if missing:raise RuntimeError('missing verified club crests: '+', '.join(missing))

if __name__=='__main__':main()
