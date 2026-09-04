from __future__ import annotations
import argparse, hashlib, html, json, re, time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
UA='Mozilla/5.0 (compatible; SahaDisiCollector/0.2; contact: app-owner)'
COMMENTATORS={
 'ahmet-cakar':['Ahmet Çakar'], 'mustafa-culcu':['Mustafa Çulcu'], 'nihat-kahveci':['Nihat Kahveci'],
 'ali-ece':['Ali Ece'], 'serdar-ali-celikler':['Serdar Ali Çelikler','SAÇ']
}
TEAMS=['Galatasaray','Fenerbahçe','Beşiktaş','Trabzonspor']
PLAYERS=['Osimhen','Sane','Barış Alper','Yunus Akgün','Talisca','Greenwood','Asensio','Kerem','Skriniar','Oğuz Aydın','Vlahovic']

class Parser(HTMLParser):
 def __init__(self): super().__init__(); self.text=[]; self.links=[]; self.skip=0; self.title=''
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag in {'script','style','svg','nav','footer'}: self.skip+=1
  if tag=='a' and attrs.get('href'): self.links.append(attrs['href'])
 def handle_endtag(self,tag):
  if tag in {'script','style','svg','nav','footer'} and self.skip:self.skip-=1
 def handle_data(self,data):
  if not self.skip:
   t=' '.join(html.unescape(data).split())
   if len(t)>2:self.text.append(t)

def fetch(url):
 req=Request(url,headers={'User-Agent':UA,'Accept-Language':'tr-TR,tr;q=0.9'})
 with urlopen(req,timeout=20) as r:
  ctype=r.headers.get('content-type','')
  if 'text/html' not in ctype and 'xml' not in ctype:return ''
  return r.read().decode('utf-8','ignore')

def parse(doc):
 p=Parser();p.feed(doc);return p

def normalize(s): return re.sub(r'\s+',' ',s).strip()

def sentence_candidates(text):
 chunks=re.split(r'(?<=[.!?])\s+',normalize(text))
 return [x for x in chunks if 40<=len(x)<=420]

def classify(sentence):
 low=sentence.casefold()
 sentiment='neutral'
 if any(x in low for x in ['çok iyi','mükemmel','başarılı','kaliteli','güçlü','övg','beğen']): sentiment='positive'
 if any(x in low for x in ['kötü','formsuz','hata','eleştir','zayıf','problem','yanlış']): sentiment='negative'
 type_='opinion'; topic='Genel yorum'; strength=6
 if any(x in low for x in ['penaltı','hakem','var ']): type_='referee'; topic='Hakem / VAR'; strength=8
 if any(x in low for x in ['olacak','kazanır','şampiyon','eler','puan alır']): type_='prediction'; topic='Tahmin'; strength=8
 if any(x in low for x in ['kesin','yüzde','asla','imkansız','tarihin','en iyi']): type_='hot_take'; strength=10
 return type_,topic,sentiment,strength

def tags(text, items):
 low=text.casefold(); return [x for x in items if x.casefold() in low]

def detect_commentators(text):
 low=text.casefold(); out=[]
 for cid,aliases in COMMENTATORS.items():
  if any(a.casefold() in low for a in aliases):out.append(cid)
 return out

def discover_index(source,max_links=40):
 doc=fetch(source['url']); p=parse(doc); host=urlparse(source['url']).netloc
 links=[]
 for href in p.links:
  u=urljoin(source['url'],href); pu=urlparse(u)
  if pu.netloc!=host:continue
  if u==source['url']:continue
  if any(k in pu.path.casefold() for k in ['spor','futbol','yazar','video','haber']): links.append(u.split('#')[0])
 # stable dedupe
 seen=set();res=[]
 for u in links:
  if u not in seen: seen.add(u);res.append(u)
 return res[:max_links]

def extract_url(url,source):
 doc=fetch(url)
 if not doc:return []
 p=parse(doc); text=' '.join(p.text)
 detected=detect_commentators(text)
 allowed=set(source.get('commentators',[]))
 commentator_ids=[x for x in detected if not allowed or x in allowed]
 if not commentator_ids:return []
 rows=[]
 for sentence in sentence_candidates(text):
  cids=detect_commentators(sentence)
  if not cids:continue
  teams=tags(sentence,TEAMS); players=tags(sentence,PLAYERS)
  if not teams and not players and not any(k in sentence.casefold() for k in ['maç','futbol','hakem','gol','transfer']):continue
  type_,topic,sentiment,strength=classify(sentence)
  for cid in cids:
   if allowed and cid not in allowed:continue
   digest=hashlib.sha256(f'{cid}|{sentence}'.encode()).hexdigest()[:20]
   rows.append({
    'candidate_id':digest,'commentator':cid,'summary_candidate':sentence,'team':teams[0] if teams else None,
    'players':players,'topic':topic,'type':type_,'sentiment':sentiment,'strength':strength,'source':source['name'],
    'url':url,'confidence':source.get('trust',70),'discovered_at':datetime.now(timezone.utc).isoformat()
   })
 return rows

def run(limit_per_source=20):
 cfg=json.loads((Path(__file__).parent/'sources.json').read_text(encoding='utf-8'))
 allrows=[]
 for source in cfg['sources']:
  try:
   links=discover_index(source,limit_per_source)
   for u in links:
    try: allrows.extend(extract_url(u,source)); time.sleep(.35)
    except Exception as e: print('WARN article',u,e)
  except Exception as e: print('WARN source',source['id'],e)
 # exact candidate dedupe
 unique={r['candidate_id']:r for r in allrows}
 out=Path(__file__).parent/'candidates.json';out.write_text(json.dumps(list(unique.values()),ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'{len(unique)} candidate -> {out}')

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=20);a=ap.parse_args();run(a.limit)
