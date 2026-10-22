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
import math
import pathlib

import rig_families as RF
import rig_poses as P
import rig_retarget as RT

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


def raw(family, keys):
    """Readable keys {frame: {bone: (pitch, side, twist[, fwd, up])}} -> clip keys."""
    signs = {}
    out = {}
    for frame, pose in keys.items():
        out[frame] = {}
        for bone, value in pose.items():
            if bone not in signs:
                signs[bone] = (_probe(family, bone, 0), _probe(family, bone, 2))
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
    rest height. The root's `up` is along the root bone, i.e. straight up."""
    floor = lowest(family, {})
    out = {}
    for frame, pose in poses.items():
        pose = {bone: P.pad(v) for bone, v in pose.items()}
        if frame not in air:
            rx, ry, rz, lift, up = pose.get("root", (0, 0, 0, 0, 0))
            pose["root"] = (rx, ry, rz, lift, up + floor - lowest(family, pose))
        out[frame] = pose
    return out


def existing(family):
    """The builder's clips today (rig_families), as {name: poses on frames 1..10}."""
    if family == "biped":
        clips = RF.BIPED_ACTIONS
    else:
        clips = RF.actions(family)
    return {name: _frames(poses) for name, poses, *_ in clips}


# ---------------------------------------------------------------- shared pieces
REST = {}


def crouch(depth):
    """Biped knees bent by `depth` (0..1): thighs forward, shins back, root down."""
    return {"thigh.L": (35 * depth, 0, 0), "shin.L": (-60 * depth, 0, 0), "foot.L": (25 * depth, 0, 0),
            "thigh.R": (35 * depth, 0, 0), "shin.R": (-60 * depth, 0, 0), "foot.R": (25 * depth, 0, 0),
            "root": (0, 0, 0, 0, -0.30 * depth)}


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
            3: _with(crouch(0.3), {"spine": (12, 0, 0), "head": (8, 0, 0),
                                   "arm.L": (150, 10, 0), "forearm.L": (20, 0, 0),
                                   "arm.R": (150, -10, 0), "forearm.R": (20, 0, 0)}),
            5: _with(crouch(0.2), {"spine": (20, 0, 0), "head": (12, 0, 0),
                                   "arm.L": (175, 8, 0), "forearm.L": (35, 0, 0),
                                   "arm.R": (175, -8, 0), "forearm.R": (35, 0, 0)}),
            6: _with(crouch(0.6), {"spine": (-28, 0, 0), "head": (-10, 0, 0),
                                   "arm.L": (55, 6, 0), "forearm.L": (10, 0, 0),
                                   "arm.R": (55, -6, 0), "forearm.R": (10, 0, 0)}),
            7: _with(crouch(0.6), {"spine": (-30, 0, 0), "head": (-10, 0, 0),
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
                                   "arm.R": (85, 0, 60), "forearm.R": (15, 0, 0), "arm.L": (35, 0, 0)}),
            6: _with(crouch(0.35), {"spine": (-10, 0, 40), "head": (0, 0, -25),
                                    "arm.R": (85, 0, -55), "forearm.R": (5, 0, 0), "arm.L": (-25, 0, 0)}),
            7: _with(crouch(0.35), {"spine": (-12, 0, 50), "head": (0, 0, -30),
                                    "arm.R": (80, 0, -80), "forearm.R": (5, 0, 0), "arm.L": (-25, 0, 0)}),
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
}


# ---------------------------------------------------------------- quadruped
def _quad_legs(front, hind):
    """Front legs (leg1/leg2) and hind legs (leg3/leg4) pitched together."""
    return {"leg1.upper": (front, 0, 0), "leg2.upper": (front, 0, 0),
            "leg3.upper": (hind, 0, 0), "leg4.upper": (hind, 0, 0)}


def _quad_crouch(front, hind):
    """Knees folded, 0..1 each: elbows back / hocks forward, so the body sinks."""
    legs = {}
    for leg, depth, sign in (("leg1", front, -1), ("leg2", front, -1), ("leg3", hind, 1), ("leg4", hind, 1)):
        legs[f"{leg}.upper"] = (sign * 35 * depth, 0, 0)
        legs[f"{leg}.lower"] = (-sign * 65 * depth, 0, 0)
    return legs


QUADRUPED = {
    "pounce": {
        "kind": "attack", "impact": 6, "air": (4, 5),
        "note": "pounce: sinks on the haunches, springs up and forward with forelegs reaching, lands head-first",
        "keys": {
            1: REST,
            3: _with(_quad_crouch(0.4, 0.9), {"root": (0, 0, 0, -0.10), "head": (-10, 0, 0),
                                              "tail.1": (-20, 0, 0)}),
            5: _with(_quad_legs(70, -55), {"root": (0, 0, 0, 0.45, 0.45), "spine.1": (10, 0, 0),
                                           "head": (15, 0, 0), "tail.1": (25, 0, 0),
                                           "leg1.lower": (-20, 0, 0), "leg2.lower": (-20, 0, 0)}),
            6: _with(_quad_legs(35, -30), {"root": (0, 0, 0, 0.60, 0.05), "spine.1": (-12, 0, 0),
                                           "head": (-30, 0, 0), "tail.1": (15, 0, 0)}),
            7: _with(_quad_legs(25, -20), {"root": (0, 0, 0, 0.55, -0.08), "spine.1": (-14, 0, 0),
                                           "head": (-30, 0, 0)}),
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
            6: _with(_quad_legs(25, -10), {"root": (-5, 0, 0, 0.05, -0.08), "head": (-20, 0, 0)}),
            10: REST,
        },
    },
    "roar": {
        "kind": "spell", "impact": 5,
        "note": "roar: plants the forelegs wide, drops the chest, stretches the neck out and up, holds",
        "keys": {
            1: REST,
            3: _with(_quad_legs(-10, 10), {"root": (0, 0, 0, -0.08, -0.05), "head": (-20, 0, 0)}),
            5: {"root": (-8, 0, 0, 0.0, -0.10), "leg1.upper": (20, 25, 0), "leg2.upper": (20, -25, 0),
                "head": (35, 0, 0), "tail.1": (30, 0, 0), "tail.2": (20, 0, 0)},
            8: {"root": (-8, 0, 0, 0.0, -0.10), "leg1.upper": (20, 25, 0), "leg2.upper": (20, -25, 0),
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


SPIDER = {
    "scratch": {
        "kind": "attack", "impact": 4,
        "note": "scratch: front-left leg rakes down, then front-right, body rocking into each swipe",
        "keys": {
            1: REST,
            3: {"body": (8, 0, 0), "leg2.upper": (55, 10, 0), "leg2.lower": (45, 0, 0)},
            4: {"body": (-6, 0, 0), "leg2.upper": (-15, -10, 0), "leg2.lower": (-25, 0, 0)},
            6: {"body": (8, 0, 0), "leg3.upper": (55, -10, 0), "leg3.lower": (45, 0, 0)},
            7: {"body": (-6, 0, 0), "leg3.upper": (-15, 10, 0), "leg3.lower": (-25, 0, 0)},
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
        "kind": "attack", "impact": 6, "air": (4, 5),
        "note": "pounce: body drops low, springs forward with the front pair raised, fangs down on landing",
        "keys": {
            1: REST,
            3: {"root": (0, 0, 0, -0.08, -0.15), "body": (-8, 0, 0), "head": (-5, 0, 0)},
            5: _with(_spider_front(70, 40), {"root": (0, 0, 0, 0.45, 0.55), "body": (15, 0, 0),
                                             "abdomen": (-15, 0, 0)}),
            6: _with(_spider_front(-10, -10), {"root": (0, 0, 0, 0.50, -0.05), "body": (-8, 0, 0),
                                               "head": (-20, 0, 0)}),
            7: _with(_spider_front(-10, -10), {"root": (0, 0, 0, 0.50, -0.05), "body": (-8, 0, 0),
                                               "head": (-20, 0, 0)}),
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
                "root": (0, 0, 0, 0.10, -0.05)},
            7: {"body": (-8, 0, 0), "abdomen": (-185, 0, 0), "head": (-10, 0, 0),
                "root": (0, 0, 0, 0.10, -0.05)},
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
def _recoil(extra_hit=None, extra_wind=None):
    """A gun's kick: the turret/barrel snaps up, the body is shoved back, then settles."""
    return {
        "kind": "attack", "impact": 3,
        "note": "fires: barrel kicks up, the whole body is shoved back, then rocks forward and settles",
        "keys": {1: REST,
                 2: {"head": (-3, 0, 0), **(extra_wind or {})},
                 3: {"head": (14, 0, 0), "root": (0, 0, 0, -0.14), **(extra_hit or {})},
                 5: {"head": (6, 0, 0), "root": (0, 0, 0, -0.08)},
                 7: {"head": (-2, 0, 0), "root": (0, 0, 0, 0.02)},
                 10: REST}}


def _brace(note, hold):
    return {"kind": "spell", "impact": 5, "note": note,
            "keys": {1: REST, 3: {"root": (0, 0, 0, 0, -0.06)}, 5: hold, 8: hold, 10: REST}}


VEHICLE = {"recoil": _recoil({"hull": (4, 0, 0)}),
           "brace": _brace("deploys: squats on its wheels, turret rises and holds", {"root": (0, 0, 0, 0, -0.08),
                                                                                       "head": (18, 0, 0)})}
TRACKED = {"recoil": _recoil({"hull": (4, 0, 0)}),
           "arm_slam": {"kind": "attack", "impact": 6,
                        "note": "tool arms rise, then slam down together; the hull dips into the blow",
                        "keys": {1: REST, 4: {"arm.L": (60, 0, 0), "arm.R": (60, 0, 0), "hull": (4, 0, 0)},
                                 6: {"arm.L": (-25, 0, 0), "arm.R": (-25, 0, 0), "hull": (-5, 0, 0),
                                     "root": (0, 0, 0, 0.06)},
                                 7: {"arm.L": (-22, 0, 0), "arm.R": (-22, 0, 0), "hull": (-4, 0, 0)}, 10: REST}},
           "brace": _brace("deploys: hull settles, turret rises and holds", {"root": (0, 0, 0, 0, -0.06),
                                                                             "head": (18, 0, 0)})}
AIRCRAFT = {"strafe": {"kind": "attack", "impact": 5,
                       "note": "strafing run: noses down and lunges, gondola swings back, pulls up",
                       "keys": {1: REST, 3: {"hull": (8, 0, 0), "gondola": (-10, 0, 0)},
                                5: {"hull": (-15, 0, 0), "gondola": (20, 0, 0), "root": (0, 0, 0, 0.25)},
                                7: {"hull": (-6, 0, 0), "gondola": (10, 0, 0), "root": (0, 0, 0, 0.15)}, 10: REST}},
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
POD = {"lash": {"kind": "attack", "impact": 6,
                "note": "lash: tendrils coil back, the body leans in, all three whip forward",
                "keys": {1: REST,
                         4: {"body": (8, 0, 0), **{f"{t}.1": (-40, 0, 0) for t in _TENDRILS},
                             **{f"{t}.2": (-30, 0, 0) for t in _TENDRILS}},
                         6: {"body": (-10, 0, 0), **{f"{t}.1": (70, 0, 0) for t in _TENDRILS},
                             **{f"{t}.2": (40, 0, 0) for t in _TENDRILS}},
                         7: {"body": (-8, 0, 0), **{f"{t}.1": (55, 0, 0) for t in _TENDRILS}}, 10: REST}},
       "pulse": {"kind": "spell", "impact": 5,
                 "note": "pulse: rises, stalk arches back, tendrils splay wide, holds, drops back",
                 "keys": {1: REST, 5: {"root": (0, 0, 0, 0, 0.15), "stalk.1": (20, 0, 0), "stalk.2": (15, 0, 0),
                                       "tendril1.1": (0, 45, 0), "tendril2.1": (0, -45, 0), "tendril3.1": (35, 0, 0)},
                          8: {"root": (0, 0, 0, 0, 0.15), "stalk.1": (20, 0, 0), "stalk.2": (15, 0, 0),
                              "tendril1.1": (0, 45, 0), "tendril2.1": (0, -45, 0), "tendril3.1": (35, 0, 0)},
                          10: REST},
                 "air": tuple(range(2, 10))}}

def _spit(body):
    """A ranged head attack for beasts without one in their references: the head draws
    up and back, the body coils, then the head snaps forward and down."""
    return {"kind": "attack", "impact": 6,
            "note": "spit: head rears up and back, the body coils, then the head snaps forward",
            "keys": {1: REST, 3: {body: (6, 0, 0), "head": (35, 0, 0), "root": (0, 0, 0, -0.08)},
                     5: {body: (8, 0, 0), "head": (45, 0, 0), "root": (0, 0, 0, -0.10)},
                     6: {body: (-6, 0, 0), "head": (-30, 0, 0), "root": (0, 0, 0, 0.10)},
                     7: {body: (-5, 0, 0), "head": (-25, 0, 0), "root": (0, 0, 0, 0.08)}, 10: REST}}


QUADRUPED["spit"] = _spit("spine.2")
CRAWLER = {"spit": _spit("body"),
           "shoot": {**_recoil(), "note": "fires: head (its gun) kicks up, the body is shoved back"}}
SLED = {"fire": {**_recoil({"spine.4": (4, 0, 0)}), "note": "fires: the front kicks up, the body is shoved back"}}

MOTIONS = {"biped": BIPED, "quadruped": QUADRUPED, "spider": SPIDER, "vehicle": VEHICLE, "tracked": TRACKED,
           "aircraft": AIRCRAFT, "crew": CREW, "pod": POD, "crawler": CRAWLER, "sled": SLED}

# ---------------------------------------------------------------- from reference animations
# (model, clip, map, kind, note): retargeted by rig_retarget from artifacts/anim-ref/<model>
_KAYKIT = [
    ("chop", "1H_Melee_Attack_Chop", "attack", "one-hand chop"),
    ("slice_diagonal", "1H_Melee_Attack_Slice_Diagonal", "attack", "one-hand diagonal slice"),
    ("slice_horizontal", "1H_Melee_Attack_Slice_Horizontal", "attack", "one-hand horizontal slice"),
    ("stab", "1H_Melee_Attack_Stab", "attack", "one-hand stab"),
    ("chop_2h", "2H_Melee_Attack_Chop", "attack", "two-hand overhead chop"),
    ("slice_2h", "2H_Melee_Attack_Slice", "attack", "two-hand slice"),
    ("spin_2h", "2H_Melee_Attack_Spin", "attack", "two-hand spin"),
    ("dual_chop", "Dualwield_Melee_Attack_Chop", "attack", "two weapons chop"),
    ("punch", "Unarmed_Melee_Attack_Punch_A", "attack", "punch"),
    ("kick", "Unarmed_Melee_Attack_Kick", "attack", "kick"),
    ("shield_bash", "Block_Attack", "attack", "shield bash"),
    ("shoot_1h", "1H_Ranged_Shoot", "attack", "one-hand shot (pistol, wand)"),
    ("shoot_2h", "2H_Ranged_Shoot", "attack", "two-hand shot (bow, rifle)"),
    ("throw", "Throw", "attack", "overarm throw"),
    ("cast_raise", "Spellcast_Raise", "spell", "spell: raise"),
    ("cast_shoot", "Spellcast_Shoot", "spell", "spell: shoot a bolt"),
    ("cast_long", "Spellcast_Long", "spell", "spell: long channel"),
    ("cheer", "Cheer", "spell", "war cry / cheer"),
    ("idle", "Idle", "loop", "idle"),
    ("walk", "Walking_A", "loop", "walk"),
    ("death_a", "Death_A", "death", "death A"),
    ("death_b", "Death_B", "death", "death B"),
]
A_ = "AnimalArmature|"
_MOUNT = "e006"             # Quaternius animal (CC0): walk, gallop, kick, headbutt
_RIDER = [                  # (name, mount clip, rider clip, kind, note)
    ("idle", "Idle", "Idle", "loop", "standing, rider sits"),
    ("walk", "Walk", "Idle", "loop", "walk, rider sits"),
    ("gallop", "Gallop", "Idle", "loop", "gallop, rider sits"),
    ("chop", "Idle", "1H_Melee_Attack_Chop", "attack", "rider: one-hand chop"),
    ("lance", "Idle", "1H_Melee_Attack_Stab", "attack", "rider: lance / spear thrust"),
    ("slice_2h", "Idle", "2H_Melee_Attack_Slice", "attack", "rider: two-hand slice"),
    ("charge_chop", "Gallop", "1H_Melee_Attack_Chop", "attack", "charge: gallop and chop"),
    ("shoot", "Idle", "2H_Ranged_Shoot", "attack", "rider: bow / rifle shot"),
    ("cast", "Idle", "Spellcast_Raise", "spell", "rider: spell, raise"),
    ("mount_kick", "Attack_Kick", "Idle", "attack", "the mount kicks"),
    ("death", "Death", "Idle", "death", "the mount falls"),
]
REF_MOTIONS = {
    "biped": {name: (kind, f"{note} (KayKit, CC0)", [("hfoo", clip, "kaykit_biped")])
              for name, clip, kind, note in _KAYKIT},
    "quadruped": {
        **{name: (kind, f"{note} (Quaternius animal, CC0)", [(_MOUNT, A_ + clip, "quaternius_animal")])
           for name, clip, kind, note in (("idle", "Idle", "loop", "idle"), ("walk", "Walk", "loop", "walk"),
                                          ("gallop", "Gallop", "loop", "gallop"),
                                          ("kick", "Attack_Kick", "attack", "hind kick"),
                                          ("headbutt", "Attack_Headbutt", "attack", "headbutt"),
                                          ("jump", "Gallop_Jump", "attack", "leap"),
                                          ("death", "Death", "death", "death"))},
        "bite": ("attack", "lunging bite (Quaternius wolf, CC0)", [("n017", A_ + "Attack", "quaternius_animal")]),
        "claw_chop": ("attack", "ghoul claws: both forelegs chop like arms (animal idle + KayKit dual-wield chop)",
                      [(_MOUNT, A_ + "Idle", "quaternius_animal"),
                       ("hfoo", "Dualwield_Melee_Attack_Chop", "kaykit_forelegs")]),
        "claw_punch": ("attack", "ghoul jab: one foreleg punches (animal idle + KayKit punch)",
                       [(_MOUNT, A_ + "Idle", "quaternius_animal"),
                        ("hfoo", "Unarmed_Melee_Attack_Punch_A", "kaykit_forelegs")]),
    },
    "mounted": {name: (kind, f"{note} (Quaternius animal + KayKit rider, CC0)",
                       [(_MOUNT, A_ + mount, "quaternius_animal"), ("hfoo", rider, "kaykit_rider")])
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
_KAYKIT_PICK = {n: c for n, c, *_ in _KAYKIT}
_RIDER_ACTS = [("chop", "1H_Melee_Attack_Chop", "attack", "rider: one-hand chop"),
               ("lance", "1H_Melee_Attack_Stab", "attack", "rider: lance thrust"),
               ("shoot", "2H_Ranged_Shoot", "attack", "rider: bow / rifle shot"),
               ("throw", "Throw", "attack", "rider: throws (hammer, spear)"),
               ("cast", "Spellcast_Raise", "spell", "rider: spell, raise")]
_CREDIT = {"hfoo": "KayKit", "e006": "Quaternius animal", "h009": "Quaternius dragon",
           "o009": "clintbellanger wyvern, CC-BY-SA-4.0",
           "n00H": "Quaternius snake", "n01P": "Quaternius apatosaurus", "cr_rat": "Quaternius rat",
           "n00U": "Quaternius spider", "h097": "Quaternius robot", "n01N": "TheGameAssets spider, CC-BY-4.0"}


def _entry(kind, note, *layers):
    models = dict.fromkeys(_CREDIT.get(layer[0], layer[0]) for layer in layers)
    return (kind, f"{note} ({' + '.join(models)})", list(layers))


def _upper_body(map_name, base):
    """KayKit actions on an upper body (naga, centaur, wraith) over `base` layers per slot."""
    acts = [("chop", "attack", "one-hand chop"), ("stab", "attack", "stab / spear thrust"),
            ("slice_2h", "attack", "two-hand slice"), ("punch", "attack", "claw / punch"),
            ("shoot_2h", "attack", "bow / rifle shot"), ("throw", "attack", "throw"),
            ("cast_raise", "spell", "spell: raise"), ("cast_shoot", "spell", "spell: bolt"),
            ("cast_long", "spell", "spell: channel"), ("cheer", "spell", "war cry")]
    out = {name: _entry(kind, note, *base["still"], ("hfoo", _KAYKIT_PICK[name], map_name))
           for name, kind, note in acts}
    out["idle"] = _entry("loop", "idle", *base["idle"], ("hfoo", "Idle", map_name))
    out["walk"] = _entry("loop", "move", *base["walk"], ("hfoo", "Walking_A", map_name))
    out["death"] = _entry("death", "death", *base["death"], ("hfoo", "Death_A", map_name))
    return out


def _flyer_rider(mount, rider_still, death):
    out = {"fly": _entry("loop", "fly, rider sits", mount["fly"], ("hfoo", "Idle", "kaykit_rider")),
           "death": _entry("death", "the mount falls", death, ("hfoo", "Idle", "kaykit_rider"))}
    for name, clip, kind, note in _RIDER_ACTS:
        out[name] = _entry(kind, note, rider_still, ("hfoo", clip, "kaykit_rider"))
    return out


_BIRD_FLY = ("h009", _DR + "Flying", "dragon_bird")
_BIRD = {"hover": _entry("loop", "hover", _BIRD_FLY), "fly": _entry("loop", "fly", _BIRD_FLY),
         "bite": _entry("attack", "bite: the neck lunges, the body keeps flying", _BIRD_FLY,
                        ("h009", _DR + "Attack", "dragon_neck")),
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
          "bite": _entry("attack", "lunging bite", ("n017", A_ + "Attack", "animal_drake"), _WINGS),
          "headbutt": _entry("attack", "head ram", (_MOUNT, A_ + "Attack_Headbutt", "animal_drake"), _WINGS),
          "claw": _entry("attack", "foreleg claw", (_MOUNT, A_ + "Idle", "animal_drake"), _WINGS,
                         ("hfoo", "Dualwield_Melee_Attack_Chop", "kaykit_forelegs")),
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
                                layers + [("hfoo", "Idle", "kaykit_rider")])
                         for name, (kind, note, layers) in _DRAKE.items()},
                      **{name: _entry(kind, note, *_DRAKE_STILL, ("hfoo", clip, "kaykit_rider"))
                         for name, clip, kind, note in _RIDER_ACTS}},
    "bird": {**_BIRD, **{f"wyvern_{k}": v for k, v in _WYVERN_MOVES.items()}},
    "bird_rider": {**_flyer_rider({"fly": _BIRD_FLY}, _BIRD_FLY, ("h009", _DR + "Death", "dragon_bird")),
                   "hover": _entry("loop", "hover, rider sits", _BIRD_FLY, ("hfoo", "Idle", "kaykit_rider")),
                   "mount_bite": _entry("attack", "the mount bites", _BIRD_FLY, ("h009", _DR + "Attack", "dragon_neck"),
                                        ("hfoo", "Idle", "kaykit_rider")),
                   "wyvern_fly": _entry("loop", "fly, rider sits", _WYVERN["fly"], ("hfoo", "Idle", "kaykit_rider")),
                   "wyvern_sting": _entry("attack", "the mount stings", ("o009", "Sting", "wyvern"),
                                          ("hfoo", "Idle", "kaykit_rider"))},
    "harpy": {name: _entry(kind, note, ("hfoo", clip, "kaykit_biped"), ("h009", _DR + "Flying", "dragon_wings"))
              for name, clip, kind, note in _KAYKIT if name in
              ("idle", "walk", "chop", "slice_diagonal", "stab", "chop_2h", "slice_2h", "punch", "kick", "shoot_1h",
               "shoot_2h", "throw", "cast_raise", "cast_shoot", "cast_long", "cheer", "death_a")},
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
                                 ("hfoo", "Idle", "kaykit_centaur")),
                "kick": _entry("attack", "hind kick", (_MOUNT, A_ + "Attack_Kick", "quaternius_animal"),
                               ("hfoo", "Idle", "kaykit_centaur"))},
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
REF_MOTIONS["spider"].update({
    "rear_strike": ("attack", "rears up on the back legs and hammers down with the front pair "
                    "(TheGameAssets spider, CC-BY-4.0)", [("n01N", "Spider_Attack_1", "gameassets_spider")]),
    "lunge": ("attack", "lunges and strikes with the front legs (TheGameAssets spider, CC-BY-4.0)",
              [("n01N", "Spider_Attack_2", "gameassets_spider")]),
})


FAMILIES = sorted(f for f in RF.FAMILIES if f not in RF.STATIC)


def impact(family, poses):
    """1-based index of the fastest moment of the limb ends (tails of leaf bones)."""
    kids = set(RF.parents(family).values())
    flaps = ("wing", "tail", "tendril")             # they beat or wave all the time
    leaves = [b for b in RF.bones(family) if b not in kids and b != "root"]
    ends = [b for b in leaves if not b.startswith(flaps)] or leaves     # a ray is all wing and tail
    tips = [P.joints(family, p) for p in poses]
    speed = [max(math.dist(tips[i][b][1], tips[i - 1][b][1]) for b in ends) for i in range(1, len(tips))]
    return speed.index(max(speed)) + 2


def _sampled(poses, count):
    keys = sorted(poses)
    return [P.sample(poses, keys[0] + (keys[-1] - keys[0]) * i / (count - 1)) for i in range(count)]


def _from_ref(family, layers, count):
    got = RT.clip(family, layers, count)
    full = plant(family, dict(enumerate(got["poses"], start=1)), {i + 1 for i in got["air"]})
    return [full[k] for k in sorted(full)]


# clip length in frames (24 fps) of the hand-keyed and today's motions, by kind
LENGTH = {"attack": 30, "spell": 36, "loop": 24, "death": 40, "existing": 30}


def _ref_length(layers):
    """Frames of the layer that drives the motion: the longest one that is not an idle."""
    lengths = [(RT.duration(model, clip), "Idle" in clip) for model, clip, *_ in layers]
    active = [n for n, idle in lengths if not idle]
    return max(active) if active else lengths[0][0]


def _today(family):
    return RF.BIPED_ACTIONS if family == "biped" else RF.actions(family)


def names(family):
    """Every motion of a family: today's clips, the retargeted ones, the hand-keyed ones."""
    return ([f"today_{name}" for name, *_ in _today(family)] + list(REF_MOTIONS.get(family, {}))
            + [f"keyed_{name}" for name in MOTIONS.get(family, {})])


def motion(family, name, rate=24):
    """{"kind", "impact", "note", "poses": {1..10: pose}, "clip": [pose] * rate, "frames":
    clip length at 24 fps} of one motion."""
    if name.startswith("today_"):
        poses = next(p for n, p, *_ in _today(family) if n == name[len("today_"):])
        return {"kind": "existing", "impact": None, "note": f"today's {name[6:]} clip", "poses": _frames(poses),
                "clip": _sampled(poses, rate), "frames": max(poses) - min(poses)}
    if name.startswith("keyed_"):
        m = MOTIONS[family][name[len("keyed_"):]]
        poses = plant(family, _frames(raw(family, m["keys"])), m.get("air", ()))
        return {"kind": m["kind"], "impact": m["impact"], "note": m["note"], "poses": poses,
                "clip": _sampled(poses, rate), "frames": LENGTH[m["kind"]]}
    kind, note, layers = REF_MOTIONS[family][name]
    full = _from_ref(family, layers, rate)
    strip = RT.ten(full, FRAMES)
    return {"kind": kind, "impact": impact(family, strip) if kind in ("attack", "spell") else None,
            "note": note, "poses": dict(enumerate(strip, start=1)), "clip": full, "frames": _ref_length(layers)}


def storyboard(family, motion_rate=24):
    """{name: motion(...)} for every motion of a family."""
    return {name: motion(family, name, motion_rate) for name in names(family)}


# ---------------------------------------------------------------- what the builder keys
def _slots(idle, walk, attack, death, spell):
    return {"idle": idle, "walk": walk, "attack": attack, "death": death, "spell": spell}


_MACHINE = ("today_idle", "today_walk", "today_death")
DEFAULTS = {
    "biped": _slots("idle", "walk", "chop", "death_a", "cast_raise"),
    "quadruped": _slots("idle", "walk", "bite", "death", "keyed_roar"),
    "mounted": _slots("idle", "walk", "chop", "death", "cast"),
    "spider": _slots("idle", "walk", "bite", "death", "keyed_rear_up"),
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
    "hydra": _slots("idle", "walk", "bite", "today_death", "bite"),
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


def unit_rows():
    if not UNIT_TABLE.exists():
        return {}
    lines = UNIT_TABLE.read_text().splitlines()
    head = lines[0].split("\t")
    return {row["unit_id"]: row for row in (dict(zip(head, line.split("\t"))) for line in lines[1:])}


def unit_in_path(path):
    """The unit id a spec path names: runs/draft/<id>/... or spec-<id>-v11.json."""
    rows = unit_rows()
    for part in reversed(pathlib.Path(path).parts):
        for token in [part, *part.replace(".", "-").split("-")]:
            if token in rows:
                return token
    return None


def unit_picks(unit_id, family):
    """The unit's row of data/unit_anim.tsv as {slot: motion}, when it is drawn on `family`."""
    row = unit_rows().get(unit_id)
    return {slot: row[slot] for slot in SLOTS} if row and row["rig"] == family else None


def clips(family, choice=None):
    """The clips a unit of `family` gets, in build_unit's format [(name, {frame: pose},
    cyclic, contacts, lags)]: DEFAULTS[family] overridden by the spec's `choice`
    ({"attack": "chop", ...}). Frames follow the reference's own timing."""
    picks = {**DEFAULTS.get(family, {}), **(choice or {})}
    out = []
    for slot in SLOTS:
        if slot not in picks:
            continue
        m = motion(family, picks[slot])
        span = max(m["frames"], len(m["clip"]) - 1)
        last = len(m["clip"]) - 1
        poses = {1 + round(i * span / last): pose for i, pose in enumerate(m["clip"])}
        hit = 1 + round((m["impact"] - 1) * span / (FRAMES - 1)) if m["impact"] else None
        out.append((slot, poses, m["kind"] == "loop" or slot in ("idle", "walk"), (hit,) if hit else (), ()))
    return out
