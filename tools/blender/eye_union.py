#!/usr/bin/env python3
"""L17-2 union by material of the eye stage's pieces (PIPELINE 35.L17-2): 40-65 primitives -> a few welded meshes of ~100 triangles.

    python3.14 tools/blender/eye_union.py run --id n005 --from v16-r3 --tag v17-union-material --mode material

The pieces of a DSL (eye_lib.py) are grouped; the pieces of one group become ONE surface: the smooth-min of their distance fields
(a small k, so a joint gets skin and the pieces do not melt), surface nets on the group's box, guarded QEM (retopo.reduce) down to the group's
share of BUDGET, vertices weighted by the bone of the nearest piece (a blend over JOINT_BLEND where two bones meet). Props (role 'prop') stay
rigid pieces. Modes: material (the pieces of one material), group (material and touching: one mesh per cluster), bone (the pieces of one bone).
eye_skin.build is the Blender side (`--eye-union` reaches it as the technique 'union-<mode>'); this file is numpy and imports without Blender."""
import argparse
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eye_lib as EL  # noqa: E402
import eye_mold  # noqa: E402
import eye_skin as K  # noqa: E402
import retopo  # noqa: E402
from retopo_mc import surface_nets  # noqa: E402

MODES = ("off", "material", "bone", "group")
JOINTS = ("off", "smooth")  # lever 3 (author 2026-11-05): smooth = a limb's union also holds a stub of the trunk piece it touches (and the trunk one of the limb),
JOINT_GAP = 0.02            # cut to a sphere of JOINT_R round the contact, blended with JOINT_K: a fillet at the shoulder, hip, neck, tail root, never a group union
JOINT_R = 0.07
JOINT_K = 0.05
REDUCERS = ("qem", "cvt")   # L18-2b: the step from the surface-nets grid to the budget: guarded QEM (retopo.reduce) or curvature-guided CVT (retopo.cvt)
SMOOTH_K = 0.02         # smooth-min width, share of the height
VOXEL = 0.006           # grid step, share of the height
JOINT_BLEND = 0.03      # the weights of two bones cross-fade over this (share of the height) of difference of distance
TOUCH = 0.03            # group: pieces this close (share of the height) are one cluster
BUDGET = 550            # triangles of the unions of a model
TOTAL = 700             # unions + props
MIN_TRIS = 12
FEATURES = 30           # retopo.reduce keeps the edges of the primitives sharper than this (degrees)
DEV = 0.015             # retopo.reduce refuses a collapse that moves a triangle farther than this (share of the height) from the surface
KEEP = 0.9              # share of its pieces' triangles a union keeps (L17-2: budget by area at 100 tris per mesh erased limbs)
DETAIL = 0.10           # L18-2: a piece whose longest side is under this share of the height (a buckle, a slit, an eye, a lens) stays rigid, like a prop:
                        # the smooth-min and the QEM of its group erased it (n01X's furnace slit) and the paint has nothing left to colour
FAR = 10.0
SHARP = K.SHARP


def is_prop(piece):
    return piece["p"]["role"] == "prop"


def is_detail(piece, height):
    """A small piece the union would swallow: kept rigid (L18-2)."""
    return float(np.max(piece["hi"] - piece["lo"])) < DETAIL * height


def rigid(piece, height):
    return is_prop(piece) or is_detail(piece, height)


def union_find(n, pairs):
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in pairs:
        parent[find(a)] = find(b)
    return [find(i) for i in range(n)]


def clusters_of(pieces, idx, height):
    """The pieces of `idx` split into the sets that touch (convex gap <= TOUCH x height, transitively): [[index, ...], ...]."""
    reach, pairs = TOUCH * height, []
    for x, i in enumerate(idx):
        for y in range(x + 1, len(idx)):
            j = idx[y]
            if K.aabb_gap(pieces[i], pieces[j]) <= reach and K.nearest(pieces[i], pieces[j])["gap"] <= reach:
                pairs.append((x, y))
    root = union_find(len(idx), pairs)
    out = {}
    for x, r in enumerate(root):
        out.setdefault(r, []).append(idx[x])
    return list(out.values())


def groups_of(pieces, mode, height):
    """[[cluster, ...], ...]: one entry per mesh budget; a cluster is a list of piece indices united in one field. Props are left out."""
    body = [i for i, p in enumerate(pieces) if not rigid(p, height)]
    key = (lambda i: pieces[i]["p"]["mat"]) if mode != "bone" else (lambda i: pieces[i]["bone"])
    by = {}
    for i in body:
        by.setdefault(key(i), []).append(i)
    if mode == "group":
        return [[c] for idx in by.values() for c in clusters_of(pieces, idx, height)]
    return [clusters_of(pieces, idx, height) for idx in by.values()]


def split_budget(tris, total=BUDGET, keep=KEEP, lo=MIN_TRIS):
    """Triangles per group from the triangles of its pieces: KEEP of them (the union drops what is hidden; a primitive is already the
    cheapest shape that holds, so cutting deeper loses limbs), at least lo, the whole scaled down to fit `total` (never under lo)."""
    want = [max(lo, round(keep * t)) for t in tris]
    scale = min(1.0, total / max(sum(want), 1))
    return [max(lo, int(w * scale)) for w in want]


def joint_stubs(members, pieces, height):
    """[(piece, centre, radius)]: the body pieces of another bone that touch a member (lever 3), each with the contact point and the sphere the
    stub is cut to; one stub per foreign piece, at its nearest member."""
    bones, reach, out = {m["bone"] for m in members}, JOINT_GAP * height, []
    for f in pieces:
        if f["bone"] in bones or rigid(f, height):
            continue
        best = None
        for m in members:
            if K.aabb_gap(m, f) > reach:
                continue
            near = K.nearest(m, f)
            if near["gap"] <= reach and (best is None or near["gap"] < best["gap"]):
                best = near
        if best:
            out.append((f, np.asarray(best["centre"]), JOINT_R * height))
    return out


def field_of(members, height, stubs=()):
    """sdf(points (N, 3)) of the smooth union of the convex `members` (piece records); each piece is read only near itself (the field of a
    convex piece is a lower bound away from it). `stubs` (joint_stubs) join with JOINT_K inside their sphere. (The mold of lever 1 is not a
    term here: a blended hull at a 14-20 triangle target left the CVT fragments; eye_mold.inflate moves the pieces' vertices instead, before the plan.)"""
    k = SMOOTH_K * height

    def sdf(pts):
        d = np.full(len(pts), FAR)
        for p in members:
            near = ((pts > p["lo"] - 2 * k) & (pts < p["hi"] + 2 * k)).all(1)
            if near.any():
                di = np.full(len(pts), FAR)
                di[near] = K.convex_d(p["planes"], pts[near])
                d = K.smin(d, di, k)
        for f, c, r in stubs:
            dj = np.maximum(K.convex_d(f["planes"], pts), np.linalg.norm(pts - c, axis=1) - r)
            d = K.smin(d, dj, JOINT_K * height)
        return d
    return sdf


def pieces_mesh(members):
    """(verts, tris) of the members as they are, side by side, not united (a primitive is the cheapest shape that holds)."""
    verts, tris, base = [], [], 0
    for m in members:
        verts.append(np.asarray(m["verts"], float))
        tris += [[base + f[0], base + f[i], base + f[i + 1]] for f in m["faces"] for i in range(1, len(f) - 1)]
        base += len(m["verts"])
    return np.concatenate(verts), np.array(tris)


def reduced(verts, tris, target, sdf, dev, reducer):
    """(verts, tris) of `reducer` (REDUCERS) to about `target`; the CVT falls to the guarded QEM on an empty dual (a cluster too thin for its
    seeds: n00U's legs)."""
    if reducer == "cvt":
        try:
            return retopo.cvt(verts, tris, target, sdf=sdf, max_dev=dev)[:2]
        except ValueError:
            pass
    return retopo.reduce(verts, tris, target, sdf=sdf, max_dev=dev)[:2]


def union_mesh(members, height, target, vox=None, reducer="qem", stubs=()):
    """(verts, tris) of the union of `members`, reduced to about `target` triangles by `reducer` (REDUCERS); ([], []) when nothing came out.
    L19-0: with the CVT, a cluster whose QEM fallback refused the collapses (n00U's legs: 106 triangles for a target of 25, 704 in all) keeps
    its pieces as they are instead: a union never costs more triangles than the primitives it replaces, so the 700 budget holds.
    A single piece is still united when a joint stub changes its shape."""
    if len(members) == 1 and not stubs:      # nothing to unite: the piece as it is (a primitive is the cheapest shape that holds)
        return pieces_mesh(members)
    vox = vox or VOXEL * height
    pad = 3 * vox + 2 * SMOOTH_K * height
    boxes = [(p["lo"], p["hi"]) for p in members] + [(c - r, c + r) for _, c, r in stubs]
    lo, hi = np.min([b[0] for b in boxes], 0) - pad, np.max([b[1] for b in boxes], 0) + pad
    n = np.ceil((hi - lo) / vox).astype(int) + 1
    axes = [lo[i] + vox * np.arange(n[i]) for i in range(3)]
    pts = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    sdf = field_of(members, height, stubs)
    verts, tris = surface_nets(sdf(pts).reshape(*n), lo, vox)
    if len(tris) <= target:
        return verts, tris
    verts, tris = reduced(verts, tris, target, sdf, DEV * height, reducer)
    own = sum(len(f) - 2 for m in members for f in m["faces"])
    if reducer == "cvt" and (len(tris) > own or len(tris) < target / 2):     # over the pieces' cost, or broken to fragments (an inflated shin + paw: 4 of 29, 2026-11-05): the pieces as they are
        return pieces_mesh(members)
    return verts, np.asarray(tris)


def face_slots(members, verts, tris):
    """Per triangle the material slot of the piece nearest its centre."""
    c = verts[tris].mean(1)
    d = np.stack([K.convex_d(p["planes"], c) for p in members], 1)
    return [members[i]["slot"] for i in d.argmin(1)]


def vertex_weights(members, verts, height):
    """Per vertex {bone: w}: the bone of the nearest piece, cross-faded with the next nearest other bone where the two are within JOINT_BLEND."""
    bones = sorted({p["bone"] for p in members})
    if len(bones) == 1:
        return [{bones[0]: 1.0} for _ in verts]
    near = np.stack([np.min([K.convex_d(p["planes"], verts) for p in members if p["bone"] == b], 0) for b in bones], 1)
    order = np.argsort(near, 1)
    rows = np.arange(len(verts))
    d1, d2 = near[rows, order[:, 0]], near[rows, order[:, 1]]
    w1 = K.weight_toward_a(d1, d2, JOINT_BLEND * height)
    return [{bones[a]: float(w), bones[b]: float(1 - w)} for a, b, w in zip(order[:, 0], order[:, 1], w1)]


def build_group(clusters, pieces, height, target, reducer="qem", joints="off"):
    """The unions of one group's clusters: [(members, verts, tris, slots, weights, stubs)]; `target` is shared by area. The stubs of the joints
    (lever 3) weigh in the bones of their vertices; the materials stay the members'."""
    cost = [sum(EL.tris_of(pieces[i]["p"]) for i in c) for c in clusters]
    out = []
    for c, a in zip(clusters, cost):
        members = [pieces[i] for i in c]
        stubs = joint_stubs(members, pieces, height) if joints == "smooth" and len(members) > 1 else []     # a lone limb piece keeps its 14 triangles: the fillet is the trunk's
        verts, tris = union_mesh(members, height, max(MIN_TRIS, int(target * a / sum(cost))), reducer=reducer, stubs=stubs)
        if len(tris):
            out.append((c, verts, tris, face_slots(members, verts, tris), vertex_weights(members + [s[0] for s in stubs], verts, height), len(stubs)))
    return out


def plan(pieces, mode, height, prop_tris):
    """[(group of clusters, triangles)]: the groups and their budgets; the unions leave room for the props under TOTAL."""
    groups = groups_of(pieces, mode, height)
    tris = [sum(EL.tris_of(pieces[i]["p"]) for c in g for i in c) for g in groups]
    return list(zip(groups, split_budget(tris, min(BUDGET, TOTAL - prop_tris))))


# ---------------------------------------------------------------- Blender side (eye_skin.build calls apply)
def prop_tris_of(pieces, height=None):
    """Triangles of the pieces that stay rigid (props, and the small details when `height` is given)."""
    return sum(len(f) - 2 for p in pieces if (is_prop(p) if height is None else rigid(p, height)) for f in p["faces"])


def smooth(body, faces):
    for f in faces:
        f.smooth = True
    for e in {e for f in faces for e in f.edges}:
        e.smooth = len(e.link_faces) != 2 or e.calc_face_angle(0.0) <= math.radians(SHARP)


def apply(mode, body, pieces, joints, height, reducer="qem"):
    """eye_skin.build hook: replace the pieces of each group by their union (the props stay). Count of meshes. body.opts (the DSL's
    union_opts, eye_stage.finish): {mold: <run>/eye/mold dir or None, joints: off|smooth}."""
    opts = getattr(body, "opts", None) or {}
    soft = [p for p in pieces if not rigid(p, height)]
    mold = eye_mold.load(opts.get("mold"), soft, height)
    body.union_mold = mold.report if mold else None
    if mold and mold.ok:
        body.union_mold["inflate"] = eye_mold.inflate(soft, mold, height, VOXEL * height)      # lever 1: the pieces fill out to the hull, then unite as before
    done, mine, log = 0, [], []
    for group, target in plan(pieces, mode, height, prop_tris_of(pieces, height)):
        for c, verts, tris, slots, weights, stubs in build_group(group, pieces, height, target, reducer, opts.get("joints", "off")):
            vs, _ = body.add(verts, [], 0, weights)
            faces = []
            for t, s in zip(tris.tolist(), slots):
                try:
                    f = body.bm.faces.new([vs[i] for i in t])
                except ValueError:          # the reduce left a duplicate face
                    continue
                f.material_index = s
                faces.append(f)
            smooth(body, faces)
            mine += vs
            log.append([len(c), target, len(faces), stubs])
            K.delete_faces(body, [f for i in c for f in pieces[i]["bf"]])
            done += 1
    body.union_components, body.union_log = K.components_of(body.bm, mine), log
    return done


def parse_technique(technique):
    """('bone', 'cvt') of 'union-bone@cvt'; the reducer defaults to qem."""
    mode, _, reducer = technique.split("-", 1)[1].partition("@")
    return mode, reducer or "qem"


def technique_of(mode, reducer="qem"):
    return f"union-{mode}" + (f"@{reducer}" if reducer != "qem" else "")


def hook(technique):
    """The eye_skin.build `apply` of the technique 'union-<mode>[@<reducer>]'."""
    mode, reducer = parse_technique(technique)
    return lambda _t, body, pieces, joints, height: apply(mode, body, pieces, joints, height, reducer)


def cli():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=("run",))
    ap.add_argument("--id", required=True)
    ap.add_argument("--from", dest="src", default="v16-r3")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--mode", choices=MODES[1:], required=True)
    ap.add_argument("--reduce", choices=REDUCERS, default="qem")
    a = ap.parse_args()
    K.run_unit(a.id, a.src, a.tag, technique_of(a.mode, a.reduce))


if __name__ == "__main__":
    cli()
