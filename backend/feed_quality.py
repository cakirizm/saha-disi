"""Publication rules shared by builders and regression tests."""
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import re

def publication_problem(row):
    url=urlparse(row.get('url',''))
    if url.scheme!='https' or not url.netloc:
        return 'missing_original_url'
    if url.netloc in {'news.google.com','www.news.google.com'} or re.search(r'/(kategori|category|etiket|tag|search)(/|$)',url.path) or url.path in {'','/'}:
        return 'index_page_not_statement'
    if not row.get('date'):
        return 'missing_publication_date'
    if row.get('status')=='verified_manual':
        return None
    evidence=row.get('evidence') or {}
    if evidence.get('version')!=2 or evidence.get('speaker_id')!=row.get('commentator') or evidence.get('url')!=row.get('url'):
        return 'legacy_attribution_requires_review'
    if evidence.get('method') not in {'article_explicit_speaker','official_api_author_match'}:
        return 'unverified_speaker'
    return None

def mentioned_entities(text, names):
    # Word boundaries prevent e.g. a surname inside an unrelated longer word.
    return [name for name in names if re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)', text, re.I)]

def normalize_kickoff(value):
    try:
        date=datetime.strptime(value, '%d.%m.%Y %H:%M')
        return date.replace(tzinfo=timezone(timedelta(hours=3))).isoformat()
    except ValueError:
        return value

def merge_fixture(base, incoming, *, fallback=False):
    result = dict(base)
    for key, value in incoming.items():
        if value is None or value == '':
            continue
        if fallback and result.get(key) not in (None, ''):
            continue
        result[key] = value
    return result

def match_status(row, now=None):
    if row.get('status') in {'live', 'finished', 'postponed', 'cancelled', 'suspended'}:
        return row['status']
    if row.get('home_score') is not None and row.get('away_score') is not None:
        return 'finished'
    raw = row.get('kickoff', '')
    try:
        date = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        try:
            date = datetime.strptime(raw, '%d.%m.%Y %H:%M')
        except ValueError:
            return 'unscheduled'
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone(timedelta(hours=3)))
    return 'awaiting_result' if date <= (now or datetime.now(timezone.utc)) else 'scheduled'

def statement_image(row, photos):
    # Article OG images are not evidence of identity or relevance.
    # Only the identity-verified portrait registry supplies commentary artwork.
    return photos.get(row.get('commentator'))
