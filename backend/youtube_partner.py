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
import hashlib, json, os, random, re, sys, time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from datetime import datetime, timedelta, timezone
from pathlib import Path

import collector_v3 as c
from collector_v4 import CONFIG, youtube_entries
from feed_quality import mentioned_entities

B = Path(__file__).resolve().parent
OUT = B / 'youtube_candidates.json'
METHOD = 'partner_video_title_speaker'
MAX_AGE_DAYS = 45
# Captions cost a credit each; a clip older than this is no longer today's
# conversation and would only spend credits on yesterday's news.
VIDEO_MAX_AGE_DAYS = 5
MAX_SEEN = 3000
FETCH_BUDGET = 30          # YouTube requests per hourly run
PAUSE = 4                  # seconds, randomised up to twice this between requests
BLOCK_REST = timedelta(hours=6)


TRANSCRIPT_API = 'https://transcript-yt.com/v1'
YOUTUBE_API = 'https://www.googleapis.com/youtube/v3'


def key(name):
    """API keys live in the environment (GitHub secret, /etc/sahadisi.env), never in the repo."""
    return os.environ.get(name, '').strip()


class Blocked(RuntimeError):
    """Stop this run without marking the current video as done, and rest a while."""

    def __init__(self, message, rest=BLOCK_REST):
        super().__init__(message)
        self.rest = rest


def norm(text):
    return ' '.join(re.sub(r"[^\w\s]", ' ', (text or '').casefold()).split())


NAMES = {norm(name): cid for cid, name in c.PEOPLE}


def title_speaker(title, own=None):
    """Who the channel says is speaking, and the quote it puts in the title.

    "Nihat Kahveci: 31 Ekim'de ..."  -> ("nihat-kahveci", "31 Ekim'de ...")
    "Konu başlığı | Ali Ece"         -> ("ali-ece", None)  one name, no quote
    "Konu | Erman Yaşar & Emre Özcan" -> (None, None)      two speakers

    A name after "|" only counts as the speaker when it is the last part and one
    of the channel's own commentators: "Galatasaray'da Neler Oluyor? | Sergen
    Yalçın" on a show is a clip about him, not by him.
    """
    m = re.match(r'^\s*([^:|]{3,40}?)\s*:\s*(.+)$', title or '')
    if m and NAMES.get(norm(m.group(1))):
        return NAMES[norm(m.group(1))], m.group(2)
    parts = [p.strip() for p in (title or '').split('|')]
    last = parts[-1] if len(parts) > 1 else ''
    cid = NAMES.get(norm(last))
    if cid and own and cid in own and not any(sep in last for sep in ('&', ',', ' ve ')):
        return cid, None
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


_last_call = [0.0]
MIN_INTERVAL = 7.0   # seconds; the free plan allows 10 requests a minute


def transcript_api(path, **params):
    """GET a TranscriptYT endpoint. It fetches from its own infrastructure, so
    YouTube's block on our IP does not apply; failed calls are not billed.
    Calls are spaced to stay under the plan's per-minute limit, and a 429 is
    waited out once (Retry-After) before the run gives up."""
    for attempt in (1, 2):
        wait = _last_call[0] + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.monotonic()
        try:
            return _transcript_get(path, params)
        except HTTPError as exc:
            if exc.code == 429 and attempt == 1:
                time.sleep(min(int(exc.headers.get('Retry-After') or 30), 60))
                continue
            return _transcript_error(exc)


def _transcript_get(path, params):
    req = Request(f"{TRANSCRIPT_API}/{path}?{urlencode(params)}",
                  headers={'Authorization': 'Bearer ' + key('TRANSCRIPT_API_KEY'),
                           'Accept': 'application/json', 'User-Agent': 'SahaDisi/1.0'})
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def _transcript_error(exc):
    if exc.code == 402:
        raise Blocked('TranscriptYT kredisi bitti', rest=timedelta(hours=12))
    if exc.code == 401:
        raise Blocked('TranscriptYT anahtarı geçersiz', rest=timedelta(hours=12))
    if exc.code in (429, 503):
        raise Blocked(f'TranscriptYT {exc.code}, bir sonraki çalışmada tekrar denenecek', rest=None)
    if exc.code in (400, 404):
        return None
    raise exc


def published_dates(video_ids):
    """Upload time per video from the official YouTube Data API: 1 quota unit per
    50 videos, and an API key is never IP-blocked the way page requests are."""
    dates = {}
    ids = [v for v in video_ids if v]
    for i in range(0, len(ids), 50):
        query = urlencode({'part': 'snippet', 'id': ','.join(ids[i:i + 50]), 'key': key('YOUTUBE_API_KEY'),
                           'fields': 'items(id,snippet/publishedAt)'})
        try:
            with urlopen(Request(f'{YOUTUBE_API}/videos?{query}'), timeout=30) as r:
                for item in json.loads(r.read().decode('utf-8')).get('items', []):
                    dates[item['id']] = item['snippet']['publishedAt']
        except Exception:
            continue
    return dates


def api_channel_videos(source, seen):
    listing = transcript_api('playlist', url=source['url'], limit=50) or {}
    videos = [{'id': v.get('videoId'), 'title': v.get('title') or '', 'published_at': None}
              for v in listing.get('videos', []) if v.get('videoId') and v.get('videoId') not in seen]
    # Dates only matter for clips we may quote, and the batch call is cheap.
    if key('YOUTUBE_API_KEY'):
        dates = published_dates([v['id'] for v in videos if title_speaker(v['title'], source.get('commentators'))[0]])
        for v in videos:
            v['published_at'] = dates.get(v['id'])
    return videos, (None if listing else 'liste alınamadı')


def api_captions(video_id):
    """Turkish captions only: a machine translation is not the speaker's words,
    and mode=captions never pays per-minute AI transcription for long shows."""
    data = transcript_api('transcript', url=video_id, language='tr', originalLanguage='true', mode='captions')
    if not data or data.get('translated') or str(data.get('language', '')).split('-')[0] != 'tr':
        return None, None
    segs = [(float(x.get('start', 0)), x.get('text', '')) for x in data.get('segments', []) if x.get('text')]
    return (segs or None), ('auto' if data.get('autoGenerated') else 'manual')


def channel_videos(source, seen):
    """Unseen videos of a partner channel. With a TranscriptYT key the listing
    comes from its API. Otherwise the publish date comes free from RSS;
    from the channel page it costs a request, so it is fetched later and only
    for clips that name their speaker."""
    if key('TRANSCRIPT_API_KEY'):
        return api_channel_videos(source, seen)
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
    if key('TRANSCRIPT_API_KEY'):
        return api_captions(video_id)
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


def recent(published, now, days=MAX_AGE_DAYS):
    try:
        stamp = datetime.fromisoformat(str(published).replace('Z', '+00:00'))
    except ValueError:
        return False
    return stamp >= now - timedelta(days=days)


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
                cid, quote = title_speaker(video['title'], source.get('commentators'))
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
                if not video['published_at'] or not recent(video['published_at'], now, VIDEO_MAX_AGE_DAYS):
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
        blocked_until = (now + exc.rest).isoformat() if exc.rest else None
        wait = f'{blocked_until} saatine kadar bekleniyor' if blocked_until else 'sonraki çalışmada devam edilecek'
        print(f'Durduruldu ({exc}); {wait}. Bulunanlar kaydedildi.', flush=True)
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
