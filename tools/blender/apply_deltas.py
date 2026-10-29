#!/usr/bin/env python3
"""Per-part deltas on a spec, with frozen parts and hard limits (ROADMAP Leva 11, L11-1; PIPELINE §29.L11-1).

    python3.14 tools/blender/apply_deltas.py <spec.json> <diagnosis.json> [--out spec2.json]

`apply(spec, deltas, height) -> (spec2, log)`: pure numpy-free json code, no Blender. A delta names ONE part and
one action; a part no delta names is returned byte-equal (frozen). A delta outside the schema or the limits is
rejected ALONE (log entry `{"delta", "status": "rejected", "why"}`); the others still apply.

Part address, the same in the diagnose prompt and here: `<bone>#<k>` = the k-th part (0-based, file order of
spec["parts"]) bound to that bone, e.g. `spine#2`. A bare bone name is accepted only when the bone has exactly
one part. Addresses always refer to the spec as it came in, never to the spec half-way through the round.
For `add`, `part` is the BONE the new part binds to (no #k).

Actions (a part gets at most one delta per round):
  scale   value 0.7-1.4, axis x|y|z or none (uniform; from/to ends scale about the midpoint). Axis scale: box and
          frustum dims, the length of a prism/cyl, the height of a lathe (y) or its squash (x, z).
  radius  value 0.7-1.4 on lathe, cyl, frustum (width and depth), prism, limb, chain radii.
  move    axis, |value| <= 0.08 * height, metres (shifts at, or from/to).
  rotate  axis, |value| <= 25 degrees, added to opts rot; only box, prism, dome, frustum without from/to.
  add     kind (DSL), dims, at, material? (default: the bone's first part), opts?; <= 2 per round; the part's box
          <= 10 % of the figure (sum of part boxes); on a .L/.R bone the mirrored twin is added too.
  remove  only a part whose box is < 2 % of the figure.
A part on a .L/.R bone with a mirrored twin (same kind and dims, mirrored centre) moves its twin the same way, so
the preflight symmetry rule keeps holding. The result must pass spec_pipeline.parse_spec (snap to the 1/256 grid,
ground fix, validate); changed parts are snapped, untouched ones are not rewritten.
"""
import argparse
import copy
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import preflight as PF  # noqa: E402
import spec_pipeline as SP  # noqa: E402

ACTIONS = ("scale", "radius", "move", "rotate", "add", "remove")
AXES = ("x", "y", "z")
SCALE_RANGE = (0.7, 1.4)
MOVE_SHARE = 0.08          # of the figure height, per delta
ROTATE_MAX = 25.0          # degrees
ADD_MAX = 2                # deltas per round
ADD_SHARE = 0.10           # of the figure volume
REMOVE_SHARE = 0.02
COMMON = {"part", "action", "why"}
FIELDS = {"scale": {"axis", "value"}, "radius": {"value"}, "move": {"axis", "value"}, "rotate": {"axis", "value"},
          "add": {"kind", "dims", "at", "material", "opts"}, "remove": set()}
REQUIRED = {"scale": {"value"}, "radius": {"value"}, "move": {"axis", "value"}, "rotate": {"axis", "value"},
            "add": {"kind", "dims", "at"}, "remove": set()}
RADIAL = {"lathe": [0], "cyl": [0], "frustum": [0, 2], "prism": [0, 1], "limb": [0, 1, 2]}   # chain: every dim
AXIS_DIM = {"x": 0, "y": 1, "z": 2}


class Reject(ValueError):
    """The delta is refused; the message is the log reason."""


def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def addresses(spec):
    """[(address, part)] of the spec, `<bone>#<k>`."""
    seen, out = {}, []
    for p in spec["parts"]:
        k = seen[p[0]] = seen.get(p[0], -1) + 1
        out.append((f"{p[0]}#{k}", p))
    return out


def box_volume(p):
    lo, hi = PF.bbox(p)
    return math.prod(max(h - l, 0.0) for l, h in zip(lo, hi))


def check_delta(d):
    """Raise Reject unless `d` is inside the schema (keys, types, ranges are checked per action later)."""
    if not isinstance(d, dict) or not isinstance(d.get("part"), str) or not d["part"]:
        raise Reject("not an object with a part")
    act = d.get("action")
    if act not in ACTIONS:
        raise Reject(f"action {act!r} outside {ACTIONS}")
    extra = set(d) - COMMON - FIELDS[act]
    if extra:
        raise Reject(f"fields outside the schema: {sorted(extra)}")
    missing = REQUIRED[act] - set(d)
    if missing:
        raise Reject(f"missing fields: {sorted(missing)}")
    if "value" in d and not num(d["value"]):
        raise Reject("value is not a number")
    if d.get("axis") is not None and d["axis"] not in AXES:
        raise Reject("axis is x, y or z")
    if act == "add":
        check_add(d)


def check_add(d):
    if not (isinstance(d["dims"], list) and d["dims"] and all(num(v) for v in d["dims"])):
        raise Reject("dims is a list of numbers")
    if not (isinstance(d["at"], list) and len(d["at"]) == 3 and all(num(v) for v in d["at"])):
        raise Reject("at is [x, y, z]")
    if d["kind"] not in SP.KINDS:
        raise Reject(f"kind outside {sorted(SP.KINDS)}")
    if not isinstance(d.get("opts", {}), dict):
        raise Reject("opts is an object")


def resolve(parts, name):
    """Index into `parts` (the round's input order) of the address `name`."""
    hits = [i for i, (a, _) in enumerate(addresses({"parts": parts})) if a == name]
    if not hits and "#" not in name:
        hits = [i for i, p in enumerate(parts) if p[0] == name]
        if len(hits) > 1:
            raise Reject(f"{name} has {len(hits)} parts: say {name}#k")
    if not hits:
        raise Reject(f"no part {name}")
    return hits[0]


def twin_of(parts, i):
    """Index of the mirrored twin of parts[i], or None."""
    p = parts[i]
    if not p[0].endswith((".L", ".R")):
        return None
    other = p[0][:-1] + ("R" if p[0].endswith("L") else "L")
    cx, cy, cz = PF.centre(p)
    for j, q in enumerate(parts):
        qx, qy, qz = PF.centre(q)
        if (j != i and q[0] == other and q[1] == p[1] and q[2] == p[2]
                and abs(qx + cx) < 0.02 and abs(qy - cy) < 0.02 and abs(qz - cz) < 0.02):
            return j
    return None


def mirrored_delta(d):
    """The same delta for the twin on the other side."""
    flip = (d["action"] == "move" and d["axis"] == "x") or (d["action"] == "rotate" and d["axis"] in ("y", "z"))
    return {**d, "value": -d["value"]} if flip else d


def mirrored_part(p):
    """The twin of a new part on the other side of x = 0."""
    q = copy.deepcopy(p)
    q[0] = p[0][:-1] + ("R" if p[0].endswith("L") else "L")
    q[3] = [-p[3][0], p[3][1], p[3][2]]
    opts = q[5]
    for end in ("from", "to"):
        if end in opts:
            opts[end] = [-opts[end][0], *opts[end][1:]]
    if "knee" in opts:
        opts["knee"] = [opts["knee"][0], -opts["knee"][1], *opts["knee"][2:]]
    if "rot" in opts:
        rx, ry, rz = PF.rot_euler(opts)
        opts["rot"] = [rx, -ry, -rz]
    return q


def in_range(v, lo, hi, what):
    if not lo <= v <= hi:
        raise Reject(f"{what} {v} outside [{lo}, {hi}]")


def spans(p):
    return "from" in p[5] and "to" in p[5]


def scale_ends(opts, v):
    a, b = opts["from"], opts["to"]
    mid = [(a[i] + b[i]) / 2 for i in range(3)]
    for end, pt in (("from", a), ("to", b)):
        opts[end] = [mid[i] + (pt[i] - mid[i]) * v for i in range(3)]


def scale_axis(q, axis, v):
    kind, opts = q[1], q[5]
    if spans(q):
        raise Reject("axis scale needs a part without from/to")
    if kind in ("box", "frustum"):
        q[2][AXIS_DIM[axis]] *= v
    elif kind in ("prism", "cyl") and axis == ("z" if opts.get("axis") == "fwd" else "y"):
        q[2][2 if kind == "prism" else 1] *= v
    elif kind == "lathe" and "axis" not in opts and axis == "y":
        q[2][1] *= v
    elif kind == "lathe" and "axis" not in opts and axis in ("x", "z"):
        opts["squash"] = opts.get("squash", 1.0) * (v if axis == "x" else 1 / v)
    else:
        raise Reject(f"axis {axis} scale unsupported on {kind}")


def do_scale(q, d):
    v = d["value"]
    in_range(v, *SCALE_RANGE, "scale")
    if d.get("axis"):
        scale_axis(q, d["axis"], v)
        return
    q[2] = [x * v for x in q[2]]
    if spans(q):
        scale_ends(q[5], v)


def do_radius(q, d):
    in_range(d["value"], *SCALE_RANGE, "radius")
    if q[1] != "chain" and q[1] not in RADIAL:
        raise Reject(f"radius unsupported on {q[1]}")
    for i in (range(len(q[2])) if q[1] == "chain" else RADIAL[q[1]]):
        q[2][i] *= d["value"]


def do_move(q, d, height):
    if q[1] == "chain":
        raise Reject("a chain is placed by its bones")
    in_range(d["value"], -MOVE_SHARE * height, MOVE_SHARE * height, "move")
    i = AXIS_DIM[d["axis"]]
    if spans(q):
        for end in ("from", "to"):
            q[5][end][i] += d["value"]
    else:
        q[3][i] += d["value"]


def do_rotate(q, d):
    in_range(d["value"], -ROTATE_MAX, ROTATE_MAX, "rotate")
    if q[1] not in PF.ROT_KINDS or spans(q) or "cut" in q[5]:
        raise Reject(f"{q[1]} takes no rotation here")
    rot = list(PF.rot_euler(q[5]))
    rot[AXIS_DIM[d["axis"]]] += d["value"]
    q[5]["rot"] = rot


def edit(p, d, height):
    """A copy of part `p` with delta `d` applied (Reject when refused)."""
    q = copy.deepcopy(p)
    if not isinstance(q[5], dict):
        q[5] = {}
    act = d["action"]
    if act == "scale":
        do_scale(q, d)
    elif act == "radius":
        do_radius(q, d)
    elif act == "move":
        do_move(q, d, height)
    else:
        do_rotate(q, d)
    return q


class Round:
    """State of one apply(): the input parts (addresses refer to them), edits, additions, removals."""

    def __init__(self, spec, height):
        self.spec, self.height = spec, height
        self.parts = copy.deepcopy(spec["parts"])
        self.new = {}             # index -> edited part
        self.removed = set()
        self.added = []
        self.adds = 0
        self.volume = sum(box_volume(p) for p in self.parts)

    def touched(self, i):
        return i in self.new or i in self.removed

    def check_part(self, q):
        """Raise Reject unless the edited part `q` is a valid part of this spec."""
        q = copy.deepcopy(q)
        PF.normalise([q], SP.RIG)           # snap to the grid, as parse_spec will
        try:
            SP.validate([q], self.spec.get("palette") or {}, SP.extra_names(self.spec))
        except (ValueError, TypeError, KeyError, IndexError) as e:
            raise Reject(f"validate: {e}") from e
        return q

    def do_edit(self, d):
        i = resolve(self.parts, d["part"])
        j = twin_of(self.parts, i)
        done = []
        for k, dd in ((i, d), (j, mirrored_delta(d))):
            if k is None:
                continue
            if self.touched(k):
                raise Reject(f"{d['part']} already changed this round")
            done.append((k, self.check_part(edit(self.parts[k], dd, self.height))))
        self.new.update(done)
        return f"ok{' (+twin)' if j is not None else ''}"

    def do_remove(self, d):
        i = resolve(self.parts, d["part"])
        j = twin_of(self.parts, i)
        ids = [k for k in (i, j) if k is not None]
        if any(self.touched(k) for k in ids):
            raise Reject(f"{d['part']} already changed this round")
        big = [k for k in ids if box_volume(self.parts[k]) >= REMOVE_SHARE * self.volume]
        if big:
            raise Reject(f"part is {box_volume(self.parts[big[0]]) / self.volume:.1%} of the figure, remove needs < {REMOVE_SHARE:.0%}")
        self.removed.update(ids)
        return f"ok{' (+twin)' if j is not None else ''}"

    def do_add(self, d):
        if self.adds >= ADD_MAX:
            raise Reject(f"more than {ADD_MAX} adds in a round")
        bone = d["part"]
        same = [p for p in self.parts if p[0] == bone]
        material = d.get("material") or (same or self.parts)[0][4]
        p = self.check_part([bone, d["kind"], list(d["dims"]), list(d["at"]), material, dict(d.get("opts", {}))])
        news = [p, self.check_part(mirrored_part(p))] if bone.endswith((".L", ".R")) else [p]
        vol = sum(box_volume(q) for q in news)
        if vol > ADD_SHARE * self.volume:
            raise Reject(f"added box is {vol / self.volume:.1%} of the figure, the limit is {ADD_SHARE:.0%}")
        self.added += news
        self.adds += 1
        return "ok" + (" (+twin)" if len(news) > 1 else "")

    def one(self, d):
        check_delta(d)
        return {"add": self.do_add, "remove": self.do_remove}.get(d["action"], self.do_edit)(d)

    def result(self):
        parts = [self.new.get(i, p) for i, p in enumerate(self.parts) if i not in self.removed]
        return {**self.spec, "parts": parts + self.added}


def apply(spec, deltas, height):
    """(spec2, log): spec with the valid deltas applied, one log entry per delta."""
    SP.set_rig(spec.get("rig", "biped"), spec.get("rig_measure"))
    rnd, log = Round(spec, height), []
    for d in deltas:
        try:
            log.append({"delta": d, "status": "applied", "why": rnd.one(d)})
        except Reject as e:
            log.append({"delta": d, "status": "rejected", "why": str(e)})
    out = rnd.result()
    try:
        SP.parse_spec(json.dumps(out))
    except (ValueError, TypeError, KeyError, IndexError) as e:      # per-part checks missed it: change nothing
        return spec, [{**x, "status": "rejected", "why": f"parse_spec: {e}"} if x["status"] == "applied" else x
                      for x in log]
    return out, log


LIMIT_WIDTH = 0.1          # scale/radius: the fit may land within value +- this (factor on the current dim)
LIMIT_MOVE = 0.02          # move: the fit may land within value +- this * height (metres)


def dim_slots(p, d):
    """Indices of the dims a scale/radius delta bounds, [] when the fit has no such dim (squash, spans)."""
    kind, axis = p[1], d.get("axis")
    if d["action"] == "radius":
        return list(RADIAL.get(kind, ()))
    if axis is None:
        return None                                     # uniform: every dim
    if kind in ("box", "frustum"):
        return [AXIS_DIM[axis]]
    if kind in ("prism", "cyl"):
        opts = p[5] if isinstance(p[5], dict) else {}
        return [2 if kind == "prism" else 1] if axis == ("z" if opts.get("axis") == "fwd" else "y") else []
    return [1] if kind == "lathe" and axis == "y" else []


def one_limit(p, d, height):
    """{"dims": {k: (lo, hi) factor}} or {"at": {k: (lo, hi) metres}} for delta `d` on part `p`, or None (no via B)."""
    act, v = d["action"], d.get("value")
    if act in ("scale", "radius"):
        if not num(v) or not SCALE_RANGE[0] <= v <= SCALE_RANGE[1]:
            return None
        if act == "radius" and p[1] != "chain" and p[1] not in RADIAL:
            return None
        slots = list(range(len(p[2]))) if p[1] == "chain" else dim_slots(p, d)
        slots = list(range(len(p[2]))) if slots is None else slots
        return {"dims": {k: (v - LIMIT_WIDTH, v + LIMIT_WIDTH) for k in slots}} if slots else None
    if act == "move" and num(v) and d.get("axis") in AXES and p[1] != "chain" and abs(v) <= MOVE_SHARE * height:
        return {"at": {AXIS_DIM[d["axis"]]: (v - LIMIT_MOVE * height, v + LIMIT_MOVE * height)}}
    return None


def fit_limits(spec, deltas, height):
    """{part index: {"dims"|"at": {slot: (lo, hi)}}}: scale/radius/move deltas as limits for the fit (L11-3, via B).
    The twin gets the mirrored limit. add/remove/rotate, unknown parts and out-of-range values have no via B: left out."""
    SP.set_rig(spec.get("rig", "biped"), spec.get("rig_measure"))
    parts, out = spec["parts"], {}
    for d in deltas:
        try:
            check_delta(d)
            i = resolve(parts, d["part"])
        except Reject:
            continue
        for k, dd in ((i, d), (twin_of(parts, i), mirrored_delta(d) if d["action"] == "move" else d)):
            lim = None if k is None else one_limit(parts[k], dd, height)
            if lim:
                out.setdefault(k, {}).update(lim)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("spec", type=pathlib.Path)
    ap.add_argument("diagnosis", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()
    import diagnose
    spec = json.loads(args.spec.read_text())
    deltas = json.loads(args.diagnosis.read_text()).get("deltas", [])
    out, log = apply(spec, deltas, diagnose.spec_height(spec))
    for e in log:
        print(f"{e['status']:8} {json.dumps(e['delta'])[:90]}  {e['why']}")
    if args.out:
        args.out.write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
