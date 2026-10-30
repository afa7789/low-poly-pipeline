#!/usr/bin/env python3
"""Polish ops: the hands of the polish stage (PIPELINE 31.L13-1).

    python3.14 tools/blender/polish_ops.py run <in.glb> <out.glb> <code.py> --sheet <sheet.jpg> [--layout unit] [--cams '{"top": -20}']
    python3.14 tools/blender/polish_ops.py carry <pre.glb> <post.glb> <model.glb> <out.glb>

`run` executes the agent's Python on the welded mesh of a clay GLB and writes the result. No Blender: like deform_to_sheet.py
only POSITION and NORMAL bytes of the GLB change (D.rewrite), so skin, weights, UVs, materials and clips stay what they were -
the rig survives by construction, and an op costs 1 s instead of a Blender start. The code sees:

  scene            .pos (N,3) welded vertices, Z-up frame of the cameras (x right in front, y depth, z up); .tri; .H height;
                   .bones (N,) dominant bone name of every vertex; .views {name: deform_to_sheet.View} (sheet panel, camera)
  np               numpy
  helpers          parts() shrink_part move_part scale_part erode_toward_view smooth_region straighten_prop snap_feet_to_ground

Amounts are fractions of the model height H. A part is a bone name, or a bone family ('leg1' = leg1.upper + leg1.lower).
`erode_toward_view` is the tool that attacks red (model outside the sheet) directly.
"""
import argparse
import json
import pathlib
import sys
import traceback

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import deform_to_sheet as D  # noqa: E402
import mesh_lint as ML  # noqa: E402
import optimize_verts as OV  # noqa: E402

VIEWS = ("front", "left", "back", "top", "bottom", "rts")
AXES = {"x": 0, "y": 1, "z": 2}
SOLE = 0.02            # vertices this close to the ground (H) keep their height, as the deformation does
PULL, ANCHOR = 10.0, 5.0   # weights of the erode targets against "stay put" in the smoothness solve (deform_to_sheet's)


def vertex_bones(glb):
    """Dominant bone name (largest skin weight) of every file vertex of `glb`, primitives merged like mesh_lint.geometry."""
    doc, blob = ML.read_glb(pathlib.Path(glb))
    names = [doc["nodes"][j]["name"] for j in doc["skins"][0]["joints"]]
    out = []
    for m in doc["meshes"]:
        for p in m["primitives"]:
            joint = ML.accessor(doc, blob, p["attributes"]["JOINTS_0"]).astype(np.int64)
            weight = ML.accessor(doc, blob, p["attributes"]["WEIGHTS_0"]).astype(np.float64)
            out += [names[j] for j in joint[np.arange(len(joint)), weight.argmax(1)]]
    return np.array(out, dtype=object)


class Scene:
    def __init__(self, pos, tri, bones, views):
        self.pos, self.tri, self.bones, self.views = pos, tri, np.asarray(bones, dtype=object), views
        self.H = float(np.ptp(pos[:, 2]))
        self._lap = None

    @property
    def lap(self):
        if self._lap is None:
            self._lap = D.laplacian(self.tri, len(self.pos))
        return self._lap

    def mask(self, part=None):
        """Boolean mask of the vertices of a bone / bone family; every vertex without a name."""
        if part is None:
            return np.ones(len(self.pos), bool)
        sel = np.array([b == part or b.startswith(part + ".") or b.split(".")[0] == part for b in self.bones])
        if not sel.any():
            raise KeyError(f"no part '{part}'; parts: {sorted(set(self.bones))}")
        return sel

    def view(self, name):
        if name not in self.views:
            raise KeyError(f"no view '{name}' with a sheet panel; views: {sorted(self.views)}")
        return self.views[name]

    def ground(self):
        return self.pos[:, 2] < self.pos[:, 2].min() + SOLE * self.H

    def parts(self):
        """{bone: {verts, lo, hi}}: vertices and bbox (fractions of H from the model's min corner) of each bone's vertices."""
        lo = self.pos.min(0)
        out = {}
        for b in sorted(set(self.bones)):
            p = self.pos[self.bones == b]
            out[b] = {"verts": int(len(p)), "lo": ((p.min(0) - lo) / self.H).round(3).tolist(),
                      "hi": ((p.max(0) - lo) / self.H).round(3).tolist()}
        return out

    def scale_part(self, name, sx=1.0, sy=1.0, sz=1.0):
        """Scale a part about its own centre, per axis."""
        sel = self.mask(name)
        c = self.pos[sel].mean(0)
        self.pos[sel] = c + (self.pos[sel] - c) * np.array([sx, sy, sz])

    def shrink_part(self, name, axis, amount):
        """Make a part `amount` (0-0.9) thinner along `axis` ('x' | 'y' | 'z'), about its centre."""
        s = [1.0, 1.0, 1.0]
        s[AXES[axis]] = 1.0 - amount
        self.scale_part(name, *s)

    def move_part(self, name, dx=0.0, dy=0.0, dz=0.0):
        """Translate a part by (dx, dy, dz) x H."""
        self.pos[self.mask(name)] += np.array([dx, dy, dz]) * self.H

    def smooth_region(self, name=None, iters=2, lam=0.5):
        """Uniform-Laplacian smoothing of a part's vertices (those that touch another part stay put)."""
        sel = self.mask(name)
        e = np.unique(np.sort(np.concatenate([self.tri[:, [0, 1]], self.tri[:, [1, 2]], self.tri[:, [2, 0]]]), axis=1), axis=0)
        free = sel.copy()
        crossing = sel[e[:, 0]] != sel[e[:, 1]]
        free[e[crossing].ravel()] = False
        for _ in range(iters):
            mean = -(self.lap @ self.pos) + self.pos                   # D^-1 A x
            self.pos[free] += lam * (mean[free] - self.pos[free])

    def straighten_prop(self, name, view):
        """Turn a prop (spear, staff) about its centre in `view`'s plane until its long axis is vertical there."""
        v = self.view(view)
        sel = self.mask(name)
        c = self.pos[sel].mean(0)
        uv = np.stack([(self.pos[sel] - c) @ v.ru, (self.pos[sel] - c) @ v.rv], 1)
        axis = np.linalg.svd(uv, full_matrices=False)[2][0]
        angle = np.arctan2(axis[0], axis[1])                         # the long axis from vertical
        angle = (angle + np.pi / 2) % np.pi - np.pi / 2
        n = np.cross(v.ru, v.rv)
        k = np.array([[0, -n[2], n[1]], [n[2], 0, -n[0]], [-n[1], n[0], 0]])
        rot = np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k   # Rodrigues, about the view axis
        self.pos[sel] = c + (self.pos[sel] - c) @ rot.T

    def snap_feet_to_ground(self):
        """Lower the model so its lowest point is at z = 0, fading out over the bottom quarter so the rest does not float off its bones."""
        z0 = self.pos[:, 2].min()
        w = np.clip(1.0 - (self.pos[:, 2] - z0) / (0.25 * self.H), 0.0, 1.0)
        self.pos[:, 2] -= z0 * w

    def erode_toward_view(self, view, px=2.0, part=None, margin=1):
        """Push the vertices that sit in RED of `view` (model outside the sheet) into the sheet's silhouette, in that
        view's image plane, at most `px` canvas pixels (the panel is 384 x 256) and `margin` pixels inside its edge;
        the rest of the part follows through the smoothing solve. The camera, mirror and framing are the gate's."""
        v = self.view(view)
        xy, mask, s = D.view_state(self.pos, self.tri, v)
        red = mask & ~v.concept
        near = ndimage.binary_dilation(red, iterations=2)
        core = ndimage.binary_erosion(v.concept, iterations=margin) if margin else v.concept
        if not core.any():
            core = v.concept
        iy, ix = ndimage.distance_transform_edt(~core, return_indices=True)[1]
        p = D.pixels(xy, mask.shape)
        bad = near[p[:, 1], p[:, 0]] & ~core[p[:, 1], p[:, 0]] & self.mask(part)
        if not bad.any():
            return 0
        move = np.stack([ix[p[:, 1], p[:, 0]], iy[p[:, 1], p[:, 0]]], 1) + 0.5 - xy
        move[~bad] = 0.0
        d = D.clamp(np.stack([move[:, 0] / s * v.mirror, -move[:, 1] / s], 1), px / s)
        w = bad.astype(float)
        d = D.clamp(D.solve(self.lap, d, PULL * w, ANCHOR * (1 - w) + 1e-3), px / s)
        world = d[:, :1] * v.ru + d[:, 1:] * v.rv
        world[self.ground(), 2] = 0.0
        self.pos += world
        return int(bad.sum())

    def namespace(self):
        names = ("shrink_part", "move_part", "scale_part", "erode_toward_view", "smooth_region", "straighten_prop",
                 "snap_feet_to_ground", "parts")
        return {"np": np, "scene": self, **{n: getattr(self, n) for n in names}}


def run_code(glb_in, glb_out, code, sheet, layout="unit", cams=None):
    """Write `glb_out` = `glb_in` after the agent's `code`; returns {moved, max_move_H, vertices}."""
    bones = vertex_bones(glb_in)

    def change(uniq, tri, nor, file):
        inv, _ = file
        named = np.empty(len(uniq), dtype=object)
        named[inv] = bones
        views = {v.name: v for v in OV.make_views(uniq, tri, sheet, VIEWS, layout, cams)}
        scene = Scene(uniq.copy(), tri, named, views)
        exec(compile(code, "<polish>", "exec"), scene.namespace())      # noqa: S102 - the agent's code is the point
        if not np.isfinite(scene.pos).all():
            raise ValueError("the code left NaN / inf vertices")
        d = np.linalg.norm(scene.pos - uniq, axis=1) / scene.H
        return scene.pos, {"vertices": len(uniq), "moved": int((d > 1e-6).sum()), "max_move_H": round(float(d.max()), 4)}

    return D.rewrite(glb_in, glb_out, change, suffix=".polish.json")


def raw_z_up(glb):
    """File-order vertex positions of a GLB, Z-up (the welded order is by position, so it changes when vertices move)."""
    doc, blob = ML.read_glb(pathlib.Path(glb))
    return D.to_z_up(ML.geometry(doc, blob)[0])


def carry(pre, post, model, out):
    """`model` with the displacement the polish gave the clay (post - pre, per file vertex) added to each vertex, taken from the nearest
    clay vertex: the textured model has the clay's topology (same count, same triangles) but its own deform / verts passes."""
    from scipy.spatial import cKDTree
    a, b = raw_z_up(pre), raw_z_up(post)

    def change(uniq, tri, nor, file):
        near = cKDTree(a).query(uniq)[1]
        return uniq + (b - a)[near], {"vertices": len(uniq), "from": str(pre), "to": str(post)}

    return D.rewrite(model, out, change, suffix=".carry.json")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("glb_in"), r.add_argument("glb_out"), r.add_argument("code")
    r.add_argument("--sheet", required=True)
    r.add_argument("--layout", default="unit")
    r.add_argument("--cams", default="{}", help="JSON {view: tilt or [elevation, azimuth]}")
    c = sub.add_parser("carry")
    for n in ("pre", "post", "model", "out"):
        c.add_argument(n)
    a = ap.parse_args()
    try:
        if a.cmd == "run":
            cams = {k: tuple(v) if isinstance(v, list) else v for k, v in json.loads(a.cams).items()}
            print(json.dumps(run_code(a.glb_in, a.glb_out, pathlib.Path(a.code).read_text(), a.sheet, a.layout, cams or None)))
        else:
            print(json.dumps(carry(a.pre, a.post, a.model, a.out)))
    except Exception:
        traceback.print_exc(limit=-4)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
