"""Fetch the official 2026-27 Süper Lig fixture from TFF.
No API key. The parser is deliberately defensive; on layout changes it leaves the
previous live feed untouched rather than publishing invented fixtures.
"""
from __future__ import annotations
import html, json, re, unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
URL='https://www.tff.org/default.aspx?ftxt=1&pageID=198'
UA='Mozilla/5.0 (compatible; SahaDisiFixture/1.0)'

class TableParser(HTMLParser):
 def __init__(self):
  super().__init__(); self.rows=[]; self.row=None; self.cell=None; self.all=[]
 def handle_starttag(self,tag,attrs):
  if tag=='tr': self.row=[]
  elif tag in {'td','th'} and self.row is not None: self.cell=[]
 def handle_data(self,data):
  t=' '.join(html.unescape(data).split())
  if not t:return
  self.all.append(t)
  if self.cell is not None:self.cell.append(t)
 def handle_endtag(self,tag):
  if tag in {'td','th'} and self.cell is not None:
   self.row.append(' '.join(self.cell)); self.cell=None
  elif tag=='tr' and self.row is not None:
   if self.row:self.rows.append(self.row)
   self.row=None

def fetch():
 req=Request(URL,headers={'User-Agent':UA,'Accept-Language':'tr-TR,tr;q=0.9'})
 with urlopen(req,timeout=25) as r:return r.read().decode('utf-8','ignore')

def clean_team(s):
 s=re.sub(r'\s+',' ',s).strip(' -–—')
 replacements={
  'GALATASARAY A.Ş.':'Galatasaray','FENERBAHÇE A.Ş.':'Fenerbahçe','BEŞİKTAŞ A.Ş.':'Beşiktaş',
  'TRABZONSPOR A.Ş.':'Trabzonspor','TÜMOSAN KONYASPOR':'Konyaspor','KONYASPOR':'Konyaspor',
  'ÇAYKUR RİZESPOR A.Ş.':'Çaykur Rizespor','GAZİANTEP FUTBOL KULÜBÜ A.Ş.':'Gaziantep FK',
  'CORENDON ALANYASPOR':'Alanyaspor','GENÇLERBİRLİĞİ':'Gençlerbirliği','KASIMPAŞA A.Ş.':'Kasımpaşa',
  'ARCA ÇORUM FK':'Çorum FK','ÇORUM FK':'Çorum FK','EYÜPSPOR':'Eyüpspor',
  'AMED SPORTİF FAALİYETLER':'Amed','ERZURUMSPOR FK':'Erzurumspor','İSTANBUL BAŞAKŞEHİR FK':'Başakşehir',
  'KOCAELİSPOR':'Kocaelispor','SAMSUNSPOR A.Ş.':'Samsunspor','GÖZTEPE A.Ş.':'Göztepe'
 }
 return replacements.get(s.upper(),s.title())

def slug(s):
 s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
 return re.sub(r'[^a-z0-9]+','-',s).strip('-')

def parse_score(text):
 m=re.search(r'(?<!\d)(\d{1,2})\s*-\s*(\d{1,2})(?!\d)',text)
 return (int(m.group(1)),int(m.group(2))) if m else (None,None)

def split_match(text):
 # Score form: TEAM 2 - 1 TEAM; fixture form: TEAM - TEAM
 m=re.match(r'(.+?)\s+(\d{1,2})\s*-\s*(\d{1,2})\s+(.+)$',text)
 if m:return m.group(1),m.group(4),int(m.group(2)),int(m.group(3))
 m=re.match(r'(.+?)\s+-\s+(.+)$',text)
 if m:return m.group(1),m.group(2),None,None
 return None

def run():
 p=TableParser(); p.feed(fetch())
 rows=[]; current_week=None
 # First try table rows, which preserve match boundaries on TFF.
 for cells in p.rows:
  text=' '.join(cells)
  wm=re.search(r'(\d{1,2})\.?\s*Hafta',text,re.I)
  if wm and len(cells)<=4: current_week=int(wm.group(1)); continue
  if current_week:
   match=split_match(text)
   if match:
    home,away,hs,as_=match
    if len(home)<4 or len(away)<4:continue
    rows.append({'week':current_week,'home':clean_team(home),'away':clean_team(away),'home_score':hs,'away_score':as_})
 # Fallback: TFF often exposes each fixture as one text node.
 if len(rows)<100:
  rows=[]; current_week=None
  for text in p.all:
   wm=re.fullmatch(r'(\d{1,2})\.?\s*Hafta',text,re.I)
   if wm: current_week=int(wm.group(1)); continue
   if current_week:
    match=split_match(text)
    if match:
     home,away,hs,as_=match
     rows.append({'week':current_week,'home':clean_team(home),'away':clean_team(away),'home_score':hs,'away_score':as_})
 unique={}
 for r in rows:
  key=(r['week'],r['home'],r['away']); unique[key]=r
 rows=list(unique.values())
 if len(rows)<100:
  raise RuntimeError(f'TFF parse returned only {len(rows)} matches; refusing to replace fixture')
 out=[]
 for r in sorted(rows,key=lambda x:(x['week'],x['home'])):
  out.append({
   'id':f"sl-2026-{r['week']:02d}-{slug(r['home'])}-{slug(r['away'])}",
   'league':'Trendyol Süper Lig','week':r['week'],'home':r['home'],'away':r['away'],
   'kickoff':f"2026-2027 · {r['week']}. Hafta",'home_score':r['home_score'],'away_score':r['away_score'],
   'image_url':None,'source':'TFF','source_url':URL
  })
 (B/'tff_matches.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print('tff fixtures',len(out),'weeks',len(set(x['week'] for x in out)))

if __name__=='__main__':run()
