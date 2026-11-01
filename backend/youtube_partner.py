"""Partner YouTube collector. Runs on the project server, not on GitHub Actions.

YouTube answers 404 to datacenter runners such as GitHub Actions, so the hourly
CI job never reaches a single video. Channels that agreed to be quoted are read
here instead, from a host YouTube serves, and the result is pushed as
youtube_candidates.json for build_feed to merge.

Only sources marked "partner": true in sources.json are read.

Speaker rule: a clip titled "Nihat Kahveci: 31 Ekim'de Fenerbahçe havlu attı"
names its speaker. The title's quote must appear in the captions, and only the
caption segment containing it is attributed (YouTube marks a change of speaker
with ">>"). Anything else stays out, so a guest's words are never put in a
commentator's mouth.
"""
from __future__ import annotations
import hashlib, json, random, re, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import collector_v3 as c
from collector_v4 import CONFIG, youtube_entries
from feed_quality import mentioned_entities

B = Path(__file__).resolve().parent
OUT = B / 'youtube_candidates.json'
METHOD = 'partner_video_title_speaker'
MAX_AGE_DAYS = 45
MAX_SEEN = 3000
FETCH_BUDGET = 30          # YouTube requests per hourly run
PAUSE = 4                  # seconds, randomised up to twice this between requests
BLOCK_REST = timedelta(hours=6)


class Blocked(RuntimeError):
    """YouTube refused this host; stop instead of marking videos as done."""


def norm(text):
    return ' '.join(re.sub(r"[^\w\s]", ' ', (text or '').casefold()).split())


NAMES = {norm(name): cid for cid, name in c.PEOPLE}


def title_speaker(title):
    """Who the channel says is speaking, and the quote it puts in the title.

    "Nihat Kahveci: 31 Ekim'de ..."  -> ("nihat-kahveci", "31 Ekim'de ...")
    "Konu başlığı | Ali Ece"         -> ("ali-ece", None)  one name, no quote
    "Konu | Erman Yaşar & Emre Özcan" -> (None, None)      two speakers
    """
    m = re.match(r'^\s*([^:|]{3,40}?)\s*:\s*(.+)$', title or '')
    if m and NAMES.get(norm(m.group(1))):
        return NAMES[norm(m.group(1))], m.group(2)
    parts = [p.strip() for p in (title or '').split('|')]
    named = {NAMES[norm(p)] for p in parts[1:] if norm(p) in NAMES}
    if len(named) == 1 and not any(sep in p for p in parts[1:] for sep in ('&', ',', ' ve ')):
        return named.pop(), None
    return None, None


def segments(snippets):
    """Caption snippets grouped into speaker turns, each part keeping its start second."""
    turns = [[]]
    for start, text in snippets:
        pieces = text.split('>>')
        for i, piece in enumerate(pieces):
            if i > 0 and turns[-1]:
                turns.append([])
            if piece.strip():
                turns[-1].append((start, piece.strip()))
    return [t for t in turns if t]


def attributed_turn(snippets, title_quote):
    """The one speaker turn that contains the title's quote, or None.
    Without a quote the clip counts only if nobody else speaks in it at all."""
    if title_quote is None:
        turns = segments(snippets)
        return turns[0] if len(turns) == 1 else None
    words = norm(title_quote).split()
    if len(words) < 4:
        return None
    anchor = ' '.join(words[:4])
    hits = [t for t in segments(snippets) if anchor in norm(' '.join(p for _, p in t))]
    return hits[0] if len(hits) == 1 else None


def second_of(turn, sentence):
    lead = ' '.join(norm(sentence).split()[:3])
    for start, text in turn:
        if lead and lead in norm(text):
            return int(start)
    return int(turn[0][0])


def statements_from(video, source, cid, turn, caption_kind, now):
    rows = []
    text = ' '.join(p for _, p in turn)
    for sentence in c.byline_statements(text):
        t = second_of(turn, sentence)
        url = f"https://www.youtube.com/watch?v={video['id']}&t={t}s"
        teams = mentioned_entities(sentence, c.TEAMS)
        typ, topic, sent, strength = c.classify(sentence)
        rows.append({
            'candidate_id': hashlib.sha256(f"{cid}|{sentence.casefold()}".encode('utf-8')).hexdigest()[:20],
            'commentator': cid, 'summary_candidate': sentence,
            'team': teams[0] if len(teams) == 1 else None,
            'players': mentioned_entities(sentence, c.PLAYERS),
            'topic': topic, 'type': typ, 'sentiment': sent, 'strength': strength,
            'source': source['name'], 'url': url, 'image_url': None, 'confidence': 95,
            'direct_quote': True, 'published_at': video['published_at'], 'discovered_at': now.isoformat(),
            'evidence': {'version': 2, 'method': METHOD, 'speaker_id': cid, 'url': url,
                         'video_id': video['id'], 'title': video['title'], 'caption': caption_kind,
                         'published_at': video['published_at']}})
    return rows


PAGE_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36',
                'Accept-Language': 'tr-TR,tr;q=0.9'}


def page(url):
    from urllib.request import Request, urlopen
    with urlopen(Request(url, headers=PAGE_HEADERS), timeout=20) as r:
        return r.read().decode('utf-8', 'replace')


def initial_data(html):
    m = re.search(r'var ytInitialData\s*=\s*(\{.*?\});\s*</script>', html, re.S)
    return json.loads(m.group(1)) if m else {}


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def text_of(value):
    if isinstance(value, dict):
        if 'simpleText' in value:
            return value['simpleText']
        if 'runs' in value:
            return ''.join(r.get('text', '') for r in value['runs'])
        if 'content' in value:
            return value['content']
    return ''


def page_videos(channel_url):
    """(id, title) from the channel's Videos and Shorts tabs. YouTube's RSS feed
    has been answering 404 for long stretches, the channel pages keep working."""
    base = channel_url.rstrip('/')
    found = {}
    for tab in ('shorts', 'videos'):
        try:
            data = initial_data(page(f'{base}/{tab}'))
        except Exception:
            continue
        for node in walk(data):
            if 'videoRenderer' in node and isinstance(node['videoRenderer'], dict):
                v = node['videoRenderer']
                found.setdefault(v.get('videoId'), text_of(v.get('title')))
            if 'lockupViewModel' in node and isinstance(node['lockupViewModel'], dict):
                v = node['lockupViewModel']
                meta = ((v.get('metadata') or {}).get('lockupMetadataViewModel') or {})
                if 'VIDEO' in str(v.get('contentType', '')) or 'SHORTS' in str(v.get('contentType', '')):
                    found.setdefault(v.get('contentId'), text_of(meta.get('title')))
            if 'shortsLockupViewModel' in node:
                v = node['shortsLockupViewModel']
                vid = str(v.get('entityId', '')).replace('shorts-shelf-item-', '')
                found.setdefault(vid, text_of((v.get('overlayMetadata') or {}).get('primaryText')))
    return [(vid, title) for vid, title in found.items() if vid and len(vid) == 11 and title]


def publish_date(video_id):
    html = page('https://www.youtube.com/watch?v=' + video_id)
    m = re.search(r'"(?:publishDate|uploadDate)":"([^"]+)"', html)
    return m.group(1) if m else None


def channel_videos(source, seen):
    """Unseen videos of a partner channel. The publish date comes free from RSS;
    from the channel page it costs a request, so it is fetched later and only
    for clips that name their speaker."""
    videos, error = [], None
    try:
        videos, error = youtube_entries(source)
    except Exception as exc:
        error = str(exc)[:80]
    if videos:
        return [v for v in videos if v['id'] not in seen], None
    listed = [{'id': vid, 'title': title, 'published_at': None}
              for vid, title in page_videos(source['url']) if vid not in seen]
    return listed, (None if listed else error)


def captions(api, video_id):
    """[(start, text)] of the Turkish track and whether it is auto-generated."""
    from youtube_transcript_api import _errors as E
    blocked = tuple(getattr(E, n) for n in ('RequestBlocked', 'IpBlocked') if hasattr(E, n))
    try:
        track = api.list(video_id).find_transcript(['tr'])
        fetched = track.fetch()
    except blocked as exc:
        raise Blocked(str(exc)[:200])
    except Exception:
        return None, None
    return [(s.start, s.text) for s in fetched], ('auto' if track.is_generated else 'manual')


def load():
    if OUT.exists():
        try:
            return json.loads(OUT.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {'seen_videos': [], 'candidates': []}


def recent(published, now):
    try:
        stamp = datetime.fromisoformat(str(published).replace('Z', '+00:00'))
    except ValueError:
        return False
    return stamp >= now - timedelta(days=MAX_AGE_DAYS)


def run(only=None, force=False, ignore_rest=False, budget=None):
    """One polite pass. YouTube blocked the server after ~600 requests in ten
    minutes, so a run now spends at most FETCH_BUDGET requests, only on clips
    whose title names a speaker, pauses between them, keeps whatever it found
    when blocked and then rests for BLOCK_REST before trying again."""
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    now = datetime.now(timezone.utc)
    state = load()
    rest = state.get('blocked_until')
    # The rest note is about the server's IP; a run from another connection ignores it.
    if rest and not ignore_rest and datetime.fromisoformat(rest) > now:
        print(f'YouTube engeli sonrası bekleniyor: {rest}')
        return
    seen = set(state.get('seen_videos', []))
    rows = {r['candidate_id']: r for r in state.get('candidates', []) if recent(r.get('published_at'), now)}
    partners = [s for s in CONFIG if (s.get('partner') or force) and (only is None or s.get('id') == only)]
    budget, blocked_until, report = budget or FETCH_BUDGET, None, []
    try:
        for source in partners:
            videos, error = channel_videos(source, seen)
            found = 0
            for video in videos:
                cid, quote = title_speaker(video['title'])
                if not cid:
                    seen.add(video['id'])
                    continue
                if budget <= 0:
                    break
                if not video['published_at']:
                    budget -= 1
                    try:
                        video['published_at'] = publish_date(video['id'])
                    except Exception:
                        continue
                    time.sleep(PAUSE + random.random() * PAUSE)
                if not video['published_at'] or not recent(video['published_at'], now):
                    seen.add(video['id'])
                    continue
                budget -= 1
                snippets, kind = captions(api, video['id'])
                turn = attributed_turn(snippets, quote) if snippets else None
                for row in (statements_from(video, source, cid, turn, kind, now) if turn else []):
                    rows[row['candidate_id']] = row
                    found += 1
                seen.add(video['id'])
                time.sleep(PAUSE + random.random() * PAUSE)
            report.append(f"{source['name']}: {found} söz" + (f" (hata: {error})" if error else ''))
            # systemd buffers a non-interactive stdout; flush so the journal shows progress per channel.
            print(report[-1], flush=True)
    except Blocked as exc:
        blocked_until = (now + BLOCK_REST).isoformat()
        print(f'YouTube bu bağlantının IP adresini engelledi, {blocked_until} saatine kadar bekleniyor. Bulunanlar kaydedildi.', flush=True)
    body = {'seen_videos': sorted(seen)[-MAX_SEEN:],
            'candidates': sorted(rows.values(), key=lambda r: r['published_at'], reverse=True),
            'blocked_until': blocked_until}
    # Rewrite only on a real change: a fresh timestamp alone would make the
    # server push an empty commit every hour.
    if any(state.get(k) != v for k, v in body.items()) or not OUT.exists():
        OUT.write_text(json.dumps({'generated_at': now.isoformat(), **body}, ensure_ascii=False, indent=1), encoding='utf-8')
    if not partners:
        print('izinli (partner) kanal tanımlı değil')
    print(f'youtube_candidates: {len(rows)} | bu çalışmada kalan istek hakkı: {max(budget, 0)}')


if __name__ == '__main__':
    arg = lambda name: sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None
    run(arg('--source'), ignore_rest='--ignore-rest' in sys.argv,
        budget=int(arg('--budget')) if arg('--budget') else None)
