"""Resolve free-licensed player photos from Wikimedia.

Only Wikipedia/Wikimedia images are used (freely licensed). Results are cached in
player_photos.json so a name is looked up once and reused.
"""
from __future__ import annotations
import json, time, urllib.parse, urllib.request
from pathlib import Path

B = Path(__file__).resolve().parent
UA = {'User-Agent': 'SahaDisi/1.0 (football commentary app; contact via github)'}


def _get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode('utf-8'))


def find_photo(name, lang='tr'):
    api = f'https://{lang}.wikipedia.org/w/api.php'
    query = {
        'action': 'query', 'format': 'json', 'generator': 'search',
        'gsrsearch': f'{name} futbolcu', 'gsrlimit': 1,
        'prop': 'pageimages', 'piprop': 'thumbnail|original', 'pithumbsize': 400,
    }
    try:
        data = _get_json(api + '?' + urllib.parse.urlencode(query))
    except Exception:
        return None
    for page in ((data.get('query') or {}).get('pages') or {}).values():
        thumb = (page.get('thumbnail') or {}).get('source') or (page.get('original') or {}).get('source')
        if thumb:
            return thumb
    return None


def run():
    feed = json.loads((B / 'feed.json').read_text(encoding='utf-8')) if (B / 'feed.json').exists() else {}
    names = {pl for s in feed.get('statements', []) for pl in s.get('players', []) if pl}
    names |= {p['name'] for p in feed.get('players', []) if p.get('name')}

    path = B / 'player_photos.json'
    cache = {}
    if path.exists():
        try:
            cache = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            cache = {}

    for name in sorted(names):
        if cache.get(name):
            continue
        photo = find_photo(name) or find_photo(name, lang='en')
        if photo:
            cache[name] = photo
        time.sleep(0.3)

    # Manual corrections win: a name mapped to a URL is pinned; mapped to "" is
    # suppressed (used for ambiguous names Wikipedia resolves to the wrong person).
    overrides_path = B / 'player_photo_overrides.json'
    if overrides_path.exists():
        try:
            for name, value in json.loads(overrides_path.read_text(encoding='utf-8')).items():
                if value:
                    cache[name] = value
                else:
                    cache.pop(name, None)
        except Exception:
            pass

    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')
    found = len([v for v in cache.values() if v])
    print(f'player photos {found} of {len(names)}')


if __name__ == '__main__':
    run()
