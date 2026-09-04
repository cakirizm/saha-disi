"""Fetch 2026-27 Trendyol Super Lig fixtures from the official TFF fixture page.
Uses only the public TFF HTML and stores a compact structured cache for the app feed.
"""
from __future__ import annotations
import html, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "backend"
URL = "https://www.tff.org/default.aspx?ftxt=1&pageID=198"
UA = "Mozilla/5.0 (compatible; SahaDisi/1.0; +public-fixture-reader)"

ALIASES = {
    "GALATASARAY A.Ş.": "Galatasaray", "FENERBAHÇE A.Ş.": "Fenerbahçe",
    "BEŞİKTAŞ A.Ş.": "Beşiktaş", "TRABZONSPOR A.Ş.": "Trabzonspor",
    "SAMSUNSPOR A.Ş.": "Samsunspor", "GÖZTEPE A.Ş.": "Göztepe",
    "TÜMOSAN KONYASPOR": "Konyaspor", "ÇAYKUR RİZESPOR A.Ş.": "Rizespor",
    "KOCAELİSPOR": "Kocaelispor", "GENÇLERBİRLİĞİ": "Gençlerbirliği",
    "ARCA ÇORUM FK": "Çorum", "EYÜPSPOR": "Eyüpspor",
    "GAZİANTEP FUTBOL KULÜBÜ A.Ş.": "Gaziantep FK", "CORENDON ALANYASPOR": "Alanyaspor",
    "İSTANBUL BAŞAKŞEHİR FK": "Başakşehir", "KASIMPAŞA A.Ş.": "Kasımpaşa",
    "AMED SPORTİF FAALİYETLER": "Amed", "ERZURUMSPOR FK": "Erzurumspor",
}

def clean_team(s: str) -> str:
    s = " ".join(s.split()).strip(" -\t")
    return ALIASES.get(s, s.title())

def fetch() -> str:
    req = Request(URL, headers={"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9"})
    with urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")

def text_lines(doc: str) -> list[str]:
    doc = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", "", doc)
    txt = re.sub(r"(?s)<[^>]+>", "\n", doc)
    return [" ".join(html.unescape(x).replace("\xa0", " ").split()) for x in txt.splitlines() if x.strip()]

def parse(doc: str) -> list[dict]:
    lines = text_lines(doc)
    week = 0; rows = []; seen = set()
    week_re = re.compile(r"^(\d{1,2})\.\s*Hafta$", re.I)
    score_re = re.compile(r"^(.+?)\s+(\d+)\s*-\s*(\d+)\s+(.+)$")
    fixture_re = re.compile(r"^(.+?)\s+-\s+(.+)$")
    dt_re = re.compile(r"^(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})\s+(.+?)\s+-\s+(.+?)(?:\s+Detaylar)?$")
    dated = {}
    for line in lines:
        m = dt_re.match(line)
        if m:
            key = (clean_team(m.group(3)), clean_team(m.group(4)))
            dated[key] = f"{m.group(1)} {m.group(2)}"
    for line in lines:
        m = week_re.match(line)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 34: week = n
            continue
        if not week: continue
        hs = as_ = None; home = away = None
        m = score_re.match(line)
        if m:
            home, hs, as_, away = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        else:
            m = fixture_re.match(line)
            if m: home, away = m.group(1), m.group(2)
        if not home or not away: continue
        # Guard against menus/copy: require both sides to look like club names.
        if len(home) < 3 or len(away) < 3 or any(x in line.lower() for x in ["sezon", "devre", "puan", "fikstür"]): continue
        home, away = clean_team(home), clean_team(away.replace(" Detaylar", ""))
        key = (week, home.casefold(), away.casefold())
        if key in seen: continue
        seen.add(key)
        kickoff = dated.get((home, away), "")
        rows.append({
            "id": f"sl-2026-{week:02d}-{len(rows)+1:03d}", "league": "Trendyol Süper Lig",
            "week": week, "home": home, "away": away, "kickoff": kickoff,
            "home_score": hs, "away_score": as_, "image_url": None,
            "source": "TFF", "source_url": URL,
        })
    return rows

def main():
    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "source": URL, "matches": []}
    try:
        out["matches"] = parse(fetch())
    except Exception as e:
        old = B / "tff_fixtures.json"
        if old.exists():
            cached = json.loads(old.read_text())
            out["matches"] = cached.get("matches", [])
        out["error"] = str(e)[:300]
    (B / "tff_fixtures.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print("tff matches", len(out["matches"]))

if __name__ == "__main__": main()
