"""Compute roster-v6 results from disk -> results-roster-v6.csv + summary printout."""
import json, os, csv, statistics as stt, collections, pathlib
REPO = str(pathlib.Path(__file__).resolve().parents[3])
R = f'{REPO}/artifacts/model-sheets'
OUT = f'{REPO}/paper/results-roster-v6.csv'
fm = json.load(open(f'{R}/runs/roster/roster-v6/final-models.json'))
st = json.load(open(f'{R}/runs/roster/roster-v6/status.json'))['units']
VIEWS = ['front', 'left', 'back', 'rts']


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def eye(run_dir):
    s = load(f'{run_dir}/eye/summary.json')
    if not s:
        return None
    fr = s.get('final_round')
    rounds = s.get('rounds') or []
    final = None
    if fr is not None:
        for r in rounds:
            if r.get('round') == fr:
                final = r
    if final is None and rounds:
        final = rounds[-1]
    base = s.get('base') or {}
    out = {'final_round': fr, 'n_rounds': len(rounds), 'llm_calls': s.get('llm_calls'), 'resends': s.get('resends'),
           'seconds': s.get('seconds')}
    for tag, src in (('eye', final), ('base', base)):
        p = (src or {}).get('parts')
        out[f'{tag}_parts_k'] = p[0] if p else None
        out[f'{tag}_parts_n'] = p[1] if p else None
        out[f'{tag}_parts_share'] = (p[0] / p[1]) if p and p[1] else None
        for v in VIEWS:
            out[f'{tag}_{v}'] = ((src or {}).get('views') or {}).get(v, {}).get('iou')
    return out


def sil(run_dir):
    s = load(f'{run_dir}/silhouette.json')
    if not s:
        return None
    a = s.get('approved') or {}
    return {f'sil_{v}': a.get(v) for v in VIEWS}


rows = []
for uid, rel in sorted(fm.items()):
    run_dir = f'{REPO}/{os.path.dirname(rel)}'
    run = os.path.basename(run_dir)
    u = st.get(uid, {})
    m = (u.get('stages') or {}).get('model') or {}
    row = {'id': uid, 'name': u.get('name'), 'race': u.get('race'), 'rig': u.get('rig'), 'final_run': run,
           'tris': m.get('tris'), 'preflight': m.get('preflight'), 'stage1': m.get('stage1'), 'stage2': m.get('stage2'),
           'verdict': m.get('verdict'), 'model_s': m.get('s'), 'cost_usd': u.get('cost_usd')}
    e = eye(run_dir) or {}
    row.update(e)
    row.update(sil(run_dir) or {})
    # crude v6 baseline for the v6e units
    if run == 'roster-v6e':
        v6 = f'{R}/runs/draft/{uid}/roster-v6'
        e6 = eye(v6) or {}
        s6 = sil(v6) or {}
        row['v6_parts_share'] = e6.get('eye_parts_share')
        row['v6_final_round'] = e6.get('final_round')
        for v in VIEWS:
            row[f'v6_sil_{v}'] = s6.get(f'sil_{v}')
    # older recipes
    for old in ('roster-v5', 'roster-v1', 'roster-v2'):
        od = f'{R}/runs/draft/{uid}/{old}'
        if os.path.exists(f'{od}/model.glb'):
            so = sil(od) or {}
            eo = eye(od) or {}
            row[f'{old}_parts_share'] = eo.get('eye_parts_share')
            for v in VIEWS:
                row[f'{old}_sil_{v}'] = so.get(f'sil_{v}')
    rows.append(row)

cols = []
for r in rows:
    for k in r:
        if k not in cols:
            cols.append(k)
with open(OUT, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
print('wrote', OUT, len(rows), 'rows')


def desc(vals, name):
    vals = [v for v in vals if v is not None]
    if not vals:
        print(name, 'n=0'); return
    q = stt.quantiles(vals, n=4) if len(vals) > 3 else [None] * 3
    print(f'{name:28s} n={len(vals):3d} mean={stt.mean(vals):.3f} median={stt.median(vals):.3f} '
          f'q1={q[0]:.3f} q3={q[2]:.3f} min={min(vals):.3f} max={max(vals):.3f}' if q[0] is not None else
          f'{name} n={len(vals)} mean={stt.mean(vals):.3f}')


print('\n== 165 final models ==')
desc([r.get('tris') for r in rows], 'tris')
desc([r.get('eye_parts_share') for r in rows], 'parts share (final eye round)')
desc([r.get('base_parts_share') for r in rows], 'parts share (base, pre-eye)')
for v in VIEWS:
    desc([r.get(f'sil_{v}') for r in rows], f'sil approved {v}')
for v in VIEWS:
    desc([r.get(f'eye_{v}') for r in rows], f'eye final {v}')
for v in VIEWS:
    desc([r.get(f'base_{v}') for r in rows], f'eye base {v}')
gates = {'front': .75, 'left': .65, 'back': .70, 'rts': .70}
fl = [r for r in rows if r.get('sil_front') is not None and r.get('sil_left') is not None]
print('silhouette gate front>=.75 & left>=.65 :', sum(1 for r in fl if r['sil_front'] >= .75 and r['sil_left'] >= .65), '/', len(fl))
print('front>=.75:', sum(1 for r in fl if r['sil_front'] >= .75), ' left>=.65:', sum(1 for r in fl if r['sil_left'] >= .65))
print('parts share >= .75:', sum(1 for r in rows if (r.get('eye_parts_share') or 0) >= .75), '/', sum(1 for r in rows if r.get('eye_parts_share') is not None))
print('tris 699-700:', sum(1 for r in rows if (r.get('tris') or 0) >= 699))
print('final_round dist:', collections.Counter(r.get('final_round') for r in rows))
print('preflight:', collections.Counter(r.get('preflight') for r in rows), 'stage1:', collections.Counter(r.get('stage1') for r in rows),
      'stage2:', collections.Counter(r.get('stage2') for r in rows))
desc([r.get('model_s') for r in rows], 'model stage seconds')
desc([r.get('llm_calls') for r in rows], 'llm_calls')
print('cost_usd sum', round(sum(r.get('cost_usd') or 0 for r in rows), 2), 'model_s sum h', round(sum(r.get('model_s') or 0 for r in rows) / 3600, 1))


def paired(rows, a, b, name):
    pr = [(r[a], r[b]) for r in rows if r.get(a) is not None and r.get(b) is not None]
    if not pr:
        print(name, 'n=0'); return
    d = [y - x for x, y in pr]
    print(f'{name:40s} n={len(pr):3d} before={stt.mean(x for x,_ in pr):.3f} after={stt.mean(y for _,y in pr):.3f} '
          f'dmean={stt.mean(d):+.3f} dmedian={stt.median(d):+.3f} up={sum(1 for v in d if v > 0)} down={sum(1 for v in d if v < 0)} '
          f'|d|>.12: up={sum(1 for v in d if v > .12)} down={sum(1 for v in d if v < -.12)}')


print('\n== within-unit: base (pre-eye massing) -> final eye round (same measure, eye_stage.measure vs deinked concept) ==')
paired(rows, 'base_parts_share', 'eye_parts_share', 'parts share base->eye')
for v in VIEWS:
    paired(rows, f'base_{v}', f'eye_{v}', f'iou {v} base->eye')

print('\n== 61 v6e units: crude v6 (strict rule, stage died) -> v6e (soft rule) [silhouette approved] ==')
v6e = [r for r in rows if r['final_run'] == 'roster-v6e']
for v in VIEWS:
    paired(v6e, f'v6_sil_{v}', f'sil_{v}', f'sil {v} v6->v6e')
paired(v6e, 'v6_parts_share', 'eye_parts_share', 'parts v6->v6e')
print('v6 final_round of the dead runs:', collections.Counter(r.get('v6_final_round') for r in v6e))
print('v6e final_round:', collections.Counter(r.get('final_round') for r in v6e))

for old in ('roster-v5', 'roster-v1', 'roster-v2'):
    print(f'\n== units with {old} and v6 (older recipe -> v6/v6e) [silhouette approved] ==')
    sub = [r for r in rows if r.get(f'{old}_sil_front') is not None]
    for v in VIEWS:
        paired(sub, f'{old}_sil_{v}', f'sil_{v}', f'sil {v} {old}->v6')
    paired(sub, f'{old}_parts_share', 'eye_parts_share', f'parts {old}->v6')
    if sub:
        both = [r for r in sub if r.get(f'{old}_sil_front') is not None and r.get(f'{old}_sil_left') is not None]
        print(' gate pass', old, sum(1 for r in both if r[f'{old}_sil_front'] >= .75 and r[f'{old}_sil_left'] >= .65), '/', len(both),
              ' v6', sum(1 for r in both if r['sil_front'] >= .75 and r['sil_left'] >= .65))
        print(' ids:', ' '.join(r['id'] for r in sub))

print('\n== per race (sil front / left / parts share) ==')
byr = collections.defaultdict(list)
for r in rows:
    byr[r['race']].append(r)
for race, rs in sorted(byr.items()):
    f = [r['sil_front'] for r in rs if r.get('sil_front') is not None]
    l = [r['sil_left'] for r in rs if r.get('sil_left') is not None]
    p = [r['eye_parts_share'] for r in rs if r.get('eye_parts_share') is not None]
    g = sum(1 for r in rs if r.get('sil_front') is not None and r.get('sil_left') is not None and r['sil_front'] >= .75 and r['sil_left'] >= .65)
    print(f'{race:16s} n={len(rs):2d} front={stt.mean(f):.3f} left={stt.mean(l):.3f} parts={stt.mean(p):.2f} gate={g}')
print('\n== per rig ==')
byg = collections.defaultdict(list)
for r in rows:
    byg[r['rig']].append(r)
for rig, rs in sorted(byg.items(), key=lambda kv: -len(kv[1])):
    f = [r['sil_front'] for r in rs if r.get('sil_front') is not None]
    l = [r['sil_left'] for r in rs if r.get('sil_left') is not None]
    p = [r['eye_parts_share'] for r in rs if r.get('eye_parts_share') is not None]
    if f and l and p:
        print(f'{rig:14s} n={len(rs):3d} front={stt.mean(f):.3f} left={stt.mean(l):.3f} parts={stt.mean(p):.2f}')
