#!/usr/bin/env python3
"""Guard of the author's spec against the massing (PIPELINE 30.L12-3).

The deterministic pre-spec (massing.py) already reaches 90-100 % of the final IoU and the author
(LLM) edit can lose views, and the fit that follows can too (v13-r1: hfoo left .719 -> .415, n017 top .920 -> .822). Before the fit:
the author's stage 1 (build, deform, vertex fit) is measured against the massing's on the same pinned cameras;
a view more than AUTHOR_DROP under the massing's is a drop.

  revert  the bones that explain the drop go back to the massing's parts (greedy over the fast 2D
          proxy of fit_spec.Proxy, ranked by the IoU gained on the dropped views), then the caller
          measures the real clay again; still a drop -> reject.
  reject  the massing's body with the author's props (opts "prop") and palette; if that still falls the
          massing itself (a prop moves the silhouette too).
  off     nothing.

Pure functions over spec dicts and a proxy with `ious(parts) -> {view: IoU}`; the builds are the caller's.
"""
import preflight

AUTHOR_DROP = 0.01
MODES = ("revert", "reject", "off")


def drops(mass, author, drop=AUTHOR_DROP):
    """[views] where the author's IoU is more than `drop` under the massing's (only views both have)."""
    return [v for v in author if v in mass and author[v] < mass[v] - drop]


def bone_of(part):
    return part[0]


def body(parts):
    return [p for p in parts if not preflight.is_prop(p)]


def differing_bones(author, mass):
    """Bones whose body parts differ between the two specs (props are the author's, never reverted)."""
    a, m = body(author["parts"]), body(mass["parts"])
    bones = {bone_of(p) for p in a} | {bone_of(p) for p in m}
    return sorted(b for b in bones if [p for p in a if bone_of(p) == b] != [p for p in m if bone_of(p) == b])


def with_bone(parts, mass_parts, bone):
    """`parts` with the body parts of `bone` replaced by the massing's (at the first one's place, else at the end)."""
    back = [p for p in body(mass_parts) if bone_of(p) == bone]
    out, put = [], False
    for p in parts:
        if bone_of(p) == bone and not preflight.is_prop(p):
            if not put:
                out.extend(back)
                put = True
            continue
        out.append(p)
    return out if put else out + back


def with_palette(spec, mass):
    """The spec's palette plus the massing slots a reverted part needs (the author's win on a name clash)."""
    return {**spec, "palette": {**mass.get("palette", {}), **spec.get("palette", {})}}


def shortfall(ious, mass, drop):
    return sum(max(0.0, mass[v] - drop - ious[v]) for v in mass if v in ious)


def revert(author, mass, proxy, falling, real_gap, drop=AUTHOR_DROP):
    """(spec, [bones reverted]). Greedy: each round reverts the bone that gains the most proxy IoU on the
    `falling` views, until the proxy says those views are back within `drop` of the massing's. `real_gap`
    {view: real massing IoU - real author IoU} says how far each one fell; the proxy moves are the signal
    (the proxy's own massing-vs-author gap can be zero where the clay's is not)."""
    spec, done = author, []
    start = proxy.ious(spec["parts"])
    need = {v: real_gap[v] - drop for v in falling}
    candidates = differing_bones(author, mass)
    while candidates:
        now = proxy.ious(spec["parts"])
        if all(now[v] - start[v] >= need[v] for v in falling):
            break
        trials = {b: proxy.ious(with_bone(spec["parts"], mass["parts"], b)) for b in candidates}
        best = max(trials, key=lambda b: sum(trials[b][v] - now[v] for v in falling))
        if sum(trials[best][v] - now[v] for v in falling) <= 1e-4:
            break
        spec = with_palette({**spec, "parts": with_bone(spec["parts"], mass["parts"], best)}, mass)
        done.append(best)
        candidates.remove(best)
    return spec, done


def reject(author, mass, props=True):
    """The massing's body with the author's props instead of its own, the author's palette (plus the massing slots) and
    rig fields; `props` off: the massing itself (props included), what stage 0 measured."""
    if not props:
        return mass
    return with_palette({**author, "parts": body(mass["parts"]) + [p for p in author["parts"] if preflight.is_prop(p)]}, mass)
