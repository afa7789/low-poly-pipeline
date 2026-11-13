"""Key poses of every rig family's motions, drawn as storyboards before they are keyed.

A motion is ten drawings, frame 1 to 10, from rest to rest. Poses are written in
readable terms and converted to the clip format the builder keys (rig_poses):

  bone: (pitch, side, twist[, fwd, up])
    pitch  degrees, counter-clockwise in the side view (forward to the right, up up):
           a hanging arm swings forward/up, an upright spine leans BACK, a forward
           neck lifts the head
    side   degrees, the bone's tip toward +x (the figure's left, the .L side)
    twist  degrees around the bone itself (an upright spine: yaw)
    fwd    metres along the bone's local Z (on the root: forward)
    up     metres along the bone (on the root: up)

Frames left out between two keys are eased in; a bone a key leaves out is at rest.
Then every frame not listed in the motion's "air" is planted: the root moves up or
down until the lowest joint sits where it sits at rest, so feet neither sink nor float.
`existing` motions are the clips the builder makes today, sampled to ten drawings
(not planted: they are drawn as the builder keys them).
"""
import functools
import math
import pathlib

import rig_families as RF
import rig_poses as P
import rig_retarget as RT
import rig_strike as RS

FRAMES = 10


def _probe(family, bone, axis):
    """+1 when a positive rotation on `axis` (0 = x, 2 = z) turns the bone's tip the
    readable way: counter-clockwise in the side view for pitch, toward +x for side."""
    rest = P.joints(family)[bone]
    turn = [0, 0, 0, 0]
    turn[axis] = 10
    tip = P.joints(family, {bone: tuple(turn)})[bone][1]
    d = [tip[i] - rest[1][i] for i in range(3)]
    if axis == 2:
        return 1 if d[0] >= 0 else -1
    r = [rest[1][i] - rest[0][i] for i in range(3)]
    # side view: forward is -y, up is z
    cross = (-r[1]) * d[2] - r[2] * (-d[1])
    if abs(cross) < 1e-6:
        return 1 if d[2] >= 0 else -1
    return 1 if cross > 0 else -1


def _signs(family, bone):
    """(pitch, side) signs of a bone's readable turns. A prop bone the family's table lacks (a
    lobster's claw, a motion's "props") is keyed as written: about its own x and z."""
    if bone not in RF.bones(family):
        return (1, 1)
    return (_probe(family, bone, 0), _probe(family, bone, 2))


def raw(family, keys):
    """Readable keys {frame: {bone: (pitch, side, twist[, fwd, up])}} -> clip keys."""
    signs = {}
    out = {}
    for frame, pose in keys.items():
        out[frame] = {}
        for bone, value in pose.items():
            if bone not in signs:
                signs[bone] = _signs(family, bone)
            pitch, side, twist, *move = tuple(value) + (0.0,) * (5 - len(value))
            out[frame][bone] = (pitch * signs[bone][0], twist, side * signs[bone][1], *move)
    return out


def _frames(clip):
    """Clip keys on any frame range -> FRAMES poses, frame 1..FRAMES."""
    return dict(enumerate(P.strip(clip, FRAMES), start=1))


def lowest(family, pose):
    """Height of the lowest joint (the root itself is a ground anchor, not a body part)."""
    js = P.joints(family, pose)
    return min(min(h[2], t[2]) for bone, (h, t) in js.items() if bone != "root")


def plant(family, poses, air=()):
    """Raise or lower the root on every grounded frame so the lowest joint sits at its
    rest height; a positive authored root `up` (a hop) is added on top, a negative one
    would sink the feet and is not used. Flying families (rig_families.HOVER) are left
    as keyed: their lowest point is a wing tip or a tail, not a foot."""
    if family in RF.HOVER:
        return {frame: {bone: P.pad(v) for bone, v in pose.items()} for frame, pose in poses.items()}
    floor = lowest(family, {})
    out = {}
    for frame, pose in poses.items():
        pose = {bone: P.pad(v) for bone, v in pose.items()}
        if frame not in air:
            rx, ry, rz, lift, up = pose.get("root", (0, 0, 0, 0, 0))
            grounded = {**pose, "root": (rx, ry, rz, lift, 0.0)}
            pose["root"] = (rx, ry, rz, lift, floor - lowest(family, grounded) + max(up, 0.0))
        out[frame] = pose
    return out


# ---------------------------------------------------------------- shared pieces
REST = {}


def crouch(depth):
    """Biped knees bent by `depth` (0..1): thighs forward, shins back (plant lowers the body)."""
    return {"thigh.L": (35 * depth, 0, 0), "shin.L": (-60 * depth, 0, 0), "foot.L": (25 * depth, 0, 0),
            "thigh.R": (35 * depth, 0, 0), "shin.R": (-60 * depth, 0, 0), "foot.R": (25 * depth, 0, 0)}


def _with(*parts):
    pose = {}
    for part in parts:
        pose.update(part)
    return pose


# ---------------------------------------------------------------- biped
BIPED = {
    "overhead": {
        "kind": "attack", "impact": 6,
        "note": "two-handed chop: both arms up and back, body arches, then slams down and forward",
        "keys": {
            1: REST,
            3: _with(crouch(0.3), {"spine": (8, 0, 0), "head": (8, 0, 0),
                                   "arm.L": (150, 10, 0), "forearm.L": (20, 0, 0),
                                   "arm.R": (150, -10, 0), "forearm.R": (20, 0, 0)}),
            5: _with(crouch(0.2), {"spine": (12, 0, 0), "head": (12, 0, 0),
                                   "arm.L": (175, 8, 0), "forearm.L": (35, 0, 0),
                                   "arm.R": (175, -8, 0), "forearm.R": (35, 0, 0)}),
            6: _with(crouch(0.6), {"spine": (-18, 0, 0), "head": (-10, 0, 0),
                                   "arm.L": (55, 6, 0), "forearm.L": (10, 0, 0),
                                   "arm.R": (55, -6, 0), "forearm.R": (10, 0, 0)}),
            7: _with(crouch(0.6), {"spine": (-19, 0, 0), "head": (-10, 0, 0),
                                   "arm.L": (45, 6, 0), "forearm.L": (8, 0, 0),
                                   "arm.R": (45, -6, 0), "forearm.R": (8, 0, 0)}),
            10: REST,
        },
    },
    "sweep": {
        "kind": "attack", "impact": 6,
        "note": "horizontal swing: torso winds back, weapon arm out to the side, then whips it across the front",
        "keys": {
            1: REST,
            3: _with(crouch(0.2), {"spine": (0, 0, -40), "head": (0, 0, 25),
                                   "arm.R": (70, 0, 35), "forearm.R": (15, 0, 0), "arm.L": (35, 0, 0)}),
            6: _with(crouch(0.35), {"spine": (-10, 0, 40), "head": (0, 0, -25),
                                    "arm.R": (70, 0, -40), "forearm.R": (5, 0, 0), "arm.L": (-25, 0, 0)}),
            7: _with(crouch(0.35), {"spine": (-12, 0, 50), "head": (0, 0, -30),
                                    "arm.R": (70, 0, -55), "forearm.R": (5, 0, 0), "arm.L": (-25, 0, 0)}),
            10: REST,
        },
    },
    "bow": {
        "kind": "attack", "impact": 7,
        "note": "bow shot: bow arm straight forward, string hand draws back to the cheek, holds, releases with a snap",
        "keys": {
            1: REST,
            3: {"spine": (0, 0, -20), "head": (0, 0, 15),
                "arm.L": (88, 0, 0), "arm.R": (88, 0, 0), "forearm.R": (40, 0, 0)},
            5: {"spine": (4, 0, -30), "head": (0, 0, 25),
                "arm.L": (90, 0, 0), "arm.R": (95, -10, 0), "forearm.R": (150, 0, 0)},
            6: {"spine": (4, 0, -30), "head": (0, 0, 25),
                "arm.L": (90, 0, 0), "arm.R": (95, -10, 0), "forearm.R": (155, 0, 0)},
            7: {"spine": (6, 0, -30), "head": (0, 0, 25),
                "arm.L": (92, 0, 0), "arm.R": (110, -50, 0), "forearm.R": (60, 0, 0)},
            8: {"spine": (4, 0, -25), "head": (0, 0, 20),
                "arm.L": (85, 0, 0), "arm.R": (90, -45, 0), "forearm.R": (30, 0, 0)},
            10: REST,
        },
    },
    "cast_raise": {
        "kind": "spell", "impact": 6,
        "note": "spell gesture: gathers low, both arms sweep up overhead, chest open, head back, then settles",
        "keys": {
            1: REST,
            3: _with(crouch(0.3), {"spine": (-12, 0, 0), "head": (-10, 0, 0),
                                   "arm.L": (30, -10, 0), "forearm.L": (40, 0, 0),
                                   "arm.R": (30, 10, 0), "forearm.R": (40, 0, 0)}),
            6: {"spine": (10, 0, 0), "head": (20, 0, 0), "root": (0, 0, 0, 0, 0.08),
                "arm.L": (165, 25, 0), "forearm.L": (10, 0, 0),
                "arm.R": (165, -25, 0), "forearm.R": (10, 0, 0)},
            8: {"spine": (10, 0, 0), "head": (20, 0, 0), "root": (0, 0, 0, 0, 0.08),
                "arm.L": (165, 25, 0), "forearm.L": (10, 0, 0),
                "arm.R": (165, -25, 0), "forearm.R": (10, 0, 0)},
            10: REST,
        },
    },
    "warcry": {
        "kind": "spell", "impact": 6,
        "note": "war cry: crouches, then rises with arms flung wide, fists up, chest out and head thrown back",
        "keys": {
            1: REST,
            3: _with(crouch(0.4), {"spine": (-20, 0, 0), "head": (-10, 0, 0),
                                   "arm.L": (20, -15, 0), "forearm.L": (60, 0, 0),
                                   "arm.R": (20, 15, 0), "forearm.R": (60, 0, 0)}),
            6: {"spine": (14, 0, 0), "head": (28, 0, 0),
                "arm.L": (10, 85, 0), "forearm.L": (0, 70, 0),
                "arm.R": (10, -85, 0), "forearm.R": (0, -70, 0)},
            8: {"spine": (14, 0, 0), "head": (28, 0, 0),
                "arm.L": (10, 90, 0), "forearm.L": (0, 70, 0),
                "arm.R": (10, -90, 0), "forearm.R": (0, -70, 0)},
            10: REST,
        },
    },
    "aim_rifle": {
        "kind": "attack", "impact": 4,
        "note": "long rifle carried on the left forearm (hrif): the left arm folds so the barrel levels "
                "forward at chest height, the right hand steadies it, the shot rocks the torso back",
        # left-arm angles searched on hrif's own armature against the rifle's rest line (muzzle up and
        # left of the head): barrel 2 degrees off dead ahead, its middle in front of the chest. The
        # KayKit two-hand shot, made for a rifle in the right hand, swung this one out to the side
        "keys": {
            1: REST,
            3: {"spine": (4, 0, 0), "head": (-4, 0, 0),
                "arm.L": (100, 10, -15), "forearm.L": (-180, -60, -10),
                "arm.R": (-70, 25, 0), "forearm.R": (-50, 0, 0)},
            4: {"spine": (16, 0, 0), "head": (-10, 0, 0), "root": (0, 0, 0, -0.24),
                "arm.L": (118, 10, -15), "forearm.L": (-180, -60, -10),
                "arm.R": (-70, 25, 0), "forearm.R": (-50, 0, 0)},
            5: {"spine": (10, 0, 0), "head": (-8, 0, 0), "root": (0, 0, 0, -0.16),
                "arm.L": (108, 10, -15), "forearm.L": (-180, -60, -10),
                "arm.R": (-70, 25, 0), "forearm.R": (-50, 0, 0)},
            7: {"spine": (4, 0, 0), "head": (-4, 0, 0),
                "arm.L": (100, 10, -15), "forearm.L": (-180, -60, -10),
                "arm.R": (-70, 25, 0), "forearm.R": (-50, 0, 0)},
            10: REST,
        },
    },
    "spike_gore": {
        "kind": "attack", "impact": 4,
        "note": "helmet spike: the head dips, then the whole torso drives the spike forward and up",
        "keys": {
            1: REST,
            2: _with(crouch(0.8), {"spine": (-18, 0, 0), "head": (-40, 0, 0), "root": (0, 0, 0, -0.25),
                                   "arm.L": (-25, 0, 0), "arm.R": (-25, 0, 0)}),
            4: _with(crouch(0.3), {"spine": (-40, 0, 0), "head": (-10, 0, 0), "root": (0, 0, 0, 0.50),
                                   "arm.L": (-35, 0, 0), "arm.R": (-35, 0, 0)}),
            5: _with(crouch(0.3), {"spine": (-37, 0, 0), "head": (-8, 0, 0), "root": (0, 0, 0, 0.50),
                                   "arm.L": (-35, 0, 0), "arm.R": (-35, 0, 0)}),
            8: REST,
            10: REST,
        },
    },
    "ram": {
        "kind": "attack", "impact": 4,
        "note": "body ram: what the chest carries (a barrel hugged in both arms) is the weapon; the body rocks back, "
                "then drives it forward and down from the hips, and holds",
        "keys": {
            1: REST,
            2: _with(crouch(0.5), {"spine": (22, 0, 0), "head": (6, 0, 0), "root": (0, 0, 0, -0.30)}),
            4: _with(crouch(0.4), {"spine": (-58, 0, 0), "head": (30, 0, 0), "root": (0, 0, 0, 0.35)}),
            5: _with(crouch(0.4), {"spine": (-54, 0, 0), "head": (28, 0, 0), "root": (0, 0, 0, 0.32)}),
            7: REST,
            10: REST,
        },
    },
    "back_tube_fire": {
        "kind": "attack", "impact": 4,
        "note": "a tube on the back: bows from the hips until it levels over the head, the shot kicks the hips back",
        "keys": {
            1: REST,
            3: _with(crouch(0.3), {"spine": (-78, 0, 0), "head": (45, 0, 0), "arm.L": (25, 0, 0), "arm.R": (25, 0, 0)}),
            4: _with(crouch(0.5), {"spine": (-84, 0, 0), "head": (45, 0, 0), "arm.L": (25, 0, 0), "arm.R": (25, 0, 0),
                                   "root": (0, 0, 0, -0.12)}),
            6: _with(crouch(0.3), {"spine": (-70, 0, 0), "head": (40, 0, 0), "arm.L": (25, 0, 0), "arm.R": (25, 0, 0),
                                   "root": (0, 0, 0, -0.06)}),
            10: REST,
        },
    },
}


# ---------------------------------------------------------------- quadruped
def _quad_legs(front, hind):
    """Front legs (leg1/leg2) and hind legs (leg3/leg4) pitched together."""
    return {"leg1.upper": (front, 0, 0), "leg2.upper": (front, 0, 0),
            "leg3.upper": (hind, 0, 0), "leg4.upper": (hind, 0, 0)}


_HIND = ("leg3", "leg4")       # a quadruped's hind legs: their feet stay by the ring while the body reaches
_FOUR = ("leg",)


def _quad_crouch(front, hind):
    """Knees folded, 0..1 each: elbows back / hocks forward, so the body sinks."""
    legs = {}
    for leg, depth, sign in (("leg1", front, -1), ("leg2", front, -1), ("leg3", hind, 1), ("leg4", hind, 1)):
        legs[f"{leg}.upper"] = (sign * 35 * depth, 0, 0)
        legs[f"{leg}.lower"] = (-sign * 65 * depth, 0, 0)
    return legs


QUADRUPED = {
    "pounce": {
        "kind": "attack", "impact": 5, "air": (4,), "stay": _HIND,
        "note": "pounce: sinks on the haunches, springs forward with forelegs reaching and lands stretched out over "
                "hind feet that stay by the ring; held, then gathers back",
        "keys": {
            1: REST,
            2: _with(_quad_crouch(0.4, 0.9), {"root": (0, 0, 0, -0.14), "head": (-10, 0, 0),
                                              "tail.1": (-20, 0, 0)}),
            4: _with(_quad_legs(70, -55), {"root": (0, 0, 0, 0.50, 0.35), "spine.1": (10, 0, 0),
                                           "head": (15, 0, 0), "tail.1": (25, 0, 0),
                                           "leg1.lower": (-20, 0, 0), "leg2.lower": (-20, 0, 0)}),
            5: {"root": (0, 0, 0, 0.72), "spine.1": (-10, 0, 0), "head": (-22, 0, 0), "tail.1": (15, 0, 0),
                "leg1.upper": (40, 0, 0), "leg2.upper": (40, 0, 0)},
            8: {"root": (0, 0, 0, 0.68), "spine.1": (-12, 0, 0), "head": (-26, 0, 0),
                "leg1.upper": (34, 0, 0), "leg2.upper": (34, 0, 0)},
            10: REST,
        },
    },
    "ram": {
        "kind": "attack", "impact": 6,
        "note": "head-butt: lowers the head, rocks back, then drives forward off the hind legs",
        "keys": {
            1: REST,
            3: _with(_quad_crouch(0.3, 0.5), {"root": (0, 0, 0, -0.15), "head": (-35, 0, 0)}),
            6: _with(_quad_legs(20, -35), {"root": (0, 0, 0, 0.35, 0.0), "head": (-45, 0, 0),
                                           "spine.1": (-8, 0, 0), "tail.1": (25, 0, 0)}),
            7: _with(_quad_legs(20, -35), {"root": (0, 0, 0, 0.35, 0.0), "head": (-40, 0, 0),
                                           "spine.1": (-8, 0, 0), "tail.1": (25, 0, 0)}),
            10: REST,
        },
    },
    "rear_up": {
        "kind": "attack", "impact": 6,
        "note": "rear and stomp: rises on the hind legs, forelegs pawing high, crashes down on them",
        "keys": {
            1: REST,
            4: {"root": (40, 0, 0, -0.30, 0.10), "leg1.upper": (80, 0, 0), "leg1.lower": (-70, 0, 0),
                "leg2.upper": (60, 0, 0), "leg2.lower": (-80, 0, 0),
                "leg3.upper": (-40, 0, 0), "leg4.upper": (-40, 0, 0), "head": (-25, 0, 0)},
            5: {"root": (45, 0, 0, -0.30, 0.12), "leg1.upper": (60, 0, 0), "leg1.lower": (-90, 0, 0),
                "leg2.upper": (85, 0, 0), "leg2.lower": (-60, 0, 0),
                "leg3.upper": (-45, 0, 0), "leg4.upper": (-45, 0, 0), "head": (-30, 0, 0)},
            6: _with(_quad_legs(25, -10), {"root": (-5, 0, 0, 0.05), "head": (-20, 0, 0)}),
            10: REST,
        },
    },
    "roar": {
        "kind": "spell", "impact": 5,
        "note": "roar: plants the forelegs wide, rocks the chest down, stretches the neck out and up, holds",
        "keys": {
            1: REST,
            3: _with(_quad_legs(-10, 10), {"root": (0, 0, 0, -0.08), "head": (-20, 0, 0)}),
            5: {"root": (-8, 0, 0, 0), "leg1.upper": (20, 25, 0), "leg2.upper": (20, -25, 0),
                "head": (35, 0, 0), "tail.1": (30, 0, 0), "tail.2": (20, 0, 0)},
            8: {"root": (-8, 0, 0, 0), "leg1.upper": (20, 25, 0), "leg2.upper": (20, -25, 0),
                "head": (30, 0, 0), "tail.1": (30, 0, 0), "tail.2": (20, 0, 0)},
            10: REST,
        },
    },
}


# ---------------------------------------------------------------- spider
FRONT_PAIR = ("leg2", "leg3")          # the ring: leg1 left-front-side ... leg2/leg3 the front pair


def _spider_front(upper, lower):
    return {f"{leg}.upper": (upper, 0, 0) for leg in FRONT_PAIR} | {
        f"{leg}.lower": (lower, 0, 0) for leg in FRONT_PAIR}


def _fore(left, right=None):
    """World directions (x, forward is -y, up) of the front pair's upper and lower bones: `left` =
    (upper, lower) of the leg on +x, `right` the other's (mirrored from `left` when left out)."""
    def flip(d):
        return (-d[0], d[1], d[2])
    right = right or left
    return {"leg2.upper": left[0], "leg2.lower": left[1], "leg3.upper": flip(right[0]), "leg3.lower": flip(right[1])}


_FORE_UP = ((0.25, -0.45, 0.85), (0.10, -0.80, 0.60))       # a front leg cocked high over the head
_FORE_OUT = ((0.20, -1.00, 0.10), (0.05, -1.00, -0.45))     # and thrust straight ahead, claw down
_SPIDER_REAR = ("leg5", "leg6", "leg7", "leg8")
_SPIDER_STAND = ("leg1", "leg4") + _SPIDER_REAR             # every leg but the front pair

_FORE_WIDE = ((0.80, -0.35, 0.50), (0.70, -0.60, 0.40))     # a front leg cocked out to its own side
_FORE_RAKED = ((0.10, -0.95, 0.20), (-0.60, -0.75, -0.25))  # and raked across the front, past the middle

SPIDER = {
    # the bite is the lunge; this one stays on the ring and reads by what crosses the front: the claws rake
    # from the sides across the target in turn and the body swings into each rake
    "scratch": {
        "kind": "attack", "impact": 5, "stay": _SPIDER_STAND,
        "note": "scratch: both front legs cocked out wide, then the left rakes across the front as the body swings "
                "into it, the right rakes back across a beat later; claws held crossed on the target, then back",
        "aims": {3: _fore(_FORE_WIDE), 5: _fore(_FORE_RAKED, _FORE_WIDE), 6: _fore(_FORE_WIDE, _FORE_RAKED),
                 7: _fore(_FORE_RAKED), 8: _fore(_FORE_RAKED)},
        "keys": {
            1: REST,
            3: {"body": (8, 0, 0), "root": (0, 0, 0, -0.10)},
            5: {"body": (-4, 0, 0), "head": (-8, 0, 0), "root": (0, 0, -16, 0.14)},
            6: {"body": (-4, 0, 0), "head": (-8, 0, 0), "root": (0, 0, 16, 0.14)},
            7: {"body": (-6, 0, 0), "head": (-10, 0, 0), "root": (0, 0, 0, 0.16)},
            8: {"body": (-6, 0, 0), "head": (-10, 0, 0), "root": (0, 0, 0, 0.14)},
            10: REST,
        },
    },
    "spit": {
        "kind": "attack", "impact": 6,
        "note": "spit: front rises, head draws back, abdomen pumps, then the head snaps forward and spits",
        "keys": {
            1: REST,
            3: {"body": (25, 0, 0), "head": (40, 0, 0), "abdomen": (30, 0, 0), "root": (0, 0, 0, -0.08)},
            5: {"body": (30, 0, 0), "head": (50, 0, 0), "abdomen": (-25, 0, 0), "root": (0, 0, 0, -0.10)},
            6: {"body": (-10, 0, 0), "head": (-45, 0, 0), "abdomen": (20, 0, 0), "root": (0, 0, 0, 0.12)},
            7: {"body": (-10, 0, 0), "head": (-40, 0, 0), "abdomen": (15, 0, 0), "root": (0, 0, 0, 0.12)},
            10: REST,
        },
    },
    "pounce": {
        "kind": "attack", "impact": 5, "air": (4,), "stay": _SPIDER_REAR,
        "note": "pounce: body drops low, springs forward with the front pair raised and lands stretched out, front "
                "claws thrust ahead, rear feet still by the ring; held, then back",
        "aims": {5: _fore(_FORE_OUT), 8: _fore(_FORE_OUT)},
        "keys": {
            1: REST,
            2: {"root": (0, 0, 0, -0.10), "body": (-8, 0, 0), "head": (-5, 0, 0)},
            4: _with(_spider_front(70, 40), {"root": (0, 0, 0, 0.42, 0.40), "body": (15, 0, 0),
                                             "abdomen": (-15, 0, 0)}),
            5: {"root": (0, 0, 0, 0.60), "body": (-8, 0, 0), "head": (-20, 0, 0)},
            8: {"root": (0, 0, 0, 0.56), "body": (-8, 0, 0), "head": (-20, 0, 0)},
            10: REST,
        },
    },
    "sting": {
        "kind": "attack", "impact": 6,
        "note": "sting: front rises, abdomen curls up and over, then jabs down and forward",
        "keys": {
            1: REST,
            3: {"body": (15, 0, 0), "abdomen": (-60, 0, 0), "head": (-5, 0, 0)},
            5: {"body": (20, 0, 0), "abdomen": (-120, 0, 0), "head": (-5, 0, 0)},
            6: {"body": (-8, 0, 0), "abdomen": (-185, 0, 0), "head": (-10, 0, 0),
                "root": (0, 0, 0, 0.1)},
            7: {"body": (-8, 0, 0), "abdomen": (-185, 0, 0), "head": (-10, 0, 0),
                "root": (0, 0, 0, 0.1)},
            10: REST,
        },
    },
    "rear_up": {
        "kind": "spell", "impact": 5,
        "note": "threat display: rears the front half up, front two pairs spread high and wide, holds",
        "keys": {
            1: REST,
            3: {"body": (15, 0, 0), "head": (5, 0, 0)},
            5: {"body": (35, 0, 0), "head": (10, 0, 0),
                "leg2.upper": (40, 25, 0), "leg3.upper": (40, -25, 0),
                "leg1.upper": (30, 20, 0), "leg4.upper": (30, -20, 0), "abdomen": (15, 0, 0)},
            8: {"body": (35, 0, 0), "head": (10, 0, 0),
                "leg2.upper": (45, 25, 0), "leg3.upper": (45, -25, 0),
                "leg1.upper": (30, 20, 0), "leg4.upper": (30, -20, 0), "abdomen": (15, 0, 0)},
            10: REST,
        },
    },
}

# ---------------------------------------------------------------- machines and odd bodies
def _scaled(pose, share):
    return {bone: tuple(c * share for c in value) for bone, value in pose.items()}


def _kick(shot, wind=None):
    """The drawings of a shot from its peak pose: a one-drawing wind-up (the barrel lowers, the body
    gathers), the kick in the next drawing, then it settles through one small overshoot. A slow
    return reads as a lean at unit size; the snap and the bounce read as a shot."""
    return {1: REST, 2: wind or REST, 3: shot, 4: _scaled(shot, 0.4), 5: _scaled(shot, -0.18), 7: REST, 10: REST}


def _thrown(shot, wind):
    """The drawings of a body that is its own weapon (a pod, a shard): gathered back for one drawing, thrown at
    the target, HELD out there for a second drawing (the game camera needs the reach to stay), then one bounce
    back. Use with "impact": 3."""
    return {1: REST, 2: wind, 3: shot, 4: _scaled(shot, 0.92), 5: _scaled(shot, 0.3), 6: _scaled(shot, -0.15),
            8: REST, 10: REST}


def _recoil(extra_hit=None, extra_wind=None):
    """A gun's kick: the turret/barrel snaps up, the body hops and is shoved back, then bounces to rest."""
    shot = {"head": (28, 0, 0), "root": (0, 0, 0, -0.28, 0.05), **(extra_hit or {})}
    return {"kind": "attack", "impact": 3,
            "note": "fires: barrel dips, then kicks up as the whole body hops back, one bounce forward and settles",
            "keys": _kick(shot, {"head": (-8, 0, 0), **(extra_wind or {})})}


def _brace(note, hold):
    return {"kind": "spell", "impact": 5, "note": note, "keys": {1: REST, 5: hold, 8: hold, 10: REST}}


_ROCK = ({"hull": (18, 0, 0)}, {"hull": (-4, 0, 0)})      # a shot's hull: the nose dips, then is thrown up
VEHICLE = {"recoil": _recoil(*_ROCK),
           "fire": {"kind": "attack", "impact": 3,
                    "note": "one-piece launcher (no turret bone): the whole cart bucks nose-up off its front wheels",
                    "keys": _kick({"hull": (28, 0, 0), "root": (0, 0, 0, -0.28, 0.10)}, {"hull": (-6, 0, 0)})},
           "brace": _brace("deploys: turret rises and holds, the hull rocks back", {"head": (18, 0, 0),
                                                                                     "hull": (3, 0, 0)})}
def _arms(pitch):
    return {"arm.L": (pitch, 0, 0), "arm.R": (pitch, 0, 0)}


# the arms of the tracked units that slam hang at the sides (h06U, n01T): overhead is a long way up, and
# the blow must stop out in front, not back at the hip where the arms rest
TRACKED = {"recoil": _recoil(*_ROCK),
           "arm_slam": {"kind": "attack", "impact": 5,
                        "note": "tool arms swing up overhead, the body leans back, then both slam down in front",
                        "keys": {1: REST, 3: _with(_arms(150), {"hull": (10, 0, 0), "root": (0, 0, 0, -0.05)}),
                                 4: _with(_arms(165), {"hull": (12, 0, 0), "root": (0, 0, 0, -0.05)}),
                                 5: _with(_arms(62), {"hull": (-16, 0, 0), "root": (0, 0, 0, 0.10)}),
                                 6: _with(_arms(55), {"hull": (-14, 0, 0), "root": (0, 0, 0, 0.10)}), 10: REST}},
           "brace": _brace("deploys: turret rises and holds, the hull rocks back", {"head": (18, 0, 0),
                                                                                     "hull": (3, 0, 0)})}
def _burst(beat):
    """A strafing pass's drawing `beat` (0..4): the nose down at the target and the craft thrown at it on the even
    beats, kicked back by its guns on the odd ones. The game camera looks down on it, so the rattle is travel along
    the ground: the airframe jolts fore and aft, the guns (gondola) slide back in their mounts, the nose shakes
    side to side and the rotor (prop) is spun on."""
    fire = beat % 2 == 0
    return {"hull": (-26 if fire else -14, 6 if fire else -6, 0), "gondola": (14, 0, 0, 0, 0.0 if fire else -0.30),
            "prop": (0, 80.0 * (beat + 1), 0), "root": (0, 0, 0, 0.95 if fire else 0.15, -0.12)}


AIRCRAFT = {"strafe": {"kind": "attack", "impact": 3,
                       "note": "strafing run: the nose swings down at the target, three bursts throw the craft at it and "
                               "kick it back along the ground, guns sliding in their mounts, then it pulls up",
                       "keys": {1: REST, 2: {"hull": (8, 0, 0), "root": (0, 0, 0, -0.20, 0.05)},
                                **{3 + i: _burst(i) for i in range(5)},
                                8: {"hull": (10, 0, 0), "gondola": (-6, 0, 0), "prop": (0, 560, 0),
                                    "root": (0, 0, 0, -0.06, 0.08)},
                                9: {"prop": (0, 720, 0)},      # two whole turns: the rest pose again
                                10: REST}},
            "bomb": {"kind": "attack", "impact": 6,
                     "note": "bomb drop: gondola swings back, then forward to release, the craft bobs up",
                     "keys": {1: REST, 4: {"gondola": (-25, 0, 0)}, 6: {"gondola": (25, 0, 0), "hull": (-4, 0, 0)},
                              7: {"gondola": (15, 0, 0), "root": (0, 0, 0, 0, 0.08)}, 10: REST}},
            "turn": {"kind": "spell", "impact": 5, "note": "banks and turns, rudder hard over",
                     "keys": {1: REST, 5: {"hull": (0, 0, 20), "rudder": (0, 30, 0)},
                              8: {"hull": (0, 0, 20), "rudder": (0, 30, 0)}, 10: REST}}}
CREW = {"fire": {"kind": "attack", "impact": 3,
                 "note": "fires: barrel kicks up, cradle jolts back on the crew's legs, then settles",
                 "keys": {1: REST, 2: {"barrel": (-4, 0, 0)},
                          3: {"barrel": (22, 0, 0), "cradle": (6, 0, 0), "root": (0, 0, 0, -0.10)},
                          5: {"barrel": (10, 0, 0), "cradle": (3, 0, 0), "root": (0, 0, 0, -0.05)}, 10: REST}},
        "reload": {"kind": "spell", "impact": 5, "note": "reload: barrel tips down, the crew crouches, back up",
                   "keys": {1: REST, 4: {"barrel": (-25, 0, 0), "thigh.L": (25, 0, 0), "thigh.R": (25, 0, 0),
                                         "shin.L": (-40, 0, 0), "shin.R": (-40, 0, 0)},
                            7: {"barrel": (-20, 0, 0)}, 10: REST}}}
_TENDRILS = ("tendril1", "tendril2", "tendril3")
def _whip(body, stalk, tendril, reach=0.0):
    """A pod's lash drawing: the body leant `body` degrees back, each stalk bone `stalk` more (a stalk is the
    whip: its tip travels the farthest along the ground), the tendrils' first bones `tendril` forward."""
    return {"body": (body, 0, 0), "stalk.1": (stalk, 0, 0), "stalk.2": (stalk, 0, 0), "root": (0, 0, 0, reach),
            **{f"{t}.1": (tendril, 0, 0) for t in _TENDRILS}, **{f"{t}.2": (0.6 * tendril, 0, 0) for t in _TENDRILS}}


POD = {"lash": {"kind": "attack", "impact": 6,
                "note": "lash: the body and stalk bend back with the tendrils coiled, then the whole stalk whips down "
                        "at the target along the ground, tendrils thrown forward after it; held, then back",
                "keys": {1: REST, 4: _whip(14, 26, -40, -0.08), 6: _whip(-26, -34, 70, 0.22),
                         7: _whip(-24, -32, 55, 0.20), 8: _whip(-22, -28, 45, 0.18), 10: REST}},
       "pulse": {"kind": "attack", "impact": 3,
                 "note": "pulse: tips back to gather, then the whole body is thrown at the target, eye first, and "
                         "held there; the stalk and tendrils whip behind, one bounce back",
                 "keys": _thrown({"body": (-16, 0, 0), "root": (0, 0, 0, 0.62, 0.06),
                                  "stalk.1": (35, 0, 0), "stalk.2": (25, 0, 0), **{f"{t}.1": (-35, 0, 0) for t in _TENDRILS}},
                                 {"body": (16, 0, 0), "root": (0, 0, 0, -0.20, 0.04),
                                  "stalk.1": (-20, 0, 0), "stalk.2": (-15, 0, 0), **{f"{t}.1": (20, 0, 0) for t in _TENDRILS}})}}

def _reach(wound, struck, held=None):
    """The drawings of a strike that reads from the game camera, which looks down on the units: a short
    pull-back, the strike out along the ground on drawing 5 (the contact), held to drawing 8 (ten
    frames of the clip, 0.4 s), back to rest on 10. Use with "impact": 5."""
    return {1: REST, 3: wound, 5: struck, 8: held or struck, 10: REST}


def _swept(upper=(0.55, 0.75, 0.25), lower=(0.30, 0.93, 0.0)):
    """World directions of both wings swept back along the body (x out, +y is back): seen from above,
    the wings open the silhouette so the head thrown forward is clear of them."""
    return {f"wing{n}.{part}": (side * d[0], d[1], d[2])
            for n, side in ((1, 1), (2, -1)) for part, d in (("upper", upper), ("lower", lower))}


def _spit(body, surge, stay=(), swept=None):
    """A ranged head attack for beasts without one in their references: the head rears as the body is
    drawn back, then head and body are thrown `surge` metres forward along the ground (over the feet
    of `stay`, wings swept back where it has them) and held."""
    return {"kind": "attack", "impact": 5, "stay": stay,
            "note": "spit: the body draws back and the head rears, then both are thrown forward along the ground; held",
            "aims": {5: swept, 8: swept} if swept else {},
            "keys": _reach({body: (18, 0, 0), "head": (40, 0, 0), "root": (0, 0, 0, -0.4 * surge)},
                           {body: (-10, 0, 0), "head": (-20, 0, 0), "root": (0, 0, 0, surge)},
                           {body: (-8, 0, 0), "head": (-16, 0, 0), "root": (0, 0, 0, 0.92 * surge)})}


# a four-legged spitter's head is what reads from above: it is cocked back and to one side, snapped out straight with
# the neck stretched (the head slides out along its bone) as the body darts under it, and the body is thrown BACK by
# the shot before it settles; a lunge that is held (quill_volley, a bite) is a different read
QUADRUPED["spit"] = {
    "kind": "attack", "impact": 5, "stay": _FOUR,
    "note": "spit: the body draws back, the head reared and cocked to one side, then the head snaps out straight at the "
            "target, neck stretched, the body darting under it; the shot throws the body back, then it settles",
    "keys": {1: REST,
             3: {"spine.2": (14, 0, 0), "head": (30, 36, 0, 0, -0.04), "root": (0, 0, 0, -0.30)},
             5: {"spine.2": (-8, 0, 0), "head": (-14, 0, 0, 0, 0.09), "root": (0, 0, 0, 0.62)},
             6: {"spine.2": (-6, 0, 0), "head": (-10, -8, 0, 0, 0.07), "root": (0, 0, 0, 0.56)},
             7: {"head": (10, 0, 0), "root": (0, 0, 0, -0.12)},
             9: REST, 10: REST}}
QUADRUPED["quill_volley"] = {
    "kind": "attack", "impact": 5, "stay": _FOUR,
    "note": "back quills: rocks back on the haunches, then drives forward over planted feet with the front down and "
            "the rump up so the quills tip over the head and fly; held, then settles",
    "keys": _reach({"root": (10, 0, 0, -0.18), "head": (20, 0, 0), "spine.1": (-6, 0, 0)},
                   {"root": (-18, 0, 0, 0.42), "head": (-22, 0, 0), "spine.1": (-12, 0, 0)},
                   {"root": (-16, 0, 0, 0.39), "head": (-20, 0, 0), "spine.1": (-10, 0, 0)})}
QUADRUPED["tail_shot"] = {
    "kind": "attack", "impact": 5, "stay": _FOUR,
    "note": "tail gun: the raised tail curls back as the body leans in, whips forward over the back and fires; the shot "
            "throws the body back onto its hind legs (a spit darts forward: this one recoils), one bounce and settles",
    "keys": {1: REST,
             3: {"tail.1": (24, 0, 0), "tail.2": (10, 0, 0), "root": (-6, 0, 0, 0.14), "head": (-10, 0, 0)},
             5: {"tail.1": (-58, 0, 0), "tail.2": (-34, 0, 0), "root": (-4, 0, 0, 0.16), "head": (-14, 0, 0)},
             6: {"tail.1": (-40, 0, 0), "tail.2": (-20, 0, 0), "root": (12, 0, 0, -0.36), "head": (10, 0, 0)},
             7: {"tail.1": (-44, 0, 0), "tail.2": (-24, 0, 0), "root": (8, 0, 0, -0.26), "head": (6, 0, 0)},
             8: {"tail.1": (-16, 0, 0), "tail.2": (-8, 0, 0), "root": (0, 0, 0, 0.05)},
             10: REST}}
WYRM = {"spit": _spit("spine.1", 0.45, swept=_swept())}
_RAY_SWEPT = _swept((0.50, 0.80, 0.10), (0.30, 0.95, 0.0))
RAY = {"spit": {"kind": "attack", "impact": 5, "aims": {5: _RAY_SWEPT, 8: _RAY_SWEPT},
                "note": "spit: the front pitches up as it drifts back, then it darts forward flat with the wings "
                        "swept back as the bolt leaves, the tail lashing; held, then back",
                "keys": _reach({"body": (30, 0, 0), "tail.1": (-25, 0, 0), "root": (0, 0, 0, -0.20, 0.06)},
                               {"body": (-14, 0, 0), "tail.1": (40, 0, 0), "tail.2": (25, 0, 0), "root": (0, 0, 0, 0.60)},
                               {"body": (-12, 0, 0), "tail.1": (32, 0, 0), "tail.2": (22, 0, 0), "root": (0, 0, 0, 0.55)})}}
_CLAWS = ("claw.L", "claw.R")       # a lobster's (n00W): prop bones of its spec, not in the crawler table


def _claws(lift, spread):
    """Both claws lifted `lift` degrees and opened `spread` degrees outward (negative: shut across the front)."""
    return {"claw.L": (lift, spread, 0), "claw.R": (lift, -spread, 0)}


_CRAWLER_REAR = ("leg3", "leg4")
CRAWLER = {"spit": _spit("body", 0.30, _CRAWLER_REAR),
           # the gun rides the head bone: it slides back along itself and the whole body is shoved back and HELD there
           # a drawing (a one-drawing kick of a body this small is lost from the game camera)
           "shoot": {"kind": "attack", "impact": 3,
                     "note": "fires: leans in behind the gun, then the gun kicks up and back and the body is thrown "
                             "back along the ground, held a beat, one bounce forward and settles",
                     "keys": {1: REST, 2: {"head": (-8, 0, 0), "body": (-6, 0, 0), "root": (0, 0, 0, 0.12)},
                              3: {"head": (24, 0, 0, 0, -0.16), "body": (10, 0, 0), "root": (0, 0, 0, -0.40, 0.04)},
                              4: {"head": (14, 0, 0, 0, -0.10), "body": (8, 0, 0), "root": (0, 0, 0, -0.36)},
                              5: {"head": (4, 0, 0, 0, -0.02), "root": (0, 0, 0, -0.12)},
                              6: {"head": (-4, 0, 0), "root": (0, 0, 0, 0.06)}, 8: REST, 10: REST}},
           "pinch": {"kind": "attack", "impact": 5, "props": _CLAWS, "stay": _CRAWLER_REAR,
                     "note": "pinch: draws back with both claws thrown wide, lunges over planted rear feet and snaps "
                             "them shut across the front; held shut on the target, then back",
                     "keys": _reach(_with(_claws(35, 55), {"body": (12, 0, 0), "root": (0, 0, 0, -0.10)}),
                                    _with(_claws(-8, -26), {"body": (-10, 0, 0), "root": (0, 0, 0, 0.32)}),
                                    _with(_claws(-6, -24), {"body": (-8, 0, 0), "root": (0, 0, 0, 0.30)}))}}
# the carriage (spine.1 carries every other piece) rocks on its wheels, the front piece kicks on top of that
SLED = {"fire": {**_recoil({"spine.1": (10, 0, 0), "spine.4": (4, 0, 0)}, {"spine.1": (-3, 0, 0)}),
                 "note": "fires: the carriage rocks back on its wheels, the front kicks up, one bounce forward"}}


def _hull_rock(lean, barrels):
    """A walker's one-piece hull leaning back `lean` degrees about the hips: the thighs turn the other
    way, so the legs stay planted under it and nothing bends at the waist."""
    return {"pelvis": (lean, 0, 0), "thigh.L": (-lean, 0, 0), "thigh.R": (-lean, 0, 0),
            **{bone: (turn, 0, 0) for bone, turn in barrels.items()}}


_LEVEL = -36        # degrees a walker's raised barrels drop to point at a target on the ground


def _levelled(shove, fired=None):
    """A walker's quick-fire drawing: the hull leant in with both barrels dropped at the target, the whole machine
    `shove` metres along the ground (negative: thrown back by the shot), the barrel `fired` slid back in its mount."""
    pose = _hull_rock(-6 if fired is None else 5, {"barrel.L": _LEVEL, "barrel.R": _LEVEL})
    if fired:
        pose[fired] = (_LEVEL + 6, 0, 0, 0, -0.30)
    return {**pose, "root": (0, 0, 0, shove)}


WALKER = {"shoot": {"kind": "attack", "impact": 3,
                    "note": "main guns: the hull dips to aim, both barrels kick and the whole hull is thrown back "
                            "on planted legs, one bounce forward",
                    "keys": _kick(_hull_rock(22, {"barrel.L": 10, "barrel.R": 10}),
                                  _hull_rock(-8, {"barrel.L": -5, "barrel.R": -5}))},
          "fire": {"kind": "attack", "impact": 3,
                   "note": "quick pair, levelled: both barrels drop at the target, the left fires and slides back in "
                           "its mount as the hull is shoved back along the ground, then the right; settles",
                   "keys": {1: REST, 2: _levelled(0.08), 3: _levelled(-0.34, "barrel.L"), 4: _levelled(-0.06),
                            5: _levelled(-0.36, "barrel.R"), 6: _levelled(-0.06),
                            7: _with(_hull_rock(-3, {"barrel.L": -16, "barrel.R": -16}), {"root": (0, 0, 0, 0.04)}),
                            9: REST, 10: REST}}}
SHARD = {"pulse": {"kind": "attack", "impact": 3,
                   "note": "pulse: the shard tips back, is thrown at the target top first and held there, one bounce back",
                   "keys": _thrown({"body": (-36, 0, 0), "root": (0, 0, 0, 0.50, 0.10), "tail.1": (30, 0, 0)},
                                   {"body": (18, 0, 0), "root": (0, 0, 0, -0.16), "tail.1": (-15, 0, 0)})}}


def _push(lean, reach, bend):
    """A limbless caster's push: the column leans `lean` degrees back, both arms `reach` degrees up
    in front, elbows bent `bend`; the head stays level."""
    return {"base": (0.5 * lean, 0, 0), "spine": (0.5 * lean, 0, 0), "head": (-0.6 * lean, 0, 0),
            **{f"{bone}.{side}": (turn, 0, 0) for side in "LR" for bone, turn in (("arm", reach), ("forearm", bend))}}


WRAITH = {"pulse": {"kind": "attack", "impact": 3,
                    "note": "scream: hands drawn to the chest as the body rears, both thrown forward as it lunges; held, then back",
                    "keys": {1: REST, 2: _with(_push(24, 35, 80), {"root": (0, 0, 0, -0.10)}),
                             3: _with(_push(-34, 95, 5), {"root": (0, 0, 0, 0.22)}),
                             4: _with(_push(-30, 92, 5), {"root": (0, 0, 0, 0.20)}),
                             5: _with(_push(-12, 50, 20), {"root": (0, 0, 0, 0.06)}),
                             6: _push(6, 10, 10), 8: REST, 10: REST}}}

_NECKS = [f"neck{n}" for n in (1, 2, 3)]
HYDRA = {"roar": {"kind": "spell", "impact": 5,
                  "note": "roar: the three necks rear up and fan out, heads high, then settle",
                  "keys": {1: REST,
                           5: {**{f"{n}.1": (35, side, 0) for n, side in zip(_NECKS, (25, 0, -25))},
                               **{f"{n}.2": (20, 0, 0) for n in _NECKS}, **{f"{n}.3": (-15, 0, 0) for n in _NECKS}},
                           8: {**{f"{n}.1": (35, side, 0) for n, side in zip(_NECKS, (25, 0, -25))},
                               **{f"{n}.2": (20, 0, 0) for n in _NECKS}, **{f"{n}.3": (-15, 0, 0) for n in _NECKS}},
                           10: REST}}}
_COILED = (28, 10, -20)         # a hydra neck's three bones: drawn back in an S, the head tucked


def _volley(note, struck):
    """A hydra's necks strike in turn, one drawing apart: all coil back, then each is thrown forward
    along the ground to `struck` (its three bones: pitch, or (pitch, side, twist, fwd, stretch along
    the bone)) and HELD for three drawings while the next ones land; the body surges a little with
    each and stays over its place."""
    def necks(surge, *states):
        pose = {f"{n}.{k + 1}": (turn if isinstance(turn, tuple) else (turn, 0, 0))
                for n, state in zip(_NECKS, states) for k, turn in enumerate(state)}
        return {**pose, "root": (0, 0, 0, surge)}
    rest, out = (0, 0, 0), struck
    return {"kind": "attack", "impact": 3, "note": note,
            "keys": {1: REST, 2: necks(-0.10, _COILED, _COILED, _COILED), 3: necks(0.16, out, _COILED, _COILED),
                     4: necks(0.22, out, out, _COILED), 5: necks(0.28, out, out, out), 6: necks(0.22, rest, out, out),
                     7: necks(0.14, rest, rest, out), 9: REST, 10: REST}}


HYDRA["spit_volley"] = _volley("spit volley: each neck in turn coils back, is thrown out level along the ground and spits; held",
                               ((-58, 0, 0, 0, 0.08), (-4, 0, 0, 0, 0.08), (22, 0, 0, 0, 0.04)))
HYDRA["bite_volley"] = _volley("bites in turn: each neck coils back and strikes out along the ground, head down; held",
                               ((-64, 0, 0, 0, 0.08), (-10, 0, 0, 0, 0.08), (-8, 0, 0, 0, 0.04)))
SLED["rear"] = {"kind": "spell", "impact": 5, "note": "rears: the front lifts and holds, then drops back",
                "keys": {1: REST, 5: {"spine.4": (25, 0, 0), "spine.3": (10, 0, 0), "head": (-15, 0, 0)},
                         8: {"spine.4": (25, 0, 0), "spine.3": (10, 0, 0), "head": (-15, 0, 0)}, 10: REST}}

MOTIONS = {"biped": BIPED, "quadruped": QUADRUPED, "spider": SPIDER, "spider_high": SPIDER, "vehicle": VEHICLE, "tracked": TRACKED,
           "aircraft": AIRCRAFT, "crew": CREW, "pod": POD, "crawler": CRAWLER, "sled": SLED, "hydra": HYDRA,
           "wyrm": WYRM, "ray": RAY, "walker": WALKER, "shard": SHARD, "wraith": WRAITH}

# ---------------------------------------------------------------- from reference animations
# (model, clip, map, kind, note): retargeted by rig_retarget from artifacts/anim-ref/<model>
# KayKit Character Animations 1.1 (CC0, Rig_Medium; the same rig as the KayKit characters),
# captured per pack file: kk_melee, kk_ranged, kk_general, kk_move, kk_sim, kk_tools.
_ML, _RG = "Melee_", "Ranged_"
_KK = {  # name: (capture, clip, kind, note[, impact frame when the fastest move is not the hit])
    "chop": ("kk_melee", _ML + "1H_Attack_Chop", "attack", "one-hand chop"),
    "jump_chop": ("kk_melee", _ML + "1H_Attack_Jump_Chop", "attack", "leaping one-hand chop"),
    "slice_diagonal": ("kk_melee", _ML + "1H_Attack_Slice_Diagonal", "attack", "one-hand diagonal slice"),
    "slice_horizontal": ("kk_melee", _ML + "1H_Attack_Slice_Horizontal", "attack", "one-hand horizontal slice"),
    "stab": ("kk_melee", _ML + "1H_Attack_Stab", "attack", "one-hand stab / short spear"),
    "chop_2h": ("kk_melee", _ML + "2H_Attack_Chop", "attack", "two-hand overhead chop"),
    "slice_2h": ("kk_melee", _ML + "2H_Attack_Slice", "attack", "two-hand slice"),
    "spin_2h": ("kk_melee", _ML + "2H_Attack_Spin", "attack", "two-hand spin"),
    "stab_2h": ("kk_melee", _ML + "2H_Attack_Stab", "attack", "two-hand thrust: spear, lance, pike"),
    "dual_chop": ("kk_melee", _ML + "Dualwield_Attack_Chop", "attack", "two weapons chop"),
    "dual_slice": ("kk_melee", _ML + "Dualwield_Attack_Slice", "attack", "two weapons slice"),
    "dual_stab": ("kk_melee", _ML + "Dualwield_Attack_Stab", "attack", "two weapons stab"),
    "punch": ("kk_melee", _ML + "Unarmed_Attack_Punch_A", "attack", "punch / claw"),
    "kick": ("kk_melee", _ML + "Unarmed_Attack_Kick", "attack", "kick"),
    "shield_bash": ("kk_melee", _ML + "Block_Attack", "attack", "shield bash"),
    "bow": ("kk_ranged", _RG + "Bow_Draw+" + _RG + "Bow_Release", "attack", "bow: draw to the cheek, release", 7),
    "bow_up": ("kk_ranged", _RG + "Bow_Draw_Up+" + _RG + "Bow_Release_Up", "attack", "bow shot upward (at flyers)", 7),
    "shoot_1h": ("kk_ranged", _RG + "1H_Shoot", "attack", "one-hand shot: pistol, wand"),
    "burst_1h": ("kk_ranged", _RG + "1H_Shooting", "attack", "one-hand rapid fire"),
    "shoot_2h": ("kk_ranged", _RG + "2H_Shoot", "attack", "two-hand shot: rifle, crossbow"),
    "burst_2h": ("kk_ranged", _RG + "2H_Shooting", "attack", "two-hand rapid fire"),
    "throw": ("kk_general", "Throw", "attack", "overarm throw: axe, spear, grenade"),
    "fist_slam": ("kk_melee", _ML + "1H_Attack_Chop", "attack", "one fist hammers down from overhead"),
    "big_arm_slam": ("kk_melee", _ML + "1H_Attack_Chop", "attack", "the big arm lifts and drops like a log"),
    "big_arm_swipe": ("kk_melee", _ML + "1H_Attack_Slice_Horizontal", "attack", "the big arm scythes across"),
    "claw_rake": ("kk_melee", _ML + "1H_Attack_Slice_Diagonal", "attack", "one claw rakes down and across"),
    "reverse_slash": ("kk_melee", _ML + "1H_Attack_Slice_Horizontal", "attack", "reverse grip: rising backhand rip"),
    "fan_gust": ("kk_melee", _ML + "1H_Attack_Slice_Horizontal", "attack", "fan: flat backhand snap outward"),
    "staff_point": ("kk_ranged", _RG + "Magic_Shoot", "attack", "staff head dips back and jabs at the target"),
    "flail_sling": ("kk_general", "Throw", "attack", "chained weight: one circle overhead, released forward"),
    "hipfire_sweep": ("kk_ranged", _RG + "2H_Shooting", "attack", "gun or nozzle at the hip, fanned while firing"),
    "tool_chop": ("kk_tools", "Chop", "attack", "builder: axe"),
    "tool_hammer": ("kk_tools", "Hammer", "attack", "builder: hammer"),
    "tool_pickaxe": ("kk_tools", "Pickaxe", "attack", "builder: pickaxe"),
    "tool_saw": ("kk_tools", "Saw", "attack", "builder: saw"),
    "cast_raise": ("kk_ranged", _RG + "Magic_Raise", "spell", "spell: raise"),
    "cast_shoot": ("kk_ranged", _RG + "Magic_Shoot", "spell", "spell: shoot a bolt"),
    "cast_channel": ("kk_ranged", _RG + "Magic_Spellcasting", "spell", "spell: channel"),
    "cast_long": ("kk_ranged", _RG + "Magic_Spellcasting_Long", "spell", "spell: long channel"),
    "summon": ("kk_ranged", _RG + "Magic_Summon", "spell", "spell: summon from the ground"),
    "cheer": ("kk_sim", "Cheering", "spell", "war cry / cheer"),
    "use_item": ("kk_general", "Use_Item", "spell", "uses an item (potion, horn)"),
    "idle": ("kk_general", "Idle_A", "loop", "idle"),
    "idle_b": ("kk_general", "Idle_B", "loop", "idle, alert"),
    "walk": ("kk_move", "Walking_A", "loop", "walk"),
    "walk_b": ("kk_move", "Walking_B", "loop", "walk, heavy"),
    "run": ("kk_move", "Running_A", "loop", "run"),
    "death_a": ("kk_general", "Death_A", "death", "death A"),
    "death_b": ("kk_general", "Death_B", "death", "death B"),
}


def kk(name, map_name):
    """A KayKit motion as a layer on `map_name`."""
    capture, clip, *_ = _KK[name]
    return (capture, clip, map_name)


A_ = "AnimalArmature|"
_MOUNT = "e006"             # Quaternius animal (CC0): walk, gallop, kick, headbutt
_RIDER = [                  # (name, mount clip, rider KayKit motion, kind, note)
    ("idle", "Idle", "idle", "loop", "standing, rider sits"),
    ("walk", "Walk", "idle", "loop", "walk, rider sits"),
    ("gallop", "Gallop", "idle", "loop", "gallop, rider sits"),
    ("chop", "Idle", "chop", "attack", "rider: one-hand chop"),
    ("slice", "Idle", "slice_diagonal", "attack", "rider: diagonal slice"),
    ("lance", "Idle", "stab_2h", "attack", "rider: lance thrust"),
    ("slice_2h", "Idle", "slice_2h", "attack", "rider: two-hand slice"),
    ("charge_chop", "Gallop", "chop", "attack", "charge: gallop and chop"),
    ("charge_lance", "Gallop", "stab_2h", "attack", "charge: gallop, lance couched"),
    ("bow", "Idle", "bow", "attack", "rider: bow"),
    ("shoot", "Idle", "shoot_2h", "attack", "rider: rifle / crossbow"),
    ("throw", "Idle", "throw", "attack", "rider: throws"),
    ("cast", "Idle", "cast_raise", "spell", "rider: spell, raise"),
    ("cheer", "Idle", "cheer", "spell", "rider: war cry"),
    ("mount_kick", "Attack_Kick", "idle", "attack", "the mount kicks"),
    ("death", "Death", "idle", "death", "the mount falls"),
]
_GAITS = ("walk", "walk_b", "run")     # KayKit gaits: their arms are replaced by a hanging swing
_STANCES = ("idle", "idle_b")          # KayKit idles: arms drawn in to the stance the gaits swing from


def _biped_map(name):
    return "kaykit_biped_walk" if name in _GAITS else "kaykit_biped_idle" if name in _STANCES else "kaykit_biped"


REF_MOTIONS = {
    "biped": {name: (kind, f"{note} (KayKit, CC0)", [kk(name, _biped_map(name))], *hit)
              for name, (_, _, kind, note, *hit) in _KK.items()},
    "quadruped": {
        **{name: (kind, f"{note} (Quaternius animal, CC0)", [(_MOUNT, A_ + clip, "quaternius_animal")])
           for name, clip, kind, note in (("idle", "Idle", "loop", "idle"), ("walk", "Walk", "loop", "walk"),
                                          ("gallop", "Gallop", "loop", "gallop"),
                                          ("kick", "Attack_Kick", "attack", "hind kick"),
                                          ("headbutt", "Attack_Headbutt", "attack", "headbutt"),
                                          ("jump", "Gallop_Jump", "attack", "leap"),
                                          ("death", "Death", "death", "death"))},
        "claw_chop": ("attack", "ghoul claws: both forelegs chop like arms (animal idle + KayKit dual-wield chop)",
                      [(_MOUNT, A_ + "Idle", "quaternius_animal"),
                       kk("dual_chop", "kaykit_forelegs")]),
    },
    "mounted": {name: (kind, f"{note} (Quaternius animal + KayKit rider, CC0)",
                       [(_MOUNT, A_ + mount, "quaternius_animal"), kk(rider, "kaykit_rider")])
                for name, mount, rider, kind, note in _RIDER},
    "spider": {name: (kind, f"{note} (Quaternius, CC0)",
                      [("n00U", f"SpiderArmature|Spider_{clip}", "quaternius_spider")])
               for name, clip, kind, note in (("idle", "Idle", "loop", "idle"), ("walk", "Walk", "loop", "walk"),
                                              ("bite", "Attack", "attack", "attack: front legs up, strike down"),
                                              ("jump", "Jump", "attack", "jump / pounce"),
                                              ("death", "Death", "death", "death"))},
}
_DR = "DragonArmature|Dragon_"
_SN = "SnakeArmature|Snake_"
_RIDER_ACTS = [("chop", "chop", "attack", "rider: one-hand chop"),
               ("slice", "slice_diagonal", "attack", "rider: diagonal slice"),
               ("lance", "stab_2h", "attack", "rider: lance thrust"),
               ("bow", "bow", "attack", "rider: bow"),
               ("shoot", "shoot_2h", "attack", "rider: rifle / crossbow"),
               ("throw", "throw", "attack", "rider: throws (hammer, spear)"),
               ("cast", "cast_raise", "spell", "rider: spell, raise")]
_CREDIT = {**dict.fromkeys(("kk_melee", "kk_ranged", "kk_general", "kk_move", "kk_sim", "kk_tools"), "KayKit"),
           "e006": "Quaternius animal", "h009": "Quaternius dragon",
           "o009": "clintbellanger wyvern, CC-BY-SA-4.0",
           "n00H": "Quaternius snake", "n01P": "Quaternius apatosaurus", "cr_rat": "Quaternius rat",
           "n00U": "Quaternius spider", "h097": "Quaternius robot", "n01N": "TheGameAssets spider, CC-BY-4.0"}


def _entry(kind, note, *layers):
    models = dict.fromkeys(_CREDIT.get(layer[0], layer[0]) for layer in layers)
    return (kind, f"{note} ({' + '.join(models)})", list(layers))


_NEW_ACTS = ("fist_slam", "big_arm_slam", "big_arm_swipe", "claw_rake", "reverse_slash", "fan_gust", "staff_point",
             "flail_sling", "hipfire_sweep", "shield_bash")


def _upper_body(map_name, base):
    """KayKit actions on an upper body (naga, centaur, wraith) over `base` layers per slot."""
    acts = _NEW_ACTS + ("chop", "slice_diagonal", "slice_horizontal", "stab", "stab_2h", "slice_2h", "chop_2h", "spin_2h",
            "dual_chop", "dual_slice", "dual_stab", "punch", "kick", "bow", "shoot_1h", "burst_1h", "shoot_2h",
            "burst_2h", "throw", "cast_raise", "cast_shoot", "cast_channel", "cast_long", "summon", "cheer")
    out = {name: _entry(_KK[name][2], _KK[name][3], *base["still"], kk(name, map_name)) for name in acts}
    out["idle"] = _entry("loop", "idle", *base["idle"], kk("idle", map_name))
    out["walk"] = _entry("loop", "move", *base["walk"], kk("walk", map_name))
    out["death"] = _entry("death", "death", *base["death"], kk("death_a", map_name))
    return out


def _flyer_rider(mount, rider_still, death):
    out = {"fly": _entry("loop", "fly, rider sits", mount["fly"], kk("idle", "kaykit_rider")),
           "death": _entry("death", "the mount falls", death, kk("idle", "kaykit_rider"))}
    for name, motion, kind, note in _RIDER_ACTS:
        out[name] = _entry(kind, note, rider_still, kk(motion, "kaykit_rider"))
    return out


_BIRD_FLY = ("h009", _DR + "Flying", "dragon_bird")
_BIRD = {"hover": _entry("loop", "hover", _BIRD_FLY), "fly": _entry("loop", "fly", _BIRD_FLY),
         "bite": _entry("attack", "peck: the neck rears, the head darts forward and down (LUNGES)", _BIRD_FLY),
         "breath": _entry("attack", "breath / roar", _BIRD_FLY, ("h009", _DR + "Attack2", "dragon_neck")),
         "death": _entry("death", "falls", ("h009", _DR + "Death", "dragon_bird"))}
_WYVERN_MOVES = {"hover": _entry("loop", "hover", ("o009", "Hover", "wyvern")),
                 "fly": _entry("loop", "fly", ("o009", "Fly", "wyvern")),
                 "sting": _entry("attack", "tail sting", ("o009", "Sting", "wyvern")),
                 "breath": _entry("attack", "breath", ("o009", "Breathe", "wyvern")),
                 "death": _entry("death", "falls", ("o009", "Die", "wyvern"))}
_WYVERN = {"fly": ("o009", "Fly", "wyvern"), "hover": ("o009", "Hover", "wyvern")}
_SNAKE_BASE = {"still": [("n00H", _SN + "Idle", "snake_tail")], "idle": [("n00H", _SN + "Idle", "snake_tail")],
               "walk": [("n00H", _SN + "Walk", "snake_tail")], "death": [("n00H", _SN + "Idle", "snake_tail")]}
_HORSE_BASE = {slot: [(_MOUNT, A_ + clip, "quaternius_animal")]
               for slot, clip in (("still", "Idle"), ("idle", "Idle"), ("walk", "Walk"), ("death", "Death"))}
_GHOST_BASE = {"still": [], "idle": [], "walk": [], "death": []}


_WINGS = ("h009", _DR + "Flying", "dragon_wings")
_DRAKE_STILL = [(_MOUNT, A_ + "Idle", "animal_drake"), _WINGS]
_DRAKE = {"fly": _entry("loop", "hover, wings beating", *_DRAKE_STILL),
          "glide": _entry("loop", "fly forward", (_MOUNT, A_ + "Walk", "animal_drake"), _WINGS),
          "bite": _entry("attack", "bite: the neck rears, the head darts out and snaps shut (LUNGES)", *_DRAKE_STILL),
          "breath": _entry("attack", "breath: the neck rears, the head thrusts forward and down, jaws held open "
                           "(fire, frost, acid; LUNGES)", *_DRAKE_STILL),
          "spit": _entry("attack", "spit: the body rears under wings swept back, then head, body and wings are thrown "
                         "forward, jaws held open (a small body under tall wings; LUNGES)", *_DRAKE_STILL),
          "headbutt": _entry("attack", "head ram", (_MOUNT, A_ + "Attack_Headbutt", "animal_drake"), _WINGS),
          "claw": _entry("attack", "foreleg claw", (_MOUNT, A_ + "Idle", "animal_drake"), _WINGS,
                         kk("dual_chop", "kaykit_forelegs")),
          "death": _entry("death", "falls", (_MOUNT, A_ + "Death", "animal_drake"),
                          ("h009", _DR + "Death", "dragon_wings"))}
_CREDIT["n017"] = "Quaternius wolf"


def _necks(clip):
    return [("n01P", f"Armature|Apatosaurus_{clip}", f"apatosaurus_neck{n}", 8 * (n - 1)) for n in (1, 2, 3)]


def _snake_body(map_name, extra=()):
    return {"idle": _entry("loop", "idle, swaying", ("n00H", _SN + "Idle", map_name), *extra),
            "walk": _entry("loop", "slither", ("n00H", _SN + "Walk", map_name), *extra),
            "bite": _entry("attack", "strike", ("n00H", _SN + "Attack", map_name), *extra),
            "lunge": _entry("attack", "leaping lunge", ("n00H", _SN + "Jump", map_name), *extra)}


REF_MOTIONS.update({
    "drake": _DRAKE,
    "mounted_flyer": {**{name: (kind, note.replace(")", " + KayKit rider)"),
                                layers + [kk("idle", "kaykit_rider")])
                         for name, (kind, note, layers) in _DRAKE.items()},
                      **{name: _entry(kind, note, *_DRAKE_STILL, kk(motion, "kaykit_rider"))
                         for name, motion, kind, note in _RIDER_ACTS}},
    "bird": {**_BIRD, **{f"wyvern_{k}": v for k, v in _WYVERN_MOVES.items()}},
    "bird_rider": {**_flyer_rider({"fly": _BIRD_FLY}, _BIRD_FLY, ("h009", _DR + "Death", "dragon_bird")),
                   "hover": _entry("loop", "hover, rider sits", _BIRD_FLY, kk("idle", "kaykit_rider")),
                   "mount_bite": _entry("attack", "the mount bites", _BIRD_FLY, ("h009", _DR + "Attack", "dragon_neck"),
                                        kk("idle", "kaykit_rider")),
                   "wyvern_fly": _entry("loop", "fly, rider sits", _WYVERN["fly"], kk("idle", "kaykit_rider")),
                   "wyvern_sting": _entry("attack", "the mount stings", ("o009", "Sting", "wyvern"),
                                          kk("idle", "kaykit_rider"))},
    "harpy": {name: _entry(_KK[name][2], _KK[name][3], kk(name, _biped_map(name)),
                           ("h009", _DR + "Flying", "dragon_wings"))
              for name in _NEW_ACTS + ("idle", "walk", "chop", "slice_diagonal", "slice_horizontal", "stab", "stab_2h", "chop_2h",
                           "slice_2h", "spin_2h", "dual_chop", "dual_slice", "dual_stab", "punch", "kick", "bow",
                           "bow_up", "shoot_1h", "shoot_2h", "throw", "cast_raise", "cast_shoot", "cast_long", "summon",
                           "cheer", "death_a")},
    "ray": {"swim": _entry("loop", "glide", ("h009", _DR + "Flying", "dragon_ray")),
            "bite": _entry("attack", "strike", ("h009", _DR + "Attack", "dragon_ray")),
            "lash": _entry("attack", "tail lash", ("h009", _DR + "Attack2", "dragon_ray")),
            "death": _entry("death", "sinks", ("h009", _DR + "Death", "dragon_ray"))},
    "shard": {"fly": _entry("loop", "hover", ("h009", _DR + "Flying", "dragon_shard")),
              "strike": _entry("attack", "strike", ("h009", _DR + "Attack", "dragon_shard")),
              "pulse": _entry("spell", "pulse", ("h009", _DR + "Attack2", "dragon_shard")),
              "death": _entry("death", "falls", ("h009", _DR + "Death", "dragon_shard"))},
    "serpent": _snake_body("snake"),
    "sled": _snake_body("snake_sled"),
    "wyrm": _snake_body("snake_wyrm", [("h009", _DR + "Flying", "dragon_wings")]),
    "hydra": {"idle": _entry("loop", "idle, necks out of step", ("n00H", _SN + "Idle", "snake_sled"), *_necks("Idle")),
              "walk": _entry("loop", "walk", ("n00H", _SN + "Walk", "snake_sled"), *_necks("Walk")),
              "bite": _entry("attack", "three heads strike in turn", ("n00H", _SN + "Idle", "snake_sled"),
                             *_necks("Attack"))},
    "naga": _upper_body("kaykit_upper", _SNAKE_BASE),
    "centaur": {**_upper_body("kaykit_centaur", _HORSE_BASE),
                "gallop": _entry("loop", "gallop", (_MOUNT, A_ + "Gallop", "quaternius_animal"),
                                 kk("idle", "kaykit_centaur")),
                "kick": _entry("attack", "hind kick", (_MOUNT, A_ + "Attack_Kick", "quaternius_animal"),
                               kk("idle", "kaykit_centaur"))},
    "wraith": _upper_body("kaykit_wraith", _GHOST_BASE),
    "crawler": {name: _entry(kind, note, ("cr_rat", f"RatArmature|Rat_{clip}", "rat"))
                for name, clip, kind, note in (("idle", "Idle", "loop", "idle"), ("walk", "Walk", "loop", "scurry"),
                                               ("bite", "Attack", "attack", "bite"), ("jump", "Jump", "attack", "leap"),
                                               ("death", "Death", "death", "death"))},
    "crustacean": {name: _entry(kind, note, ("n00U", f"SpiderArmature|Spider_{clip}", "spider_crab"))
                   for name, clip, kind, note in (("idle", "Idle", "loop", "idle"), ("walk", "Walk", "loop", "walk"),
                                                  ("pinch", "Attack", "attack", "claws up, snap down"),
                                                  ("jump", "Jump", "attack", "leap"),
                                                  ("death", "Death", "death", "death"))},
    "walker": {name: _entry(kind, note, ("h097", f"RobotArmature|{clip}", "robot_walker"))
               for name, clip, kind, note in (("idle", "Idle", "loop", "idle"), ("walk", "Walk", "loop", "stomp"),
                                              ("kick", "Kick", "attack", "kick"),
                                              ("shoot_big", "Shoot_Big", "attack", "cannon recoil"),
                                              ("shoot_small", "Shoot_Small", "attack", "gun burst"),
                                              ("death", "Death", "death", "collapse"))},
})
REF_MOTIONS["mounted_flyer"]["mount_cast"] = _entry(     # "cast" is the spell slot's: there the mount only hovers
    "attack", "rider raises the spell as the mount snaps its head out at the target (MOUNT_LUNGES)",
    *_DRAKE_STILL, kk("cast_raise", "kaykit_rider"))
REF_MOTIONS["spider"].update({
    "rear_strike": ("attack", "rears up on the back legs and hammers down with the front pair "
                    "(TheGameAssets spider, CC-BY-4.0)", [("n01N", "Spider_Attack_1", "gameassets_spider")]),
    "lunge": ("attack", "lunges and strikes with the front legs (TheGameAssets spider, CC-BY-4.0)",
              [("n01N", "Spider_Attack_2", "gameassets_spider")]),
})
_SPIDER_BITE_NOTE = ("bite: rocks back with the front pair cocked, then the body lunges over planted legs, front claws "
                     "and fangs thrust out ahead; held (LUNGES; Quaternius idle, CC0)")
REF_MOTIONS["spider"]["bite"] = ("attack", _SPIDER_BITE_NOTE, [("n00U", "SpiderArmature|Spider_Idle", "quaternius_spider")])
REF_MOTIONS["spider_high"] = REF_MOTIONS["spider"]     # same legs by name; the foot IK bends the arched knee
_STANCE = [(_MOUNT, A_ + "Idle", "quaternius_animal")]      # the idle a keyed lunge (LUNGES) is struck from
REF_MOTIONS["quadruped"].update({
    "bite": ("attack", "darting bite: the head and neck shoot level at the target, the chest behind them, and snap back (LUNGES)", _STANCE),
    "maul": ("attack", "mauling bite: rocks back, the chest drives over planted feet, the head snaps down (LUNGES)", _STANCE),
    "gore": ("attack", "gore: the head drops, the body drives horn or tusks in, the head rips upward (LUNGES)", _STANCE),
    "paw_slam": ("attack", "rocks back on planted hind legs, forepaws cocked, and throws both out ahead along the ground (LUNGES)", _STANCE),
    "claw_punch": ("attack", "paw hook: one forepaw cocked out to its side sweeps forward and across the front (LUNGES)", _STANCE),
    "hawk": ("attack", "spit: the front rears and the head draws back, then both snap forward and down (LUNGES)", _STANCE),
    "swipe": ("attack", "tusk swipe: head cocked out to one side, then head and shoulders swept across the target (LUNGES)", _STANCE),
})


FAMILIES = sorted(f for f in RF.FAMILIES if f not in RF.STATIC)


def impact(family, poses):
    """1-based index of the fastest moment of the limb ends (tails of leaf bones)."""
    kids = set(RF.parents(family).values())
    flaps = ("wing", "tail", "tendril", "foot", "shin", "thigh")  # beat/wave all the time, or stand
    leaves = [b for b in RF.bones(family) if b not in kids and b != "root"]
    ends = [b for b in leaves if not b.startswith(flaps)] or leaves     # a ray is all wing and tail
    tips = [P.joints(family, p) for p in poses]
    speed = [max(math.dist(tips[i][b][1], tips[i - 1][b][1]) for b in ends) for i in range(1, len(tips))]
    return speed.index(max(speed)) + 2


def _complete(poses):
    """Every pose keys every bone the clip moves anywhere (rest = zeros): an empty rest key
    would let Blender hold the previous value and end the clip off rest."""
    zero = (0.0, 0.0, 0.0, 0.0, 0.0)
    bones = sorted({bone for pose in (poses.values() if isinstance(poses, dict) else poses) for bone in pose})

    def fill(pose):
        return {bone: P.pad(pose.get(bone, zero)) for bone in bones}
    return {k: fill(v) for k, v in poses.items()} if isinstance(poses, dict) else [fill(v) for v in poses]


_KK_NAMES = {}
for _name, (_capture, _clip, *_) in _KK.items():
    _KK_NAMES.setdefault((_capture, _clip), _name)        # the first motion on a clip: a rider's "slice", "lance"
_BEAST_LEGS = ("leg", "thigh.", "shin.", "foot.")
_BEAST_TORSO = ("spine.2", "spine.1", "body", "pelvis")


def _strike(layers, name):
    """(strike, map) of the layer that is a KayKit strike on a pair of arms (rig_strike), or None.
    The strike is the motion's own name where rig_strike has it, else the first motion made on
    that clip (a rider's "lance" is stab_2h)."""
    for capture, clip, map_name, *_ in layers:
        found = name if name in RS.STRIKES and _KK.get(name, ())[:2] == (capture, clip) else _KK_NAMES.get((capture, clip))
        if found in RS.STRIKES and _limbs(RT.MAPS[map_name]["bones"]):
            return found, map_name
    return None


def _limbs(bones):
    """{side: (upper, fore)}: our bones on the reference's arms (a ghoul's forelegs too), or None."""
    out = {}
    for s in "lr":
        upper = [b for b, pair in bones.items() if pair == (f"upperarm.{s}", f"lowerarm.{s}")]
        fore = [b for b, pair in bones.items() if pair == (f"lowerarm.{s}", f"hand.{s}")]
        if not upper or not fore:
            return None
        out[s.upper()] = (upper[0], fore[0])
    return out


_GUNS = ("shoot_1h", "shoot_2h", "burst_1h", "burst_2h", "hipfire_sweep")     # KayKit holds these in the right hand
_BOWS = ("bow", "bow_up")                                                     # and the bow in the left
_KICK = {0: 0.0, 2: 0.0, 3: 1.0, 5: 0.6, 9: 0.0}       # samples from the shot: share of the recoil
_LOOSE = {0: 0.0, 2: 0.7, 4: 1.0, 5: -0.8, 7: -0.3, 9: 0.0}       # an archer leans back on the draw, snaps forward loosing
_PAN = {0: 0.0, 1: 1.0, 3: -1.0, 5: 1.0, 7: -1.0, 9: 1.0, 11: -1.0, 13: 0.3, 17: 0.0}    # a sweep from the hip (rig_strike._SWEEP's beats)


def _swayed(family, poses, torso, name, armed):
    """What the torso adds to a shot the arms alone do not show: an archer leans back on the draw and
    snaps forward on the release; a sweep from the hip turns the torso with the barrel, all the way
    for a gun the hands do not carry (it is skinned to the body: the torso's turn is its only pan)."""
    if name in _BOWS:
        table, axis, gain = _LOOSE, 0, 9.0 * _probe(family, torso, 0)
    elif name == "hipfire_sweep":           # in the hands: the shoulders follow the barrel the arms pan
        table, axis, gain = _PAN, 1, 7.0 if armed else 30.0
    else:
        return poses
    out = []
    for i, pose in enumerate(poses):
        turn = list(P.pad(pose.get(torso, ())))
        turn[axis] += gain * P.pad(P.sample({at: {"k": (share, 0, 0, 0)} for at, share in table.items()}, i)["k"])[0]
        out.append({**pose, torso: tuple(turn)})
    return out


def _held(family, poses, name, layers, grip):
    """A shot's poses for the hand that holds the gun or the bow (mirrored when it is not KayKit's),
    a gun's with a recoil that reads: the torso is thrown back and the body shoved, then settles."""
    found = next(((RT.MAPS[m], _limbs(RT.MAPS[m]["bones"])) for c, cl, m, *_ in layers if (c, cl) == _KK.get(name, ())[:2]), None)
    if name not in _GUNS + _BOWS or found is None or found[1] is None:
        return poses
    layer, limbs = found
    main = RS.hands({"hands": "one"}, dict(grip or ()))[1] if grip and any(b for _, b in grip) else None
    if name in _BOWS and main == "R" and all(b.endswith((".L", ".R")) for limb in limbs.values() for b in limb):
        poses = [RS.mirror(pose, layer["bones"]) for pose in poses]
    torso = next((b for b, pair in layer["bones"].items() if pair == ("spine", "head")), None)
    poses = _swayed(family, poses, torso, name, main is not None) if torso else poses
    if name in _BOWS or torso is None:
        return poses
    carried = layer.get("still_root") and family not in RF.HOVER      # a rider on legs: the mount stands; in the air it is shoved
    back, shove = 14.0 * _probe(family, torso, 0), 0.0 if carried else -0.14 * RF.top(family)
    out = []
    for i, pose in enumerate(poses):
        k = P.pad(P.sample({at: {"k": (share, 0, 0, 0)} for at, share in _KICK.items()}, i)["k"])[0]
        rx, *rest = P.pad(pose.get(torso, ()))
        lift = P.pad(pose.get("root", ()))
        out.append({**pose, torso: (rx + back * k, *rest), "root": (*lift[:3], lift[3] + shove * k, lift[4])})
    return out


def _spun(poses, hit):
    """A spin: the whole body turns once on the spot while the weapon is out (the reference's turn
    is lost by a retarget that only aims bones)."""
    out = []
    for i, pose in enumerate(poses):
        t = min(max((i - hit + 2) / 9.0, 0.0), 1.0)
        rx, ry, rz, *rest = P.pad(pose.get("root", ()))
        out.append({**pose, "root": (rx, ry + 360.0 * t * t * (3 - 2 * t), rz, *rest)})
    return out


def _struck(family, poses, name, map_name, grip, soft=1.0):
    """The reference's poses with the body's step and lean scaled down and the strike's arms keyed
    on the unit's weapons (rig_strike): the motion mirrored for a weapon in the left hand, the arms
    from and back to the idle stance. Returns (poses, contact sample, samples cut from the start)."""
    spec, layer = RS.STRIKES[name], RT.MAPS[map_name]
    bones, grip = layer["bones"], dict(grip or ())
    limbs = _limbs(bones)
    legs = [b for b in bones if b.startswith(("thigh.", "shin.", "foot."))] + ["root"]
    torso = next((b for b, pair in bones.items() if pair == ("spine", "head")), None)
    poses = RS.calm(family, poses, [] if layer.get("still_root") else legs, torso, spec.get("root", RS.ROOT_MAX))
    sided = all(b.endswith((".L", ".R")) for limb in limbs.values() for b in limb)
    if sided and spec["hands"] in ("one", "two", "off", "free") and RS.left_handed(spec, grip):
        poses = [RS.mirror(pose, bones) for pose in poses]
    idle = motion(family, DEFAULTS[family]["idle"])["clip"][0]
    out, hit = RS.arms(family, poses, spec, grip, idle, limbs, soft)
    if name == "spin_2h" and not layer.get("still_root"):
        out = _spun(out, hit)
    if name == "jump_chop" and not layer.get("still_root"):
        out = _leapt(family, out, hit)
    if (map_name == "kaykit_rider" and family in RF.HOVER) or family == "harpy":
        out = _glided(out)
    return out, hit, len(poses) - len(out)


RIDER_WINGS = 0.3       # share of its wing beat a flying mount keeps while its rider strikes


def _glided(poses):
    """A flying mount under a striking rider holds its wings near the first pose: at full beat the
    wings are the motion and the rider's weapon, a few pixels long, is lost behind them. A harpy's
    own strike too: its arms are thin under wings three times their size."""
    first = poses[0]
    return [{bone: RS._toward(P.pad(v), P.pad(first.get(bone, ())), RIDER_WINGS) if bone.startswith("wing") else v
             for bone, v in pose.items()} for pose in poses]


def _stood(family, poses):
    """A beast's strike on the spot (a bite): its lunge and lean scaled down as a biped's are
    (rig_strike.calm), legs with it. Legs on foot IK are held by _from_ref instead."""
    names = RF.bones(family)
    torso = next((b for b in _BEAST_TORSO if b in names), None)
    if torso is None:
        return poses
    return RS.calm(family, poses, [b for b in names if b.startswith(_BEAST_LEGS)] + ["root"], torso, BEAST_REACH)


BEAST_REACH = 0.3       # body heights a beast's chest may drive forward in a bite or a butt: its body is the weapon
_SNAP = {-5: 0.0, -3: 45.0, -2: 55.0, 0: -70.0, 2: -65.0, 7: 0.0}      # samples from the bite: head pitch


_DART = {1: 0.0, 3: 1.0, 4: 1.0, 6: -1.0, 8: -1.0, 14: 0.0}     # sample: neck reared (+) or thrust out and down (-)
_DART_TURN = {"neck.1": (22.0, -24.0), "neck.2": (18.0, -20.0), "head": (14.0, -26.0), "jaw": (-30.0, -22.0)}


def _dart(family, poses):
    """A necked beast's bite or breath, keyed in place of the reference's neck (stacking a snap on it
    folds the neck): the neck and head rear back, thrust forward and down with the jaw open and
    hold; the wings only flare (their beat scaled down about the first pose)."""
    first, out = poses[0], []
    for i, pose in enumerate(poses):
        k = P.pad(P.sample({at: {"k": (v, 0, 0, 0)} for at, v in _DART.items()}, i)["k"])[0]
        pose = dict(pose)
        for bone, (back, out_) in _DART_TURN.items():
            if bone in RF.bones(family):
                base = P.pad(first.get(bone, ()))
                pose[bone] = (base[0] + (back if k > 0 else -out_) * k * _probe(family, bone, 0), *base[1:])
        for bone in (b for b in pose if b.startswith("wing")):
            pose[bone] = RS._toward(P.pad(pose[bone]), P.pad(first.get(bone, ())), 0.35)
        out.append(pose)
    return out


# A beast's strike keyed over its idle stance, where the reference's own does not survive our meshes
# (a wolf's lunge folds a bear in two, the dragon's neck at twice its turn pitches a drake flat):
#   "root":  body heights the body is drawn back, driven forward at the hit, and where it is after it
#   "turns": {bone: (wound up, struck[, after])} from the stance (the idle is the look each model was
#            accepted in; its bind pose may carry the head anywhere): readable pitch in degrees, or
#            (pitch, side, twist, fwd, stretch along the bone)
#   "aims":  {bone: (wound up, struck[, after])} world directions (x, forward is -y, up) the bone points
#            in at that beat, None = as the stance has it: a paw hooked across the front, wings swept back
#   "stay":  the legs (name prefixes) whose feet stay where the stance put them, by two-bone IK: the body
#            is the weapon and reaches over them ("feet": the same by turning the upper bone only)
#   "wings": share kept of the wing beat about the stance (wings an aim does not key)
#   "beats": the samples of each beat where the strike is not _BEATS'
# The game camera looks down on the units from 56 degrees (CameraMath.hpp): a strike reads there by how
# far it travels along the ground toward the target and by how long it stays out, hardly by how far a
# head dips or a paw is raised. So every strike is a short pull-back, a reach of about half a body
# length by the contact (sample _LUNGE_HIT, frame CONTACT), the reached pose HELD eight samples (nine
# frames, 0.38 s: three frames of a 640x360 capture, whose frames are 0.13 s apart), and a slower
# return; the clip is 1.1 s, inside the units' cooldowns (ClipPlayer speeds a longer clip up).
_BEATS = {"stance": (0, 21), "wound": (2, 3), "struck": (5,), "after": (13,)}      # samples of a 24-sample clip
_LUNGE_HIT = 5
_LUNGE_FRAMES = 26      # a lunge's clip: the contact on frame CONTACT (_early), held nine frames, home on 24
_DART_BEATS = {"stance": (0, 19), "wound": (2, 3), "struck": (5,), "after": (13,)}     # held as long, back faster
_NECK_OUT = {"neck.1": (14, (-46, 0, 0, 0, 0.05)), "neck.2": (10, (-14, 0, 0, 0, 0.05))}    # reared, then thrown out level
_WINGS_BACK = {bone: (None, d) for bone, d in _swept().items()}
_PAWS_OUT = {f"leg{n}.{part}": tuple((side * d[0], d[1], d[2]) for d in beats)
             for n, side in ((1, 1), (2, -1))
             for part, beats in (("upper", ((0.25, -0.55, 0.60), (0.15, -1.00, -0.25))),
                                 ("lower", ((0.10, -0.90, 0.30), (0.05, -1.00, -0.35))))}
_PAW_HOOK = {"leg1.upper": ((0.90, -0.10, -0.30), (0.25, -0.95, -0.15), (-0.20, -0.95, -0.20)),      # out to its side,
             "leg1.lower": ((0.95, 0.10, -0.10), (-0.35, -0.90, -0.10), (-0.70, -0.65, -0.15))}     # hooked across the front
_SPIDER_BITE = {"root": (-0.14, 0.60, 0.56), "stay": _SPIDER_STAND,
                "turns": {"body": (8, -6), "head": (6, -16)},
                "aims": {bone: (_fore(_FORE_UP)[bone], d) for bone, d in _fore(_FORE_OUT).items()}}
LUNGES = {
    "quadruped": {
        "bite": {"root": (-0.14, 0.52, 0.52), "stay": _FOUR, "beats": _DART_BEATS,
                 "turns": {"spine.2": (8, -4), "head": (18, -8), "jaw": (-34, -30, 0)}},
        "maul": {"root": (-0.12, 0.46, 0.46), "stay": _FOUR,
                 "turns": {"spine.2": (6, -8), "head": (14, -26, -32)}},
        "gore": {"root": (-0.14, 0.50, 0.44), "stay": _FOUR,
                 "turns": {"spine.2": (-8, -8, 8), "head": (-40, -45, 5)}},
        "hawk": {"root": (-0.22, 0.42, 0.36), "stay": _FOUR,
                 "turns": {"root": (16, -8), "spine.2": (16, -10), "head": (30, -22, -20)}},
        # a second strike for a beast that already gores: where the gore drives straight in, this one crosses the front
        # (the body's yaw and the head's own side turn), which is what tells them apart from above
        "swipe": {"root": (-0.06, 0.32, 0.30), "stay": _FOUR,
                  "beats": {"stance": (0, 21), "wound": (2, 3), "struck": (5,), "after": (8, 14)},
                  "turns": {"root": ((0, 0, 20), (0, 0, 2), (0, 0, -22)),
                            "head": ((-8, 30, 0), (-14, 4, 0), (-6, -36, 0))}},
        "paw_slam": {"root": (-0.08, 0.40, 0.40), "stay": _HIND, "aims": _PAWS_OUT,
                     "turns": {"root": (14, -6), "head": (-10, -20)}},
        # the shoulder turns into the hook (the root's yaw), the paw's arm stretched a little past its length
        "claw_punch": {"root": (-0.08, 0.42, 0.42), "stay": ("leg2",) + _HIND, "aims": _PAW_HOOK,
                       "turns": {"root": ((0, 0, 12), (0, 0, -14), (0, 0, -18)), "head": (6, -10),
                                 "leg1.lower": (0, (0, 0, 0, 0, 0.10))}},
    },
    "drake": {
        "breath": {"root": (-0.10, 0.36, 0.32), "wings": 0.2, "aims": _WINGS_BACK,
                   "turns": {**_NECK_OUT, "head": (-6, -14), "jaw": (-6, -40)}},
        "bite": {"root": (-0.08, 0.36, 0.30), "wings": 0.2, "aims": _WINGS_BACK,
                 "turns": {**_NECK_OUT, "head": (0, -10), "jaw": (-34, -30, 0)}},
        # a small body under tall wings: the head alone is a few pixels, so the body rears and dives with it
        "spit": {"root": (-0.14, 0.40, 0.34), "wings": 0.2, "aims": _WINGS_BACK,
                 "turns": {"root": (10, -8), **_NECK_OUT, "head": (-6, -14), "jaw": (-6, -40)}},
    },
    "bird": {
        "bite": {"root": (-0.06, 0.36, 0.30), "wings": 0.2, "aims": _WINGS_BACK,
                 "turns": {"root": (6, -10), "neck.1": (14, -34), "neck.2": (10, -14), "head": (8, -8)}},
    },
    "spider": {"bite": _SPIDER_BITE},
    "spider_high": {"bite": _SPIDER_BITE},
}
LUNGES["mounted_flyer"] = LUNGES["drake"]      # the same body under a rider
# The MOUNT's strike under its rider's, by the rider's motion (_mount_strike): from the game camera a rider's weapon
# is a few pixels, so the mount carries the hit along the ground on the rider's contact: it drives its head in under
# a chop, sweeps head and shoulders across the front under a slice, charges under a lance, and a flying mount is thrown
# back by a shot. "sweep": samples after the contact by which the "after" pose is reached (default: held).
_MOUNT_GORE = {"root": (-0.10, 0.40, 0.36), "stay": _FOUR,
               "turns": {"spine.2": (-6, -6, 4), "head": (-26, -34, 4)}}
_MOUNT_SWIPE = {"root": (-0.06, 0.30, 0.28), "stay": _FOUR, "sweep": 3,
                "turns": {"root": ((0, 0, 20), (0, 0, 2), (0, 0, -24)), "head": ((-6, 28, 0), (-12, 4, 0), (-6, -32, 0))}}
_MOUNT_CHARGE = {"root": (-0.14, 0.50, 0.45), "stay": _FOUR, "turns": {"spine.2": (6, -6), "head": (14, -16)}}
# a flying mount under a gun: it noses in on the aim and the shot throws it back along the ground (a neck snapped out
# and held reads as a hover from above: the rifle is a few pixels), most of the way home four samples later
_MOUNT_RECOIL = {"root": (0.10, -0.60, -0.10), "sweep": 4, "wings": 0.2, "aims": _WINGS_BACK,
                 "turns": {"root": (-4, 10, 0), **_NECK_OUT, "head": (0, -10, 0)}}
MOUNT_LUNGES = {
    "mounted": {"chop": _MOUNT_GORE, "slice": _MOUNT_SWIPE, "lance": _MOUNT_CHARGE},
    "mounted_flyer": {"shoot": _MOUNT_RECOIL, "mount_cast": LUNGES["drake"]["breath"]},
    "bird_rider": {"shoot": LUNGES["bird"]["bite"]},
}
FITTED = {"quadruped": 1.25, "spider": 0.95, "spider_high": 0.95, "hydra": 1.0, "drake": 1.2, "wyrm": 0.9, "ray": 1.2,
          "bird": 1.5, "crawler": 0.65}
"""Families whose strikes are a reach along the ground, with the length in metres of the body their
travel was drawn for (about half of it): anim_refresh measures the unit against it (fit), so a long
beast travels in proportion to its own length and a short-legged one still has its feet solved."""


def _unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def _aimed(family, pose, aims, soft=1.0):
    """`pose` with each bone of `aims` ({bone: world direction or None}) pointed that way, `soft` of
    the way from where the pose has it."""
    aims = {bone: d for bone, d in aims.items() if d is not None and bone in RF.bones(family)}
    if not aims:
        return pose
    now, targets = P.joints(family, pose), {}
    for bone, want in aims.items():
        head, tail = now[bone]
        have = _unit([t - h for h, t in zip(head, tail)])
        targets[bone] = _unit([a + (b - a) * soft for a, b in zip(have, _unit(want))])
    return P.repose(family, pose, targets)


def _knee_side(hip, knee, foot):
    """The direction a leg's knee stands off the line from hip to foot (forward when it is straight)."""
    line = _unit([f - h for h, f in zip(hip, foot)])
    off = [k - h for h, k in zip(hip, knee)]
    along = sum(a * b for a, b in zip(off, line))
    side = [o - along * c for o, c in zip(off, line)]
    return _unit(side) if math.sqrt(sum(c * c for c in side)) > 1e-3 else (0.0, -1.0, 0.0)


def _reached(family, pose, want, uppers):
    """`pose` with each leg of `uppers` bent (two-bone IK) so its foot is where `want` (joints) has it."""
    now, targets = P.joints(family, pose), {}
    for upper in uppers:
        lower = upper.replace(".upper", ".lower")
        (hip, knee), foot = want[upper], want[lower][1]
        at = now[upper][0]
        bent, end = P.two_bone(at, foot, math.dist(hip, knee), math.dist(knee, foot), _knee_side(hip, knee, foot))
        targets[upper] = tuple(b - a for a, b in zip(at, bent))
        targets[lower] = tuple(e - b for b, e in zip(bent, end))
    return P.repose(family, pose, targets)


def _stay(family, pose, stance, legs, stride=1.0):
    """`pose` with the legs of `legs` (name prefixes) reaching for the feet of `stance`: the body moves
    and the feet stay put, the legs stretching behind it (out of reach they straighten and the foot
    drags). `stride` scales the body's travel the legs are solved for: a unit with legs half the
    family's length travels twice as far in leg lengths (anim_refresh.fit). The pose is solved at the
    height plant will give it."""
    uppers = [b for b in RF.bones(family) if b.startswith(tuple(legs)) and b.endswith(".upper")] if legs else []
    if not uppers:
        return pose
    want, floor = P.joints(family, stance), lowest(family, {})
    rx, ry, rz, lift, up = P.pad(pose.get("root", ()))
    base = P.pad(stance.get("root", ()))[3]
    far = {**pose, "root": (rx, ry, rz, base + (lift - base) * stride, up)}
    for _ in range(1 if family in RF.HOVER else 6):
        far = _reached(family, far, want, uppers)
        if family not in RF.HOVER:
            level = {**far, "root": (*far["root"][:4], 0.0)}
            far["root"] = (*far["root"][:4], floor - lowest(family, level) + max(up, 0.0))
    return {**pose, **{b: far[b] for u in uppers for b in (u, u.replace(".upper", ".lower"))}}


def _planted(family, pose, stance, legs):
    """`pose` with the upper bone of each of `legs` (name prefixes) turned until its foot is as far
    forward as in `stance`: the body moves over feet that stay put (plant then sets the height)."""
    want, out = P.joints(family, stance), dict(pose)
    for upper in (b for b in RF.bones(family) if b.startswith(tuple(legs)) and b.endswith(".upper")):
        lower, value = upper.replace(".upper", ".lower"), P.pad(pose.get(upper, ()))
        lo, hi = -70.0, 70.0
        ahead = P.joints(family, {**out, upper: (value[0] + hi, *value[1:])})[lower][1][1] < want[lower][1][1]
        for _ in range(12):
            mid = (lo + hi) / 2
            y = P.joints(family, {**out, upper: (value[0] + mid, *value[1:])})[lower][1][1]
            lo, hi = (lo, mid) if (y < want[lower][1][1]) == ahead else (mid, hi)
        out[upper] = (value[0] + (lo + hi) / 2, *value[1:])
    return out


def _turned(family, bone, base, turn, soft):
    """`base` (a bone's stance) plus a LUNGES turn: readable pitch, or (pitch, side, twist, fwd, stretch)."""
    pitch, side, twist, fwd, up = P.pad(turn if isinstance(turn, tuple) else (turn,))
    signs = _signs(family, bone)
    return tuple(b + a * soft for b, a in zip(base, (pitch * signs[0], twist, side * signs[1], fwd, up)))


def _beat(table, phase):
    """{bone: value at beat `phase`} of a LUNGES table whose rows may stop before the last beat."""
    return {bone: row[min(phase, len(row) - 1)] for bone, row in table.items()}


def _lunge_key(family, stance, spec, phase, soft, stride=1.0):
    """The pose of one beat of a lunge (phase 0 = wound up, 1 = struck, 2 = after) over `stance`."""
    names, pose = RF.bones(family), {}
    for bone, turn in _beat(spec["turns"], phase).items():
        if bone in names:
            pose[bone] = _turned(family, bone, P.pad(stance.get(bone, ())), turn, soft)
    rx, ry, rz, lift, up = P.pad(pose.get("root", stance.get("root", ())))
    pose["root"] = (rx, ry, rz, lift + spec["root"][phase] * RF.top(family) * soft, up)
    pose = _aimed(family, {**stance, **pose}, _beat(spec.get("aims", {}), phase), soft)
    pose = _stay(family, pose, stance, spec.get("stay", ()), stride)
    return _planted(family, pose, stance, spec.get("feet", ()))


def _lunge(family, poses, spec, soft=1.0, stride=1.0):
    """The layers' poses with the strike of `spec` (LUNGES) keyed over their first pose, the stance:
    wound up, struck and held, back to the stance. What the strike does not key (a tail, a rider)
    keeps the layers' motion; the wings keep a share of their beat."""
    stance = {bone: P.pad(v) for bone, v in poses[0].items()}
    beats = {"stance": stance, **{name: _lunge_key(family, stance, spec, phase, soft, stride)
                                  for phase, name in enumerate(("wound", "struck", "after"))}}
    keyed = {b for name in ("wound", "struck", "after") for b, v in beats[name].items() if v != stance.get(b)}
    keys = {at: {b: beats[name][b] for b in keyed} for name, ats in spec.get("beats", _BEATS).items() for at in ats}
    out = []
    for i, pose in enumerate(poses):
        pose = {**pose, **P.sample(keys, i)}
        for bone in (b for b in pose if b.startswith("wing") and b not in keyed):      # a keyed wing is the strike's
            pose[bone] = RS._toward(P.pad(pose[bone]), stance.get(bone, P.pad(())), spec.get("wings", 0.35))
        out.append(pose)
    return out


def _staged(family, keys, m, soft, stride):
    """A hand-keyed motion's key drawings with its "aims" ({drawing: {bone: world direction}}) pointed and
    the feet of its "stay" legs held where they rest (a drawing at rest is left alone)."""
    out = {}
    for frame, pose in keys.items():
        pose = {bone: P.pad(v) for bone, v in pose.items()}
        if pose:
            pose = _aimed(family, pose, m.get("aims", {}).get(frame) or {}, soft)
            if frame not in m.get("air", ()):          # in the air the legs fly with the body
                pose = _stay(family, pose, {}, m.get("stay", ()), stride)
        out[frame] = pose
    return out


def _leapt(family, poses, hit):
    """A jumping chop leaves the ground: the body rises 0.15 of its height with the legs tucked and
    lands on the contact (plant adds an authored rise on top of the floor)."""
    out = []
    for i, pose in enumerate(poses):
        k = math.sin(math.pi * min(i / max(hit, 1), 1.0)) if i <= hit else 0.0
        pose = dict(pose)
        rx, ry, rz, lift, up = P.pad(pose.get("root", ()))
        pose["root"] = (rx, ry, rz, lift, max(up, 0.0) + 0.15 * RF.top(family) * k)
        for bone, turn in crouch(0.8 * k).items():
            if bone in RF.bones(family):
                v = P.pad(pose.get(bone, ()))
                pose[bone] = (v[0] + turn[0] * _probe(family, bone, 0), *v[1:])
        out.append(pose)
    return out


def _snap(family, poses):
    """A beast that strikes with its head shows it: the head rears, snaps down onto the target at
    the moment the body is farthest forward and holds there (the reference bites by lunging the
    whole body, which is scaled down). Returns (poses, bite sample), or (poses, None) without a head."""
    names = RF.bones(family)
    if any(b.startswith("neck") for b in names):
        return _dart(family, poses), 6
    if "head" not in names or RS.contact_free(family, poses):
        return poses, None
    lifts = [P.pad(p.get("root", ()))[3] for p in poses]
    hit = min(max(lifts.index(max(lifts)), 5), len(poses) - 3)
    sign = _probe(family, "head", 0)
    keys = {hit + at: {"head": (value * sign, 0, 0, 0)} for at, value in _SNAP.items()}
    jaw = _probe(family, "jaw", 0) if "jaw" in RF.bones(family) else 0
    out = []
    for i, pose in enumerate(poses):
        rx, *rest = P.pad(pose.get("head", ()))
        turn = P.pad(P.sample(keys, i)["head"])[0]
        pose = {**pose, "head": (rx + turn, *rest)}
        if jaw:                                 # the mouth opens as the head rears, shuts on the bite
            pose["jaw"] = (-0.6 * max(turn * sign, 0.0) * jaw, 0.0, 0.0, 0.0, 0.0)
        out.append(pose)
    return out, hit


def _mount_strike(family, poses, name, hit, soft, stride):
    """`poses` with the mount's own strike (MOUNT_LUNGES) keyed under the rider's: wound up just before the
    rider's contact sample `hit` (a rider without a keyed strike: _LUNGE_HIT), struck on it, held, home by
    the last sample. The rider's bones are not touched: the mount carries them."""
    spec = MOUNT_LUNGES.get(family, {}).get(name)
    last = len(poses) - 1
    if spec is None or last < 12:
        return poses
    at = min(max(_LUNGE_HIT if hit is None else hit, 3), last - 8)
    after = sorted({min(at + spec.get("sweep", 8), last - 3), min(at + 8, last - 3)})
    beats = {"stance": (0, last), "wound": (at - 2,), "struck": (at,), "after": tuple(after)}
    return _lunge(family, poses, {**spec, "beats": beats}, soft, stride)


def _from_ref(family, layers, count, name="", grip=None, stand=False, soft=1.0, stride=1.0):
    """([pose] planted on the floor, contact sample of a strike or None). A strike's clip starts at
    its wind-up, so it may be shorter than `count`. `stand`: an attack that is not a leap, whose
    body is to stay on the spot."""
    got = RT.clip(family, layers, count)
    poses, hit, cut, found = _held(family, got["poses"], name, layers, grip), None, 0, _strike(layers, name)
    if name in LUNGES.get(family, ()):
        poses, hit = _lunge(family, poses, LUNGES[family][name], soft, stride), _LUNGE_HIT
    elif found:
        poses, hit, cut = _struck(family, poses, *found, grip, soft)
    elif stand and not got["air"]:
        if any("legs" in RT.MAPS[layer[2]] for layer in layers):
            poses = RT.clip(family, layers, count, RS.ROOT_MAX * RF.top(family))["poses"]     # the feet stay: foot IK
        else:
            poses = _stood(family, poses)
        poses, hit = _snap(family, poses)
    poses = _mount_strike(family, poses, name, hit, soft, stride)
    full = plant(family, dict(enumerate(poses, start=1)), {i + 1 - cut for i in got["air"]})
    return [full[k] for k in sorted(full)], hit


# clip length in frames (24 fps) of the hand-keyed and today's motions, by kind
LENGTH = {"attack": 30, "spell": 36, "loop": 24, "death": 40}


# Loops that only accompany a motion (wings beating, a mount or rider standing, a snake
# swaying): the motion's length comes from the first layer that is not one of them.
COMPANIONS = {("h009", "DragonArmature|Dragon_Flying"), ("e006", "AnimalArmature|Idle"),
              ("kk_general", "Idle_A"), ("n00H", "SnakeArmature|Snake_Idle"), ("o009", "Hover"),
              ("n01P", "Armature|Apatosaurus_Idle")}


def _ref_length(layers):
    """Frames of the layer that drives the motion: the first that is not a companion loop
    (a harpy's chop runs at the chop's pace, not its wings'); all companions: the first."""
    driver = next((layer for layer in layers if (layer[0], layer[1]) not in COMPANIONS), layers[0])
    return RT.duration(driver[0], driver[1])


def _today(family):
    return RF.BIPED_ACTIONS if family == "biped" else RF.actions(family)


def names(family):
    """Every motion of a family: today's clips, the retargeted ones, the hand-keyed ones."""
    return ([f"today_{name}" for name, *_ in _today(family)] + list(REF_MOTIONS.get(family, {}))
            + [f"keyed_{name}" for name in MOTIONS.get(family, {})])


@functools.lru_cache(maxsize=None)
def motion(family, name, rate=24, grip=None, soft=1.0, stride=1.0):
    """{"kind", "impact", "note", "poses": {1..10: pose}, "clip": [pose] * rate, "frames":
    clip length at 24 fps} of one motion (cached: treat the result as read-only). `grip` is the
    unit's weapons ((side, blade), ...) for the strikes keyed on them (rig_strike); `stride` is the
    unit's travel in leg lengths over the family's (_stay)."""
    if name.startswith("today_"):
        poses = next(p for n, p, *_ in _today(family) if n == name[len("today_"):])
        return {"kind": "existing", "impact": None, "note": f"today's {name[6:]} clip",
                "poses": _complete(_frames(poses)), "clip": _complete(P.strip(poses, rate)),
                "frames": max(poses) - min(poses)}
    if name.startswith("keyed_"):
        m = MOTIONS[family][name[len("keyed_"):]]
        keys = {f: {b: tuple(c * soft for c in v) for b, v in pose.items()} for f, pose in m["keys"].items()}
        poses = _complete(plant(family, _frames(_staged(family, raw(family, keys), m, soft, stride)), m.get("air", ())))
        return {"kind": m["kind"], "impact": m["impact"], "note": m["note"], "poses": poses, "props": m.get("props", ()),
                "clip": _complete(P.strip(poses, rate)), "frames": LENGTH[m["kind"]]}
    kind, note, layers, *hit = REF_MOTIONS[family][name]
    full, struck = _from_ref(family, layers, rate, name, grip, kind == "attack" and family not in RF.HOVER, soft, stride)
    strip = RT.ten(full, FRAMES)
    auto = impact(family, strip) if kind in ("attack", "spell") else None
    out = {"kind": kind, "impact": hit[0] if hit else auto, "note": note, "poses": dict(enumerate(strip, start=1)),
           "clip": full, "frames": round(_ref_length(layers) * (len(full) - 1) / (rate - 1))}
    if name in LUNGES.get(family, ()):
        out["frames"] = _LUNGE_FRAMES
    if struck is not None:
        out["impact"], out["hit"] = min(max(2, 1 + round(struck * (FRAMES - 1) / (len(full) - 1))), FRAMES - 1), struck
    return out


def storyboard(family, motion_rate=24):
    """{name: motion(...)} for every motion of a family."""
    return {name: motion(family, name, motion_rate) for name in names(family)}


# ---------------------------------------------------------------- what the builder keys
def _slots(idle, walk, attack, death, spell):
    return {"idle": idle, "walk": walk, "attack": attack, "death": death, "spell": spell}


_MACHINE = ("today_idle", "today_walk", "today_death")
DEFAULTS = {
    "biped": _slots("idle", "walk", "chop+slice_diagonal+slice_horizontal", "death_a", "cast_raise"),
    "quadruped": _slots("idle", "walk", "bite", "death", "keyed_roar"),
    "mounted": _slots("idle", "walk", "chop", "death", "cast"),
    "spider": _slots("idle", "walk", "bite", "death", "keyed_rear_up"),
    "spider_high": _slots("idle", "walk", "bite", "death", "keyed_rear_up"),
    "drake": _slots("fly", "glide", "bite", "death", "claw"),
    "mounted_flyer": _slots("fly", "glide", "chop", "death", "cast"),
    "bird": _slots("hover", "fly", "bite", "death", "breath"),
    "bird_rider": _slots("hover", "fly", "lance", "death", "cast"),
    "harpy": _slots("idle", "walk", "chop", "death_a", "cast_shoot"),
    "ray": _slots("swim", "swim", "bite", "death", "lash"),
    "shard": _slots("fly", "fly", "strike", "death", "pulse"),
    "serpent": _slots("idle", "walk", "bite", "today_death", "lunge"),
    "sled": _slots("idle", "walk", "bite", "today_death", "lunge"),
    "wyrm": _slots("idle", "walk", "bite", "today_death", "lunge"),
    "hydra": _slots("idle", "walk", "bite", "today_death", "keyed_roar"),
    "naga": _slots("idle", "walk", "stab", "death", "cast_shoot"),
    "centaur": _slots("idle", "walk", "chop", "death", "cheer"),
    "wraith": _slots("idle", "walk", "punch", "death", "cast_shoot"),
    "crawler": _slots("idle", "walk", "bite", "death", "jump"),
    "crustacean": _slots("idle", "walk", "pinch", "death", "jump"),
    "walker": _slots("idle", "walk", "kick", "death", "shoot_big"),
    **{fam: _slots(_MACHINE[0], _MACHINE[1], attack, _MACHINE[2], spell) for fam, attack, spell in (
        ("vehicle", "keyed_recoil", "keyed_brace"), ("tracked", "keyed_arm_slam", "keyed_brace"),
        ("aircraft", "keyed_strafe", "keyed_turn"), ("crew", "keyed_fire", "keyed_reload"),
        ("pod", "keyed_lash", "keyed_pulse"))},
}


SLOTS = ("idle", "walk", "attack", "death", "spell")


UNIT_TABLE = pathlib.Path(__file__).resolve().parents[2] / "data/unit_anim.tsv"


@functools.lru_cache(maxsize=1)
def unit_rows():
    """data/unit_anim.tsv as {unit_id: row} (read once per process)."""
    if not UNIT_TABLE.exists():
        return {}
    lines = UNIT_TABLE.read_text().splitlines()
    head = lines[0].split("\t")
    return {row["unit_id"]: row for row in (dict(zip(head, line.split("\t"))) for line in lines[1:])}


def unit_in_path(path):
    """The unit id a spec path names: spec-<id>-v11.json, or runs/draft/<id>/<variant>/spec.json.
    Other directories are not looked at (a checkout under a folder named like a unit is not one)."""
    rows, path = unit_rows(), pathlib.Path(path)
    stem = path.stem.split("-")
    if len(stem) > 1 and stem[0] == "spec" and stem[1] in rows:
        return stem[1]
    parts = path.parts
    if len(parts) >= 4 and parts[-4] == "draft" and parts[-3] in rows:
        return parts[-3]
    return None


def unit_picks(unit_id, family):
    """The unit's row of data/unit_anim.tsv as {slot: motion}, when it is drawn on `family`."""
    row = unit_rows().get(unit_id)
    return {slot: row[slot] for slot in SLOTS} if row and row["rig"] == family else None


STRIDE_MAX = 1.5    # travel in leg lengths over the family's past which the feet drag: legs laid flat tear the mesh


def _fitted(clip, reach, legs):
    """A strike's poses for a unit whose skeleton is `reach` times the family's along the body and whose
    legs are `legs` times as long: the root travels in proportion, and rises or sinks by its own legs."""
    out = []
    for pose in clip:
        rx, ry, rz, lift, up = P.pad(pose.get("root", ()))
        out.append({**pose, "root": (rx, ry, rz, lift * reach, up * legs)})
    return out


def clips(family, choice=None, grip=None, soft=1.0, fit=None):
    """The clips a unit of `family` gets, in build_unit's format [(name, {frame: pose},
    cyclic, contacts, lags)]: DEFAULTS[family] overridden by the spec's `choice`
    ({"attack": "chop", ...}). Frames follow the reference's own timing. `grip` {side: blade or
    None} is the unit's weapons (rig_strike): its strikes are keyed on them, `soft` (1 = full) of
    the way from the stance when the unit's mesh tears on the full arc (anim_refresh). `fit` (reach,
    legs) is the unit's skeleton over the family's (anim_refresh.fit): its strikes travel by it."""
    picks = {**DEFAULTS.get(family, {}), **(choice or {})}
    held = tuple(sorted((side, blade and tuple(round(c, 3) for c in blade)) for side, blade in (grip or {}).items()))
    out = []
    reach, legs = fit or (1.0, 1.0)
    for slot, name in _expanded(picks):
        strike = slot.startswith("attack") and fit is not None
        m = motion(family, name, 24, held or None, soft, round(min(reach / legs, STRIDE_MAX), 2) if strike else 1.0)
        span = max(m["frames"], len(m["clip"]) - 1)
        last = len(m["clip"]) - 1
        clip = _fitted(m["clip"], reach, legs) if strike else m["clip"]
        cyclic = m["kind"] == "loop" or slot in ("idle", "walk")
        if slot == "death" and name.startswith("today_"):     # the old roll-over sinks: lay it on the floor
            clip = [plant(family, {1: pose})[1] for pose in clip]
        if cyclic:                          # the last sample is the first again: keying it holds a frame
            clip = clip[:-1]
        poses = {1 + round(i * span / last): pose for i, pose in enumerate(clip)}
        hit = 1 + round((m["impact"] - 1) * span / (FRAMES - 1)) if m["impact"] else None
        if "hit" in m:
            hit = 1 + round(m["hit"] * span / last)
        if slot.startswith("attack") and hit and hit > CONTACT:
            poses, hit = _early(poses, hit), CONTACT
        out.append((slot, poses, cyclic, (hit,) if hit else (), ()))
    return out


CONTACT = 6     # the frame an attack lands on at the latest: the game starts the clip when the hit is dealt


def _early(poses, hit):
    """An attack's keys with everything before the hit played faster, so the hit is on frame CONTACT:
    the game starts a swing when the sim deals the hit (ClipPlayer), a long wind-up lands late."""
    out = {}
    for frame in sorted(poses):
        early = 1 + round((frame - 1) * (CONTACT - 1) / (hit - 1)) if frame <= hit else frame - hit + CONTACT
        out[early] = poses[frame]
    return out


def combo(value):
    """The motions of a slot: "chop+slice_diagonal+stab" is a combo the game plays in turn."""
    return value.split("+")


def _expanded(picks):
    """[(action name, motion)]: a combo's motions become attack, attack2, attack3..."""
    out = []
    for slot in SLOTS:
        for i, name in enumerate(combo(picks[slot]) if slot in picks else []):
            out.append((slot if i == 0 else f"{slot}{i + 1}", name))
    return out
