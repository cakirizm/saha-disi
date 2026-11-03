"""Publication rules shared by builders and regression tests."""
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import re

# Mirrors the publish-gate rule in .github/workflows: these verbs mark reported speech.
EDITORIAL_MARKERS=(' eleştirdi',' yorumladı',' değerlendirdi',' söyledi',' sert dille',' açıkladı')

# Mojibake markers the publish gate rejects anywhere in the feed. One bad page in
# one run used to fail the whole publication; now only that row is held back.
BROKEN_TEXT=('Ã','Å','Ä','Â','�')

def has_broken_text(value):
    if isinstance(value,str): return any(x in value for x in BROKEN_TEXT)
    if isinstance(value,dict): return any(has_broken_text(x) for x in value.values())
    if isinstance(value,list): return any(has_broken_text(x) for x in value)
    return False

# Sites publish articleBody with paragraphs run together ("varİkinci", "kazandı.Taraftarı").
# Real names keep their internal capital, so those prefixes are not treated as glue.
GLUED_WORDS=re.compile(r'[a-zçğıöşü][.!?…]?[A-ZÇĞİÖŞÜ]')
CAMEL_NAMES=re.compile(r'(?<!\w)(?:Mc|Mac|De|Di|Le|La|Ku|You|Tik|Siyah|Bordo|Sarı)(?=[A-ZÇĞİÖŞÜ])')

def text_problem(row):
    summary=(row.get('summary') or '').strip()
    # A lowercase start means the sentence lost its beginning ("dakikada ...").
    if summary[:1].islower():
        return 'sentence_fragment'
    # "... kuran G." is "G. Saray" cut in half.
    if re.search(r'(?<!\w)[A-ZÇĞİÖŞÜ]\.$',summary):
        return 'sentence_fragment'
    if GLUED_WORDS.search(CAMEL_NAMES.sub(' ',summary)):
        return 'glued_words'
    if (row.get('evidence') or {}).get('method')=='columnist_byline' and not re.search(r'[.!?…"”»)]$',summary):
        return 'sentence_fragment'
    return None

def publication_problem(row):
    url=urlparse(row.get('url',''))
    if url.scheme!='https' or not url.netloc:
        return 'missing_original_url'
    if url.netloc in {'news.google.com','www.news.google.com'} or re.search(r'/(kategori|category|etiket|tag|search)(/|$)',url.path) or url.path in {'','/'}:
        return 'index_page_not_statement'
    if not row.get('date'):
        return 'missing_publication_date'
    # "X eleştirdi / söyledi" is the column reporting a third party, not the
    # commentator's own words. The publish gate rejects these, so drop them here
    # instead of failing the whole run at validation time.
    if any(x in ' ' + (row.get('summary') or '').casefold() for x in EDITORIAL_MARKERS):
        return 'reported_speech_not_own_words'
    if has_broken_text(row):
        return 'broken_text'
    if text_problem(row):
        return text_problem(row)
    if row.get('status')=='verified_manual':
        return None
    evidence=row.get('evidence') or {}
    if evidence.get('version')!=2 or evidence.get('speaker_id')!=row.get('commentator') or evidence.get('url')!=row.get('url'):
        return 'legacy_attribution_requires_review'
    if evidence.get('method') not in {'article_explicit_speaker','official_api_author_match','columnist_byline','partner_video_title_speaker'}:
        return 'unverified_speaker'
    return None

# Short quotation, not a copy of the column: how many sentences of one article may
# be published. The reader goes to the source for the rest.
MAX_QUOTES_PER_ARTICLE=2

def cap_article_quotes(statements, limit=MAX_QUOTES_PER_ARTICLE, preferred=()):
    """Keep each column's most useful sentences; hand-verified rows and videos are untouched."""
    def usefulness(s):
        return (s.get('id') in preferred,s.get('topic') in {'Hakem / VAR','Tahmin'},bool(s.get('team'))+len(s.get('players') or []),
                s.get('strength') or 0,-abs(len(s.get('summary') or '')-160),str(s.get('summary')))
    articles={}
    for s in statements:
        if (s.get('evidence') or {}).get('method')=='columnist_byline':
            articles.setdefault(s.get('url'),[]).append(s)
    dropped={id(s) for rows in articles.values() for s in sorted(rows,key=usefulness,reverse=True)[limit:]}
    return [s for s in statements if id(s) not in dropped]

FUTURE_TENSE=re.compile(r'\b\w{2,}(?:acak|ecek)(?:tır|tir|lar|ler)?\b')
NOT_FUTURE=re.compile(r'\b(?:bacak|sıcak|kucak|yumuşacık)\w*',re.I)

def is_preview_claim(summary, published, kickoff):
    """A sentence in the future tense, printed before kickoff, about that match."""
    return bool(published and kickoff and published<kickoff and FUTURE_TENSE.search(NOT_FUTURE.sub(' ',summary or '')))

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
