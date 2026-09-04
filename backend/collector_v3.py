"""Saha Dışı V3 public-source collector.
Discovery: direct editorial hubs + Google News RSS queries (no API key).
Extraction is conservative. Nothing is auto-published unless confidence >= configured gate.
Do not download/rehost video/audio or copy full articles into the app.
"""
from __future__ import annotations
import hashlib, html, json, re, time, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
UA='Mozilla/5.0 (compatible; SahaDisiCollector/0.3; public-source-indexer)'
PEOPLE=json.loads((B/'commentators.json').read_text())
COMMENTATORS={cid:[name] for cid,name in PEOPLE}
TEAMS=['Galatasaray','Fenerbahçe','Beşiktaş','Trabzonspor','Samsunspor','Göztepe','Konyaspor','Kocaelispor','Gaziantep','Rizespor','Eyüpspor','Alanyaspor','Başakşehir','Kasımpaşa','Gençlerbirliği','Erzurumspor','Çorum','Amed']
PLAYERS=['Osimhen','Sane','Barış Alper','Yunus Akgün','Talisca','Greenwood','Asensio','Kerem','Skriniar','Oğuz Aydın','Vlahovic','Trossard','Batrakov','Orkun Kökçü','Guendouzi','Kante','Semedo','Muriqi','Singo','Torreira','Leao']
class Parser(HTMLParser):
 def __init__(self): super().__init__(); self.text=[]; self.links=[]; self.skip=0
 def handle_starttag(self,t,a):
  a=dict(a)
  if t in {'script','style','svg','nav','footer'}: self.skip+=1
  if t=='a' and a.get('href'): self.links.append(a['href'])
 def handle_endtag(self,t):
  if t in {'script','style','svg','nav','footer'} and self.skip:self.skip-=1
 def handle_data(self,d):
  if not self.skip:
   x=' '.join(html.unescape(d).split())
   if len(x)>2:self.text.append(x)
def fetch(url):
 req=Request(url,headers={'User-Agent':UA,'Accept-Language':'tr-TR,tr;q=0.9'})
 with urlopen(req,timeout=20) as r:return r.read().decode('utf-8','ignore')
def parse(doc): p=Parser();p.feed(doc);return p
def detect(text):
 low=text.casefold();return [cid for cid,aliases in COMMENTATORS.items() if any(a.casefold() in low for a in aliases)]
def tags(text,items):
 low=text.casefold();return [x for x in items if x.casefold() in low]
def classify(s):
 l=s.casefold(); typ='opinion';topic='Genel yorum';sent='neutral';strength=6
 if any(x in l for x in ['çok iyi','başarılı','kaliteli','güçlü','beğen','mükemmel']):sent='positive'
 if any(x in l for x in ['kötü','hata','eleştir','zayıf','problem','yanlış']):sent='negative'
 if any(x in l for x in ['penaltı','hakem','var ']):typ='referee';topic='Hakem / VAR';strength=8
 if any(x in l for x in ['olacak','kazanır','yenilmez','şampiyon','eler','puan alır']):typ='prediction';topic='Tahmin';strength=8
 if any(x in l for x in ['kesin','asla','imkansız','en iyi']):typ='hot_take';strength=10
 return typ,topic,sent,strength
def rss_urls(cid,name):
 q=urllib.parse.quote(f'"{name}" futbol')
 return [{'url':f'https://news.google.com/rss/search?q={q}&hl=tr&gl=TR&ceid=TR:tr','source':'Google News RSS','trust':78,'cid':cid}]
def direct_sources():
 return [
  {'url':'https://kontraspor.com/haberleri/nihat-kahveci','source':'Kontraspor','trust':95,'cid':'nihat-kahveci'},
  {'url':'https://www.aspor.com.tr/yazarlar/ahmet-cakar/arsiv','source':'A Spor','trust':100,'cid':'ahmet-cakar'},
  {'url':'https://www.aspor.com.tr/yazarlar/levent-tuzemen/arsiv','source':'A Spor','trust':100,'cid':'levent-tuzemen'},
  {'url':'https://beinsports.com.tr/yazarlar/ugurmeleke','source':'beIN SPORTS','trust':100,'cid':'ugur-meleke'}]
def discover(src,limit=12):
 doc=fetch(src['url'])
 if '<rss' in doc[:500].lower() or '<feed' in doc[:500].lower():
  root=ET.fromstring(doc); out=[]
  for item in root.findall('.//item')[:limit]:
   link=item.findtext('link'); title=item.findtext('title') or ''
   if link: out.append((link,title))
  return out
 p=parse(doc);host=urlparse(src['url']).netloc;out=[]
 for h in p.links:
  u=urljoin(src['url'],h);pu=urlparse(u)
  if pu.netloc==host and u!=src['url'] and any(k in pu.path.casefold() for k in ['spor','futbol','yazar','video','haber']):out.append((u.split('#')[0],''))
 return list(dict.fromkeys(out))[:limit]
def extract(url,src,hint=''):
 try: doc=fetch(url); p=parse(doc); text=' '.join(p.text)
 except Exception: text=hint
 if src['cid'] not in detect(text+' '+hint): return []
 chunks=re.split(r'(?<=[.!?])\s+',re.sub(r'\s+',' ',text))
 rows=[]
 for s in chunks:
  if not 45<=len(s)<=420 or src['cid'] not in detect(s):continue
  teams=tags(s,TEAMS);players=tags(s,PLAYERS)
  if not teams and not players and not any(k in s.casefold() for k in ['maç','futbol','hakem','gol','transfer']):continue
  typ,topic,sent,strength=classify(s); key=hashlib.sha256(f"{src['cid']}|{s}".encode()).hexdigest()[:20]
  rows.append({'candidate_id':key,'commentator':src['cid'],'summary_candidate':s,'team':teams[0] if teams else None,'players':players,'topic':topic,'type':typ,'sentiment':sent,'strength':strength,'source':src['source'],'url':url,'confidence':src['trust'],'discovered_at':datetime.now(timezone.utc).isoformat()})
 return rows
def run(limit=10):
 sources=direct_sources()+[x for cid,name in PEOPLE for x in rss_urls(cid,name)]
 rows=[]; health=[]
 for src in sources:
  count=0;err=None
  try:
   for url,hint in discover(src,limit):
    found=extract(url,src,hint);rows+=found;count+=len(found);time.sleep(.12)
  except Exception as e:err=str(e)[:180]
  health.append({'commentator':src['cid'],'source':src['source'],'candidates':count,'ok':err is None,'error':err})
 unique={x['candidate_id']:x for x in rows}
 (B/'candidates.json').write_text(json.dumps(list(unique.values()),ensure_ascii=False,indent=2))
 (B/'collector_health.json').write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'sources':health},ensure_ascii=False,indent=2))
 print('candidates',len(unique),'sources',len(sources))
if __name__=='__main__': run()
