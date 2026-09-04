"""Resolve commentator portraits conservatively from verified public identities.
A picture is accepted only when an exact-name Wikipedia page, exact-name YouTube channel,
or public social profile title matches the commentator. Ambiguous article images are rejected;
initials remain the fallback instead of ever showing the wrong face.
"""
from __future__ import annotations
import html, json, re, unicodedata, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'; OUT=B/'commentator_photos.json'
ROSTER=json.loads((B/'commentator_roster.json').read_text())
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36'
ALLOWED=('youtube.com','www.youtube.com','instagram.com','www.instagram.com','x.com','twitter.com','tr.wikipedia.org')

def norm(value):
 value=unicodedata.normalize('NFKD',value or '').encode('ascii','ignore').decode().casefold()
 return re.sub(r'[^a-z0-9]+',' ',value).strip()

def identity_matches(name,title):
 n=norm(name);t=norm(title);tokens=[x for x in n.split() if len(x)>1]
 return len(tokens)>=2 and all(x in t.split() for x in tokens)

def exact_identity(name,title):
 return norm(name)==norm(title)

def fetch(url,timeout=9):
 req=Request(url,headers={'User-Agent':UA,'Accept-Language':'tr-TR,tr;q=0.9'})
 with urlopen(req,timeout=timeout) as r:return r.read().decode('utf-8','ignore'),r.geturl()

def get_json(url):
 raw,_=fetch(url);return json.loads(raw)

def wikipedia(name):
 q=urllib.parse.urlencode({'action':'query','generator':'search','gsrsearch':f'"{name}"','gsrnamespace':0,'gsrlimit':5,'prop':'pageimages|info','piprop':'thumbnail|original','pithumbsize':600,'inprop':'url','format':'json','origin':'*'})
 data=get_json('https://tr.wikipedia.org/w/api.php?'+q)
 pages=list(data.get('query',{}).get('pages',{}).values())
 pages.sort(key=lambda p:(0 if norm(p.get('title'))==norm(name) else 1,int(p.get('index',999))))
 for p in pages:
  title=p.get('title','')
  if not identity_matches(name,title):continue
  img=(p.get('thumbnail') or {}).get('source') or (p.get('original') or {}).get('source')
  if img:return {'photoURL':img,'photoSource':p.get('fullurl') or 'https://tr.wikipedia.org/','resolvedTitle':title,'verified_identity':True,'resolver':'wikipedia'}
 return None

def extract_initial_data(doc):
 markers=('var ytInitialData =','window["ytInitialData"] =','ytInitialData =')
 for marker in markers:
  pos=doc.find(marker)
  if pos<0:continue
  start=doc.find('{',pos+len(marker))
  if start<0:continue
  depth=0;quoted=False;esc=False
  for i in range(start,len(doc)):
   ch=doc[i]
   if quoted:
    if esc:esc=False
    elif ch=='\\':esc=True
    elif ch=='"':quoted=False
    continue
   if ch=='"':quoted=True
   elif ch=='{':depth+=1
   elif ch=='}':
    depth-=1
    if depth==0:
     try:return json.loads(doc[start:i+1])
     except Exception:break
 return None

def walk_channel_renderers(node):
 if isinstance(node,dict):
  cr=node.get('channelRenderer')
  if isinstance(cr,dict):yield cr
  for v in node.values():yield from walk_channel_renderers(v)
 elif isinstance(node,list):
  for v in node:yield from walk_channel_renderers(v)

def text_value(obj):
 if not isinstance(obj,dict):return ''
 if obj.get('simpleText'):return obj['simpleText']
 runs=obj.get('runs') or []
 return ''.join(x.get('text','') for x in runs if isinstance(x,dict)).strip()

def youtube_channel(name):
 query=urllib.parse.quote(name+' futbol yorumcu')
 try:doc,_=fetch('https://www.youtube.com/results?search_query='+query,timeout=10)
 except Exception:return None
 data=extract_initial_data(doc)
 if not data:return None
 for cr in walk_channel_renderers(data):
  title=text_value(cr.get('title'))
  if not exact_identity(name,title):continue
  thumbs=(cr.get('thumbnail') or {}).get('thumbnails') or []
  image=next((x.get('url') for x in reversed(thumbs) if x.get('url','').startswith('http')),None)
  channel_id=cr.get('channelId')
  if image and channel_id:
   return {'photoURL':image,'photoSource':f'https://www.youtube.com/channel/{channel_id}','resolvedTitle':title,'verified_identity':True,'resolver':'youtube_exact_channel'}
 return None

def meta(doc,key):
 patterns=[rf'<meta[^>]+(?:property|name)=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)',rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{re.escape(key)}["\']']
 for pattern in patterns:
  m=re.search(pattern,doc,re.I)
  if m:return html.unescape(m.group(1)).strip()
 return None

def page_title(doc):
 title=re.search(r'<title[^>]*>(.*?)</title>',doc,re.I|re.S)
 return meta(doc,'og:title') or (html.unescape(title.group(1)).strip() if title else '')

def search_public_profiles(name):
 query=urllib.parse.quote(f'"{name}" (YouTube OR Instagram OR X)')
 try:doc,_=fetch('https://html.duckduckgo.com/html/?q='+query)
 except Exception:return []
 urls=[]
 for href in re.findall(r'href=["\']([^"\']+)["\']',doc,re.I):
  href=html.unescape(href)
  if 'uddg=' in href:
   try:href=urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get('uddg',[href])[0]
   except Exception:pass
  host=urllib.parse.urlparse(href).netloc.casefold()
  if any(host==d or host.endswith('.'+d) for d in ALLOWED):urls.append(href)
 return list(dict.fromkeys(urls))[:4]

def public_profile(name):
 for url in search_public_profiles(name):
  try:doc,final=fetch(url);title=page_title(doc)
  except Exception:continue
  if not identity_matches(name,title):continue
  img=meta(doc,'og:image') or meta(doc,'twitter:image')
  if img and img.startswith('http'):
   return {'photoURL':img,'photoSource':final,'resolvedTitle':title,'verified_identity':True,'resolver':'public_profile'}
 return None

def resolve(name):
 for fn in (wikipedia,youtube_channel,public_profile):
  try:
   hit=fn(name)
   if hit:return hit
  except Exception:pass
 return None

def resolve_one(cid,name):return cid,name,resolve(name)

def main():
 previous={}
 if OUT.exists():
  try:previous=json.loads(OUT.read_text()).get('photos',{})
  except Exception:pass
 by_id={cid:name for cid,name,_ in ROSTER};photos={}
 for cid,row in previous.items():
  name=by_id.get(cid)
  if name and row.get('photoURL') and row.get('verified_identity') and identity_matches(name,row.get('resolvedTitle','')):photos[cid]=row
 pending=[(cid,name) for cid,name,_ in ROSTER if cid not in photos];found=0
 with ThreadPoolExecutor(max_workers=20) as pool:
  futures=[pool.submit(resolve_one,cid,name) for cid,name in pending]
  for f in as_completed(futures):
   cid,name,hit=f.result()
   if hit:photos[cid]=hit;found+=1
 OUT.write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'photos':photos},ensure_ascii=False,indent=2))
 counts={}
 for row in photos.values():counts[row.get('resolver','unknown')]=counts.get(row.get('resolver','unknown'),0)+1
 print('verified commentator photos',len(photos),'of',len(ROSTER),'new',found,'checked',len(pending),'by_resolver',counts)

if __name__=='__main__':main()
