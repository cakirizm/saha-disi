"""Saha Dışı V7 public-source collector.
Only clear, attributable football remarks can reach the live feed. Generic headlines,
old recycled stories and publisher labels stay out of live data. Article images are retained.
"""
from __future__ import annotations
import hashlib, html, json, re, time, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
UA='Mozilla/5.0 (compatible; SahaDisiCollector/0.7; public-source-indexer)'
ROSTER=json.loads((B/'commentator_roster.json').read_text())
PEOPLE=[(cid,name) for cid,name,_groups in ROSTER]
COMMENTATORS={cid:[name] for cid,name in PEOPLE}
TEAMS=['Galatasaray','Fenerbahçe','Beşiktaş','Trabzonspor','Samsunspor','Göztepe','Konyaspor','Kocaelispor','Gaziantep','Rizespor','Eyüpspor','Alanyaspor','Başakşehir','Kasımpaşa','Gençlerbirliği','Erzurumspor','Çorum','Amed']
PLAYERS=['Osimhen','Sane','Barış Alper','Yunus Akgün','Talisca','Greenwood','Asensio','Kerem','Skriniar','Oğuz Aydın','Vlahovic','Trossard','Batrakov','Orkun Kökçü','Guendouzi','Kante','Semedo','Muriqi','Singo','Torreira','Leao','Cerny','Ndidi','Onuachu','Muçi']
QUOTE_RE=re.compile(r'[“\"‘](.{20,360}?)[”\"’]')
GENERIC={'yorumladı','eleştirdi','övdü','değerlendirdi','açıklamalarda bulundu','konuştu'}
CURRENT_YEAR=datetime.now(timezone.utc).year

class Parser(HTMLParser):
 def __init__(self): super().__init__(); self.text=[]; self.links=[]; self.images=[]; self.skip=0
 def handle_starttag(self,t,a):
  a=dict(a)
  if t in {'script','style','svg','nav','footer'}: self.skip+=1
  if t=='a' and a.get('href'): self.links.append(a['href'])
  if t=='meta':
   key=(a.get('property') or a.get('name') or '').casefold()
   if key in {'og:image','twitter:image','twitter:image:src'} and a.get('content'): self.images.append(a['content'])
 def handle_endtag(self,t):
  if t in {'script','style','svg','nav','footer'} and self.skip:self.skip-=1
 def handle_data(self,d):
  if not self.skip:
   x=' '.join(html.unescape(d).split())
   if len(x)>2:self.text.append(x)

def fetch(url):
 req=Request(url,headers={'User-Agent':UA,'Accept-Language':'tr-TR,tr;q=0.9'})
 with urlopen(req,timeout=16) as r:return r.read().decode('utf-8','ignore')
def parse(doc): p=Parser();p.feed(doc);return p
def detect(text):
 low=text.casefold();return [cid for cid,aliases in COMMENTATORS.items() if any(a.casefold() in low for a in aliases)]
def tags(text,items):
 low=text.casefold();return [x for x in items if x.casefold() in low]
def classify(s):
 l=s.casefold(); typ='opinion';topic='Genel yorum';sent='neutral';strength=6
 if any(x in l for x in ['çok iyi','başarılı','kaliteli','güçlü','beğen','mükemmel','harika']):sent='positive'
 if any(x in l for x in ['kötü','hata','zayıf','problem','yanlış','yetersiz']):sent='negative'
 if any(x in l for x in ['penaltı','hakem','var ']):typ='referee';topic='Hakem / VAR';strength=8
 if any(x in l for x in ['olacak','kazanır','yenilmez','şampiyon','eler','puan alır']):typ='prediction';topic='Tahmin';strength=8
 if any(x in l for x in ['transfer','imza','anlaşma','bonservis']):typ='transfer';topic='Transfer';strength=max(strength,8)
 if any(x in l for x in ['kesin','asla','imkansız','en iyi']):typ='hot_take';strength=10
 return typ,topic,sent,strength

def rss_urls(cid,name):
 qs=[f'"{name}" futbol when:14d',f'"{name}" (dedi OR söyledi OR açıkladı) when:14d',f'"{name}" (transfer OR hakem OR derbi OR maç) when:14d']
 return [{'url':f'https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=tr&gl=TR&ceid=TR:tr','source':'Google News RSS','trust':84,'cid':cid,'rss':True} for q in qs]

def direct_sources():
 return [
  {'url':'https://kontraspor.com/haberleri/nihat-kahveci','source':'Kontraspor','trust':95,'cid':'nihat-kahveci'},
  {'url':'https://www.aspor.com.tr/yazarlar/ahmet-cakar/arsiv','source':'A Spor','trust':100,'cid':'ahmet-cakar'},
  {'url':'https://www.aspor.com.tr/yazarlar/levent-tuzemen/arsiv','source':'A Spor','trust':100,'cid':'levent-tuzemen'},
  {'url':'https://beinsports.com.tr/yazarlar/ugurmeleke','source':'beIN SPORTS','trust':100,'cid':'ugur-meleke'}]

def discover(src,limit=6):
 doc=fetch(src['url'])
 if '<rss' in doc[:500].lower() or '<feed' in doc[:500].lower():
  root=ET.fromstring(doc);out=[]
  for item in root.findall('.//item')[:limit]:
   link=item.findtext('link');title=html.unescape(item.findtext('title') or '')
   if link:out.append((link,title))
  return out
 p=parse(doc);host=urlparse(src['url']).netloc;out=[]
 for h in p.links:
  u=urljoin(src['url'],h);pu=urlparse(u)
  if pu.netloc==host and u!=src['url'] and any(k in pu.path.casefold() for k in ['spor','futbol','yazar','video','haber']):out.append((u.split('#')[0],''))
 return list(dict.fromkeys(out))[:limit]

def clean_statement(text,name):
 text=' '.join(html.unescape(text).replace('“','"').replace('”','"').split()).strip(' -–—')
 text=re.sub(r'\s+-\s+[^-]{2,70}$','',text).strip()
 quotes=QUOTE_RE.findall(text)
 if quotes:
  q=max(quotes,key=len).strip(' "')
  if len(q)>=20:return q[:360]
 if ':' in text:
  left,right=text.split(':',1)
  if name.casefold() in left.casefold() and len(right.strip())>=20:return right.strip(' "')[:360]
 text=re.sub(r'^.*?'+re.escape(name)+r'\s*(?:,|:|-)?\s*','',text,flags=re.I)
 for g in GENERIC:text=re.sub(r'^'+re.escape(g)+r'\s*[:,-]?\s*','',text,flags=re.I)
 return text.strip(' "-–—')[:360]

def noisy(summary, raw, rss=False):
 low=summary.casefold()
 if len(summary)<24:return True
 if any(x in low for x in ['tüm yazılar','beın sports türkiye','son dakika','haberleri','çarpıcı değerlendirme!']):return True
 years=[int(x) for x in re.findall(r'\b20\d{2}\b',summary)]
 if years and max(years)<CURRENT_YEAR:return True
 if rss and not (QUOTE_RE.search(raw) or ':' in raw):return True
 return False

def candidate_from_text(text,src,url,image_url=None):
 text=' '.join(html.unescape(text).split())
 if src['cid'] not in detect(text): return []
 name=COMMENTATORS[src['cid']][0]
 chunks=[text] if len(text)<=650 else re.split(r'(?<=[.!?])\s+',text)
 rows=[]
 for raw in chunks:
  if not 30<=len(raw)<=650 or src['cid'] not in detect(raw):continue
  teams=tags(raw,TEAMS);players=tags(raw,PLAYERS)
  if not teams and not players and not any(k in raw.casefold() for k in ['maç','futbol','hakem','gol','transfer','şampiyon','derbi','takım','oyuncu']):continue
  summary=clean_statement(raw,name)
  if noisy(summary,raw,src.get('rss',False)):continue
  typ,topic,sent,strength=classify(summary)
  direct_quote=bool(QUOTE_RE.search(raw)) or (':' in raw and name.casefold() in raw.split(':',1)[0].casefold())
  confidence=max(src['trust'],95) if direct_quote else src['trust']
  key=hashlib.sha256(f"{src['cid']}|{summary.casefold()}".encode()).hexdigest()[:20]
  rows.append({'candidate_id':key,'commentator':src['cid'],'summary_candidate':summary,'team':teams[0] if teams else None,'players':players,'topic':topic,'type':typ,'sentiment':sent,'strength':strength,'source':src['source'],'url':url,'image_url':image_url,'confidence':confidence,'direct_quote':direct_quote,'discovered_at':datetime.now(timezone.utc).isoformat()})
 return rows

def extract(url,src,hint=''):
 if src.get('rss'):return candidate_from_text(hint,src,url)
 try:
  doc=fetch(url);p=parse(doc);text=' '.join(p.text);image=urljoin(url,p.images[0]) if p.images else None
 except Exception:text=hint;image=None
 return candidate_from_text(text+' '+hint,src,url,image)

def run(limit=6):
 sources=direct_sources()+[x for cid,name in PEOPLE for x in rss_urls(cid,name)]
 rows=[];health=[]
 for src in sources:
  count=0;err=None
  try:
   for url,hint in discover(src,limit):
    found=extract(url,src,hint);rows+=found;count+=len(found)
    if not src.get('rss'):time.sleep(.08)
  except Exception as e:err=str(e)[:180]
  health.append({'commentator':src['cid'],'source':src['source'],'candidates':count,'ok':err is None,'error':err})
 unique={x['candidate_id']:x for x in rows}
 (B/'candidates.json').write_text(json.dumps(list(unique.values()),ensure_ascii=False,indent=2))
 (B/'collector_health.json').write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'tracked_commentators':len(PEOPLE),'sources':health},ensure_ascii=False,indent=2))
 print('candidates',len(unique),'commentators',len(PEOPLE),'sources',len(sources))
if __name__=='__main__':run()
