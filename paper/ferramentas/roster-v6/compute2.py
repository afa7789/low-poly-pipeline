import json, os, statistics as stt, collections, re, pathlib
REPO = str(pathlib.Path(__file__).resolve().parents[3])
R = f'{REPO}/artifacts/model-sheets'
fm = json.load(open(f'{R}/runs/roster/roster-v6/final-models.json'))
VIEWS = ['front', 'left', 'back', 'rts']


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


# 1. the 61: what did the dead v6 eye leave? compare v6 last round / base vs v6e final
print('== 61 v6e: dead v6 state ==')
dead = collections.Counter()
pairs_parts, pairs_front, pairs_left = [], [], []
for uid, rel in fm.items():
    if 'roster-v6e' not in rel:
        continue
    s6 = load(f'{R}/runs/draft/{uid}/roster-v6/eye/summary.json')
    se = load(f'{R}/runs/draft/{uid}/roster-v6e/eye/summary.json')
    r6 = s6.get('rounds') or []
    dead[(len(r6), s6.get('final_round'))] += 1
    last6 = r6[-1] if r6 else None
    base = s6.get('base') or {}
    fr = se.get('final_round'); fin = [r for r in se['rounds'] if r['round'] == fr][0]
    ref = last6 if last6 and last6.get('parts') else base
    if ref.get('parts') and fin.get('parts'):
        pairs_parts.append((ref['parts'][0] / ref['parts'][1], fin['parts'][0] / fin['parts'][1]))
        pairs_front.append((ref['views']['front']['iou'], fin['views']['front']['iou']))
        pairs_left.append((ref['views']['left']['iou'], fin['views']['left']['iou']))
print('dead v6 (n_rounds, final_round):', dead)
for name, pr in (('parts', pairs_parts), ('front', pairs_front), ('left', pairs_left)):
    d = [b - a for a, b in pr]
    print(f'{name}: n={len(pr)} before={stt.mean(a for a,_ in pr):.3f} after={stt.mean(b for _,b in pr):.3f} d={stt.mean(d):+.3f} up={sum(x>0 for x in d)} down={sum(x<0 for x in d)}')
# does the v6 model.glb of the dead runs equal the base/input? vertex hash
same = 0; n = 0
for uid, rel in fm.items():
    if 'roster-v6e' not in rel:
        continue
    a = f'{R}/runs/draft/{uid}/roster-v6/model.glb'; b = f'{R}/runs/draft/{uid}/roster-v6/eye/input.glb'
    if os.path.exists(a) and os.path.exists(b):
        n += 1; same += (os.path.getsize(a) == os.path.getsize(b))
print('dead v6 model.glb same size as eye/input.glb:', same, '/', n)

# 2. reviewer scores, artist share, gate on final round, resends
print('\n== 165: reviewer scores (Sonnet per view), artist time share, final-round gate ==')
first, last = collections.defaultdict(list), collections.defaultdict(list)
artist_share, llm_s, total_s, resends, rounds_n = [], [], [], [], []
gate_final = 0; gate_base = 0; n = 0
best_is_0 = 0
for uid, rel in fm.items():
    run = f'{REPO}/{os.path.dirname(rel)}'
    s = load(f'{run}/eye/summary.json')
    v = s.get('views') or []
    if v:
        for k, x in v[0]['before'].items():
            first[k].append(x)
        for k, x in v[-1]['after'].items():
            last[k].append(x)
    t = s.get('timing') or {}
    if t.get('artist') and s.get('seconds'):
        artist_share.append(t['artist']['s'] / s['seconds'])
        total_s.append(s['seconds'])
    resends.append(s.get('resends') or 0)
    rounds_n.append(len(s.get('rounds') or []))
    fr = s.get('final_round'); fin = [r for r in s['rounds'] if r['round'] == fr][0]
    fv = fin['views']; bv = s['base']['views']
    n += 1
    gate_final += (fv['front']['iou'] >= .75 and fv['left']['iou'] >= .65)
    gate_base += (bv['front']['iou'] >= .75 and bv['left']['iou'] >= .65)
    best_is_0 += (fr == 0)
for k in ['front', 'left', 'back', 'top', 'bottom', 'rts']:
    if first[k]:
        print(f'view score {k:7s}: before r0 {stt.mean(first[k]):.2f} -> after last {stt.mean(last[k]):.2f} (n={len(first[k])})')
print(f'artist share of eye seconds: mean {stt.mean(artist_share):.3f} median {stt.median(artist_share):.3f}; eye seconds median {stt.median(total_s):.0f} (n={len(total_s)})')
print('resends:', collections.Counter(resends), ' rounds:', collections.Counter(rounds_n))
print(f'gate front>=.75 & left>=.65 (eye measure, deinked): base {gate_base}/{n}  final round {gate_final}/{n}; final_round==0: {best_is_0}')

# 3. how is the final round chosen / what is parts? grep eye_stage
src = open(f'{REPO}/tools/blender/eye_stage.py').read()
for pat in ['final_round', 'def measure', 'def pick', 'best']:
    for m in re.finditer(pat, src):
        ln = src.count('\n', 0, m.start()) + 1
        line = src.split('\n')[ln - 1].strip()
        print(f'{pat} @{ln}: {line[:140]}')
        break
i = src.find('def measure(')
print(src[i:i + 1800])
