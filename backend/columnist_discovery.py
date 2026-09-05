"""Discover football columnists from publisher author indexes.

Publishers list their columnists on a single index page. Instead of hand-listing
authors in collector_v3.direct_sources(), this walks those indexes and keeps only
authors that actually pass the collector's own bar: a recent column whose body
yields football sentences. Politics/religion/lifestyle columnists on the same
index fail that test and are dropped.

Output is written to columnists.json and read by collector_v3; discovered names
are also merged into commentator_roster.json so the app can show them.
Run periodically (not hourly) - it fetches a few hundred pages.
"""
from __future__ import annotations
import json, random, re, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import collector_v3 as c
from article_content import article_content

B = Path(__file__).resolve().parent
MAX_AGE_DAYS = 45
MIN_SENTENCES = 3
RETIRE_DAYS = 120
REFRESH_DAYS = 3
# Index paths carry section links (/yazarlar/arsiv) alongside real author slugs.
SKIP_SLUGS = {
    'tum-yazarlar', 'gunun-yazarlari', 'bugunun-yazilari', 'arsiv', 'yazarlar', 'yazar',
    'spor', 'sabah', 'sabaharsiv', 'site', 'kitap', 'sandik', 'bolgeler', 'perspektif',
    'gunaydin', 'cumartesi', 'pazar', 'internet', 'erdem', 'hayri', 'ozgur', 'kadir',
    'mustafa', 'gurcan', 'gunen', 'abdullah', 'cevdet', 'emre', 'hakki', 'huseyin',
    'levent', 'necmi', 'serkan', 'sinan', 'turgay', 'ulas', 'zeki', 'bilgic', 'didin',
    'suat', 'tekin', 'uluc', 'urundul', 'murat', 'fdogan', 'dilmen-arsiv',
}

PUBLISHERS = [
    {'index': 'https://www.aspor.com.tr/yazarlar/tum-yazarlar', 'source': 'A Spor',
     'template': 'https://www.aspor.com.tr/yazarlar/{slug}/arsiv', 'trust': 98},
    {'index': 'https://www.fotomac.com.tr/yazarlar/tum-yazarlar', 'source': 'Fotomaç',
     'template': 'https://www.fotomac.com.tr/yazarlar/{slug}/arsiv', 'trust': 95},
    {'index': 'https://www.takvim.com.tr/yazarlar', 'source': 'Takvim',
     'template': 'https://www.takvim.com.tr/yazarlar/{slug}/arsiv', 'trust': 92},
    {'index': 'https://www.sabah.com.tr/spor/yazarlar', 'source': 'Sabah Spor',
     'template': 'https://www.sabah.com.tr/yazarlar/{slug}/arsiv', 'trust': 95},
    {'index': 'https://www.fanatik.com.tr/yazarlar', 'source': 'Fanatik',
     'template': 'https://www.fanatik.com.tr/yazarlar/{slug}', 'trust': 95},
]

NAME_NOISE = re.compile(
    r'\s*(tüm\s+)?(köşe\s+)?yazıları(nı)?\b.*$|\s*arşiv\b.*$|\s*yazarı\b.*$', re.I)


def polite_fetch(url, attempts=3):
    """Publishers answer 429 when walked quickly; back off instead of losing a source."""
    for attempt in range(attempts):
        try:
            return c.fetch(url)
        except Exception as exc:
            if '429' not in str(exc) or attempt == attempts - 1:
                raise
            time.sleep(2 * (attempt + 1) + random.random())
    raise RuntimeError('unreachable')


def slugs_of(publisher):
    """Author slugs on an index page (Turkuvaz renders the list from inline JSON)."""
    doc = polite_fetch(publisher['index'])
    found = re.findall(r'/yazarlar/([a-z0-9\-]{4,40})', doc)
    return sorted({s for s in found if s not in SKIP_SLUGS})


def display_name(doc, slug):
    # A Spor leaves og:title off and titles the page "Yazarlar"; its <h1> carries
    # the name with correct Turkish characters, which the slug cannot round-trip.
    for pattern in (r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
                    r'<h1[^>]*>(.*?)</h1>', r'<title>(.*?)</title>'):
        m = re.search(pattern, doc, re.I | re.S)
        if not m:
            continue
        name = c.repair_text(re.sub(r'<[^>]+>', ' ', m.group(1))).split('|')[0]
        name = NAME_NOISE.sub('', name).strip(' -–—')
        if 4 <= len(name) <= 40 and ' ' in name:
            return name
    return ' '.join(w.capitalize() for w in slug.split('-'))


def is_recent(published, now):
    try:
        stamp = datetime.fromisoformat(str(published).replace('Z', '+00:00'))
    except ValueError:
        return False
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp >= now - timedelta(days=MAX_AGE_DAYS)


def validate(job):
    """Keep an author only if a recent column of theirs yields football sentences."""
    publisher, slug = job
    url = publisher['template'].format(slug=slug)
    src = {'url': url, 'source': publisher['source'], 'trust': publisher['trust'],
           'cid': slug, 'byline': True}
    now = datetime.now(timezone.utc)
    try:
        doc = polite_fetch(url)
        links = c.discover(src, 3)
    except Exception:
        return None
    sentences = 0
    for article_url, _ in links[:2]:
        try:
            text, published = article_content(polite_fetch(article_url))
        except Exception:
            continue
        if not text or not published or not is_recent(published, now):
            continue
        sentences += len(c.byline_statements(text))
    # One stray football sentence is how politics columnists slip in; require a
    # column that is actually about football.
    if sentences < MIN_SENTENCES:
        return None
    return {'cid': slug, 'name': display_name(doc, slug), 'url': url,
            'source': publisher['source'], 'trust': publisher['trust'],
            'sample_sentences': sentences}


def load_existing():
    path = B / 'columnists.json'
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding='utf-8')).get('columnists', [])
    except Exception:
        return []


def kept(row, now):
    stamp = row.get('last_validated')
    if not stamp:
        return True
    try:
        seen = datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return seen >= now - timedelta(days=RETIRE_DAYS)


def merge_roster(columnists):
    """Discovered authors must exist in the roster or build_feed cannot name them."""
    path = B / 'commentator_roster.json'
    roster = json.loads(path.read_text(encoding='utf-8'))
    known = {row[0] for row in roster}
    added = [[col['cid'], col['name'], ['Genel']] for col in columnists if col['cid'] not in known]
    if added:
        path.write_text(json.dumps(roster + added, ensure_ascii=False, indent=1), encoding='utf-8')
    return len(added)


def due(days=REFRESH_DAYS):
    """Discovery walks a few hundred pages, so the hourly job skips it when fresh."""
    path = B / 'columnists.json'
    if not path.exists():
        return True
    try:
        stamp = json.loads(path.read_text(encoding='utf-8'))['generated_at']
        return datetime.fromisoformat(stamp) < datetime.now(timezone.utc) - timedelta(days=days)
    except Exception:
        return True


def run():
    jobs = []
    for publisher in PUBLISHERS:
        try:
            jobs += [(publisher, slug) for slug in slugs_of(publisher)]
        except Exception as exc:
            print('index failed', publisher['source'], str(exc)[:60])
    with ThreadPoolExecutor(max_workers=6) as pool:
        found = [row for row in pool.map(validate, jobs) if row]
    now = datetime.now(timezone.utc)
    for row in found:
        row['last_validated'] = now.date().isoformat()
    # A publisher answering 429 must not silently delete authors it validated
    # before, so a run merges into the previous list; entries that stop
    # re-validating for RETIRE_DAYS are dropped as genuinely stale.
    merged = {row['cid']: row for row in load_existing()}
    merged.update({row['cid']: row for row in found})
    columnists = sorted((row for row in merged.values() if kept(row, now)),
                        key=lambda row: (row['source'], row['cid']))
    (B / 'columnists.json').write_text(json.dumps(
        {'generated_at': now.isoformat(), 'columnists': columnists},
        ensure_ascii=False, indent=1), encoding='utf-8')
    added = merge_roster(columnists)
    print(f'columnists {len(columnists)} of {len(jobs)} candidates, roster +{added}')


if __name__ == '__main__':
    import sys
    if '--if-due' in sys.argv and not due():
        print('columnists.json still fresh, skipping discovery')
    else:
        run()
