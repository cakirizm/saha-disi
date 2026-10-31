"""Pozisyon Kararı: per-incident verdicts drawn from published statements.

A verdict is emitted only when a sentence both names the incident (penaltı,
kırmızı kart, gol...) and states a judgement about it. Reporting sentences
("87'de hakem kırmızı kartla oyundan attı") carry no judgement and are left
out. The commentator's own sentence always travels with the verdict, so the
app never shows a label without the words it came from.
"""
from __future__ import annotations
import json, re
from pathlib import Path

B = Path(__file__).resolve().parent

EX_REFEREES = {'ahmet-cakar', 'deniz-coban', 'firat-aydinus', 'erman-toroglu', 'bulent-yildirim'}
KIND_LABELS = {'penalty': 'Penaltı pozisyonu', 'red': 'Kırmızı kart pozisyonu',
               'yellow': 'Sarı kart pozisyonu', 'goal': 'Gol pozisyonu'}

MINUTE = re.compile(r"(?<!\d)(\d{1,3})(?:\+\d{1,2})?\s*(?:['’][a-zçğıöşü]{0,5}|\.?\s*dakika\w*)", re.I)
CORRECT = ('doğru', 'yerinde', 'isabetli')
MISSED = ('atladı', 'göremedi', 'vermedi', 'es geçti', 'es geçilen', 'yok saydı')
SHOULD_PAST = ('vermeliydi', 'verilmeliydi', 'verilmesi gereken', 'gerekirdi', 'olmalıydı', 'görmeliydi')
PEN_NOT = ('penaltı değil', 'penaltı yok', 'penaltı olmadığ', 'devam kararı doğru', 'devam kararları doğru',
           'temas yoktu', 'faul yoktu')
PEN_GIVEN_WRONG = ('penaltı kararı hatalı', 'penaltı kararı yanlış', 'penaltısı hatalı', 'penaltı hatalı',
                   'penaltısı yanlış')
GOAL_VALID = ('gol karar', 'gol geçerli', 'golü geçerli')
GOAL_VOID = ('gol iptal edilmeliydi', 'golden önce faul vardı', 'gol öncesinde faul vardı', 'ofsayttı',
             'iptal kararı doğru', 'iptali doğru')


def minute_of(text):
    for m in MINUTE.finditer(text):
        n = int(m.group(1))
        if 1 <= n <= 130:
            return n
    return None


def near(low, anchors, cues, span=70):
    """A cue counts only close to the incident word; columns pack several
    positions into one sentence and a distant "doğru" belongs to another."""
    for a in anchors:
        for m in re.finditer(re.escape(a), low):
            window = low[max(0, m.start() - span):m.end() + span]
            if any(c in window for c in cues):
                return True
    return False


NEGATED = ('mümkün değil', 'söylenemez', 'denemez', 'doğru değil')


def judgements(text):
    """[(kind, verdict, referee_call)] stated in one sentence; empty when unclear."""
    # "doğrusu" means "frankly", not "the right call".
    low = re.sub(r'doğrusu\w*', '', text.casefold())
    if any(n in low for n in NEGATED):
        return []
    out = []
    red = ('kırmızı', 'ihraç')
    if any(a in low for a in red):
        if near(low, red, ('sarı kart yeterli', 'sarı yeterli')):
            out.append(('red', 'SARI', 'hatali'))
        elif near(low, red, MISSED + SHOULD_PAST):
            out.append(('red', 'KIRMIZI', 'hatali'))
        elif near(low, red, ('hatalı', 'yanlış')):
            out.append(('red', 'DEĞİL', 'hatali'))
        elif near(low, red, CORRECT):
            out.append(('red', 'KIRMIZI', 'dogru'))
    pen = ('penaltı',)
    if 'penaltı' in low:
        if any(x in low for x in PEN_GIVEN_WRONG):
            out.append(('penalty', 'DEĞİL', 'hatali'))
        elif near(low, pen, ('devam', 'temas yoktu', 'faul yoktu', 'penaltı değil', 'penaltı yok')) and not near(low, pen, MISSED + SHOULD_PAST):
            # "penaltı beklentisinde devam kararı doğruydu": the call was play on.
            out.append(('penalty', 'DEĞİL', 'dogru' if near(low, pen, CORRECT) else None))
        elif near(low, pen, MISSED + SHOULD_PAST):
            out.append(('penalty', 'PENALTI', 'hatali'))
        elif near(low, pen, ('olmalı', 'net bir penaltı', 'penaltıydı')):
            out.append(('penalty', 'PENALTI', None))
        elif near(low, pen, CORRECT):
            out.append(('penalty', 'PENALTI', 'dogru'))
    if 'gol' in low and not out:
        if any(x in low for x in GOAL_VOID):
            out.append(('goal', 'GOL İPTAL', 'dogru' if any(x in low for x in ('iptal kararı doğru', 'iptali doğru')) else 'hatali'))
        elif near(low, GOAL_VALID, CORRECT):
            out.append(('goal', 'GOL GEÇERLİ', 'dogru'))
    if 'sarı kart' in low and not any(k == 'red' for k, _, _ in out):
        if near(low, ('sarı kart',), ('görmeliydi', 'gerekirdi', 'çıkarmalıydı')):
            out.append(('yellow', 'SARI', 'hatali'))
        elif near(low, ('sarı kart',), CORRECT, span=40):
            out.append(('yellow', 'SARI', 'dogru'))
    return out


TRAILING_MINUTE = re.compile(r"(?<!\d)(\d{1,3})(?:\+\d{1,2})?\.\s*$")


def recovered_minutes(statements):
    """Columns write "48. Dakika: ..." and older collections split after "48.",
    leaving the number on the previous sentence. Read it back from there."""
    by_url = {}
    for s in statements:
        by_url.setdefault(s.get('url'), []).append(s)
    found = {}
    for rows in by_url.values():
        rows.sort(key=lambda r: r.get('id') or 0)
        for prev, row in zip(rows, rows[1:]):
            if (row.get('id') or 0) - (prev.get('id') or 0) != 1:
                continue
            if not (row.get('summary') or '').casefold().startswith('dakika'):
                continue
            m = TRAILING_MINUTE.search(prev.get('summary') or '')
            if m and 1 <= int(m.group(1)) <= 130:
                found[row.get('id')] = int(m.group(1))
    return found


def load_overrides():
    path = B / 'incident_overrides.json'
    if not path.exists():
        return {'hide_statement_ids': [], 'verdicts': {}}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {'hide_statement_ids': [], 'verdicts': {}}
    data.setdefault('hide_statement_ids', [])
    data.setdefault('verdicts', {})
    return data


def build_incidents(statements, overrides=None):
    """Group verdicts by match, minute and kind. Without a minute two different
    penalty claims in one match cannot be told apart, so those stay one per article."""
    overrides = overrides or load_overrides()
    hidden = {int(x) for x in overrides['hide_statement_ids']}
    groups = {}
    recovered = recovered_minutes(statements)
    for s in statements:
        match_id = s.get('match_id')
        if not match_id or s.get('id') in hidden:
            continue
        text = s.get('summary') or ''
        minute = minute_of(text) or recovered.get(s.get('id'))
        for kind, verdict, call in judgements(text):
            fixed = overrides['verdicts'].get(str(s.get('id')))
            if fixed:
                verdict, call = fixed.get('verdict', verdict), fixed.get('referee_call', call)
            key = (match_id, minute, kind) if minute else (match_id, None, kind, s.get('url'))
            groups.setdefault(key, []).append({
                'statement_id': s.get('id'), 'commentator': s.get('commentator'), 'verdict': verdict,
                'referee_call': call, 'summary': text, 'url': s.get('url'),
                'expert': s.get('commentator') in EX_REFEREES})
    incidents = []
    for key, opinions in groups.items():
        match_id, minute, kind = key[0], key[1], key[2]
        seen, unique = set(), []
        for o in opinions:
            if o['commentator'] not in seen:
                seen.add(o['commentator'])
                unique.append(o)
        incidents.append({'id': f"{match_id}-{minute or 'x'}-{kind}-{unique[0]['statement_id']}",
                          'match_id': match_id, 'minute': minute, 'kind': kind,
                          'kind_label': KIND_LABELS[kind], 'opinions': unique})
    incidents.sort(key=lambda i: (i['match_id'], i['minute'] is None, i['minute'] or 0))
    return incidents
