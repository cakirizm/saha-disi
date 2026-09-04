"""Incremental multi-source commentary collector.

Uses direct article sources, Google News discovery and configured YouTube channels.
YouTube clips are accepted automatically only when the title identifies exactly one
tracked commentator; otherwise transcript excerpts stay out of the public feed.
"""
from __future__ import annotations

import hashlib, html, json, re, urllib.parse, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from collector_v3 import (
    B, COMMENTATORS, PEOPLE, PLAYERS, TEAMS, candidate_rows, classify, direct_sources,
    extract, fetch, process_source, repair_text, rss_source, tags,
)

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi=None

CONFIG=json.loads((B/'sources.json').read_text(encoding='utf-8'))['sources']
STATE_PATH=B/'collector_state.json'
MAX_VIDEOS_PER_CHANNEL=30

def norm(value):
    value=(value or '').casefold().translate(str.maketrans('çğıöşü','cgiosu'))
    return re.sub(r'[^a-z0-9]+',' ',value).strip()

def load_state():
    try:return json.loads(STATE_PATH.read_text(encoding='utf-8'))
    except Exception:return {'seen_videos':[]}

def resolve_channel_id(url):
    doc=fetch(url)
    for pattern in (r'<meta\s+itemprop="channelId"\s+content="(UC[\w-]{20,})"',r'"externalId":"(UC[\w-]{20,})"',r'"browseId":"(UC[\w-]{20,})"',r'"channelId":"(UC[\w-]{20,})"'):
        hit=re.search(pattern,doc)
        if hit:return hit.group(1)
    return None

def youtube_entries(source):
    channel_id=source.get('channel_id') or resolve_channel_id(source['url'])
    if not channel_id:return [],'channel id not found'
    raw=fetch('https://www.youtube.com/feeds/videos.xml?channel_id='+channel_id)
    root=ET.fromstring(raw);ns={'a':'http://www.w3.org/2005/Atom','yt':'http://www.youtube.com/xml/schemas/2015'}
    rows=[]
    for entry in root.findall('a:entry',ns)[:MAX_VIDEOS_PER_CHANNEL]:
        video_id=entry.findtext('yt:videoId',default='',namespaces=ns)
        title=repair_text(entry.findtext('a:title',default='',namespaces=ns))
        published=entry.findtext('a:published',default='',namespaces=ns)
        if video_id:rows.append({'id':video_id,'title':title,'published_at':published})
    return rows,None

def video_document(video_id):
    return fetch('https://www.youtube.com/watch?v='+video_id)

def video_description(doc):
    hit=re.search(r'"shortDescription":"((?:\\.|[^"\\])*)"',doc)
    if not hit:return ''
    try:return repair_text(json.loads('"'+hit.group(1)+'"'))
    except Exception:return ''

def caption_url(doc):
    hit=re.search(r'"captionTracks":(\[.*?\])\s*,\s*"audioTracks"',doc)
    if not hit:return None
    try:tracks=json.loads(hit.group(1))
    except Exception:return None
    preferred=next((x for x in tracks if (x.get('languageCode') or '').startswith('tr')),None)
    track=preferred or (tracks[0] if tracks else None)
    return html.unescape(track.get('baseUrl','')) if track else None

def transcript(doc,video_id):
    if YouTubeTranscriptApi is not None:
        try:
            fetched=YouTubeTranscriptApi().fetch(video_id,languages=['tr'])
            return repair_text(' '.join(item.text for item in fetched))
        except Exception:pass
    url=caption_url(doc)
    if not url:return ''
    try:root=ET.fromstring(fetch(url))
    except Exception:return ''
    return repair_text(' '.join(''.join(node.itertext()) for node in root.iter() if node.tag.rsplit('}',1)[-1] in {'text','p'}))

def transcript_quotes(text):
    sentences=re.split(r'(?<=[.!?])\s+',repair_text(text))
    out=[]
    for sentence in sentences:
        sentence=re.sub(r'(^|\s)(?:eee+|ııı+|hıı+)(?=\s|[,.;])',' ',sentence,flags=re.I)
        sentence=repair_text(sentence.replace('>>',' ')).strip(' -“”"')
        low=sentence.casefold()
        entities=tags(sentence,TEAMS+PLAYERS)
        filler=sum(low.count(x) for x in (' yani ',' abi ',' hani ',' şey ',' kardeşim',' diyorsun'))
        words=sentence.split()
        repeated=any(words[i].casefold()==words[i-1].casefold() for i in range(1,len(words)))
        if 80<=len(sentence)<=320 and entities and len(words)>=10 and '?' not in sentence and filler<2 and not repeated:
            out.append(sentence)
    return out[:10]

def youtube_rows(source,seen):
    entries,error=youtube_entries(source);rows=[];processed=[]
    mapped=source.get('commentators') or []
    for video in entries:
        if video['id'] in seen:continue
        doc=video_document(video['id']);context=norm(video['title'])
        speakers=[cid for cid in mapped if norm(COMMENTATORS.get(cid,'')) in context]
        if len(speakers)!=1:continue
        cid=speakers[0];text=transcript(doc,video['id'])
        if not text:continue
        url='https://www.youtube.com/watch?v='+video['id']
        for quote in transcript_quotes(text):
            typ,topic,sentiment,strength=classify(quote)
            teams=tags(quote,TEAMS);players=tags(quote,PLAYERS)
            digest=hashlib.sha256(f'{cid}|{quote.casefold()}'.encode()).hexdigest()[:20]
            rows.append({'candidate_id':digest,'commentator':cid,'summary_candidate':quote,'team':teams[0] if teams else None,'players':players,'topic':topic,'type':typ,'sentiment':sentiment,'strength':strength,'source':source['name'],'url':url,'image_url':f'https://i.ytimg.com/vi/{video["id"]}/hqdefault.jpg','confidence':96,'direct_quote':True,'published_at':video['published_at'],'discovered_at':datetime.now(timezone.utc).isoformat(),'resolver':'youtube_caption_exact_speaker'})
        processed.append(video['id'])
    return rows,processed,{'source':source['name'],'kind':'youtube','items':len(entries),'new_videos':len(processed),'candidates':len(rows),'ok':error is None,'error':error}

def configured_html_sources():
    out=[]
    for src in CONFIG:
        if src.get('kind')!='html_index':continue
        for cid in src.get('commentators') or []:
            out.append({'url':src['url'],'source':src['name'],'trust':src.get('trust',95),'cid':cid})
    return out

def run():
    state=load_state();seen=set(state.get('seen_videos',[]));rows=[];health=[];processed=[]
    youtube=[s for s in CONFIG if s.get('kind','').startswith('youtube')]
    article_sources=direct_sources()+configured_html_sources()
    existing={(x['url'],x['cid']) for x in article_sources};article_sources=[x for i,x in enumerate(article_sources) if (x['url'],x['cid']) not in {(y['url'],y['cid']) for y in article_sources[:i]}]
    active_ids=[]
    try:
        live=json.loads((B/'feed.json').read_text(encoding='utf-8'))
        active_ids=list(dict.fromkeys([s['commentator'] for s in live.get('statements',[])]))
    except Exception:pass
    priority=list(dict.fromkeys(active_ids+[cid for cid,_ in PEOPLE[:50]]))
    jobs=[]
    with ThreadPoolExecutor(max_workers=16) as pool:
        for src in article_sources+[rss_source(cid,COMMENTATORS[cid]) for cid in priority]:jobs.append(('web',pool.submit(process_source,src),src))
        for src in youtube:jobs.append(('youtube',pool.submit(youtube_rows,src,seen),src))
        for kind,future,src in jobs:
            try:
                if kind=='youtube':found,done,status=future.result();processed.extend(done);health.append(status)
                else:found,status=future.result();status['kind']='web';health.append(status)
                rows.extend(found)
            except Exception as exc:health.append({'source':src.get('name') or src.get('source'),'kind':kind,'candidates':0,'ok':False,'error':str(exc)[:180]})
    unique={x['candidate_id']:x for x in rows}
    STATE_PATH.write_text(json.dumps({'updated_at':datetime.now(timezone.utc).isoformat(),'seen_videos':list(dict.fromkeys(state.get('seen_videos',[])+processed))[-3000:]},ensure_ascii=False,indent=2),encoding='utf-8')
    (B/'candidates.json').write_text(json.dumps(list(unique.values()),ensure_ascii=False,indent=2),encoding='utf-8')
    totals={'sources':len(health),'successful':sum(x.get('ok',False) for x in health),'youtube_sources':len(youtube),'new_videos':len(processed),'candidates':len(unique)}
    (B/'collector_health.json').write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'tracked_commentators':len(PEOPLE),'totals':totals,'sources':health},ensure_ascii=False,indent=2),encoding='utf-8')
    print('collector v4',totals)

if __name__=='__main__':run()
