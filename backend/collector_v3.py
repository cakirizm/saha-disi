"""Saha Dışı public-source collector.
Only attributable, literal football quotes are emitted as candidates. Editorial headlines are never converted into quotes.
Network work runs concurrently so the hourly live-feed job stays bounded.
"""
from __future__ import annotations
import hashlib, html, json, re, urllib.parse, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
UA='Mozilla/5.0 (compatible; SahaDisiCollector/2.1; literal-quote-indexer)'
ROSTER=json.loads((B/'commentator_roster.json').read_text(encoding='utf-8'))
PEOPLE=[(cid,name) for cid,name,_ in ROSTER]; COMMENTATORS={cid:name for cid,name in PEOPLE}
TEAMS=['Galatasaray','Fenerbahçe','Beşiktaş','Trabzonspor','Samsunspor','Göztepe','Konyaspor','Kocaelispor','Gaziantep','Rizespor','Eyüpspor','Alanyaspor','Başakşehir','Kasımpaşa','Gençlerbirliği','Erzurumspor','Çorum','Amed']
PLAYERS=['Osimhen','Sane','Barış Alper','Yunus Akgün','Talisca','Greenwood','Asensio','Kerem','Skriniar','Oğuz Aydın','Vlahovic','Trossard','Batrakov','Orkun Kökçü','Guendouzi','Kante','Semedo','Muriqi','Singo','Torreira','Leao','Cerny','Ndidi','Onuachu','Muçi']
QUOTE_RE=re.compile(r'[“\"‘](.{20,420}?)[”\"’]',re.S)
BAD_MARKERS=('eleştirdi','yorumladı','değerlendirdi','açıkladı','söyledi','ifade etti','konuştu','övdü','sert dille','çarpıcı sözler','flaş sözler')

class Parser(HTMLParser):
 def __init__(self): super().__init__();self.text=[];self.links=[];self.images=[];self.skip=0
 def handle_starttag(self,t,a):
  a=dict(a)
  if t in {'script','style','svg','nav','footer'}:self.skip+=1
  if t=='a' and a.get('href'):self.links.append(a['href'])
  if t=='meta':
   key=(a.get('property') or a.get('name') or '').casefold()
   if key in {'og:image','twitter:image','twitter:image:src'} and a.get('content'):self.images.append(a['content'])
 def handle_endtag(self,t):
  if t in {'script','style','svg','nav','footer'} and self.skip:self.skip-=1
 def handle_data(self,d):
  if not self.skip:
   x=' '.join(html.unescape(d).replace('\xa0',' ').split())
   if len(x)>2:self.text.append(x)

def decode_body(raw,content_type=''):
 declared='';m=re.search(r'charset=([\w-]+)',content_type,re.I)
 if m:declared=m.group(1)
 for enc in [declared,'utf-8','windows-1254','iso-8859-9']:
  if not enc:continue
  try:
   text=raw.decode(enc)
   if not any(x in text for x in ('Ã§','Ã¼','ÅŸ','Ä±','Ä°','Ã¶','ÄŸ')):return text
  except Exception:pass
 return raw.decode('windows-1254','replace')

def repair_text(value):
 value=html.unescape(value or '').replace('\xa0',' ')
 for _ in range(2):
  if any(x in value for x in ('Ã','Å','Ä')):
   try:
    fixed=value.encode('latin1').decode('utf-8')
    if fixed!=value:value=fixed;continue
   except Exception:pass
  break
 return ' '.join(value.split())

def fetch(url):
 req=Request(url,headers={'User-Agent':UA,'Accept-Language':'tr-TR,tr;q=0.9'})
 with urlopen(req,timeout=12) as r:return decode_body(r.read(),r.headers.get('Content-Type',''))
def parse(doc):p=Parser();p.feed(doc);return p
def tags(text,items):
 low=text.casefold();return [x for x in items if x.casefold() in low]
def classify(s):
 l=s.casefold();typ='opinion';topic='Genel yorum';sent='neutral';strength=6
 if any(x in l for x in ['çok iyi','başarılı','kaliteli','güçlü','mükemmel','harika']):sent='positive'
 if any(x in l for x in ['kötü','hata','zayıf','problem','yanlış','yetersiz']):sent='negative'
 if any(x in l for x in ['penaltı','hakem','var ']):typ='referee';topic='Hakem / VAR';strength=8
 if any(x in l for x in ['olacak','kazanır','yenilmez','şampiyon','eler','puan alır']):typ='prediction';topic='Tahmin';strength=8
 if any(x in l for x in ['transfer','imza','anlaşma','bonservis']):typ='transfer';topic='Transfer';strength=max(strength,8)
 if any(x in l for x in ['kesin','asla','imkansız','en iyi']):typ='hot_take';strength=10
 return typ,topic,sent,strength

def rss_source(cid,name):
 q=f'"{name}" (futbol OR maç OR transfer OR hakem) when:14d'
 return {'url':f'https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=tr&gl=TR&ceid=TR:tr','source':'Google News RSS','trust':90,'cid':cid,'rss':True}
def direct_sources():
 return [
  {'url':'https://kontraspor.com/haberleri/nihat-kahveci','source':'Kontraspor','trust':98,'cid':'nihat-kahveci'},
  {'url':'https://www.aspor.com.tr/yazarlar/ahmet-cakar/arsiv','source':'A Spor','trust':100,'cid':'ahmet-cakar'},
  {'url':'https://www.aspor.com.tr/yazarlar/levent-tuzemen/arsiv','source':'A Spor','trust':100,'cid':'levent-tuzemen'},
  {'url':'https://beinsports.com.tr/yazarlar/ugurmeleke','source':'beIN SPORTS','trust':100,'cid':'ugur-meleke'}]
def discover(src,limit=3):
 doc=fetch(src['url'])
 if '<rss' in doc[:700].lower() or '<feed' in doc[:700].lower():
  root=ET.fromstring(doc);out=[]
  for item in root.findall('.//item')[:limit]:
   link=item.findtext('link');title=repair_text(item.findtext('title') or '')
   if link:out.append((link,title))
  return out
 p=parse(doc);host=urlparse(src['url']).netloc;out=[]
 for h in p.links:
  u=urljoin(src['url'],h);pu=urlparse(u)
  if pu.netloc==host and u!=src['url'] and any(k in pu.path.casefold() for k in ['spor','futbol','yazar','video','haber']):out.append((u.split('#')[0],''))
 return list(dict.fromkeys(out))[:limit]
def literal_quotes(text,name):
 text=repair_text(text);quotes=[]
 for q in QUOTE_RE.findall(text):
  q=repair_text(q).strip(' "“”')
  if 20<=len(q)<=420:quotes.append(q)
 speaker=re.compile(re.escape(name)+r'\s*[:：]\s*([^\n]{20,420})',re.I)
 for m in speaker.findall(text):
  q=repair_text(re.split(r'(?<=[.!?])\s+',m)[0]).strip(' "“”')
  if 20<=len(q)<=420:quotes.append(q)
 return list(dict.fromkeys(quotes))
def candidate_rows(text,src,url,image_url=None):
 name=COMMENTATORS[src['cid']];text=repair_text(text)
 if name.casefold() not in text.casefold():return []
 rows=[]
 for quote in literal_quotes(text,name):
  low=quote.casefold()
  if any(low.startswith(x+' ') or low==x for x in BAD_MARKERS):continue
  teams=tags(text,TEAMS);players=tags(quote+' '+text,PLAYERS)
  if not teams and not players and not any(k in low for k in ['maç','futbol','hakem','gol','transfer','şampiyon','derbi','takım','oyuncu']):continue
  typ,topic,sent,strength=classify(quote)
  key=hashlib.sha256(f"{src['cid']}|{quote.casefold()}".encode('utf-8')).hexdigest()[:20]
  rows.append({'candidate_id':key,'commentator':src['cid'],'summary_candidate':quote,'team':teams[0] if teams else None,'players':players,'topic':topic,'type':typ,'sentiment':sent,'strength':strength,'source':src['source'],'url':url,'image_url':image_url,'confidence':max(src['trust'],95),'direct_quote':True,'discovered_at':datetime.now(timezone.utc).isoformat()})
 return rows
def extract(url,src,hint=''):
 try:
  doc=fetch(url);p=parse(doc);text=' '.join(p.text);image=urljoin(url,p.images[0]) if p.images else None
 except Exception:return []
 return candidate_rows(text+' '+hint,src,url,image)
def process_source(src):
 rows=[];err=None
 try:
  for url,hint in discover(src,3):rows.extend(extract(url,src,hint))
 except Exception as e:err=str(e)[:180]
 return rows,{'commentator':src['cid'],'source':src['source'],'candidates':len(rows),'ok':err is None,'error':err}
def run():
 sources=direct_sources()+[rss_source(cid,name) for cid,name in PEOPLE]
 rows=[];health=[]
 with ThreadPoolExecutor(max_workers=20) as pool:
  futures=[pool.submit(process_source,s) for s in sources]
  for f in as_completed(futures):
   found,h=f.result();rows.extend(found);health.append(h)
 unique={x['candidate_id']:x for x in rows}
 health.sort(key=lambda x:(x['commentator'],x['source']))
 (B/'candidates.json').write_text(json.dumps(list(unique.values()),ensure_ascii=False,indent=2),encoding='utf-8')
 (B/'collector_health.json').write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'tracked_commentators':len(PEOPLE),'sources':health},ensure_ascii=False,indent=2),encoding='utf-8')
 print('literal quote candidates',len(unique),'commentators',len(PEOPLE),'sources',len(sources))
if __name__=='__main__':run()
