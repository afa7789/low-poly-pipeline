#!/usr/bin/env python3
"""Turn the v9 parts spec into a variant from a dial dict, so an iteration loop can
change proportions without hand-editing JSON.

    python3 tools/blender/variant.py <base.json> <dials.json> <out.json>

dials: wheel, shoulder, fist, legs, chest (multipliers), arm_out, hunch (degrees),
       ramp, trim (atlas gains), union (0/1).
"""
import json
import sys


def main():
    base, dials_path, out = sys.argv[1:4]
    spec = json.loads(open(base).read())
    d = json.loads(open(dials_path).read())

    for part in spec["parts"]:
        bone, kind, dims, at, mat, opts = part
        if bone == "head" and kind in ("wheel", "box", "cyl") and at[1] > 2.3:
            part[2] = [v * d.get("wheel", 1.0) for v in dims]
        if bone.startswith("arm.") and kind == "dome":
            part[2] = [v * d.get("shoulder", 1.0) for v in dims]
        if bone.startswith("forearm.") and kind in ("box", "dome"):
            part[2] = [v * d.get("fist", 1.0) for v in dims]
        if bone.startswith("thigh.") or bone.startswith("shin."):
            if kind in ("prism", "box"):
                part[2] = [v * d.get("legs", 1.0) for v in dims]
        if bone == "spine" and kind == "box" and dims[0] > 0.8:
            part[2][2] = dims[2] * d.get("chest", 1.0)
        if bone.startswith("arm.") and kind == "prism":
            opts["rot"] = [float(d.get("hunch", 0)), 0, float(d.get("arm_out", 0))]

    spec["dials"] = d
    json.dump(spec, open(out, "w"), indent=1)
    print("variant written:", out, "| union", d.get("union", 0))


if __name__ == "__main__":
    main()
