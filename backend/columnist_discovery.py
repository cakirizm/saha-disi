"""Discover football columnists from publisher author indexes.

Publishers list their columnists on a single index page. Instead of hand-listing
authors in collector_v3.direct_sources(), this walks those indexes and keeps only
authors that actually pass the collector's own bar: a recent column whose body
yields football sentences. Politics/religion/lifestyle columnists on the same
index fail that test and are dropped.

General newspapers (Hürriyet, Habertürk, Cumhuriyet...) list hundreds of
non-sports authors, so their indexes are not walked; only the author pages of
people already in the roster (TARGETED) are tried, under the same test.

Output is written to columnists.json and read by collector_v3; discovered names
are also merged into commentator_roster.json so the app can show them.
Run periodically (not hourly) - it fetches a few hundred pages.
"""
from __future__ import annotations
import json, re, unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import collector_v3 as c
from article_content import article_content
from feed_quality import has_broken_text

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
# Fotomaç and A Spor use slugs like "mustafa_culcu" and "serkan.korkmaz"; a
# hyphen-only pattern never tried those authors.
SLUG_RE = re.compile(r'/yazarlar/([a-z0-9][a-z0-9_.\-]{3,40})')
FILE_SUFFIX = re.compile(r'\.(html?|aspx?|php|jpe?g|png|webp|svg|css|js)$')

PUBLISHERS = [
    {'index': 'https://www.aspor.com.tr/yazarlar/tum-yazarlar', 'source': 'A Spor',
     'template': 'https://www.aspor.com.tr/yazarlar/{slug}/arsiv', 'trust': 98},
    {'index': 'https://www.fotomac.com.tr/yazarlar/tum-yazarlar', 'source': 'Fotomaç',
     'template': 'https://www.fotomac.com.tr/yazarlar/{slug}/arsiv', 'trust': 95},
    # Takvim was 92, below build_feed's 95 bar, so its validated columnists
    # (Serkan Korkmaz, Ulaş Özdemir, Abdullah Ercan...) never reached the feed.
    {'index': 'https://www.takvim.com.tr/yazarlar', 'source': 'Takvim',
     'template': 'https://www.takvim.com.tr/yazarlar/{slug}/arsiv', 'trust': 95},
    {'index': 'https://www.sabah.com.tr/spor/yazarlar', 'source': 'Sabah Spor',
     'template': 'https://www.sabah.com.tr/yazarlar/{slug}/arsiv', 'trust': 95},
    {'index': 'https://www.fanatik.com.tr/yazarlar', 'source': 'Fanatik',
     'template': 'https://www.fanatik.com.tr/yazarlar/{slug}', 'trust': 95},
    # Sports-only indexes: walking every author is cheap and finds no politics
    # columnists to filter out.
    {'index': 'https://www.ntvspor.net/yazarlar', 'source': 'NTV Spor',
     'template': 'https://www.ntvspor.net/yazarlar/{slug}', 'trust': 95},
    {'index': 'https://beinsports.com.tr/yazarlar', 'source': 'beIN SPORTS',
     'template': 'https://beinsports.com.tr/yazarlar/{slug}', 'trust': 95},
]

# Roster commentators who sign a column on a general newspaper, or whose slug
# the index walk cannot turn into their roster id (Sabah's "dilmen"). Found
# from each site's author index on 2026-11-16.
TARGETED_TRUST = 95
TARGETED = [
    ('Sabah Spor', 'https://www.sabah.com.tr/yazarlar/dilmen/arsiv', 'ridvan-dilmen'),
    ('Sabah Spor', 'https://www.sabah.com.tr/yazarlar/tekin/arsiv', 'metin-tekin'),
    ('Sabah Spor', 'https://www.sabah.com.tr/yazarlar/bilgic/arsiv', 'gurcan-bilgic'),
    ('Sabah Spor', 'https://www.sabah.com.tr/yazarlar/mustafa-culcu/arsiv', 'mustafa-culcu'),
    ('A Spor', 'https://www.aspor.com.tr/yazarlar/mustafa_culcu/arsiv', 'mustafa-culcu'),
    ('A Spor', 'https://www.aspor.com.tr/yazarlar/gurcan-bilgic/arsiv', 'gurcan-bilgic'),
    ('Hürriyet', 'https://www.hurriyet.com.tr/yazarlar/erman-toroglu/', 'erman-toroglu'),
    ('Hürriyet', 'https://www.hurriyet.com.tr/yazarlar/ali-naci-kucuk/', 'ali-naci-kucuk'),
    ('Hürriyet', 'https://www.hurriyet.com.tr/yazarlar/ahmet-ercanlar/', 'ahmet-ercanlar'),
    ('Hürriyet', 'https://www.hurriyet.com.tr/yazarlar/mehmet-ayan/', 'mehmet-ayan'),
    ('Hürriyet', 'https://www.hurriyet.com.tr/yazarlar/sinan-engin/', 'sinan-engin'),
    ('Hürriyet', 'https://www.hurriyet.com.tr/yazarlar/rustu-recber/', 'rustu-recber'),
    ('Hürriyet', 'https://www.hurriyet.com.tr/yazarlar/sergen-yalcin/', 'sergen-yalcin'),
    ('Hürriyet', 'https://www.hurriyet.com.tr/yazarlar/ogun-temizkanoglu/', 'ogun-temizkanoglu'),
    ('Hürriyet', 'https://www.hurriyet.com.tr/yazarlar/firat-aydinus/', 'firat-aydinus'),
    ('Hürriyet', 'https://www.hurriyet.com.tr/yazarlar/bunyamin-gezer/', 'bunyamin-gezer'),
    ('Hürriyet', 'https://www.hurriyet.com.tr/yazarlar/murat-fevzi-tanirli/', 'murat-fevzi-tanirli'),
    ('Hürriyet', 'https://www.hurriyet.com.tr/yazarlar/mehmet-arslan/', 'mehmet-arslan'),
    ('Hürriyet', 'https://www.hurriyet.com.tr/yazarlar/ismail-er/', 'ismail-er'),
    ('Habertürk', 'https://www.haberturk.com/htyazar/ibrahim-yildiz', 'ibrahim-yildiz'),
    ('Habertürk', 'https://www.haberturk.com/htyazar/mehmet-ayan', 'mehmet-ayan'),
    ('Habertürk', 'https://www.haberturk.com/htyazar/haluk-ayyildiz', 'haluk-ayyildiz'),
    ('Habertürk', 'https://www.haberturk.com/htyazar/ibrahim-akbulut', 'ibrahim-akbulut'),
    ('Habertürk', 'https://www.haberturk.com/htyazar/erhan-telli', 'erhan-telli'),
    ('Türkiye', 'https://www.turkiyegazetesi.com.tr/yazarlar/gokhan-karatas', 'gokhan-karatas'),
    ('Türkiye', 'https://www.turkiyegazetesi.com.tr/yazarlar/omer-faruk-unal', 'omer-faruk-unal'),
    ('Star', 'https://www.star.com.tr/yazarlar/aygun-ozipek/', 'aygun-ozipek'),
    ('Star', 'https://www.star.com.tr/yazarlar/ferudun-nigdelioglu/', 'feridun-nigdelioglu'),
    ('Ajansspor', 'https://ajansspor.com/yazarlar/aygun-ozipek', 'aygun-ozipek'),
    ('Sporx', 'https://www.sporx.com/yazar-altan-tanrikulu', 'altan-tanrikulu'),
    ('Yeni Şafak', 'https://www.yenisafak.com/yazarlar/oguz-altay', 'oguz-altay'),
    ('Cumhuriyet', 'https://www.cumhuriyet.com.tr/yazarlar/cumhur-onder-arslan', 'cumhur-onder-arslan'),
    ('Cumhuriyet', 'https://www.cumhuriyet.com.tr/yazarlar/hasan-al', 'hasan-al'),
    ('Akşam', 'https://www.aksam.com.tr/yazarlar/alen-markaryan/', 'alen-markaryan'),
    ('Milliyet Skorer', 'https://www.milliyet.com.tr/skorer/aksal-yavuz/', 'aksal-yavuz'),
    ('Karar', 'https://www.karar.com/yazarlar/ogulcan-coksayar', 'ogulcan-coksayar'),
    ('61saat', 'https://www.61saat.com/cagri-aktas', 'cagri-aktas'),
]

NAME_NOISE = re.compile(
    r'\s*(tüm\s+)?(köşe\s+)?yazıları(nı)?\b.*$|\s*arşiv\b.*$|\s*yazarı\b.*$', re.I)


def name_key(name):
    """Accent- and case-free key, so "Rıdvan Dilmen" and "RIDVAN DİLMEN" meet."""
    name = (name or '').replace('ı', 'i').replace('İ', 'i').casefold()
    return ''.join(ch for ch in unicodedata.normalize('NFKD', name) if ch.isalnum())


ROSTER_BY_NAME = {name_key(name): cid for cid, name in c.PEOPLE}


def slug_cid(slug):
    return re.sub(r'[_.]+', '-', slug).strip('-')


def author_cid(name, slug):
    """The roster id when the author is already tracked. Using the slug made
    beIN's "feyyazucar" a second Feyyaz Uçar beside the roster's feyyaz-ucar."""
    return ROSTER_BY_NAME.get(name_key(name)) or slug_cid(slug)


def slugs_of(publisher):
    """Author slugs on an index page (Turkuvaz renders the list from inline JSON)."""
    doc = c.fetch(publisher['index'])
    found = SLUG_RE.findall(doc)
    return sorted({s.rstrip('.') for s in found
                   if s not in SKIP_SLUGS and not FILE_SUFFIX.search(s)})


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
        # A wrongly decoded page must not put a garbled name in the roster.
        if 4 <= len(name) <= 40 and ' ' in name and not has_broken_text(name):
            return name
    return ' '.join(w.capitalize() for w in slug_cid(slug).split('-'))


def is_recent(published, now):
    try:
        stamp = datetime.fromisoformat(str(published).replace('Z', '+00:00'))
    except ValueError:
        return False
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp >= now - timedelta(days=MAX_AGE_DAYS)


def index_job(publisher, slug):
    return {'url': publisher['template'].format(slug=slug), 'source': publisher['source'],
            'trust': publisher['trust'], 'slug': slug, 'cid': None}


def targeted_jobs():
    return [{'url': url, 'source': source, 'trust': TARGETED_TRUST, 'slug': cid, 'cid': cid}
            for source, url, cid in TARGETED if cid in c.COMMENTATORS]


def football_sentences(src, now):
    sentences = 0
    for article_url, _ in c.discover(src, 3)[:2]:
        try:
            text, published = article_content(c.fetch(article_url))
        except Exception:
            continue
        if not text or not published or not is_recent(published, now):
            continue
        sentences += len(c.byline_statements(text))
    return sentences


def validate(job):
    """Keep an author only if a recent column of theirs yields football sentences."""
    src = {'url': job['url'], 'source': job['source'], 'trust': job['trust'],
           'cid': job['cid'] or job['slug'], 'byline': True}
    now = datetime.now(timezone.utc)
    try:
        doc = c.fetch(job['url'])
        sentences = football_sentences(src, now)
    except Exception:
        return None
    # One stray football sentence is how politics columnists slip in; require a
    # column that is actually about football.
    if sentences < MIN_SENTENCES:
        return None
    if job['cid']:
        cid, name = job['cid'], c.COMMENTATORS[job['cid']]
    else:
        name = display_name(doc, job['slug'])
        cid = author_cid(name, job['slug'])
        name = c.COMMENTATORS.get(cid, name)
    return {'cid': cid, 'name': name, 'url': job['url'], 'source': job['source'],
            'trust': job['trust'], 'sample_sentences': sentences}


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


def current_trust(row):
    """Rows validated before a publisher's trust changed keep the old value
    until they re-validate; the configured value is the one that counts."""
    for publisher in PUBLISHERS:
        if publisher['source'] == row.get('source'):
            return publisher['trust']
    return row.get('trust', TARGETED_TRUST)


def merge_roster(columnists):
    """Discovered authors must exist in the roster or build_feed cannot name them."""
    path = B / 'commentator_roster.json'
    roster = json.loads(path.read_text(encoding='utf-8'))
    known = {row[0] for row in roster}
    added = []
    for col in columnists:
        if col['cid'] not in known:
            known.add(col['cid'])
            added.append([col['cid'], col['name'], ['Genel']])
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


def merge(existing, found, now):
    """One commentator may sign on several sites (Rıdvan Dilmen: NTV Spor and
    Sabah), so rows are keyed by (cid, url), not by cid alone."""
    # A publisher answering 429 must not silently delete authors it validated
    # before, so a run merges into the previous list; entries that stop
    # re-validating for RETIRE_DAYS are dropped as genuinely stale.
    merged = {(row['cid'], row['url']): row for row in existing}
    merged.update({(row['cid'], row['url']): row for row in found})
    rows = [row for row in merged.values() if kept(row, now)]
    for row in rows:
        row['trust'] = current_trust(row)
    return sorted(rows, key=lambda row: (row['source'], row['cid'], row['url']))


def run():
    jobs = targeted_jobs()
    for publisher in PUBLISHERS:
        try:
            jobs += [index_job(publisher, slug) for slug in slugs_of(publisher)]
        except Exception as exc:
            print('index failed', publisher['source'], str(exc)[:60])
    with ThreadPoolExecutor(max_workers=6) as pool:
        found = [row for row in pool.map(validate, jobs) if row]
    now = datetime.now(timezone.utc)
    for row in found:
        row['last_validated'] = now.date().isoformat()
    columnists = merge(load_existing(), found, now)
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
