#!/usr/bin/env python3
"""L18: fuse the near colours of an eye-stage DSL so a unit has at most MAX_MATS materials (PIPELINE 36.L18-1).

    eye_fuse.fuse(dsl, max_mats=12) -> (dsl with the pieces re-pointed at the fused materials, log)

Why: the eye stage writes 15-20 materials per unit (one per colour the artist sampled) and the union by material / bone (L17-2)
then leaves 13-19 meshes, each too small to keep its detail, and the painted atlas (L17-3) gets ~300 islands of ~12 texels. The Hive
models carry 5 materials. Here two materials of the same class (glow, glass, skin, other: a lamp never melts into a coat, skin never
into cloth) whose OKLab distance is under THRESHOLD are one; when the unit still has more than max_mats, the closest pair of a class
is fused until it does not. The fused colour is the triangle-weighted mean in OKLab; the name is the heavier material's. A piece with
its own "colour" is its own material first (name#colour) so it is fused by what it looks like. Pure python, no numpy."""
import json

MAX_MATS = 12
THRESHOLD = 0.04        # OKLab distance under which two colours of one class are one paint (olive cloth x steel is .057: kept apart)
CLASSES = {"glow": ("glow", "lamp", "flame", "fire", "ember", "furnace", "light", "lantern"),
           "glass": ("glass", "lens", "goggle", "visor"),
           "skin": ("skin", "flesh", "face", "hide")}


def class_of(mat):
    low = mat.lower()
    return next((c for c, words in CLASSES.items() if any(w in low for w in words)), "other")


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    c = min(max(c, 0.0), 1.0)
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def oklab(hexv):
    """(L, a, b) of a 6-digit hex colour (Bjorn Ottosson's OKLab)."""
    r, g, b = (srgb_to_linear(int(hexv[i:i + 2], 16) / 255) for i in (0, 2, 4))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def hex_of(lab):
    """The hex colour of an OKLab triple."""
    L, a, b = lab
    l_, m_, s_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3, (L - 0.1055613458 * a - 0.0638541728 * b) ** 3, (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    g = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    bb = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    return "".join(f"{round(255 * linear_to_srgb(c)):02X}" for c in (r, g, bb))


def dist(p, q):
    return sum((x - y) ** 2 for x, y in zip(p, q)) ** 0.5


def materials_of(dsl):
    """{key: {"hex", "class", "weight", "pieces": [indices]}}: a piece with its own colour is its own key (mat#colour)."""
    import eye_lib as EL
    colours = dsl.get("colours") or {}
    out = {}
    for i, p in enumerate(dsl["pieces"]):
        own = p.get("colour")
        key = f"{p['mat']}#{own}" if own and own.upper() != str(colours.get(p["mat"], "")).upper() else p["mat"]
        m = out.setdefault(key, {"hex": (own or colours.get(p["mat"]) or "808080").upper(), "class": class_of(p["mat"]), "weight": 0, "pieces": []})
        m["weight"] += EL.tris_of(p)
        m["pieces"].append(i)
    return out


def closest_pair(mats):
    """(distance, a, b) of the closest two materials of one class; None with fewer than two in every class."""
    keys = list(mats)
    best = None
    for x, a in enumerate(keys):
        for b in keys[x + 1:]:
            if mats[a]["class"] != mats[b]["class"]:
                continue
            d = dist(oklab(mats[a]["hex"]), oklab(mats[b]["hex"]))
            if best is None or d < best[0]:
                best = (d, a, b)
    return best


def merge(mats, a, b):
    """Fuse b into a (the heavier keeps its name): weighted OKLab mean, pieces joined."""
    if mats[b]["weight"] > mats[a]["weight"]:
        a, b = b, a
    wa, wb = mats[a]["weight"], mats[b]["weight"]
    la, lb = oklab(mats[a]["hex"]), oklab(mats[b]["hex"])
    mats[a] = {"hex": hex_of(tuple((wa * x + wb * y) / (wa + wb) for x, y in zip(la, lb))), "class": mats[a]["class"], "weight": wa + wb,
               "pieces": mats[a]["pieces"] + mats[b]["pieces"]}
    del mats[b]
    return a, b


def fuse(dsl, max_mats=MAX_MATS, threshold=THRESHOLD):
    """(new dsl, log). Materials of one class under `threshold` apart are fused; then the closest pair of a class until there are at
    most `max_mats`. The pieces point at the fused material (their own "colour" dropped); "colours" is the new palette."""
    mats = materials_of(dsl)
    before, merges = len(mats), []
    while True:
        pair = closest_pair(mats)
        if pair is None or (pair[0] > threshold and len(mats) <= max_mats):
            break
        kept, gone = merge(mats, pair[1], pair[2])
        merges.append({"kept": kept, "gone": gone, "d": round(pair[0], 4), "hex": mats[kept]["hex"]})
    pieces = [dict(p) for p in dsl["pieces"]]
    colours = {}
    for key, m in mats.items():
        name = key.split("#")[0]
        while name in colours and colours[name] != m["hex"]:
            name += "_"
        colours[name] = m["hex"]
        for i in m["pieces"]:
            pieces[i]["mat"] = name
            pieces[i].pop("colour", None)
    out = dict(dsl, colours=colours, pieces=pieces)
    return out, {"before": before, "after": len(mats), "max_mats": max_mats, "threshold": threshold, "merges": merges,
                 "classes": {c: sum(m["class"] == c for m in mats.values()) for c in (*CLASSES, "other")}}


if __name__ == "__main__":
    import pathlib
    import sys
    doc, log = fuse(json.loads(pathlib.Path(sys.argv[1]).read_text()), *(int(a) for a in sys.argv[2:3]))
    print(json.dumps(log, indent=1))
