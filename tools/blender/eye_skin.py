#!/usr/bin/env python3
"""L16-4 skin at the joints of the eye stage's pieces (PIPELINE 34.L16-4): the primitives of eye_lib joined by surface, not by edges seen.

    blender -b -P tools/blender/eye_skin.py -- build <in.glb> <dsl.json> <out.glb> <technique>     # eye_lib.build + the skin
    python3.14 tools/blender/eye_skin.py run --id n005 --from v16-r1 --tag v16-skin-bridge --technique bridge   # a copy of the run, skinned, measured

The pieces of a DSL (eye_lib.py) overlap at a joint without boolean, so the eye sees the end of a limb sticking out of the next one.
Joints = pairs of pieces closer than GAP x height (convex distance, negative when they overlap) that share a bone or are parent and
child in the armature; joints.json lists them. Techniques (the skin of a joint takes the material of the piece of larger area, its
vertices the weights of the two bones by how near each piece is, so the stretch of a clip stays about the pieces'):
    bridge  two tubes (limbs): the end caps nearest each other are deleted and the rings joined by bridge loops (CUTS cuts); boxes and balls stay
    blend   the smooth-min of the two pieces' distance fields in a sphere of RADIUS x height round the joint, surface nets, Blender's
            quadric decimate to PATCH_TRIS, the faces of the pieces hidden under it deleted; nothing outside the sphere changes
    wrap    a 3-ring 8-sided sleeve over the joint, its vertices pulled onto the two pieces (a shrinkwrap on the convex planes)
    weld    no new geometry: coincident vertices of one material merged, smooth normals except on edges over SHARP degrees
bpy is imported inside the functions that need it: the pure helpers import and test without Blender."""
import argparse
import json
import math
import pathlib
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eye_lib as EL  # noqa: E402

TECHNIQUES = ("off", "bridge", "blend", "wrap", "weld")
UNIONS = ("union-material", "union-bone", "union-group")      # L17-2: eye_union.py, through the same build
GAP = 0.03          # joint: pieces this close (share of the height) or overlapping
RADIUS = 0.06       # blend: the sphere of the skin round a joint (share of the height); the patch reaches 1.25 x this
SPREAD = 1.25
SMOOTH_K = 0.03     # blend / weights: smooth-min width (share of the height)
VOXEL = 0.008       # blend: grid step (share of the height)
PATCH_TRIS = 30     # blend: triangles of one patch after the decimate
EXTRA = 150         # triangles the skin may add over the eye budget (the pieces use all of it: 33.L15-5); the acceptance reports the 700 anyway
BURIED = 0.003      # a face whose vertices all lie this far (share of the height) inside another piece of its bone is hidden: deleted
HIDDEN = 0.8        # blend: faces of the pieces entirely inside this share of the radius are under the skin
CUTS = 1            # bridge: rings cut in the middle of the bridge
SIDES = 8           # wrap: sleeve sides
OFFSET = 0.003      # wrap: the sleeve rides this far (share of the height) outside the pieces
SHARP = 40.0        # weld: degrees above which an edge keeps its crease
WELD_DIST = 0.004   # weld: merge distance (share of the height)
RUNS = HERE.parents[1] / "artifacts/model-sheets/runs/draft"


# ---------------------------------------------------------------- pure helpers (numpy)
def face_planes(verts, faces):
    """(normals (f, 3), offsets (f,)) with outward unit normals of the faces of a closed convex piece: inside is n . p < offset."""
    centre, n, d = verts.mean(0), [], []
    for f in faces:
        q = verts[f]
        nor = sum(np.cross(q[i], q[(i + 1) % len(q)]) for i in range(len(q)))
        size = np.linalg.norm(nor)
        if size < 1e-12:
            continue
        nor, off = nor / size, float(nor @ q.mean(0) / size)
        n.append(-nor if nor @ centre > off else nor)
        d.append(-off if nor @ centre > off else off)
    return np.array(n), np.array(d)


def convex_d(planes, pts):
    """Signed distance to a convex piece (exact inside and on the surface, a lower bound outside): max over its planes."""
    n, d = planes
    return (pts @ n.T - d).max(1)


def smin(a, b, k):
    """Polynomial smooth minimum: min(a, b) pulled down by up to k/4 where the two are within k."""
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.minimum(a, b) - h * h * k / 4


def samples_of(verts, faces):
    """Vertices and edge midpoints of a piece: where its surface is probed."""
    mids = [(verts[f[i]] + verts[f[(i + 1) % len(f)]]) / 2 for f in faces for i in range(len(f))]
    return np.vstack([verts, mids])


def related(a, b, parents):
    return a == b or parents.get(a) == b or parents.get(b) == a


def aabb_gap(p, q):
    return float(np.linalg.norm(np.maximum(np.maximum(q["lo"] - p["hi"], p["lo"] - q["hi"]), 0)))


def nearest(p, q):
    """{gap, centre} of two pieces: the least convex distance of one's samples to the other (negative = overlap) and the
    midpoint of the two samples that give it."""
    dq, dp = convex_d(q["planes"], p["samples"]), convex_d(p["planes"], q["samples"])
    i, j = int(dq.argmin()), int(dp.argmin())
    return {"gap": round(float(min(dq[i], dp[j])), 4), "centre": ((p["samples"][i] + q["samples"][j]) / 2).round(4).tolist()}


def find_joints(pieces, parents, height, gap=GAP):
    """[{a, b, gap, centre}] for the pairs of pieces (indices into `pieces`, each with bone, lo, hi, planes, samples) within gap x height."""
    reach, out = gap * height, []
    for i, p in enumerate(pieces):
        for j in range(i + 1, len(pieces)):
            q = pieces[j]
            if not related(p["bone"], q["bone"], parents) or aabb_gap(p, q) > reach:
                continue
            near = nearest(p, q)
            if near["gap"] <= reach:
                out.append({"a": i, "b": j, **near})
    return out


LIMBS = ("arm", "hand", "leg", "foot", "wing", "tail")      # roles of eye_lib whose joints are the articulations the eye sees


def rank_joints(joints, pieces):
    """Joints in the order the skin is spent on them: between different bones first, a limb at either end first, larger pieces first."""
    def key(j):
        a, b = pieces[j["a"]], pieces[j["b"]]
        return (a["bone"] == b["bone"], not {a["p"]["role"], b["p"]["role"]} & set(LIMBS), -min(a["area"], b["area"]))
    return sorted(joints, key=key)


def buried_faces(pieces, i, depth):
    """Indices of the faces of piece i whose vertices all lie more than `depth` inside another piece on the same bone."""
    p, gone = pieces[i], set()
    for j, q in enumerate(pieces):
        if j != i and q["bone"] == p["bone"]:
            inside = convex_d(q["planes"], p["verts"]) < -depth
            gone |= {k for k, f in enumerate(p["faces"]) if inside[f].all()}
    return sorted(gone)


def weight_toward_a(da, db, k):
    """Share of the bone of piece A at a point whose distances to A and B are da, db: 1 at A's surface, 1/2 where equal."""
    return np.clip(0.5 + (db - da) / (2 * k), 0.0, 1.0)


def hidden_faces(verts, faces, centre, radius):
    """Indices of the faces whose vertices all lie inside the sphere (centre, radius)."""
    inside = np.linalg.norm(verts - centre, axis=1) < radius
    return [i for i, f in enumerate(faces) if inside[list(f)].all()]


def patch_radius(pa, pb, centre, height):
    """Radius of the sphere of a blend patch: RADIUS x height, or the thicker piece's radius when that is more (the crease of two thick
    limbs lies a radius away from where they overlap)."""
    return max(RADIUS * height, axis_of(pa, centre)[1], axis_of(pb, centre)[1])


def blend_grid(pa, pb, centre, radius, height):
    """(grid, origin, voxel): the smooth union of the two pieces' distances on a cube round the joint, biased outward by a third of a voxel
    inside the patch (fading to nothing at its rim) so the skin lies over the pieces and not in them."""
    vox, reach = VOXEL * height, radius * SPREAD
    half = reach + 3 * vox
    n = int(math.ceil(2 * half / vox)) + 1
    origin = np.asarray(centre) - half
    axes = [origin[i] + vox * np.arange(n) for i in range(3)]
    pts = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    d = smin(convex_d(pa["planes"], pts), convex_d(pb["planes"], pts), SMOOTH_K * height)
    t = np.clip((np.linalg.norm(pts - centre, axis=1) / reach - 0.6) / 0.4, 0, 1)
    return (d - vox / 3 * (1 - t * t * (3 - 2 * t))).reshape(n, n, n), origin, vox


def crop(verts, tris, centre, reach):
    """The triangles whose centroid lies within `reach` of `centre`, vertices compacted."""
    keep = np.linalg.norm(verts[tris].mean(1) - centre, axis=1) <= reach
    used = np.unique(tris[keep])
    remap = np.full(len(verts), -1)
    remap[used] = np.arange(len(used))
    return verts[used], remap[tris[keep]]


def axis_of(piece, joint_point):
    """(unit direction from the piece's body toward the joint, radius across it): the end of a limb points along its axis."""
    c = piece["verts"].mean(0)
    u = np.asarray(joint_point) - c
    u = u / max(np.linalg.norm(u), 1e-9)
    across = piece["verts"] - c
    across = across - np.outer(across @ u, u)
    return u, float(np.linalg.norm(across, axis=1).mean())


def ring_basis(normal, ref=None):
    """Orthonormal (e1, e2) round `normal`; e1 follows `ref` (parallel transport) when given so rings do not twist."""
    normal = normal / np.linalg.norm(normal)
    if ref is None:
        ref = np.array([0.0, 0.0, 1.0]) if abs(normal[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = ref - (ref @ normal) * normal
    e1 = e1 / max(np.linalg.norm(e1), 1e-9)
    return e1, np.cross(normal, e1)


def sleeve_rings(pa, pb, joint, height):
    """(3 x SIDES points, 3 weights of A) of the sleeve over a joint: a ring in A's end, one at the joint, one in B's end."""
    centre = np.asarray(joint["centre"])
    ua, ra = axis_of(pa, centre)
    ub, rb = axis_of(pb, centre)
    ca, cb = centre - ua * 0.5 * ra, centre - ub * 0.5 * rb
    mid = (ca + cb) / 2 if np.linalg.norm(ca - cb) > 1e-9 else centre
    mid_n = ua - ub if np.linalg.norm(ua - ub) > 1e-6 else ua
    rings, ref = [], None
    for c, n, r in ((ca, ua, 1.15 * ra), (mid, mid_n, 1.2 * max(ra, rb)), (cb, -ub, 1.15 * rb)):
        e1, e2 = ring_basis(n, ref)
        ref = e1
        t = 2 * np.pi * np.arange(SIDES) / SIDES
        rings.append(c + max(r, 0.01 * height) * (np.cos(t)[:, None] * e1 + np.sin(t)[:, None] * e2))
    return np.vstack(rings), np.repeat([1.0, 0.5, 0.0], SIDES)


def pull_onto(planes_list, pts, offset, iters=4):
    """Move each point along the active plane of the nearer piece until it lies `offset` outside the union of the convex pieces."""
    pts = pts.copy()
    for _ in range(iters):
        for i, p in enumerate(pts):
            best = None
            for n, d in planes_list:
                s = n @ p - d
                k = int(s.argmax())
                best = (s[k], n[k]) if best is None or s[k] < best[0] else best
            pts[i] = p - (best[0] - offset) * best[1]
    return pts


# ---------------------------------------------------------------- Blender side
def piece_data(p, obj, slot):
    """The numpy record of a piece object (world-frame verts, faces, planes, box, area); the object is not touched."""
    m = obj.matrix_basis
    verts = np.array([tuple(m @ v.co) for v in obj.data.vertices])
    faces = [list(poly.vertices) for poly in obj.data.polygons]
    tube = p["op"] in ("tube", "between") and p.get("sides", 8) >= 5
    return {"p": p, "bone": p["bone"], "slot": slot, "verts": verts, "faces": faces, "planes": face_planes(verts, faces), "samples": samples_of(verts, faces),
            "lo": verts.min(0), "hi": verts.max(0), "tube": tube, "sides": p.get("sides", 8), "area": float(sum(poly.area for poly in obj.data.polygons))}


class Body:
    """The pieces and the skin as one bmesh with deform weights; vertex groups are the rig's bones."""

    def __init__(self, groups):
        import bmesh
        self.bm, self.groups = bmesh.new(), groups
        self.dl = self.bm.verts.layers.deform.verify()

    def add(self, verts, faces, slot, weights):
        """Add a mesh; `weights`: per vertex a {bone: weight}. (bm verts, bm faces)."""
        vs = [self.bm.verts.new(tuple(c)) for c in verts]
        for v, w in zip(vs, weights):
            for bone, x in w.items():
                v[self.dl][self.groups[bone]] = float(x)
        fs = []
        for f in faces:
            if len(set(f)) < 3:
                continue
            try:
                face = self.bm.faces.new([vs[i] for i in f])
            except ValueError:          # the decimate left a duplicate face
                continue
            face.material_index = slot
            fs.append(face)
        return vs, fs

    def weights_of(self, v):
        names = {i: n for n, i in self.groups.items()}
        return {names[i]: w for i, w in v[self.dl].items()}

    def average_weights(self, verts, old):
        """Give each new vertex the mean weights of the old ones (their vkeys in `old`) it shares an edge with."""
        for v in verts:
            around = [e.other_vert(v) for e in v.link_edges if vkey(e.other_vert(v)) in old]
            acc = {}
            for u in around:
                for g, w in u[self.dl].items():
                    acc[g] = acc.get(g, 0.0) + w / len(around)
            v[self.dl].clear()
            for g, w in acc.items():
                v[self.dl][g] = w


def parent_map(arm):
    return {b.name: b.parent.name for b in arm.data.bones if b.parent}


def caps_of(t):
    """The two end caps of a tube as (bm face, centre, radius)."""
    out = []
    for f in t["bf"]:
        if f.is_valid and len(f.verts) == t["sides"]:
            c = np.array(f.calc_center_median())
            out.append((f, c, float(np.mean([np.linalg.norm(np.array(v.co) - c) for v in f.verts]))))
    return out


def bridge_candidates(a, b):
    """(distance, cap of a, cap of b) of the cap pairs of two tubes, nearest first."""
    pairs = [(float(np.linalg.norm(x[1] - y[1])), x, y) for x in caps_of(a) for y in caps_of(b)]
    return sorted(pairs, key=lambda t: t[0])


def vkey(v):
    """A vertex by its place: bmesh operators reset tags and rebuild wrappers, a position survives them."""
    return tuple(np.round(np.array(v.co), 5))


def fkey(f):
    return frozenset(vkey(v) for v in f.verts)


def bridge_one(body, a, b, cap_a, cap_b, cuts):
    """Delete the two caps and bridge their rings; the new faces carry the material of the larger piece, the new vertices mean weights."""
    import bmesh
    bm = body.bm
    before_v, before_f = {vkey(v) for v in bm.verts}, {fkey(f) for f in bm.faces}
    ring = list(cap_a[0].edges) + list(cap_b[0].edges)
    bmesh.ops.delete(bm, geom=[cap_a[0], cap_b[0]], context="FACES_ONLY")
    out = bmesh.ops.bridge_loops(bm, edges=ring, use_pairs=False, use_cyclic=False, use_merge=False, merge_factor=0.5, twist_offset=0)
    if cuts:
        bmesh.ops.subdivide_edges(bm, edges=[e for e in out["edges"] if e.is_valid], cuts=cuts, use_grid_fill=True)
    fresh = [f for f in bm.faces if fkey(f) not in before_f]
    for f in fresh:
        f.material_index = a["slot"] if a["area"] >= b["area"] else b["slot"]
    body.average_weights([v for v in bm.verts if vkey(v) not in before_v], before_v)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return len(fresh)


def do_bridge(body, pieces, joints, budget, cuts=CUTS):
    """Bridge the nearest caps of the tubes of each joint (a cap serves one bridge), while the triangles stay under `budget`. Count of bridges."""
    used, done = set(), 0
    for j in joints:
        a, b = pieces[j["a"]], pieces[j["b"]]
        if not (a["tube"] and b["tube"]) or tris_of_bm(body.bm) + 4 * a["sides"] * (cuts + 1) > budget:
            continue
        for dist, ca, cb in bridge_candidates(a, b):
            if dist <= ca[2] + cb[2] and not {ca[0], cb[0]} & used:
                bridge_one(body, a, b, ca, cb, cuts)
                used |= {ca[0], cb[0]}
                done += 1
                break
    return done


def decimate(verts, tris, target):
    """Blender's quadric collapse of a triangle soup to about `target` triangles."""
    import bpy
    if len(tris) <= target:
        return verts, tris
    me = bpy.data.meshes.new("patch")
    me.from_pydata(verts.tolist(), [], tris.tolist())
    ob = bpy.data.objects.new("patch", me)
    bpy.context.collection.objects.link(ob)
    ob.modifiers.new("d", "DECIMATE").ratio = target / len(tris)
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    m.calc_loop_triangles()
    v = np.array([tuple(x.co) for x in m.vertices])
    t = np.array([tuple(x.vertices) for x in m.loop_triangles])
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    return v, t


def skin_weights(pa, pb, verts, height):
    """Per vertex {bone: w}: the bones of the two pieces by how near each is."""
    wa = weight_toward_a(convex_d(pa["planes"], verts), convex_d(pb["planes"], verts), SMOOTH_K * height)
    if pa["bone"] == pb["bone"]:
        return [{pa["bone"]: 1.0} for _ in wa]
    return [{pa["bone"]: float(w), pb["bone"]: float(1 - w)} for w in wa]


def delete_faces(body, faces):
    import bmesh
    bmesh.ops.delete(body.bm, geom=[f for f in faces if f.is_valid], context="FACES")
    bmesh.ops.delete(body.bm, geom=[v for v in body.bm.verts if not v.link_faces], context="VERTS")


def do_blend(body, pieces, joints, height, budget):
    """A smooth-union patch over each joint, the faces it hides deleted, while the triangles stay under `budget`. Count of patches."""
    from retopo_mc import surface_nets
    done = 0
    for j in joints:
        if tris_of_bm(body.bm) + PATCH_TRIS > budget:
            continue
        pa, pb, c = pieces[j["a"]], pieces[j["b"]], np.array(j["centre"])
        j["radius"] = round(patch_radius(pa, pb, c, height), 4)
        grid, origin, vox = blend_grid(pa, pb, c, j["radius"], height)
        if not ((grid < 0).any() and (grid >= 0).any()):
            continue
        verts, tris = crop(*surface_nets(grid, origin, vox), c, j["radius"] * SPREAD)
        if len(tris) < 4:
            continue
        verts, tris = decimate(verts, tris, PATCH_TRIS)
        if tris_of_bm(body.bm) + len(tris) > budget:        # the decimate may land over its target: this patch does not fit
            continue
        slot = pa["slot"] if pa["area"] >= pb["area"] else pb["slot"]
        body.add(verts, tris.tolist(), slot, skin_weights(pa, pb, verts, height))
        for p in (pa, pb):
            gone = hidden_faces(p["verts"], p["faces"], c, HIDDEN * j["radius"])
            delete_faces(body, [p["bf"][i] for i in gone])
        done += 1
    return done


def do_wrap(body, pieces, joints, height, budget):
    """A sleeve over each joint while the triangles stay under `budget`. Count of sleeves."""
    done = 0
    for j in joints:
        if tris_of_bm(body.bm) + 4 * SIDES > budget:
            continue
        pa, pb = pieces[j["a"]], pieces[j["b"]]
        ring, share = sleeve_rings(pa, pb, j, height)
        ring = pull_onto([pa["planes"], pb["planes"]], ring, OFFSET * height)
        faces = [[s * SIDES + i, s * SIDES + (i + 1) % SIDES, (s + 1) * SIDES + (i + 1) % SIDES, (s + 1) * SIDES + i] for s in range(2) for i in range(SIDES)]
        weights = [({pa["bone"]: float(w), pb["bone"]: float(1 - w)} if pa["bone"] != pb["bone"] else {pa["bone"]: 1.0}) for w in share]
        body.add(ring, faces, pa["slot"] if pa["area"] >= pb["area"] else pb["slot"], weights)
        done += 1
    return done


def do_weld(body, pieces, height):
    """Merge coincident vertices of one material, smooth faces, sharp edges only above SHARP degrees. Vertices merged."""
    import bmesh
    bm, before = body.bm, len(body.bm.verts)
    for slot in {p["slot"] for p in pieces}:
        bmesh.ops.remove_doubles(bm, verts=list({v for f in bm.faces if f.material_index == slot for v in f.verts}), dist=WELD_DIST * height)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        e.smooth = len(e.link_faces) != 2 or e.calc_face_angle(0.0) <= math.radians(SHARP)
    return before - len(bm.verts)


def components(bm):
    """Connected pieces of the mesh (union-find over edges)."""
    parent = {v: v for v in bm.verts}

    def find(v):
        while parent[v] is not v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v
    for e in bm.edges:
        parent[find(e.verts[0])] = find(e.verts[1])
    return len({find(v) for v in bm.verts})


def components_of(bm, verts):
    """Connected pieces of the mesh among `verts` (the vertices of one set of faces; their edges stay inside it)."""
    seen, n = set(), 0
    for v in verts:
        if v in seen:
            continue
        n += 1
        stack = [v]
        while stack:
            u = stack.pop()
            if u not in seen:
                seen.add(u)
                stack += [e.other_vert(u) for e in u.link_edges]
    return n


def tris_of_bm(bm):
    return sum(len(f.verts) - 2 for f in bm.faces)


def make_materials(dsl):
    import bpy
    colours, mats = dsl.get("colours") or {}, {}
    for p in dsl["pieces"]:
        if p["mat"] not in mats:
            m = bpy.data.materials.new(p["mat"])
            m.use_nodes = True
            bsdf = m.node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Base Color"].default_value = EL.srgb(p.get("colour", colours.get(p["mat"])))
            bsdf.inputs["Roughness"].default_value = 0.9
            mats[p["mat"]] = m
    return mats


def cull(body, pieces, height):
    """Delete the faces buried in another piece of their bone: invisible, and the triangles the skin is paid from. Count of triangles."""
    before = tris_of_bm(body.bm)
    for i, p in enumerate(pieces):
        delete_faces(body, [p["bf"][k] for k in buried_faces(pieces, i, BURIED * height)])
    return before - tris_of_bm(body.bm)


def apply_technique(technique, body, pieces, joints, height, budget=EL.BUDGET + EXTRA):
    if technique in UNIONS:
        import eye_union
        return eye_union.hook(technique)(technique, body, pieces, joints, height)
    if technique == "bridge":
        return do_bridge(body, pieces, joints, budget)
    if technique == "blend":
        return do_blend(body, pieces, joints, height, budget)
    if technique == "wrap":
        return do_wrap(body, pieces, joints, height, budget)
    return do_weld(body, pieces, height) if technique == "weld" else 0


def build(src, dsl, out, technique):
    """eye_lib.build with the skin of `technique` between the pieces and the export; the info dict (tris before / after, joints, count, components)."""
    import bpy
    arm, old = EL.load_rig(src)
    mats = make_materials(dsl)
    EL.drop_faces(old, set())
    old.data.materials.clear()
    names = list(mats)
    for m in mats.values():
        old.data.materials.append(m)
    body, pieces = Body({g.name: g.index for g in old.vertex_groups}), []
    for p in dsl["pieces"]:
        obj = EL.make_piece(p, mats[p["mat"]])
        pieces.append(piece_data(p, obj, names.index(p["mat"])))
        mesh = obj.data
        bpy.data.objects.remove(obj)
        bpy.data.meshes.remove(mesh)
        piece = pieces[-1]
        piece["bv"], piece["bf"] = body.add(piece["verts"], piece["faces"], piece["slot"], [{p["bone"]: 1.0}] * len(piece["verts"]))
    height = float(max(pc["hi"][2] for pc in pieces) - min(pc["lo"][2] for pc in pieces))
    skinned = technique in ("bridge", "blend", "wrap")
    joints = rank_joints(find_joints(pieces, parent_map(arm), height), pieces) if skinned else []
    before, culled = tris_of_bm(body.bm), cull(body, pieces, height) if skinned else 0
    done = apply_technique(technique, body, pieces, joints, height)
    info = {"technique": technique, "tris_pieces": before, "culled": culled, "tris": tris_of_bm(body.bm), "pieces": len(pieces), "joints": joints, "skins": done,
            "components": components(body.bm), "body_components": getattr(body, "union_components", None), "unions": getattr(body, "union_log", None), "height": round(height, 3)}
    body.bm.to_mesh(old.data)
    body.bm.free()
    export(arm, old, out)
    return info


def export(arm, old, out):
    import bpy
    old.name = old.data.name = "eye"
    if not any(m.type == "ARMATURE" for m in old.modifiers):
        old.modifiers.new("Armature", "ARMATURE").object = arm
    old.parent = arm
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", export_yup=True, export_animations=True,
                              export_animation_mode="ACTIONS", export_apply=True, export_skins=True, export_morph=False)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    info = build(args[1], json.loads(pathlib.Path(args[2]).read_text()), args[3], args[4])
    pathlib.Path(args[3]).with_suffix(".json").write_text(json.dumps(info))
    print("SKIN", json.dumps({k: v for k, v in info.items() if k != "joints"}))


# ---------------------------------------------------------------- python side
def run_blender(src, dsl_path, out, technique):
    return subprocess.run(["nice", "-n", "10", "blender", "-b", "-P", str(HERE / "eye_skin.py"), "--", "build", str(src), str(dsl_path), str(out), technique],
                          capture_output=True, text=True)


def skin_build(src, dsl, out, technique):
    """eye_skin build in Blender: the GLB `out` and its info dict; RuntimeError when no GLB came out."""
    out = pathlib.Path(out)
    dsl_path = out.with_suffix(".dsl.json")
    dsl_path.write_text(json.dumps(dsl))
    out.unlink(missing_ok=True)
    p = run_blender(src, dsl_path, out, technique)
    dsl_path.unlink()
    if not out.exists():
        raise RuntimeError("eye_skin build failed: " + (p.stderr or p.stdout)[-400:])
    info = json.loads(out.with_suffix(".json").read_text())
    out.with_suffix(".json").unlink()
    return info


def apply_stage(src, dsl, out, technique, clay="B4B4B4", always=False):
    """The one call of eye_stage.finish: model.glb and clay.glb of the run rebuilt from the last DSL with the skin. {} when technique is off."""
    if technique == "off" and not always:
        return {}
    info = skin_build(src, dsl, out / "model.glb", technique)
    skin_build(src, dict(dsl, colours={}, pieces=[dict(p, colour=clay) for p in dsl["pieces"]]), out / "clay.glb", technique)
    (out / "joints.json").write_text(json.dumps(info.pop("joints"), indent=1))
    return info


# ---------------------------------------------------------------- the battery: a copy of a run, skinned and measured
def final_round(src_run):
    """(round dir, its dsl) of the last built round of a v16 run."""
    s = json.loads((src_run / "eye/summary.json").read_text())
    d = src_run / "eye" / f"round-{s['final_round']}"
    return d, json.loads((d / "dsl.json").read_text())


def geometry_stats(glb):
    """Planarity, crease share (edges over look.CREASE_DEG) and verts / tri of a GLB's welded mesh; nonmanifold edges, components of the file."""
    import look
    import mesh_lint
    doc, blob = mesh_lint.read_glb(pathlib.Path(glb))
    pos, _, _, tri = mesh_lint.geometry(doc, blob)
    uniq, inv = np.unique(np.round(pos / mesh_lint.WELD).astype(np.int64), axis=0, return_inverse=True)
    wt, wp = inv.reshape(-1)[tri], uniq * mesh_lint.WELD
    wt = wt[(wt[:, 0] != wt[:, 1]) & (wt[:, 1] != wt[:, 2]) & (wt[:, 0] != wt[:, 2])]
    n, w = look.face_normals(wp, wt)
    uniq, (rows, f0, f1) = look.edge_table(wt)
    ang = look.dihedral(n, f0, f1, w)
    return {"planarity": round(look.planarity(wp, wt), 3), "crease_pct": round(100 * float((ang >= look.CREASE_DEG).mean()), 1) if len(ang) else 0.0,
            "verts_per_tri": round(len(uniq) / max(len(wt), 1), 2)}


def run_unit(unit_id, src_name, tag, technique, log=print):
    """runs/draft/<id>/<tag> = a copy of <src_name> whose model.glb / clay.glb are rebuilt with the skin, outlined, measured. The summary."""
    import eye_stage
    import mesh_lint
    import outline
    src_run, out = RUNS / unit_id / src_name, RUNS / unit_id / tag
    if out.exists():
        raise SystemExit(f"{out} exists: rename it -invalid<ts> first")
    shutil.copytree(src_run, out, ignore=shutil.ignore_patterns("pairwise*"))
    rd, dsl = final_round(src_run)
    t0 = time.monotonic()
    info = apply_stage(out / "eye/input.glb", dsl, out, technique, always=True)
    skin_s = time.monotonic() - t0
    spec = json.loads((src_run / "spec.json").read_text()) if (src_run / "spec.json").exists() else {}
    rig = spec.get("rig") or "biped"
    ev = eye_stage.measure(out / "model.glb", out / "eye/skin", eye_stage.REFS / unit_id / "sheet.jpg", rig)
    stats = geometry_stats(out / "model.glb")
    outline.apply(out / "model.glb", hull=True)
    stretch = eye_stage.stretch_of(out / "model.glb", out / "eye/skin-anim.json")
    lint = mesh_lint.lint(out / "model.glb")
    summary = {"unit": unit_id, "technique": technique, "from": src_name, "skin_s": round(skin_s, 1), **{k: v for k, v in info.items()}, **stats,
               "parts": ev["parts"], "views": ev["views"], "disaster": ev["disaster"], "stretch": stretch,
               "file_tris": lint["tris"], "nonmanifold": lint["nonmanifold_edges"], "components_body": lint["components_body"], "compactness": lint["compactness"]}
    (out / "skin.json").write_text(json.dumps(summary, indent=1))
    log(f"{unit_id} {tag}: {info.get('tris_pieces')} -> {info.get('tris')} tris, {info.get('skins')} skins, parts {ev['parts']}, {skin_s:.0f}s")
    return summary


def cli():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=("run",))
    ap.add_argument("--id", required=True)
    ap.add_argument("--from", dest="src", default="v16-r1")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--technique", choices=TECHNIQUES, required=True)
    a = ap.parse_args()
    run_unit(a.id, a.src, a.tag, a.technique)


if __name__ == "__main__":
    if sys.argv[sys.argv.index("--") + 1:][:1] == ["build"] if "--" in sys.argv else False:
        main()
    else:
        cli()
