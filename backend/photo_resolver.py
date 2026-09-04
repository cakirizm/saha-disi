"""Resolve commentator portrait URLs from Wikimedia/Wikipedia public APIs.
No images are copied into the repository; the feed stores source URLs only.
"""
from __future__ import annotations
import json, time, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
UA='SahaDisi/1.0 public profile image resolver'
ROSTER=json.loads((B/'commentator_roster.json').read_text())
OUT=B/'commentator_photos.json'

def get_json(url):
    req=Request(url,headers={'User-Agent':UA,'Accept-Language':'tr'})
    with urlopen(req,timeout=12) as r:return json.loads(r.read().decode('utf-8','ignore'))

def resolve(name):
    q=urllib.parse.urlencode({'action':'query','generator':'search','gsrsearch':name,'gsrnamespace':0,'gsrlimit':3,'prop':'pageimages|info','piprop':'thumbnail|original','pithumbsize':480,'inprop':'url','format':'json','origin':'*'})
    data=get_json('https://tr.wikipedia.org/w/api.php?'+q)
    pages=list(data.get('query',{}).get('pages',{}).values())
    target=name.casefold()
    pages.sort(key=lambda p:(0 if p.get('title','').casefold()==target else 1, -int(p.get('index',0) or 0)))
    for p in pages:
        title=p.get('title','')
        if not title: continue
        # Reject obviously unrelated results. Exact title is preferred; otherwise require surname overlap.
        surname=name.split()[-1].casefold()
        if title.casefold()!=target and surname not in title.casefold(): continue
        img=(p.get('thumbnail') or {}).get('source') or (p.get('original') or {}).get('source')
        if img:
            return {'photoURL':img,'photoSource':p.get('fullurl') or 'https://tr.wikipedia.org/','resolvedTitle':title}
    return None

def main():
    previous={}
    if OUT.exists():
        try: previous=json.loads(OUT.read_text()).get('photos',{})
        except Exception: pass
    photos=dict(previous); checked=0; found=0
    for cid,name,_groups in ROSTER:
        if cid in photos and photos[cid].get('photoURL'): continue
        checked+=1
        try:
            hit=resolve(name)
            if hit: photos[cid]=hit; found+=1
        except Exception: pass
        time.sleep(.05)
    OUT.write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'photos':photos},ensure_ascii=False,indent=2))
    print('photos total',len(photos),'new',found,'checked',checked)

if __name__=='__main__': main()
