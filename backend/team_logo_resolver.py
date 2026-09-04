"""Resolve club crest thumbnails from Turkish Wikipedia pageimages API.
Only public remote image URLs are stored; no image binaries are copied into the repo.
"""
from __future__ import annotations
import json, urllib.parse
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
UA='SahaDisi/1.1 team-logo-resolver'
TEAM_PAGES={
 'Galatasaray':'Galatasaray_(futbol_takımı)','Fenerbahçe':'Fenerbahçe_(futbol_takımı)','Beşiktaş':'Beşiktaş_(futbol_takımı)','Trabzonspor':'Trabzonspor',
 'Samsunspor':'Samsunspor','Göztepe':'Göztepe_SK','Konyaspor':'Konyaspor','Rizespor':'Çaykur_Rizespor','Kocaelispor':'Kocaelispor','Gençlerbirliği':'Gençlerbirliği_SK',
 'Çorum FK':'Çorum_FK','Çorum':'Çorum_FK','Eyüpspor':'Eyüpspor','Gaziantep FK':'Gaziantep_FK','Gaziantep':'Gaziantep_FK','Alanyaspor':'Alanyaspor',
 'Başakşehir':'İstanbul_Başakşehir_FK','Kasımpaşa':'Kasımpaşa_SK','Amed SK':'Amed_SK','Amed':'Amed_SK','Erzurumspor':'Erzurumspor_FK'}

def resolve(page):
 params=urllib.parse.urlencode({'action':'query','format':'json','prop':'pageimages','pithumbsize':'256','titles':page,'redirects':'1'})
 req=Request('https://tr.wikipedia.org/w/api.php?'+params,headers={'User-Agent':UA})
 with urlopen(req,timeout=15) as r:data=json.load(r)
 for row in data.get('query',{}).get('pages',{}).values():
  if row.get('thumbnail',{}).get('source'): return row['thumbnail']['source']
 return None

def main():
 out={}
 for team,page in TEAM_PAGES.items():
  try:
   url=resolve(page)
   if url: out[team]=url
  except Exception as e: print('logo miss',team,str(e)[:80])
 (B/'team_logos.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print('team logos',len(out))

if __name__=='__main__':main()
