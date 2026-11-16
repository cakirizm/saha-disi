"""Build the live app feed from verified public-source material.

Only actual/direct commentator words enter the live feed. Current fixture overrides are
merged on top of the automated TFF cache so the app never shows a known-wrong current score.
"""
from __future__ import annotations
import json, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict
from collector_v3 import classify
from feed_quality import cap_article_quotes, has_broken_text, is_preview_claim, merge_fixture, match_status, statement_image, normalize_kickoff, publication_problem, mentioned_entities
from collector_v3 import PLAYERS, TEAMS
from incidents import build_incidents

ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'backend'
# Continue from the last published feed so verified history never disappears when
# a source has no new items in the current collection window.
seed_path=(B/'feed.json') if (B/'feed.json').exists() else (ROOT/'data/seed.json')
seed=json.loads(seed_path.read_text(encoding='utf-8'))
candidates=json.loads((B/'candidates.json').read_text(encoding='utf-8')) if (B/'candidates.json').exists() else []
# Partner channels' videos are read on the project server (YouTube refuses GitHub
# runners) and arrive as their own file, so the two collectors never write the same one.
if (B/'youtube_candidates.json').exists():
    candidates+=json.loads((B/'youtube_candidates.json').read_text(encoding='utf-8')).get('candidates',[])

PARAPHRASE_MARKERS=('düşünüyor','değerlendiriyor','savunuyor','belirtiyor','söylüyor','ifade ediyor','eleştirdi','övdü','değerlendirdi','açıkladı','yorumladı','iddia etti','vurguladı','yönündeki iddia','olarak görüyor','olarak değerlendiriyor')
TRANSCRIPT_SOURCES={'Socrates','TRT Spor · Stadyum','VOLE / NEO Spor','Tivibu Spor · Orta Nokta'}
TRANSCRIPT_ENTITIES=('galatasaray','fenerbahçe','beşiktaş','trabzonspor','samsunspor','göztepe','konyaspor','kocaelispor','gaziantep','rizespor','eyüpspor','alanyaspor','başakşehir','kasımpaşa','gençlerbirliği','erzurumspor','çorum','amed','osimhen','sane','barış alper','yunus','talisca','greenwood','asensio','kerem','skriniar','oğuz aydın','vlahovic','trossard','batrakov','orkun','guendouzi','kante','semedo','muriqi','singo','torreira','leao','cerny','ndidi','onuachu','muçi')
CANON={
 'galatasaray a.ş.':'Galatasaray','galatasaray':'Galatasaray','fenerbahçe a.ş.':'Fenerbahçe','fenerbahçe':'Fenerbahçe',
 'beşiktaş a.ş.':'Beşiktaş','beşiktaş':'Beşiktaş','trabzonspor a.ş.':'Trabzonspor','trabzonspor':'Trabzonspor',
 'samsunspor a.ş.':'Samsunspor','samsunspor':'Samsunspor','göztepe a.ş.':'Göztepe','göztepe':'Göztepe',
 'tümosan konyaspor':'Konyaspor','konyaspor':'Konyaspor','çaykur rizespor a.ş.':'Rizespor','çaykur rizespor':'Rizespor','ç. rizespor':'Rizespor','rizespor':'Rizespor',
 'kocaelispor':'Kocaelispor','gençlerbirliği':'Gençlerbirliği','arca çorum fk':'Çorum FK','çorum fk':'Çorum FK','çorum':'Çorum FK',
 'eyüpspor':'Eyüpspor','gaziantep futbol kulübü a.ş.':'Gaziantep FK','gaziantep futbol kulübü':'Gaziantep FK','gaziantep fk':'Gaziantep FK','gaziantep':'Gaziantep FK',
 'corendon alanyaspor':'Alanyaspor','alanyaspor':'Alanyaspor','istanbul başakşehir fk':'Başakşehir','istanbul başakşehir':'Başakşehir','başakşehir':'Başakşehir',
 'kasımpaşa a.ş.':'Kasımpaşa','kasımpaşa':'Kasımpaşa','amed sportif faaliyetler':'Amed SK','amed sk':'Amed SK','amed':'Amed SK','erzurumspor fk':'Erzurumspor','erzurumspor':'Erzurumspor'}

def canonical(v):
    raw=' '.join((v or '').split()).strip()
    return CANON.get(raw.casefold(),raw)

# Columnists write the short forms ("G.Saray", "F.Bahçe", "BJK"), which the club
# list does not contain; without them most statements stayed untagged and could
# not be tied to a fixture.
TEAM_ALIASES={
 'Galatasaray':('G.Saray','G. Saray','Cimbom','Cim Bom'),
 'Fenerbahçe':('F.Bahçe','F. Bahçe','F.Bahce','Kanarya'),
 'Beşiktaş':('BJK','Kara Kartal'),
 'Trabzonspor':('T.Spor','T. Spor','Fırtına'),
 'Başakşehir':('İ.Başakşehir','Başakşehir FK'),
 'Gaziantep FK':('Gaziantep',),
 'Çorum FK':('Çorum',),
 'Amed SK':('Amed','Amedspor'),
}

# Columns also use colours, demonyms and the bare city. "Sarı-kırmızılı" is left
# out: Göztepe shares it with Galatasaray, and a wrong club is worse than none.
TEAM_PATTERNS={
 'Galatasaray':r'(?<!\w)(?:galatasaraylı|cimbom)\w*',
 'Fenerbahçe':r'(?<!\w)(?:sar[ıi][- ]?lacivertli|fenerbahçeli|kanarya)\w*',
 'Beşiktaş':r'(?<!\w)(?:siyah[- ]?beyazl[ıi]|beşiktaşlı)\w*',
 'Trabzonspor':r'(?<!\w)(?:bordo[- ]?mavili|trabzonsporlu)\w*|(?<!\w)trabzon(?!\w)',
 'Samsunspor':r'(?<!\w)samsun(?!\w)',
 'Konyaspor':r'(?<!\w)konya(?!\w)',
 'Rizespor':r'(?<!\w)rize(?!\w)',
 'Alanyaspor':r'(?<!\w)alanya(?!\w)',
 'Gaziantep FK':r'(?<!\w)antep(?!\w)',
}

# The national team is a side of its own. Only first-person or explicitly
# Turkish forms count: a bare "milli takım" is often another country's.
NATIONAL_TEAM='Türkiye'
NATIONAL_PATTERN=r'(?<!\w)(?:a milli takım|a milli|milli takımımız|millilerimiz|ay[- ]?yıldızlı|türkiye milli takım)\w*'

def teams_in(text):
    """Canonical clubs named in a piece of text, short forms included."""
    found=[NATIONAL_TEAM] if re.search(NATIONAL_PATTERN,text or '',re.I) else []
    for club in TEAMS:
        surfaces=(club,)+TEAM_ALIASES.get(club,())
        pattern=TEAM_PATTERNS.get(canonical(club))
        if mentioned_entities(text,list(surfaces)) or (pattern and re.search(pattern,text,re.I)):
            found.append(canonical(club))
    return sorted(set(found))

def clean_summary(value):
    value=' '.join((value or '').split()).strip(' “”-')
    if ':' in value:
        left,right=value.split(':',1)
        generic=('yorumladı','eleştirdi','övdü','değerlendirdi','açıkladı','konuştu','dedi')
        if any(x in left.casefold() for x in generic) and len(right.strip())>=20:value=right.strip(' “”-')
    value=re.sub(r"^['\"]?den\s+",'',value,flags=re.I)
    return value[:420]

def looks_paraphrased(value):
    low=clean_summary(value).casefold()
    return any(x in low for x in PARAPHRASE_MARKERS)

def valid_transcript(value):
    clean=clean_summary(value);low=clean.casefold();words=clean.split()
    repeated=any(words[i].casefold()==words[i-1].casefold() for i in range(1,len(words)))
    filler=sum(low.count(x) for x in (' yani ',' abi ',' hani ',' şey ',' kardeşim',' diyorsun'))
    return 80<=len(clean)<=320 and len(words)>=10 and '?' not in clean and filler<2 and not repeated and any(x in low for x in TRANSCRIPT_ENTITIES)

def is_league(m):return m.get('competition') in (None,'','super_lig')
def fixture_key(m):
    # European and national-team matches carry UEFA's own id; the league is keyed by
    # week and clubs because the TFF page has no stable match id.
    if not is_league(m):return ('uefa',m.get('id'))
    return (int(m.get('week') or 0),canonical(m.get('home')),canonical(m.get('away')))

legacy=[]
for s in seed.get('statements',[]):
    summary=clean_summary(s.get('summary',''))
    if s.get('source') in TRANSCRIPT_SOURCES and not valid_transcript(summary):continue
    if len(summary)>=20 and s.get('verbatim') is True:
        row=dict(s);row['summary']=summary;row['team']=canonical(row.get('team')) if row.get('team') else None;row['verbatim']=True;legacy.append(row)
seed['statements']=legacy

tff=[]
try:tff=json.loads((B/'tff_matches.json').read_text(encoding='utf-8'))
except Exception:pass
matches={}
official_scores=set()
for m in seed.get('matches',[]):
    row=dict(m);row['home']=canonical(row.get('home'));row['away']=canonical(row.get('away'));matches[fixture_key(row)]=row
for m in tff:
    row=dict(m);row['home']=canonical(row.get('home'));row['away']=canonical(row.get('away'));key=fixture_key(row)
    base=merge_fixture(matches.get(key,{}),row);base.setdefault('home_score',None);base.setdefault('away_score',None);matches[key]=base
    if row.get('home_score') is not None and row.get('away_score') is not None:official_scores.add(key)

overrides=[]
try:overrides=json.loads((B/'fixture_overrides.json').read_text(encoding='utf-8'))
except Exception:pass
for m in overrides:
    row=dict(m);row['home']=canonical(row.get('home'));row['away']=canonical(row.get('away'));key=fixture_key(row)
    base=merge_fixture(matches.get(key,{}),row,fallback=True)
    # Explicit, sourced corrections may replace stale data; schedule fallbacks may not.
    if key not in official_scores and row.get('verified_at') and row.get('source_url'):
        base=merge_fixture(base,row)
    base.setdefault('image_url',None);matches[key]=base

uefa=[]
try:uefa=json.loads((B/'uefa_matches.json').read_text(encoding='utf-8'))
except Exception:pass
for m in uefa:
    row=dict(m);row['home']=canonical(row.get('home'));row['away']=canonical(row.get('away'));key=fixture_key(row)
    matches[key]=merge_fixture(matches.get(key,{}),row)

def _stamp(value):
    try:
        d=datetime.fromisoformat(str(normalize_kickoff(value or '')).replace('Z','+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:return None

# Older app builds group the fixture list by league week only. A European night
# is filed under the league week it is played in, so it still shows up there
# instead of under an empty "0. Hafta"; newer builds group by competition.
league_starts={}
for row in matches.values():
    stamp=_stamp(row.get('kickoff'))
    if is_league(row) and stamp and row.get('week'):
        w=int(row['week']);league_starts[w]=min(stamp,league_starts.get(w,stamp))
for row in matches.values():
    if is_league(row):row['competition']='super_lig';continue
    stamp=_stamp(row.get('kickoff'))
    before=[w for w,start in league_starts.items() if stamp and start<=stamp]
    row['week']=max(before) if before else (min(league_starts) if league_starts else 1)

for row in matches.values():
    # Keep the API shape stable while TFF kickoff dates are still unannounced.
    # A missing optional schedule date must never invalidate the whole iOS feed.
    row.setdefault('kickoff','')
    row.setdefault('league','Trendyol Süper Lig')
    row.setdefault('week',0)
    row['kickoff']=normalize_kickoff(row['kickoff'])
    row['status']=match_status(row)
seed['matches']=sorted(matches.values(),key=lambda x:(int(x.get('week') or 0),x.get('kickoff',''),x.get('home','')))

logos={}
try:logos=json.loads((B/'team_logos.json').read_text(encoding='utf-8'))
except Exception:pass
for m in seed.get('matches',[]):
    # European opponents and national teams carry UEFA's own crest.
    m['home_logo_url']=logos.get(m.get('home')) or m.get('home_logo_url')
    m['away_logo_url']=logos.get(m.get('away')) or m.get('away_logo_url')

photo_by_commentator={}
try:
    pdata=json.loads((B/'commentator_photos.json').read_text(encoding='utf-8')).get('photos',{})
    for cid,row in pdata.items():
        if row.get('verified_identity') and row.get('photoURL'):photo_by_commentator[cid]=row['photoURL']
except Exception:pass

roster_path=B/'commentator_roster.json'
if roster_path.exists():
    roster=json.loads(roster_path.read_text(encoding='utf-8'));existing={c['id']:c for c in seed.get('commentators',[])}
    def initials(name):
        parts=[x for x in name.replace('-',' ').split() if x];return ''.join(x[0].upper() for x in parts[:3]) or '?'
    merged=[]
    for cid,name,groups in roster:
        if cid in existing:row=dict(existing[cid])
        else:
            clubs=[g for g in groups if g!='Genel']
            if len(clubs)==1:role=f'{clubs[0]} muhabiri / yorumcu';source=f'{clubs[0]} kaynak taraması'
            elif len(clubs)>1:role='Futbol yorumcusu / muhabir';source='Çoklu kulüp kaynak taraması'
            else:role='Futbol yorumcusu / muhabir';source='Genel futbol kaynak taraması'
            row={'id':cid,'name':name,'role':role,'primarySource':source,'avatar':initials(name)}
        row['focusTeams']=groups;row['photoURL']=photo_by_commentator.get(cid);merged.append(row)
    seed['commentators']=merged

known={(s['commentator'],clean_summary(s['summary']).casefold()) for s in seed.get('statements',[]) if s.get('commentator')}
next_id=max((int(s.get('id',0)) for s in seed.get('statements',[])),default=0)+1;review=[]

manual=[]
try:manual=json.loads((B/'manual_verified.json').read_text(encoding='utf-8'))
except Exception:pass
for row in manual:
    summary=clean_summary(row.get('summary',''));key=(row.get('commentator'),summary.casefold())
    if not row.get('commentator') or len(summary)<20 or key in known:continue
    seed['statements'].append({'id':next_id,'commentator':row['commentator'],'date':row.get('date',''),'team':canonical(row.get('team')) if row.get('team') else None,'players':row.get('players',[]),'topic':row.get('topic','Genel yorum'),'type':row.get('type','opinion'),'sentiment':row.get('sentiment','neutral'),'strength':row.get('strength',7),'summary':summary,'source':row.get('source','Doğrulanmış kaynak'),'url':row.get('url',''),'image_url':row.get('image_url'),'confidence':row.get('confidence',100),'status':'verified_manual','verbatim':True,'match_id':row.get('match_id')})
    known.add(key);next_id+=1

for c in candidates:
    if c.get('confidence',0)<95 or not c.get('direct_quote'):
        review.append(c);continue
    summary=clean_summary(c.get('summary_candidate',''))
    # Partner clips arrive as the one line each clip is about (picked in
    # youtube_partner.py); the long-sentence transcript gate would drop exactly
    # the short headline lines the channels chose.
    partner_clip=(c.get('evidence') or {}).get('method')=='partner_video_title_speaker'
    if c.get('source') in TRANSCRIPT_SOURCES and not partner_clip and not valid_transcript(summary):review.append(c);continue
    if len(summary)<20 or looks_paraphrased(summary):review.append(c);continue
    key=(c.get('commentator'),summary.casefold())
    if not c.get('commentator') or key in known:continue
    seed['statements'].append({'id':next_id,'commentator':c['commentator'],'date':c.get('published_at') or c.get('discovered_at','')[:10],'team':canonical(c.get('team')) if c.get('team') else None,'players':c.get('players',[]),'topic':c.get('topic','Genel yorum'),'type':c.get('type','opinion'),'sentiment':c.get('sentiment','neutral'),'strength':c.get('strength',6),'summary':summary,'source':c.get('source','Kamuya açık kaynak'),'url':c.get('url',''),'image_url':c.get('image_url'),'confidence':c.get('confidence',95),'status':'verified_direct_quote','verbatim':True,'match_id':c.get('match_id')})
    known.add(key);next_id+=1

# Final publish-time cleanup: aggregator titles, logo images and source labels
# leak through as low-quality noise. Tidy them before the app ever sees them.
SOURCE_RENAME={'343':'343 Digital'}
LOGO_IMAGE_HOSTS=('googleusercontent.com','gstatic.com','news.google.com','google.com/')
HEADLINE_SOURCES={'Google News RSS'}

def strip_headline_suffix(value):
    text=' '.join((value or '').split()).strip(' “”"\'')
    # Aggregator titles end with a " - Site Name" credit; drop that trailing credit.
    if ' - ' in text or ' – ' in text:
        text=re.sub(r"\s*[-–]\s*[^-–]{2,32}$",'',text).strip(' “”"\'')
    return text

def inherit_article_team(statements):
    """A column that only ever names one club is about that club, so its other
    sentences belong on that club's page. One passing mention is not enough."""
    named=defaultdict(list)
    for s in statements:
        if (s.get('evidence') or {}).get('method')=='columnist_byline':
            named[s.get('url')].extend(teams_in(s.get('summary','')))
    for s in statements:
        clubs=named.get(s.get('url'),[])
        if not s.get('team') and len(clubs)>=2 and len(set(clubs))==1:
            # Kept on the row: once the article is capped its other sentences are gone.
            s['team']=s['inherited_team']=clubs[0]
    return statements

quarantine_path=B/'quarantined_statements.json'
quarantine=json.loads(quarantine_path.read_text(encoding='utf-8')) if quarantine_path.exists() else []
quarantine_by_key={(s.get('commentator'),s.get('summary'),s.get('url')):s for s in quarantine}
candidate_evidence={(c.get('commentator'),clean_summary(c.get('summary_candidate','')).casefold()):c.get('evidence') for c in candidates if c.get('evidence')}
deduped=[];seen_norm=set()
for s in seed.get('statements',[]):
    key=(s.get('commentator'),clean_summary(s.get('summary','')).casefold())
    if key in candidate_evidence:s['evidence']=candidate_evidence[key]
    # An old splitter cut the minute off some referee verdicts ("61. dakikada ...").
    # Pozisyon Kararı needs them, and the ellipsis says the quote is partial.
    if s.get('summary','').startswith('dakika') and classify(s['summary'])[1]=='Hakem / VAR':
        s['summary']='…'+s['summary']
    reason=publication_problem(s)
    if reason:
        quarantine_by_key[(s.get('commentator'),s.get('summary'),s.get('url'))]={**s,'review_reason':reason}
        continue
    # Repair historical page-wide tags; only the actual statement supplies entities.
    s['players']=mentioned_entities(s.get('summary',''),PLAYERS)
    teams=teams_in(s.get('summary',''))
    # "Galatasaraylı Barış Alper A Milli Takım'da": the club stays the page it belongs on.
    clubs=[t for t in teams if t!=NATIONAL_TEAM]
    s['team']=clubs[0] if len(clubs)==1 else (NATIONAL_TEAM if teams==[NATIONAL_TEAM] else s.get('inherited_team'))
    # Older rows carry labels from the previous keyword rules, so label them again.
    if (s.get('evidence') or {}).get('method')=='columnist_byline':
        s['type'],s['topic'],_,s['strength']=classify(s.get('summary',''))
    s['image_url']=statement_image(s,photo_by_commentator)
    s['image_kind']='verified_portrait' if s['image_url'] else None
    if s.get('type')=='transfer':
        s['transfer_status']='reported'
    s['source']=SOURCE_RENAME.get(str(s.get('source','')).strip(),s.get('source'))
    if s.get('source') in HEADLINE_SOURCES:
        cleaned=strip_headline_suffix(s.get('summary',''))
        if len(cleaned)>=20:s['summary']=cleaned
    key=(s.get('commentator'),clean_summary(s.get('summary','')).casefold())
    if key in seen_norm:continue
    seen_norm.add(key);deduped.append(s)
seed['statements']=inherit_article_team(deduped)

# Nothing tied a statement to a fixture, so every match screen opened empty. A
# single sentence rarely names both clubs ("Beşiktaş hak etti"), but the column
# it came from does, so the article - not the sentence - is what gets matched.
def parse_stamp(value):
    try:stamp=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    except ValueError:return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)

GENERIC_CLUB_WORDS={'fc','ac','as','sc','sk','fk','cf','afc','real','club','sporting','athletic','atletico','atlético','dinamo','dynamo','royal','union','rapid','red','sport','city','united'}
OPPONENT_ALIASES={'Paris Saint-Germain':('PSG',),'Bayern München':('Bayern','Bayern Münih'),'FC Bayern München':('Bayern','Bayern Münih'),
 'Manchester City':('Man City','City'),'Manchester United':('Man United','Man Utd','United'),'Internazionale':('Inter',),'Inter':('Inter',),
 'Atleti':('Atletico Madrid','Atlético Madrid'),'Borussia Dortmund':('Dortmund',),'Tottenham Hotspur':('Tottenham',),'Bayer Leverkusen':('Leverkusen',)}

def opponent_surfaces(name):
    """How a Turkish column names a foreign opponent: full name, known short
    forms, and a distinctive first word ("Liverpool", "Benfica")."""
    out=[name]+list(OPPONENT_ALIASES.get(name,()))
    words=[w for w in re.split(r'[\s-]+',name) if w]
    if len(words)>1:
        first=next((w for w in words if w.casefold() not in GENERIC_CLUB_WORDS and len(w)>=4),None)
        if first:out.append(first)
    return out

def link_matches(statements,matches):
    fixtures=[]
    for m in matches or []:
        kickoff=parse_stamp(normalize_kickoff(m.get('kickoff')) or m.get('kickoff'))
        if not (kickoff and m.get('home') and m.get('away')):continue
        home,away=canonical(m['home']),canonical(m['away'])
        if is_league(m):fixtures.append((m['id'],{home,away},kickoff,None));continue
        # Only the Turkish side is in our club list; the opponent has to be named in the text.
        ours={home,away}&(set(map(canonical,TEAMS))|{NATIONAL_TEAM})
        if len(ours)!=1:continue
        other=away if home in ours else home
        fixtures.append((m['id'],ours,kickoff,opponent_surfaces(other)))
    articles={}
    for s in statements:
        url=s.get('url') or ''
        if url:articles.setdefault(url,[]).append(s)
    linked=0
    for rows in articles.values():
        named=set();stamp=None
        for s in rows:
            named|=set(teams_in(s.get('summary','')))
            stamp=stamp or parse_stamp(s.get('date'))
        if not named or stamp is None:continue
        text=' '.join(s.get('summary','') for s in rows)
        # A column runs the morning after kickoff; a preview may run the day before.
        best=[(mid,clubs) for mid,clubs,kickoff,opp in fixtures
              if clubs<=named and (len(named)>=2 if opp is None else bool(mentioned_entities(text,opp)))
              and kickoff-timedelta(days=1)<=stamp<=kickoff+timedelta(days=4)]
        if len(best)!=1:continue
        for s in rows:
            if not s.get('match_id'):s['match_id']=best[0][0];linked+=1
    # Referee reviews cover the whole week in one column, so the article names many
    # clubs and matches no single fixture. Those sentences say "Trabzonspor lehine
    # penaltı": a named club with exactly one kickoff in the two days before the
    # column is enough. Narrow window, so a midweek European night is not mistaken
    # for the weekend league match.
    for s in statements:
        if s.get('match_id') or s.get('topic')!='Hakem / VAR':continue
        stamp=parse_stamp(s.get('date'));named=set(teams_in(s.get('summary','')))
        if not named or stamp is None:continue
        best={mid for mid,clubs,kickoff,_ in fixtures if clubs&named and kickoff<=stamp<=kickoff+timedelta(days=2)}
        if len(best)==1:s['match_id']=best.pop();linked+=1
    return linked

linked=link_matches(seed['statements'],seed.get('matches'))
# Keyword rules cannot tell a prediction from a sentence that happens to use the
# word; a future-tense sentence printed before that match's kickoff can be trusted.
kickoffs={m.get('id'):parse_stamp(normalize_kickoff(m.get('kickoff')) or m.get('kickoff')) for m in seed.get('matches') or []}
for s in seed['statements']:
    if (s.get('evidence') or {}).get('method')=='columnist_byline' and s.get('topic')!='Hakem / VAR' and is_preview_claim(s.get('summary'),parse_stamp(s.get('date')),kickoffs.get(s.get('match_id'))):
        s['type'],s['topic']='prediction','Tahmin'
# After linking, which reads whole articles to find the fixture.
# Sentences Pozisyon Kararı already uses go first, so the limit costs it as little as it can.
in_incidents={o.get('statement_id') for i in build_incidents(seed['statements']) for o in i.get('opinions',[])}
seed['statements']=cap_article_quotes(seed['statements'],preferred=in_incidents)
# Pozisyon Kararı: verdicts per incident, built only from statements that passed
# the publication gate above, each carrying the commentator's own sentence.
seed['incidents']=build_incidents(seed['statements'])
quarantine_path.write_text(json.dumps(list(quarantine_by_key.values()),ensure_ascii=False,indent=2),encoding='utf-8')

counts={}
for s in seed.get('statements',[]):counts[s['commentator']]=counts.get(s['commentator'],0)+1
seed['commentators']=sorted(seed.get('commentators',[]),key=lambda c:(-counts.get(c['id'],0),c['name']))

# Publish a stable player directory even before a statistics provider is connected.
# Provider-supplied bio/stat fields already present in the feed are preserved.
existing_players={p.get('name','').casefold():dict(p) for p in seed.get('players',[]) if p.get('name')}
mentioned={}
for statement in seed.get('statements',[]):
    for raw_name in statement.get('players',[]):
        name=re.sub(r'[^\wÇĞİÖŞÜçğıöşü .\'-]+$','',str(raw_name)).strip()
        if len(name)<2:continue
        key=name.casefold();mentioned.setdefault(key,name)
player_photos={}
try:player_photos=json.loads((B/'player_photos.json').read_text(encoding='utf-8'))
except Exception:player_photos={}
photo_by_name={str(n).casefold():u for n,u in player_photos.items() if u}
players=[]
for key,name in sorted(mentioned.items(),key=lambda item:item[1].casefold()):
    row=existing_players.get(key,{'id':re.sub(r'[^a-z0-9]+','-',name.casefold().replace('ı','i').replace('ş','s').replace('ğ','g').replace('ü','u').replace('ö','o').replace('ç','c')).strip('-'),'name':name})
    row['comment_count']=sum(1 for s in seed.get('statements',[]) if any(str(p).casefold()==key for p in s.get('players',[])))
    photo=photo_by_name.get(name.casefold())
    if photo:row['photoURL']=photo
    players.append(row)
seed['players']=players
publication_path=B/'source_publications.json'
seed['publications']=[x for x in json.loads(publication_path.read_text(encoding='utf-8')) if not has_broken_text(x)] if publication_path.exists() else []
seed['generated_at']=datetime.now(timezone.utc).isoformat()
(B/'feed.json').write_text(json.dumps(seed,ensure_ascii=False,indent=2),encoding='utf-8')
(B/'review_queue.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
print('match links',linked,'incidents',len(seed['incidents']));print('feed',len(seed.get('commentators',[])),'commentators',len(seed.get('statements',[])),'statements',len(seed.get('matches',[])),'matches','review',len(review))
