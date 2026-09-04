"""Build reliable remote club crest URLs without paid APIs.

We use the Google favicon endpoint against each club's official domain. It is deliberately
simple: no scraping, no API key and no binary assets are copied into the repository.
"""
from __future__ import annotations
import json, urllib.parse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
DOMAINS={
 'Galatasaray':'galatasaray.org','Fenerbahçe':'fenerbahce.org','Beşiktaş':'bjk.com.tr','Trabzonspor':'trabzonspor.org.tr',
 'Samsunspor':'samsunspor.org.tr','Göztepe':'goztepe.org.tr','Konyaspor':'konyaspor.org.tr','Rizespor':'caykurrizespor.org.tr',
 'Kocaelispor':'kocaelispor.com.tr','Gençlerbirliği':'genclerbirligi.org.tr','Çorum FK':'corumfk.com.tr','Eyüpspor':'eyupspor.org.tr',
 'Gaziantep FK':'gaziantepfk.org','Alanyaspor':'alanyaspor.org.tr','Başakşehir':'ibfk.com.tr','Kasımpaşa':'kasimpasa.com.tr',
 'Amed SK':'amedspor.com.tr','Erzurumspor':'erzurumspor.org.tr'
}
ALIASES={
 'İstanbul Başakşehir':'Başakşehir','İstanbul Başakşehir FK':'Başakşehir','Tümosan Konyaspor':'Konyaspor',
 'Çaykur Rizespor':'Rizespor','Arca Çorum FK':'Çorum FK','Çorum':'Çorum FK','Gaziantep':'Gaziantep FK',
 'Gaziantep Futbol Kulübü':'Gaziantep FK','Amed Sportif Faaliyetler':'Amed SK','Erzurumspor FK':'Erzurumspor',
 'Corendon Alanyaspor':'Alanyaspor'
}

def logo(domain: str) -> str:
    return 'https://www.google.com/s2/favicons?domain='+urllib.parse.quote(domain)+'&sz=256'

def main():
    out={team:logo(domain) for team,domain in DOMAINS.items()}
    for alias,canonical in ALIASES.items(): out[alias]=out[canonical]
    (B/'team_logos.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print('team logos',len(out))

if __name__=='__main__':main()
