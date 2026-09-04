"""Build the live app feed from curated seed + high-confidence candidates.
Only confidence >=95 candidates are auto-added. Lower-confidence discoveries stay in review_queue.json.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
seed = json.loads((ROOT / 'data/seed.json').read_text())
cp = ROOT / 'backend/candidates.json'
candidates = json.loads(cp.read_text()) if cp.exists() else []

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
(ROOT / 'backend/feed.json').write_text(json.dumps(seed, ensure_ascii=False, indent=2))
(ROOT / 'backend/review_queue.json').write_text(json.dumps(review, ensure_ascii=False, indent=2))
print('feed', len(seed['statements']), 'review', len(review), 'generated_at', seed['generated_at'])
