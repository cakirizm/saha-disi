"""Resolve commentator portraits only when identity can be validated by page title.
Wrong faces are worse than initials, so ambiguous search results are rejected.
"""
from __future__ import annotations
import json, re, time, unicodedata, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
UA='SahaDisi/1.2 verified public profile image resolver'
ROSTER=json.loads((B/'commentator_roster.json').read_text())
OUT=B/'commentator_photos.json'

def get_json(url):
    req=Request(url,headers={'User-Agent':UA,'Accept-Language':'tr'})
    with urlopen(req,timeout=12) as r:return json.loads(r.read().decode('utf-8','ignore'))

def norm(value):
    value=unicodedata.normalize('NFKD', value or '').encode('ascii','ignore').decode().casefold()
    return re.sub(r'[^a-z0-9]+',' ',value).strip()

def identity_matches(name,title):
    n=norm(name); t=norm(title)
    if not n or not t:return False
    if n==t:return True
    tokens=[x for x in n.split() if len(x)>1]
    # All name tokens must exist in the resolved title; surname-only matches caused wrong people.
    return len(tokens)>=2 and all(x in t.split() for x in tokens)

def resolve(name):
    q=urllib.parse.urlencode({'action':'query','generator':'search','gsrsearch':f'"{name}"','gsrnamespace':0,'gsrlimit':5,'prop':'pageimages|info','piprop':'thumbnail|original','pithumbsize':480,'inprop':'url','format':'json','origin':'*'})
    data=get_json('https://tr.wikipedia.org/w/api.php?'+q)
    pages=list(data.get('query',{}).get('pages',{}).values())
    pages.sort(key=lambda p:(0 if norm(p.get('title'))==norm(name) else 1, int(p.get('index',999))))
    for p in pages:
        title=p.get('title','')
        if not identity_matches(name,title): continue
        img=(p.get('thumbnail') or {}).get('source') or (p.get('original') or {}).get('source')
        if img:
            return {'photoURL':img,'photoSource':p.get('fullurl') or 'https://tr.wikipedia.org/','resolvedTitle':title,'verified_identity':True}
    return None

def main():
    previous={}
    if OUT.exists():
        try: previous=json.loads(OUT.read_text()).get('photos',{})
        except Exception: pass
    photos={}; checked=0; found=0
    by_id={cid:name for cid,name,_groups in ROSTER}
    for cid,row in previous.items():
        name=by_id.get(cid)
        if name and row.get('photoURL') and row.get('verified_identity') and identity_matches(name,row.get('resolvedTitle','')):
            photos[cid]=row
    for cid,name,_groups in ROSTER:
        if cid in photos: continue
        checked+=1
        try:
            hit=resolve(name)
            if hit: photos[cid]=hit; found+=1
        except Exception: pass
        time.sleep(.05)
    OUT.write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'photos':photos},ensure_ascii=False,indent=2))
    print('verified photos total',len(photos),'new',found,'checked',checked)

if __name__=='__main__': main()
