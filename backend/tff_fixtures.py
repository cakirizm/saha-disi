"""Fetch the 2026-27 Trendyol Super Lig fixture from official TFF pages.
The parser tries both table-preserving and text-node strategies and never overwrites a healthier cache.
"""
from __future__ import annotations
import html, json, re, unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
URLS=['https://www.tff.org/default.aspx?pageID=198','https://www.tff.org/default.aspx?ftxt=1&pageID=198']
UA='Mozilla/5.0 (compatible; SahaDisi/1.3; official-fixture-reader)'
ALIASES={
 'GALATASARAY A.Ş.':'Galatasaray','FENERBAHÇE A.Ş.':'Fenerbahçe','BEŞİKTAŞ A.Ş.':'Beşiktaş','TRABZONSPOR A.Ş.':'Trabzonspor',
 'SAMSUNSPOR A.Ş.':'Samsunspor','GÖZTEPE A.Ş.':'Göztepe','TÜMOSAN KONYASPOR':'Konyaspor','KONYASPOR':'Konyaspor',
 'ÇAYKUR RİZESPOR A.Ş.':'Rizespor','KOCAELİSPOR':'Kocaelispor','GENÇLERBİRLİĞİ':'Gençlerbirliği','ARCA ÇORUM FK':'Çorum FK','ÇORUM FK':'Çorum FK',
 'EYÜPSPOR':'Eyüpspor','GAZİANTEP FUTBOL KULÜBÜ A.Ş.':'Gaziantep FK','CORENDON ALANYASPOR':'Alanyaspor','İSTANBUL BAŞAKŞEHİR FK':'Başakşehir',
 'KASIMPAŞA A.Ş.':'Kasımpaşa','AMED SPORTİF FAALİYETLER':'Amed SK','ERZURUMSPOR FK':'Erzurumspor'}

class Parser(HTMLParser):
    def __init__(self): super().__init__(); self.rows=[]; self.row=None; self.cell=None; self.nodes=[]
    def handle_starttag(self,t,a):
        if t=='tr': self.row=[]
        elif t in {'td','th'} and self.row is not None: self.cell=[]
    def handle_data(self,d):
        x=' '.join(html.unescape(d).replace('\xa0',' ').split())
        if not x:return
        self.nodes.append(x)
        if self.cell is not None:self.cell.append(x)
    def handle_endtag(self,t):
        if t in {'td','th'} and self.cell is not None:
            self.row.append(' '.join(self.cell)); self.cell=None
        elif t=='tr' and self.row is not None:
            if self.row:self.rows.append(self.row)
            self.row=None

def clean_team(s):
    s=' '.join(html.unescape(s).replace('\xa0',' ').split()).strip(' -\t')
    return ALIASES.get(s,s.title())

def slug(s):
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')

def fetch(url):
    req=Request(url,headers={'User-Agent':UA,'Accept-Language':'tr-TR,tr;q=0.9'})
    with urlopen(req,timeout=30) as r:return r.read().decode('utf-8','ignore')

def split_match(text):
    text=text.replace(' Detaylar','').strip()
    m=re.match(r'^(.+?)\s+(\d{1,2})\s*-\s*(\d{1,2})\s+(.+)$',text)
    if m:return m.group(1),m.group(4),int(m.group(2)),int(m.group(3))
    m=re.match(r'^(.+?)\s+-\s+(.+)$',text)
    if m:return m.group(1),m.group(2),None,None
    return None

def parse(doc):
    p=Parser(); p.feed(doc); out=[]; current_week=None; dates={}
    all_text=[' '.join(r) for r in p.rows] + p.nodes
    for text in all_text:
        dm=re.search(r'(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})\s+(.+?)\s+-\s+(.+?)(?:\s+Detaylar)?$',text)
        if dm: dates[(clean_team(dm.group(3)),clean_team(dm.group(4)))]=f'{dm.group(1)} {dm.group(2)}'
    for text in all_text:
        wm=re.fullmatch(r'.*?(\d{1,2})\s*\.\s*Hafta.*?',text,re.I)
        if wm:
            n=int(wm.group(1)); current_week=n if 1<=n<=34 else current_week; continue
        if not current_week: continue
        match=split_match(text)
        if not match: continue
        home,away,hs,as_=match; home=clean_team(home); away=clean_team(away)
        if len(home)<3 or len(away)<3:continue
        out.append({'week':current_week,'home':home,'away':away,'home_score':hs,'away_score':as_,'kickoff':dates.get((home,away),'')})
    unique={}
    for r in out: unique[(r['week'],r['home'].casefold(),r['away'].casefold())]=r
    rows=list(unique.values())
    result=[]
    for r in sorted(rows,key=lambda x:(x['week'],x['kickoff'],x['home'])):
        result.append({'id':f"sl-2026-{r['week']:02d}-{slug(r['home'])}-{slug(r['away'])}",'league':'Trendyol Süper Lig','week':r['week'],'home':r['home'],'away':r['away'],'kickoff':r['kickoff'],'home_score':r['home_score'],'away_score':r['away_score'],'image_url':None,'source':'TFF','source_url':URLS[0]})
    return result

def main():
    p=B/'tff_matches.json'; old=[]
    if p.exists():
        try:old=json.loads(p.read_text())
        except Exception:pass
    best=[]; errors=[]
    for url in URLS:
        try:
            rows=parse(fetch(url))
            if len(rows)>len(best):best=rows
        except Exception as e: errors.append(str(e)[:100])
    # A Süper Lig season should be hundreds of matches. Never publish a tiny/partial parse.
    rows=best if len(best)>=250 else old
    p.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    print('tff matches',len(rows),'weeks',len(set(x.get('week') for x in rows)),'best_parse',len(best),'errors',errors)

if __name__=='__main__':main()
