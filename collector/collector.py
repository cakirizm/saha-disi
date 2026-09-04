"""Saha Dışı Collector V1

Amaç: tanımlı kamuya açık kaynak URL'lerinden aday metinleri toplamak,
yorumcu/takım/oyuncu etiketleriyle normalize etmek ve seed benzeri JSON üretmek.
Bu dosya internete erişebilen bir sunucuda çalıştırılmak üzere hazırlanmıştır.
"""
from __future__ import annotations
import argparse, hashlib, json, re, time
from dataclasses import dataclass, asdict
from datetime import datetime
from urllib.request import Request, urlopen
from html.parser import HTMLParser

UA="Mozilla/5.0 (compatible; SahaDisiCollector/0.1; +https://example.invalid)"

COMMENTATORS={
 "Ahmet Çakar":{"id":"ahmet-cakar","aliases":["Ahmet Çakar"]},
 "Mustafa Çulcu":{"id":"mustafa-culcu","aliases":["Mustafa Çulcu"]},
 "Nihat Kahveci":{"id":"nihat-kahveci","aliases":["Nihat Kahveci"]},
 "Ali Ece":{"id":"ali-ece","aliases":["Ali Ece"]},
 "Serdar Ali Çelikler":{"id":"serdar-ali-celikler","aliases":["Serdar Ali Çelikler","SAÇ"]},
}
TEAMS=["Galatasaray","Fenerbahçe","Beşiktaş","Trabzonspor"]
PLAYERS=["Osimhen","Sane","Barış Alper","Yunus","Talisca","Greenwood","Asensio","Kerem","Skriniar"]

class TextExtractor(HTMLParser):
 def __init__(self): super().__init__(); self.skip=0; self.parts=[]
 def handle_starttag(self, tag, attrs):
  if tag in {"script","style","nav","footer","header"}: self.skip+=1
 def handle_endtag(self, tag):
  if tag in {"script","style","nav","footer","header"} and self.skip: self.skip-=1
 def handle_data(self, data):
  if not self.skip:
   t=" ".join(data.split())
   if len(t)>2:self.parts.append(t)

@dataclass
class Candidate:
 url:str; commentator:str; title:str; text:str; discovered_at:str; content_hash:str

def fetch(url:str)->str:
 req=Request(url,headers={"User-Agent":UA})
 with urlopen(req,timeout=20) as r:return r.read().decode("utf-8","ignore")

def clean_text(html:str)->str:
 p=TextExtractor(); p.feed(html); return "\n".join(p.parts)

def title_of(html:str)->str:
 m=re.search(r"<title[^>]*>(.*?)</title>",html,re.I|re.S)
 return re.sub(r"\s+"," ",m.group(1)).strip() if m else ""

def detect_commentator(text:str):
 low=text.casefold()
 for name,cfg in COMMENTATORS.items():
  if any(a.casefold() in low for a in cfg["aliases"]):return cfg["id"]
 return None

def tags(text:str):
 low=text.casefold()
 return {
  "teams":[x for x in TEAMS if x.casefold() in low],
  "players":[x for x in PLAYERS if x.casefold() in low]
 }

def collect(urls):
 out=[]
 for url in urls:
  try:
   html=fetch(url); text=clean_text(html); c=detect_commentator(text)
   if not c: continue
   digest=hashlib.sha256(text.encode()).hexdigest()[:24]
   out.append(Candidate(url,c,title_of(html),text[:14000],datetime.utcnow().isoformat()+"Z",digest))
   time.sleep(1.0)
  except Exception as e: print(f"WARN {url}: {e}")
 return out

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("urls",nargs="*"); ap.add_argument("--out",default="candidates.json"); args=ap.parse_args()
 rows=collect(args.urls)
 payload=[]
 for r in rows:
  d=asdict(r); d.update(tags(r.text)); payload.append(d)
 with open(args.out,"w",encoding="utf-8") as f:json.dump(payload,f,ensure_ascii=False,indent=2)
 print(f"{len(payload)} aday kayıt yazıldı -> {args.out}")
if __name__=="__main__":main()
