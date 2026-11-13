"""Measure the final model.glb of the 165 roster-v6 models with eye_stage.measure (same ruler as the eye rounds).
usage: python3.14 measure_final.py [n_workers] [limit]   -> scratchpad/final-measure/<uid>.json (skips existing)"""
import json, os, sys, pathlib, time, traceback
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, '/Users/afa/Developer/arthur/castle_fight/tools/blender')
CF = pathlib.Path('/Users/afa/Developer/arthur/castle_fight')
R = CF / 'artifacts/model-sheets'
OUT = pathlib.Path(__file__).parent / 'final-measure'
OUT.mkdir(exist_ok=True)


def one(args):
    uid, rel, rig = args
    dst = OUT / f'{uid}.json'
    if dst.exists():
        return uid, 'skip'
    try:
        import eye_stage
        t0 = time.time()
        glb = CF / rel
        ev = eye_stage.measure(glb, OUT / 'work' / uid, R / 'refs' / uid / 'sheet.jpg', rig)
        row = {'id': uid, 'run': os.path.basename(os.path.dirname(rel)), 'parts': ev.get('parts'),
               'views': {v: {k: ev['views'][v].get(k) for k in ('iou', 'spill', 'bare')} for v in ev.get('views', {})},
               's': round(time.time() - t0, 1)}
        dst.write_text(json.dumps(row, indent=1))
        return uid, f"ok {row['s']}s"
    except Exception as e:
        (OUT / f'{uid}.err').write_text(traceback.format_exc())
        return uid, f'ERR {e!r}'[:200]


if __name__ == '__main__':
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    fm = json.load(open(R / 'runs/roster/roster-v6/final-models.json'))
    st = json.load(open(R / 'runs/roster/roster-v6/status.json'))['units']
    jobs = [(uid, rel, st.get(uid, {}).get('rig', 'biped')) for uid, rel in sorted(fm.items())][:limit]
    with ProcessPoolExecutor(workers) as ex:
        for uid, msg in ex.map(one, jobs):
            print(uid, msg, flush=True)
