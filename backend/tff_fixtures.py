"""Fetch the full 2026-27 Trendyol Super Lig fixture from the official TFF page."""
from __future__ import annotations
import html, json, re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
URL='https://www.tff.org/default.aspx?ftxt=1&pageID=198'
UA='Mozilla/5.0 (compatible; SahaDisi/1.1; public-fixture-reader)'
ALIASES={
 'GALATASARAY A.Ş.':'Galatasaray','FENERBAHÇE A.Ş.':'Fenerbahçe','BEŞİKTAŞ A.Ş.':'Beşiktaş','TRABZONSPOR A.Ş.':'Trabzonspor',
 'SAMSUNSPOR A.Ş.':'Samsunspor','GÖZTEPE A.Ş.':'Göztepe','TÜMOSAN KONYASPOR':'Konyaspor','KONYASPOR':'Konyaspor',
 'ÇAYKUR RİZESPOR A.Ş.':'Rizespor','KOCAELİSPOR':'Kocaelispor','GENÇLERBİRLİĞİ':'Gençlerbirliği','ARCA ÇORUM FK':'Çorum FK','ÇORUM FK':'Çorum FK',
 'EYÜPSPOR':'Eyüpspor','GAZİANTEP FUTBOL KULÜBÜ A.Ş.':'Gaziantep FK','CORENDON ALANYASPOR':'Alanyaspor','İSTANBUL BAŞAKŞEHİR FK':'Başakşehir',
 'KASIMPAŞA A.Ş.':'Kasımpaşa','AMED SPORTİF FAALİYETLER':'Amed SK','ERZURUMSPOR FK':'Erzurumspor'}

def clean_team(s):
 s=' '.join(html.unescape(s).replace('\xa0',' ').split()).strip(' -\t')
 return ALIASES.get(s,s.title())

def fetch():
 req=Request(URL,headers={'User-Agent':UA,'Accept-Language':'tr-TR,tr;q=0.9'})
 with urlopen(req,timeout=30) as r:return r.read().decode('utf-8','ignore')

def text_lines(doc):
 doc=re.sub(r'(?is)<script.*?</script>|<style.*?</style>','',doc)
 txt=re.sub(r'(?s)<[^>]+>','\n',doc)
 return [' '.join(html.unescape(x).replace('\xa0',' ').split()) for x in txt.splitlines() if x.strip()]

def parse(doc):
 xs=text_lines(doc); rows=[]; seen=set(); week=0; dated={}
 week_re=re.compile(r'^(\d{1,2})\s*\.\s*Hafta$',re.I)
 dated_re=re.compile(r'^(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})\s+(.+?)\s+-\s+(.+?)(?:\s+Detaylar)?$')
 score_re=re.compile(r'^(.+?)\s+(\d+)\s*-\s*(\d+)\s+(.+)$')
 fixture_re=re.compile(r'^(.+?)\s+-\s+(.+)$')

 for line in xs:
  m=dated_re.match(line)
  if m: dated[(clean_team(m.group(3)),clean_team(m.group(4)))]=f'{m.group(1)} {m.group(2)}'

 for line in xs:
  m=week_re.match(line)
  if m:
   n=int(m.group(1)); week=n if 1<=n<=34 else week; continue
  if not week: continue
  if any(x in line.casefold() for x in ['sezon','devre','puan cetveli','fikstür listesi','trendyol süper lig']): continue
  hs=as_=None; home=away=None
  m=score_re.match(line)
  if m: home,hs,as_,away=m.group(1),int(m.group(2)),int(m.group(3)),m.group(4)
  else:
   m=fixture_re.match(line)
   if m: home,away=m.group(1),m.group(2)
  if not home or not away: continue
  home=clean_team(home); away=clean_team(away.replace(' Detaylar',''))
  if len(home)<3 or len(away)<3: continue
  key=(week,home.casefold(),away.casefold())
  if key in seen: continue
  seen.add(key)
  rows.append({'id':f'sl-2026-{week:02d}-{len(rows)+1:03d}','league':'Trendyol Süper Lig','week':week,'home':home,'away':away,'kickoff':dated.get((home,away),''),'home_score':hs,'away_score':as_,'image_url':None,'source':'TFF','source_url':URL})
 return rows

def main():
 p=B/'tff_matches.json'; old=[]
 if p.exists():
  try: old=json.loads(p.read_text())
  except Exception: pass
 try: rows=parse(fetch())
 except Exception as e:
  print('TFF fetch failed:',e); rows=old
 # Full fixture should contain 306 matches. Never replace a healthier cache with a partial result.
 if len(rows)<250 and len(old)>len(rows): rows=old
 p.write_text(json.dumps(rows,ensure_ascii=False,indent=2)); print('tff matches',len(rows),'weeks',len(set(x.get('week') for x in rows)))

if __name__=='__main__': main()
