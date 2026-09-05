"""Official social API readers. Credentials stay in server environment variables."""
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from collector_v3 import B, classify, tags, TEAMS, PLAYERS

def api_get(url, params, token):
    request = Request(url + '?' + urlencode(params), headers={'Authorization': 'Bearer ' + token})
    with urlopen(request, timeout=20) as response:
        result = json.load(response)
    if result.get('errors') or result.get('error'):
        raise ValueError('provider returned an API error')
    return result

def post_candidate(account, text, url, date, platform):
    text = ' '.join(text.split())
    if not 20 <= len(text) <= 420 or not date or not url.startswith('https://'):
        return None
    teams = tags(text, TEAMS)
    players = tags(text, PLAYERS)
    if not teams and not players and not any(w in text.casefold() for w in ('transfer', 'football', 'futbol', 'signing', 'contract', 'here we go', 'bonservis')):
        return None
    typ, topic, sentiment, strength = classify(text)
    return dict(candidate_id=hashlib.sha256((account['commentator']+'|'+text.casefold()).encode()).hexdigest()[:20],
                commentator=account['commentator'], summary_candidate=text, team=teams[0] if len(teams)==1 else None,
                players=players, type=typ, topic=topic, sentiment=sentiment, strength=strength,
                source=platform+' · @'+account['username'], url=url, published_at=date,
                discovered_at=datetime.now(timezone.utc).isoformat(), image_url=None,
                confidence=95, direct_quote=True, resolver='official_api_author_match')

def x_posts(account, token):
    payload = api_get('https://api.x.com/2/tweets/search/recent', {
        'query': 'from:'+account['username']+' -is:retweet -is:reply', 'max_results': 20,
        'tweet.fields': 'author_id,created_at,referenced_tweets,note_tweet',
        'expansions': 'author_id', 'user.fields': 'username'}, token)
    authors = {u['id']: u['username'].casefold() for u in payload.get('includes', {}).get('users', [])}
    rows=[]
    for post in payload.get('data', []):
        if authors.get(post.get('author_id')) != account['username'].casefold():
            continue
        if any(r['type'] in {'retweeted','replied_to'} for r in post.get('referenced_tweets', [])):
            continue
        row=post_candidate(account, post.get('note_tweet', {}).get('text') or post.get('text',''),
                           'https://x.com/'+account['username']+'/status/'+post['id'], post.get('created_at'), 'X')
        if row: rows.append(row)
    return rows, bool(payload.get('meta', {}).get('next_token'))

def instagram_posts(account, token):
    owner=os.environ.get('INSTAGRAM_BUSINESS_ACCOUNT_ID','')
    version=os.environ.get('META_GRAPH_VERSION','')
    if not owner.isdigit() or not re.fullmatch(r'v\d+\.0', version):
        raise ValueError('INSTAGRAM_BUSINESS_ACCOUNT_ID / META_GRAPH_VERSION missing')
    fields='business_discovery.username('+account['username']+'){username,media.limit(20){caption,permalink,timestamp}}'
    payload=api_get('https://graph.facebook.com/'+version+'/'+owner, {'fields':fields}, token)
    profile=payload.get('business_discovery', {})
    if profile.get('username','').casefold()!=account['username'].casefold():
        raise ValueError('Instagram account identity mismatch')
    rows=[]
    for post in profile.get('media',{}).get('data',[]):
        row=post_candidate(account,post.get('caption',''),post.get('permalink',''),post.get('timestamp'),'Instagram')
        if row: rows.append(row)
    return rows, bool(profile.get('media',{}).get('paging',{}).get('next'))

def collect_social():
    accounts=json.loads((B/'social_accounts.json').read_text(encoding='utf-8'))['accounts']
    rows=[]; health=[]
    for platform, env, reader in [('x','X_BEARER_TOKEN',x_posts),('instagram','INSTAGRAM_ACCESS_TOKEN',instagram_posts)]:
        token=os.environ.get(env,'')
        selected=[a for a in accounts if a['platform']==platform and a.get('identity_source') and a.get('verified_identity')]
        if not token or not selected:
            health.append(dict(source=platform,kind=platform,ok=False,candidates=0,error='missing_credentials' if not token else 'no_verified_accounts'))
            continue
        for account in selected:
            status=dict(source=platform+' · '+account['username'],kind=platform,candidates=0,ok=False)
            try:
                found,partial=reader(account,token);rows.extend(found)
                status.update(ok=True,candidates=len(found),partial=partial)
            except Exception as exc:
                # Never log request URLs, response bodies or bearer tokens.
                status['error']=type(exc).__name__
            health.append(status)
    return rows,health
