"""Reference animation -> rig family poses: each of our bones is aimed where its
counterpart points in the reference (rig_poses.aim), the body follows the reference
anchor, and frames where the reference stands are planted by rig_motions.

Input is ref_capture.py's joints.json (artifacts/anim-ref/<model>/joints.json). A map
names, per bone of ours, the two reference points it runs between: "bone" is that
bone's head (joint), "bone.tail" its tail. Joints are used rather than bone tails
because glTF bones often carry no length (the spider's and the animals' are zero long).

A motion is one or more layers (model, clip, map) driving disjoint bones: a mounted
knight is the animal's gallop on the mount plus a KayKit chop on the rider. The body
moves with the first layer whose map is not `still_root`.
"""
import json
import math
import pathlib

import rig_poses as P

REF_DIR = pathlib.Path(__file__).resolve().parents[2] / "artifacts/anim-ref"


def _sides(pairs, prefix=""):
    """{our bone with {S}: (ref from, ref to) with {s}} for both sides."""
    out = {}
    for ours, (a, b) in pairs.items():
        for s, S in (("l", "L"), ("r", "R")):
            out[prefix + ours.format(S=S)] = (a.format(s=s), b.format(s=s))
    return out


_KAYKIT_ARMS = {"arm.{S}": ("upperarm.{s}", "lowerarm.{s}"), "forearm.{S}": ("lowerarm.{s}", "hand.{s}")}
_KAYKIT_LEGS = {"thigh.{S}": ("upperleg.{s}", "lowerleg.{s}"), "shin.{S}": ("lowerleg.{s}", "foot.{s}"),
                "foot.{S}": ("foot.{s}", "toes.{s}.tail")}

_SPIDER_LEGS = {  # our ring (rig_families._legs) -> Quaternius leg names; feet are the IK targets
    "leg1": ("MidFrontLeg.L", "MidFrontFoot.L"), "leg2": ("FrontLeg.L", "FrontFoot.L"),
    "leg3": ("FrontLeg.R", "FrontFoot2.R"), "leg4": ("MidFrontLeg.R", "MidFrontFoot.R"),
    "leg5": ("MidBackLeg.R", "MidBackFoot.R"), "leg6": ("BackLeg.R", "BackFoot.R"),
    "leg7": ("BackLeg.L", "BackFoot.L"), "leg8": ("MidBackLeg.L", "MidBackFoot.L")}


def _spider_legs():
    """leg -> (hip, knee, foot) reference joints, for the foot IK."""
    return {ours: (hip, hip.replace("Leg.", "Leg2."), foot) for ours, (hip, foot) in _SPIDER_LEGS.items()}


# Quaternius animals (CC0, e006/n016/n017): leg1/leg2 front L/R, leg3/leg4 hind L/R; the
# hind leg skips the knee (hip -> hock -> hoof), so it keeps its dog-leg shape on two bones
_ANIMAL = {"spine.1": ("Torso", "Torso2"), "spine.2": ("Torso2", "Torso3"), "head": ("Neck1", "Head"),
           "tail.1": ("Tail1", "Tail2"), "tail.2": ("Tail2", "Tail3"),
           "leg1.upper": ("FrontUpperLeg.L", "FrontLowerLeg.L"), "leg1.lower": ("FrontLowerLeg.L", "FF.L"),
           "leg2.upper": ("FrontUpperLeg.R", "FrontLowerLeg.R"), "leg2.lower": ("FrontLowerLeg.R", "FF.R"),
           "leg3.upper": ("BackLeg.L", "BackLowerLeg.L"), "leg3.lower": ("BackLowerLeg.L", "FFB.L"),
           "leg4.upper": ("BackLeg.R", "BackLowerLeg.R"), "leg4.lower": ("BackLowerLeg.R", "FFB.R")}

# TheGameAssets spider (CC-BY-4.0, n01N): legs 1 (front) .. 4 (back) per side, five joints
# each from the body out (2 = hip, 3 = knee, 5 = foot); the index suffixes are resolved
_GAMEASSETS_RING = {"leg2": (1, "L"), "leg3": (1, "R"), "leg1": (2, "L"), "leg4": (2, "R"),
                    "leg8": (3, "L"), "leg5": (3, "R"), "leg7": (4, "L"), "leg6": (4, "R")}

def _rel(anchor, ours, neutral, bones, legs=None, still=False, leg_bones=None):
    """A map retargeted relative to the reference's `neutral` clip (first frame); an
    optional "gain" on the map scales every turn. Legs
    are {leg: (hip, knee, foot)} driving our `leg.upper`/`leg.lower`, or the two bones
    `leg_bones[leg]` names."""
    spec = {"anchor": anchor, "ours": ours, "neutral": neutral, "bones": bones}
    if legs:
        spec["legs"] = legs
    if leg_bones:
        spec["leg_bones"] = leg_bones
    if still:
        spec["still_root"] = True
    return spec


_H = "DragonArmature|"          # Quaternius dragon (CC0, h009): two hind legs, four-bone wings
_DRAGON_WINGS = {"wing1.upper": ("Wing1.L", "Wing3.L"), "wing1.lower": ("Wing3.L", "Wing4.L"),
                 "wing2.upper": ("Wing1.R", "Wing3.R"), "wing2.lower": ("Wing3.R", "Wing4.R")}
_DRAGON_TAIL = {"tail.1": ("Tail1", "Tail2"), "tail.2": ("Tail2", "Tail3"), "tail.3": ("Tail3", "Tail4")}
_W = {"spine.1": ("Hip", "Back1"), "spine.2": ("Back1", "Back2"), "neck.1": ("Back2", "Neck1"),
      "neck.2": ("Neck1", "Neck2"), "head": ("Neck2", "Head"),
      "leg1.upper": ("Thigh.Left", "Shin.Left"), "leg1.lower": ("Shin.Left", "Foot.Left"),
      "leg2.upper": ("Thigh.Right", "Shin.Right"), "leg2.lower": ("Shin.Right", "Foot.Right"),
      "wing1.upper": ("Upperarm.Left", "Wing1b.Left"), "wing1.lower": ("Wing1b.Left", "Wing1c.Left"),
      "wing2.upper": ("Upperarm.Right", "Wing1b.Right"), "wing2.lower": ("Wing1b.Right", "Wing1c.Right"),
      "tail.1": ("Tail1", "Tail3"), "tail.2": ("Tail3", "Tail5"), "tail.3": ("Tail5", "Tail6")}

# Quaternius snake (CC0, n00H): head -> neck -> chest -> body, the tail beyond
_SNAKE_CHAIN = [("Head", "Mouth"), ("Neck", "Head"), ("Chest", "Neck"), ("Body", "Chest"),
                ("Tail", "Body"), ("Tail1", "Tail"), ("Tail2", "Tail1"), ("Tail3", "Tail2")]


def _snake(ours):
    """Our chain bones (head end first) <- the snake's segments, reversed to point tailward."""
    return {bone: (b, a) for bone, (a, b) in zip(ours, _SNAKE_CHAIN[1:])}


_KAYKIT_UPPER = {"spine": ("spine", "head"), "head": ("head", "head.tail"), **_sides(_KAYKIT_ARMS)}
_RAT_LEGS = {"leg1": ("FrontUpLeg.L", "FrontLowLeg.L", "FrontFoot.L"),
             "leg2": ("FrontUpLeg.R", "FrontLowLeg.R", "FrontFoot.R"),
             "leg3": ("BackUpLeg.R", "BackLowLeg.R", "BackFoot.R"),
             "leg4": ("BackUpLeg.L", "BackLowLeg.L", "BackFoot.L")}
_N00U_LEG = {ours: (hip, hip.replace("Leg.", "Leg2."), foot) for ours, (hip, foot) in {
    "leg1": ("MidFrontLeg.L", "MidFrontFoot.L"), "leg2": ("BackLeg.L", "BackFoot.L"),
    "leg3": ("MidFrontLeg.R", "MidFrontFoot.R"), "leg4": ("MidBackLeg.R", "MidBackFoot.R"),
    "leg5": ("BackLeg.R", "BackFoot.R"), "leg6": ("MidBackLeg.L", "MidBackFoot.L")}.items()}
_HYDRA_NECK = [("Shoulders", "Neck"), ("Neck", "Head"), ("Neck", "Head")]

MAPS = {
    # KayKit Character Animations (CC0, Rig_Medium): kk_melee, kk_ranged, kk_general ...
    "kaykit_biped": {"anchor": "hips", "ours": "pelvis", "bones": {
        "pelvis": ("hips", "spine"), "spine": ("spine", "head"), "head": ("head", "head.tail"),
        **_sides(_KAYKIT_ARMS), **_sides(_KAYKIT_LEGS)}},
    # a KayKit walk or run: legs and body from the clip, arms hanging as in Idle_A and swung by _swing
    "kaykit_biped_walk": {"anchor": "hips", "ours": "pelvis", "swing": {"stance": ("kk_general", "Idle_A")},
                          "bones": {"pelvis": ("hips", "spine"), "spine": ("spine", "head"),
                                    "head": ("head", "head.tail"), **_sides(_KAYKIT_ARMS), **_sides(_KAYKIT_LEGS)}},
    # a KayKit idle: the stance the walk swings from (_narrow), so idle and walk meet
    "kaykit_biped_idle": {"anchor": "hips", "ours": "pelvis", "narrow": True,
                          "bones": {"pelvis": ("hips", "spine"), "spine": ("spine", "head"),
                                    "head": ("head", "head.tail"), **_sides(_KAYKIT_ARMS), **_sides(_KAYKIT_LEGS)}},
    # the KayKit upper body on a rider (mounted, mounted_flyer, bird_rider): the mount moves the body
    "kaykit_rider": {"anchor": "hips", "still_root": True, "bones": {
        "rider.spine": ("spine", "head"), "rider.head": ("head", "head.tail"), **_sides(_KAYKIT_ARMS, "rider.")}},
    # a beast on all fours that strikes with its forelegs as arms (ghoul, crypt fiend)
    "kaykit_forelegs": {"anchor": "hips", "still_root": True, "bones": {
        "leg1.upper": ("upperarm.l", "lowerarm.l"), "leg1.lower": ("lowerarm.l", "hand.l"),
        "leg2.upper": ("upperarm.r", "lowerarm.r"), "leg2.lower": ("lowerarm.r", "hand.r")}},
    "quaternius_animal": {"anchor": "Torso2", "ours": "spine.2", "bones": _ANIMAL},
    # Quaternius spider (CC0): n00U. Its legs are three times ours, so it is retargeted
    # relative to its idle: the body turns as much as the reference turns, and each foot
    # moves as far as the reference foot, scaled to our leg, with the knee bent its way
    "quaternius_spider": {"anchor": "Thorax", "ours": "body", "neutral": "SpiderArmature|Spider_Idle",
                          "bones": {"body": ("Thorax", "Head"), "head": ("Thorax", "Head"),
                                    "abdomen": ("Thorax", "Abdomen")},
                          "legs": _spider_legs()},
    # flyers and their riders
    # a drake's horizontal body is an animal's: neck in two, head and jaw, three tail bones
    "animal_drake": {"anchor": "Torso2", "ours": "spine.2", "bones": {
        **{k: v for k, v in _ANIMAL.items() if k != "head"},
        "neck.1": ("Neck1", "Neck2"), "neck.2": ("Neck2", "Neck3"), "head": ("Neck3", "Head"),
        "jaw": ("Neck3", "Head"), "tail.3": ("Tail2", "Tail3")}},
    "dragon_wings": _rel("Body", "spine.1", _H + "Dragon_Flying", _DRAGON_WINGS, still=True),
    "dragon_ray": _rel("Body", "body", _H + "Dragon_Flying",
                       {"body": ("BodyRoot", "Body"), **_DRAGON_WINGS,
                        **{f"tail.{i}": (f"Tail{i}", f"Tail{i + 1}") for i in (1, 2, 3)},
                        "tail.4": ("Tail3", "Tail4")}),
    "dragon_shard": _rel("Body", "body", _H + "Dragon_Flying",
                         {"body": ("BodyRoot", "Body"), **_DRAGON_WINGS, "tail.1": ("Tail1", "Tail3")}),
    "wyvern": _rel("Hip", "spine.1", "Hover", _W),
    # the dragon's neck and head alone, over a body that keeps flying (its attacks spin the body)
    "dragon_neck": {**_rel("Body", "spine.1", _H + "Dragon_Flying",
                           {"neck.1": ("Body", "Neck"), "neck.2": ("Neck", "Head"), "head": ("Head", "Nose")},
                           still=True), "gain": 2.0},   # without its body's spin the neck moves too little
    # the CC0 dragon on a bird body (two legs, wings, neck, tail): the default for birds
    "dragon_bird": _rel("Body", "spine.1", _H + "Dragon_Flying", {
        "spine.1": ("BodyRoot", "Body"), "spine.2": ("BodyRoot", "Body"), "neck.1": ("Body", "Neck"),
        "neck.2": ("Neck", "Head"), "head": ("Head", "Nose"),
        "leg1.upper": ("UpperLeg.L", "LowerLeg.L"), "leg1.lower": ("LowerLeg.L", "Feet.L"),
        "leg2.upper": ("UpperLeg.R", "LowerLeg.R"), "leg2.lower": ("LowerLeg.R", "Feet.R"),
        **_DRAGON_WINGS, **_DRAGON_TAIL}),
    # long bodies
    "snake": _rel("Body", "spine.4", "SnakeArmature|Snake_Idle",
                  {"head": ("Head", "Mouth"), **_snake([f"spine.{i}" for i in range(1, 8)])}),
    "snake_sled": _rel("Body", "spine.2", "SnakeArmature|Snake_Idle",
                       {"head": ("Head", "Mouth"), **_snake(["spine.4", "spine.3", "spine.2", "spine.1"])}),
    "snake_wyrm": _rel("Body", "spine.3", "SnakeArmature|Snake_Idle",
                       {"head": ("Head", "Mouth"), **_snake([f"spine.{i}" for i in range(1, 7)])}),
    # the naga's tail follows the snake from the body on (chest -> body -> tail tip), not its neck
    "snake_tail": _rel("Body", "tail.1", "SnakeArmature|Snake_Idle",
                       {f"tail.{i + 1}": (b, a) for i, (a, b) in enumerate(_SNAKE_CHAIN[3:] + _SNAKE_CHAIN[-1:])}),
    **{f"apatosaurus_neck{n}": _rel("Body", "spine.4", "Armature|Apatosaurus_Idle",
                                    {f"neck{n}.{i + 1}": pair for i, pair in enumerate(_HYDRA_NECK)}, still=n > 1)
       for n in (1, 2, 3)},
    # half men
    "kaykit_upper": {"anchor": "hips", "still_root": True, "bones": _KAYKIT_UPPER},
    "kaykit_wraith": {"anchor": "hips", "ours": "base", "bones": {"base": ("hips", "spine"), **_KAYKIT_UPPER}},
    "kaykit_centaur": {"anchor": "hips", "still_root": True,
                       "bones": {"spine.3": ("spine", "head"), "head": ("head", "head.tail"), **_sides(_KAYKIT_ARMS)}},
    # small walkers
    "rat": _rel("Body", "body", "RatArmature|Rat_Idle", {"body": ("Hips", "Shoulders"), "head": ("Neck", "Head")},
                legs=_RAT_LEGS),
    "spider_crab": _rel("Thorax", "body", "SpiderArmature|Spider_Idle",
                        {"body": ("Thorax", "Head"), "head": ("Thorax", "Head"),
                         "claw.L": ("FrontLeg.L", "FrontLeg2.L"), "pincer.L": ("FrontLeg2.L", "FrontFoot.L"),
                         "claw.R": ("FrontLeg.R", "FrontLeg2.R"), "pincer.R": ("FrontLeg2.R", "FrontFoot2.R"),
                         "tail.1": ("Thorax", "Abdomen")},
                        legs=_N00U_LEG),
    "robot_walker": _rel("Torso", "pelvis", "RobotArmature|Idle",
                         {"pelvis": ("Torso", "Chest"), "head": ("Chest", "Head")},
                         legs={s: (f"UpperLeg.{s}", f"LowerLeg.{s}", f"Foot.{s}") for s in "LR"},
                         leg_bones={"L": ("thigh.L", "shin.L"), "R": ("thigh.R", "shin.R")}),
    # TheGameAssets spider (CC-BY-4.0): the rearing strike and the lunge
    "gameassets_spider": {"anchor": "back_03", "ours": "body", "neutral": "Spider_Idle",
                          "bones": {"body": ("back_03", "body_02"), "head": ("back_03", "body_02"),
                                    "abdomen": ("back_03", "popa_04")},
                          "legs": {ours: (f"lapa_{n}_{s}_2", f"lapa_{n}_{s}_3", f"lapa_{n}_{s}_5")
                                   for ours, (n, s) in _GAMEASSETS_RING.items()}},
}


_CACHE = {}


def load(model):
    if model not in _CACHE:
        _CACHE[model] = json.loads((REF_DIR / model / "joints.json").read_text())
    return _CACHE[model]


def _key(frame, bone):
    """A bone by name, or by prefix for exporters that suffix an index ("lapa_1_L_2" ->
    "lapa_1_L_2_08")."""
    if bone in frame:
        return bone
    found = [k for k in frame if k.startswith(bone + "_")]
    if len(found) != 1:
        raise KeyError(f"reference joint {bone!r}: {'missing' if not found else 'ambiguous: ' + str(found)}")
    return found[0]


def _point(frame, name):
    if name.endswith(".tail"):
        return frame[_key(frame, name[:-len(".tail")])][1]
    return frame[_key(frame, name)][0]


def _points(spec):
    pairs = list(spec["bones"].values()) + list(spec.get("legs", {}).values())
    return [p for chain in pairs for p in chain]


def _lowest(frame, spec):
    return min(_point(frame, p)[2] for p in _points(spec))


def duration(model, clip, fps=24):
    """Length of a captured clip in frames at `fps`."""
    ref = load(model)
    if clip not in ref.get("frames", {}):
        raise KeyError(f"{model}: clip {clip!r} was not captured (ref_capture.py)")
    start, end = ref["frames"][clip]
    return round((end - start) * fps / ref.get("fps", fps))


def ten(seq, count=10):
    """`count` items evenly spread over a sequence, first and last included."""
    return [seq[round(i * (len(seq) - 1) / (count - 1))] for i in range(count)]


def _directions(frame, spec):
    out = {}
    for ours, (a, b) in spec["bones"].items():
        pa, pb = _point(frame, a), _point(frame, b)
        out[ours] = tuple(pb[i] - pa[i] for i in range(3))
    return out


def _relative(family, frame, neutral, spec):
    """Our rest direction of each bone, turned as the reference turned from `neutral`."""
    rest, now, then = P.joints(family), _directions(frame, spec), _directions(neutral, spec)
    gain = spec.get("gain", 1.0)
    return {b: P.turn(then[b], now[b], [rest[b][1][i] - rest[b][0][i] for i in range(3)], gain)
            for b in now if b in rest}


def _leg(spec, leg):
    """Our (upper, lower) bones of a leg."""
    return spec.get("leg_bones", {}).get(leg, (f"{leg}.upper", f"{leg}.lower"))


def _leg_scale(family, neutral, spec):
    """Our leg length over the reference's, averaged over the legs."""
    rest, ratios = P.joints(family), []
    for leg, (hip, knee, foot) in spec["legs"].items():
        up, low = _leg(spec, leg)
        h, k, f = (_point(neutral, j) for j in (hip, knee, foot))
        theirs = math.dist(h, k) + math.dist(k, f)
        ours = math.dist(*rest[up]) + math.dist(*rest[low])
        ratios.append(ours / theirs)
    return sum(ratios) / len(ratios)


def _legs(family, pose, frame, neutral, spec, scale):
    """Foot IK: each foot = our rest foot + the reference foot's move from `neutral`."""
    rest, now = P.joints(family), P.joints(family, pose)
    out = {}
    for leg, (hip, knee, foot) in spec["legs"].items():
        up, low = _leg(spec, leg)
        upper, lower = rest[up], rest[low]
        moved = [_point(frame, foot)[i] - _point(neutral, foot)[i] for i in range(3)]
        target = [lower[1][i] + moved[i] * scale for i in range(3)]
        bend = [_point(frame, knee)[i] - _point(frame, hip)[i] for i in range(3)]
        h = now[up][0]
        k, e = P.two_bone(h, target, math.dist(*upper), math.dist(*lower), bend)
        out[up] = [k[i] - h[i] for i in range(3)]
        out[low] = [e[i] - k[i] for i in range(3)]
    return out


def _base(ref, spec):
    """The reference pose motions are measured from: the neutral clip's first frame for a
    relative map (some bind poses lie on the floor), else the bind pose."""
    return ref["clips"][spec["neutral"]][0] if "neutral" in spec else ref["rest"]


def _body(family, ref, spec, frames, scale=None):
    """(root per frame, frames off the ground) of the layer that carries the body."""
    base = _base(ref, spec)
    rest = _point(base, spec["anchor"])
    if scale is None:
        scale = P.joints(family)[spec["ours"]][0][2] / max(rest[2], 1e-6)
    roots = [(-(_point(f, spec["anchor"])[1] - rest[1]) * scale, (_point(f, spec["anchor"])[2] - rest[2]) * scale)
             for f in frames]
    floor = _lowest(base, spec)
    air = {i for i, f in enumerate(frames) if _lowest(f, spec) > floor + 0.08 * rest[2]}
    return roots, air


def _absolute(spec, frames):
    """Per-frame directions of a map read as absolute: the reference's world directions, taken
    as they are, KayKit's arms drawn in (narrow) or swung from the stance (swing) where asked."""
    out = [_directions(f, spec) for f in frames]
    if spec.get("narrow"):
        out = [_narrow(d) for d in out]
    if "swing" in spec:
        _swing(spec, out)
    return out


SWING_GAIN, SWING_MAX = 0.5, math.radians(30)
NARROW = 0.5    # share kept of a KayKit stance's sideways arm reach and forward elbow bend


def _narrow(dirs):
    """KayKit's chibi stance holds the arms well out from a wide belly, elbows bent forward; our
    figures are authored with the arms hanging, so that stance reads as arms held open. Arms keep
    NARROW of their sideways reach and forearms NARROW of their forward bend."""
    return {b: ([v[0] * NARROW, v[1] * (NARROW if b.startswith("forearm.") else 1.0), v[2]]
                if b.startswith(("arm.", "forearm.")) else v) for b, v in dirs.items()}


def _swing(spec, out):
    """A walk's arms hang as in the (narrowed) stance clip and swing fore and aft with the
    opposite thigh. KayKit's chibi walk holds its arms out near level, swinging them in the
    horizontal plane; on our figures that reads as arms held out like a sleepwalker's."""
    model, name = spec["swing"]["stance"]
    stance = _narrow(_directions(load(model)["clips"][name][0], spec))
    for dirs in out:
        for side, other in (("L", "R"), ("R", "L")):
            thigh = dirs["thigh." + other]
            pitch = math.atan2(-thigh[1], -thigh[2])          # + : the thigh reaches forward (-y)
            a = -max(-SWING_MAX, min(SWING_MAX, SWING_GAIN * pitch))
            dirs["arm." + side] = _about_x(stance["arm." + side], a)
            dirs["forearm." + side] = _about_x(stance["forearm." + side], a)


def _about_x(v, a):
    c, s = math.cos(a), math.sin(a)
    return [v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c]


def _layer(family, ref, spec, frames):
    """Per-frame directions of one layer, plus its leg-aware root scale (or None)."""
    if "neutral" not in spec:
        return _absolute(spec, frames), None
    neutral = ref["clips"][spec["neutral"]][0]
    scale = _leg_scale(family, neutral, spec) if "legs" in spec else None
    return [_relative(family, f, neutral, spec) for f in frames], scale


def clip(family, layers, count=24):
    """layers [(model, clip, map[, offset])] -> {"poses": [pose] * count, "air": {frame}}.
    A layer's offset starts its clip that many frames late (three hydra necks out of step)."""
    roots, air, body = [(0.0, 0.0)] * count, set(), None
    dirs, legs = [{} for _ in range(count)], []
    for model, name, map_name, *offset in layers:
        ref, spec = load(model), MAPS[map_name]
        frames = ten(ref["clips"][name], count)
        if offset:
            frames = frames[offset[0]:] + frames[:offset[0]]
        layer, scale = _layer(family, ref, spec, frames)
        for i, d in enumerate(layer):
            dirs[i].update(d)
        if "legs" in spec:
            legs.append((ref, spec, frames, scale))
        if body is None and not spec.get("still_root"):
            body = map_name
            roots, air = _body(family, ref, spec, frames, scale)
    poses = [P.aim(family, d, r) for d, r in zip(dirs, roots)]
    for ref, spec, frames, scale in legs:
        neutral = ref["clips"][spec["neutral"]][0]
        for i, f in enumerate(frames):
            dirs[i].update(_legs(family, poses[i], f, neutral, spec, scale))
            poses[i] = P.aim(family, dirs[i], roots[i])
    _unwrap(poses)
    return {"poses": poses, "air": air}


def _unwrap(poses):
    """Each bone's angles take the turn nearest the previous frame's: an aim that lands on
    +180 then -180 is one pose, but keys interpolated between them sweep the bone round."""
    for prev, pose in zip(poses, poses[1:]):
        for bone, v in pose.items():
            if bone in prev:
                pose[bone] = tuple(a - 360.0 * round((a - prev[bone][i]) / 360.0) if i < 3 else a
                                   for i, a in enumerate(v))
