"""Build the live app feed from curated seed + high-confidence candidates.
Only confidence >=95 candidates are auto-added. Lower-confidence discoveries stay in review_queue.json.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'backend'
seed = json.loads((ROOT / 'data/seed.json').read_text())
cp = B / 'candidates.json'
candidates = json.loads(cp.read_text()) if cp.exists() else []

# Merge the full tracked roster into the app feed while preserving richer metadata
# already curated for the original profiles.
roster_path = B / 'commentator_roster.json'
if roster_path.exists():
    roster = json.loads(roster_path.read_text())
    existing = {c['id']: c for c in seed.get('commentators', [])}

    def initials(name: str) -> str:
        parts = [x for x in name.replace('-', ' ').split() if x]
        return ''.join(x[0].upper() for x in parts[:3]) or '?'

    merged = []
    for cid, name, groups in roster:
        if cid in existing:
            row = dict(existing[cid])
        else:
            club_groups = [g for g in groups if g != 'Genel']
            if len(club_groups) == 1:
                role = f"{club_groups[0]} muhabiri / yorumcu"
                source = f"{club_groups[0]} kaynak taraması"
            elif len(club_groups) > 1:
                role = "Futbol yorumcusu / muhabir"
                source = "Çoklu kulüp kaynak taraması"
            else:
                role = "Futbol yorumcusu / muhabir"
                source = "Genel futbol kaynak taraması"
            row = {
                'id': cid,
                'name': name,
                'role': role,
                'primarySource': source,
                'avatar': initials(name),
            }
        row['focusTeams'] = groups
        merged.append(row)
    seed['commentators'] = merged

# Önder Özen is currently a club executive rather than an active commentator.
PAUSED_COMMENTATORS = {'onder-ozen'}
known = {(s['commentator'], s['summary']) for s in seed['statements']}
next_id = max((s['id'] for s in seed['statements']), default=0) + 1
review = []

for c in candidates:
    if c['commentator'] in PAUSED_COMMENTATORS:
        continue
    if c['confidence'] < 95:
        review.append(c)
        continue

    summary = ' '.join(c['summary_candidate'].split())[:220]
    key = (c['commentator'], summary)
    if key in known:
        continue

    seed['statements'].append({
        'id': next_id,
        'commentator': c['commentator'],
        'date': c['discovered_at'][:10],
        'team': c['team'],
        'players': c['players'],
        'topic': c['topic'],
        'type': c['type'],
        'sentiment': c['sentiment'],
        'strength': c['strength'],
        'summary': summary,
        'source': c['source'],
        'url': c['url'],
        'confidence': c['confidence'],
        'status': 'auto_candidate'
    })
    known.add(key)
    next_id += 1

seed['generated_at'] = datetime.now(timezone.utc).isoformat()
(B / 'feed.json').write_text(json.dumps(seed, ensure_ascii=False, indent=2))
(B / 'review_queue.json').write_text(json.dumps(review, ensure_ascii=False, indent=2))
print('feed', len(seed['commentators']), 'commentators', len(seed['statements']), 'statements', 'review', len(review), 'generated_at', seed['generated_at'])
