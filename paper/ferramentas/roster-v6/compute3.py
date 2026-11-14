"""Merge final-GLB measurements into results-roster-v6.csv, print stats, draw figure."""
import json, os, csv, statistics as stt, collections, pathlib
S = pathlib.Path(__file__).resolve().parent  # measure_final.py writes final-measure/ here
P = pathlib.Path(__file__).resolve().parents[2]  # paper/
CSV = P / 'results-roster-v6.csv'
VIEWS = ['front', 'left', 'back', 'rts']
rows = list(csv.DictReader(open(CSV)))
fm = {}
for f in (S / 'final-measure').glob('*.json'):
    d = json.load(open(f)); fm[d['id']] = d
errs = list((S / 'final-measure').glob('*.err'))
print('measured', len(fm), 'errors', len(errs), [e.stem for e in errs])


def fl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


for r in rows:
    m = fm.get(r['id'])
    if m:
        k, n = m['parts']
        r['glb_parts_k'], r['glb_parts_n'] = k, n
        r['glb_parts_share'] = round(k / n, 4) if n else ''
        for v in VIEWS:
            r[f'glb_{v}'] = round(m['views'][v]['iou'], 4) if v in m['views'] else ''
            r[f'glb_{v}_spill'] = round(m['views'][v]['spill'], 4) if v in m['views'] and m['views'][v].get('spill') is not None else ''
    else:
        for c in ['glb_parts_k', 'glb_parts_n', 'glb_parts_share'] + [f'glb_{v}' for v in VIEWS] + [f'glb_{v}_spill' for v in VIEWS]:
            r[c] = ''
cols = list(rows[0].keys())
with open(CSV, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
print('rewrote', CSV, len(rows), 'rows', len(cols), 'cols')


def desc(vals, name):
    vals = [v for v in vals if v is not None]
    q = stt.quantiles(vals, n=4)
    print(f'{name:30s} n={len(vals):3d} mean={stt.mean(vals):.3f} median={stt.median(vals):.3f} q1={q[0]:.3f} q3={q[2]:.3f} min={min(vals):.3f} max={max(vals):.3f}')


def paired(a, b, name):
    pr = [(fl(r[a]), fl(r[b])) for r in rows if fl(r.get(a)) is not None and fl(r.get(b)) is not None]
    d = [y - x for x, y in pr]
    print(f'{name:36s} n={len(pr):3d} before={stt.mean(x for x,_ in pr):.3f} after={stt.mean(y for _,y in pr):.3f} dmean={stt.mean(d):+.3f} dmed={stt.median(d):+.3f} up={sum(v>0 for v in d)} down={sum(v<0 for v in d)} |d|>.12 up={sum(v>.12 for v in d)} down={sum(v<-.12 for v in d)}')


print('\n== final model.glb (eye_stage.measure, deinked sheet) ==')
desc([fl(r['glb_parts_share']) for r in rows], 'glb parts share')
for v in VIEWS:
    desc([fl(r[f'glb_{v}']) for r in rows], f'glb iou {v}')
g = [r for r in rows if fl(r['glb_front']) is not None and fl(r['glb_left']) is not None]
print('glb gate front>=.75 & left>=.65:', sum(fl(r['glb_front']) >= .75 and fl(r['glb_left']) >= .65 for r in g), '/', len(g),
      ' front>=.75', sum(fl(r['glb_front']) >= .75 for r in g), ' left>=.65', sum(fl(r['glb_left']) >= .65 for r in g))
print('glb spill<=.03 front&left:', sum(fl(r['glb_front_spill']) <= .03 and fl(r['glb_left_spill']) <= .03 for r in g if fl(r['glb_front_spill']) is not None), '/', len(g))
print('\n== base (massing) -> final model.glb, same ruler ==')
paired('base_parts_share', 'glb_parts_share', 'parts base->glb')
for v in VIEWS:
    paired(f'base_{v}', f'glb_{v}', f'iou {v} base->glb')
print('\n== final eye round (pieces) -> final model.glb (union+mold+joints) ==')
paired('eye_parts_share', 'glb_parts_share', 'parts round->glb')
for v in VIEWS:
    paired(f'eye_{v}', f'glb_{v}', f'iou {v} round->glb')
print('\n== per rig group (glb) ==')
grp = collections.defaultdict(list)
for r in rows:
    grp['biped' if r['rig'] == 'biped' else 'não-bípede'].append(r)
for k, rs in grp.items():
    f = [fl(r['glb_front']) for r in rs if fl(r['glb_front']) is not None]; l = [fl(r['glb_left']) for r in rs if fl(r['glb_left']) is not None]
    p = [fl(r['glb_parts_share']) for r in rs if fl(r['glb_parts_share']) is not None]
    gg = sum(fl(r['glb_front']) >= .75 and fl(r['glb_left']) >= .65 for r in rs if fl(r['glb_front']) is not None and fl(r['glb_left']) is not None)
    print(f'{k:12s} n={len(rs):3d} front={stt.mean(f):.3f} left={stt.mean(l):.3f} parts={stt.mean(p):.3f} gate={gg}')
print('\n== per race (glb) ==')
byr = collections.defaultdict(list)
for r in rows:
    byr[r['race']].append(r)
for race, rs in sorted(byr.items()):
    f = [fl(r['glb_front']) for r in rs if fl(r['glb_front']) is not None]; l = [fl(r['glb_left']) for r in rs if fl(r['glb_left']) is not None]
    p = [fl(r['glb_parts_share']) for r in rs if fl(r['glb_parts_share']) is not None]
    gg = sum(fl(r['glb_front']) >= .75 and fl(r['glb_left']) >= .65 for r in rs if fl(r['glb_front']) is not None and fl(r['glb_left']) is not None)
    print(f'{race:16s} n={len(rs):2d} front={stt.mean(f):.3f} left={stt.mean(l):.3f} parts={stt.mean(p):.2f} gate={gg}')
print('\n== worst 12 by glb parts share ==')
for r in sorted(rows, key=lambda r: fl(r['glb_parts_share']) or 0)[:12]:
    print(r['id'], r['name'], r['rig'], r['glb_parts_share'], r['glb_front'], r['glb_left'])

# figure
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, ax = plt.subplots(1, 3, figsize=(13, 4.2))
bp = [fl(r['base_parts_share']) for r in rows]; gp = [fl(r['glb_parts_share']) for r in rows]
bins = [i / 10 for i in range(11)]
ax[0].hist([x for x in bp if x is not None], bins=bins, alpha=.55, label='massing (antes do olho)', color='#888')
ax[0].hist([x for x in gp if x is not None], bins=bins, alpha=.55, label='model.glb final', color='#1f77b4')
ax[0].set_xlabel('peças reconhecidas k/n'); ax[0].set_ylabel('unidades'); ax[0].set_title('parts share, 165 modelos'); ax[0].legend(fontsize=8)
bx = [fl(r['base_front']) for r in rows]; gx = [fl(r['glb_front']) for r in rows]
pts = [(x, y, r['rig'] == 'biped') for x, y, r in zip(bx, gx, rows) if x is not None and y is not None]
ax[1].scatter([x for x, y, b in pts if b], [y for x, y, b in pts if b], s=12, label='bípede', color='#1f77b4')
ax[1].scatter([x for x, y, b in pts if not b], [y for x, y, b in pts if not b], s=12, label='não-bípede', color='#d62728')
ax[1].plot([0, 1], [0, 1], 'k--', lw=.8); ax[1].set_xlabel('IoU front, massing'); ax[1].set_ylabel('IoU front, model.glb final')
ax[1].set_title('IoU front: antes vs depois do olho'); ax[1].legend(fontsize=8); ax[1].set_xlim(0, 1); ax[1].set_ylim(0, 1)
rigs = collections.defaultdict(list)
for r in rows:
    if fl(r['glb_front']) is not None:
        rigs[r['rig']].append(r)
top = sorted(rigs.items(), key=lambda kv: -len(kv[1]))[:8]
names = [f'{k} ({len(v)})' for k, v in top]
ax[2].barh(names, [stt.mean(fl(r['glb_front']) for r in v) for k, v in top], color='#1f77b4', alpha=.7, label='IoU front')
ax[2].barh(names, [stt.mean(fl(r['glb_left']) for r in v) for k, v in top], color='#ff7f0e', alpha=.5, label='IoU left', height=.4)
ax[2].axvline(.75, color='#1f77b4', ls=':', lw=.8); ax[2].axvline(.65, color='#ff7f0e', ls=':', lw=.8)
ax[2].invert_yaxis(); ax[2].set_xlim(0, 1); ax[2].set_title('IoU médio por família de rig (model.glb)'); ax[2].legend(fontsize=8)
fig.tight_layout()
out = P / 'figuras' / 'resultados-roster-v6.png'
fig.savefig(out, dpi=130); print('figure', out)
