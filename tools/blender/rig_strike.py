"""Strikes: the arms of a melee motion keyed on the weapon, over the reference's body.

A retargeted KayKit strike copies where the reference's arm bones point. That is not enough to
read as a strike on our figures: KayKit swings a blade held square to the forearm with its wrist
and its whole body, and our weapons are skinned to the forearm itself, each model its own way (a
spear carried upright, a sword held forward, bare claws), in either hand. So the striking arm is
keyed here from what a strike must show: where the hand is and where the weapon points at the
wind-up, at the contact and after it. The legs, the torso and the head stay the reference's.

  grip    {"L": blade, "R": blade}: the weapon in each hand as the vector wrist -> tip in the
          forearm's rest frame (anim_refresh.grips measures it on the mesh); None: a bare hand,
          which strikes along the forearm. Without a grip the right hand strikes bare. STILL
          for a side: that arm waits in the stance whenever it is not the one striking (a fist
          the mesh fuses to the leg tears as soon as the reference swings it).
  STRIKES per KayKit motion: "hands" (one / two / dual) and "keys" [(samples from contact,
          hand, weapon)], hand = where the wrist is from the shoulder in arm lengths, weapon =
          where the blade points, both as (out, forward, up), out = away from the body on the
          arm's own side. Before and after the keys the arm is in the idle stance.

A weapon in the left hand mirrors the whole motion. The forearm takes the one turn that points
the blade as keyed and puts the wrist nearest its place (reach); the root's step and the legs are
scaled down together to ROOT_MAX body heights, the torso's pitch to TORSO_MAX degrees.
"""
import math

import rig_families as RF
import rig_poses as P

ROOT_MAX = 0.10         # body heights the root may travel in a strike (the weapon does the work)
TORSO_MAX = 28.0        # degrees of torso pitch range
LEAD, TAIL = 4, 9       # samples from the stance to the contact, and back to the stance
NARROW = 0.5            # share kept of the free arm's sideways reach (rig_retarget.NARROW)
WIDE = math.radians(110)    # a weapon's turn between two keys from which it goes over the top
OVER = (0.0, -0.9, 1.2)     # up and forward (armature axes): what such a turn passes through
OFF_GRIP = 0.45         # forearm lengths down the shaft where a two-handed grip's other hand goes
STILL = (0.0, 0.0, 0.0)     # a grip's blade for an arm that must not move

_HIGH = ((0.25, -0.05, 0.75), (0.10, -0.60, 0.80))          # hand over the shoulder, blade up and back
_DOWN = ((0.05, 0.82, -0.22), (0.0, 0.78, -0.62))            # arm out ahead and low, blade forward and down
_CHOP = [(-3, *_HIGH), (-2, (0.25, -0.10, 0.80), (0.10, -0.70, 0.70)), (0, *_DOWN), (2, *_DOWN)]
_SIDE = ((0.80, -0.15, -0.12), (0.80, -0.60, -0.05))        # arm out to the side below the shoulder, blade out and back
_ACROSS = ((-0.30, 0.70, 0.0), (-0.75, 0.65, -0.05))        # arm across the chest, blade past the target
_SLICE = [(-3, *_SIDE), (-2, (0.80, -0.25, -0.12), (0.70, -0.70, -0.05)),
          (-1, (0.50, 0.65, 0.02), (0.55, 0.85, 0.0)), (0, *_ACROSS), (2, *_ACROSS)]
# a diagonal cut runs sideways as much as down: from high and wide on the weapon's side to low across the body
# (a chop stays in the plane ahead, a flat slice at one height)
_LOW = ((-0.45, 0.55, -0.30), (-0.65, 0.35, -0.70))          # arm across and low, blade down past the target
_DIAGONAL = [(-3, (0.70, -0.10, 0.50), (0.80, -0.35, 0.50)), (-2, (0.70, -0.20, 0.55), (0.75, -0.45, 0.50)),
             (-1, (0.30, 0.70, 0.15), (0.35, 0.90, 0.10)), (0, *_LOW), (2, *_LOW)]
_BACK = ((0.15, -0.40, -0.25), (0.0, 1.0, 0.05))            # hand drawn back at the hip, blade at the target
_OUT = ((0.0, 0.97, 0.0), (0.0, 1.0, -0.05))                # arm straight at the target, blade along it
_STAB = [(-3, *_BACK), (-2, (0.15, -0.45, -0.25), (0.0, 1.0, 0.08)), (0, *_OUT), (2, *_OUT)]
# a weapon carried upright cannot be pushed out ahead (the forearm lies along it): it stabs overhand,
# tipped from over the shoulder down onto the target
_JAB = ((0.10, 0.35, -0.22), (0.0, 1.0, 0.0))                # couched: level at chest height, tip at the target
_OVERHAND = [(-3, (0.20, -0.45, -0.15), (0.0, 0.85, 0.50)), (-2, (0.20, -0.60, -0.20), (0.0, 0.97, 0.20)),
             (0, *_JAB), (2, *_JAB)]
# a rider strikes down past the mount: the arm reaches out to the side, forward and down at a foot target
_LANCED = ((0.45, 0.70, -0.45), (0.25, 0.80, -0.55))
_LANCE = [(-3, (0.50, -0.30, 0.35), (0.30, 0.50, 0.80)), (-2, (0.50, -0.40, 0.40), (0.30, 0.40, 0.85)),
          (0, *_LANCED), (2, *_LANCED)]
# a rider's second cut must not repeat the chop (up, then down beside the mount): the blade swings from low behind,
# under the hand, and rises ahead on the weapon's side, clear of the mount's neck
_RISEN = ((0.45, 0.75, 0.30), (0.25, 0.80, 0.55))
_RIDER_SWEEP = [(-3, (0.50, -0.45, -0.35), (0.30, -0.75, -0.55)), (-2, (0.50, -0.55, -0.30), (0.30, -0.85, -0.40)),
                (-1, (0.55, 0.30, -0.45), (0.35, 0.60, -0.70)), (0, *_RISEN), (2, *_RISEN)]
# a gun: levelled at the target; seen from above a muzzle that only climbs does not read, so the shot throws the
# weapon straight back along the ground (rig_motions._held shoves the body with it), then it settles level again
_LEVEL = ((0.10, 0.58, -0.12), (0.0, 1.0, 0.0))
_SHOT = [(-2, *_LEVEL), (-1, *_LEVEL), (0, (0.10, 0.28, -0.06), (0.0, 0.95, 0.30)), (1, (0.10, 0.32, -0.08), (0.0, 0.97, 0.24)),
         (4, *_LEVEL), (12, *_LEVEL)]
# a bow, read from the game's camera (56 degrees above the ground): the bow arm points at the target and the stave
# stands upright across it (leaning out it points at the camera from one side, leaning far ahead it lies down like a staff); the string hand pulls back along the ground
# and on the release snaps open forward while the bow kicks. Everything is over four samples after the shot.
_CANT = (0.0, 0.15, 1.0)                                    # the stave: upright, its top limb a little ahead
_KICKED = (0.0, 0.60, 0.80)                                 # loosed: the top limb rocks at the target
_BOWED = ((0.0, 0.97, 0.02), _CANT)
_BOW = [(-4, (0.10, 0.60, -0.20), (0.30, 0.30, 0.90)), (-3, *_BOWED), (-1, *_BOWED),
        (0, (0.0, 0.97, 0.08), _KICKED), (1, (0.0, 0.97, 0.08), _KICKED), (2, *_BOWED)]
# a bow skinned along its forearm stands only on a forearm that hangs: the upper arm alone points at the target, the
# forearm drops under it and the stave rises above the hand
_BOWED_LOW = ((0.0, 0.52, -0.42), (0.0, 0.10, 1.0))
_LOW_KICK = ((0.0, 0.66, -0.34), (0.0, 0.45, 0.89))
_BOW_LOW = [(-4, (0.0, 0.25, -0.60), (0.0, 0.0, 1.0)), (-3, *_BOWED_LOW), (-1, *_BOWED_LOW),
            (0, *_LOW_KICK), (1, *_LOW_KICK), (2, *_BOWED_LOW)]
# a bow the hand does not carry (skinned to the upper arm, the chest): it stays upright only while the upper arm
# hangs, so the forearm alone levels at the target and pushes out on the release
_BOW_AIM = ((0.02, 0.50, -0.55), (0.0, 1.0, 0.0))
_BOW_HUNG = [(-4, (0.05, 0.35, -0.65), (0.0, 0.90, -0.35)), (-3, *_BOW_AIM), (-1, *_BOW_AIM),
             (0, (0.02, 0.62, -0.48), (0.0, 1.0, 0.12)), (2, *_BOW_AIM)]
# the same bow shot high (bow_up): the upper arm swings a little forward and the stave cants with it, foot ahead
# and head back, as a bow aimed up does (swung far it reads as a lance); the release kicks the stave on forward
_BOW_UP = ((0.02, 0.60, -0.42), (0.0, 1.0, 0.12))
_BOW_LOB = [(-4, (0.05, 0.40, -0.62), (0.0, 0.90, -0.35)), (-3, *_BOW_UP), (-1, *_BOW_UP),
            (0, (0.02, 0.74, -0.30), (0.0, 0.95, 0.30)), (2, *_BOW_UP)]
# the string hand: out to the bow, drawn back level to the chest with the elbow behind, and on the release it
# springs open forward and out (the beat that shows the shot)
_DRAWN = ((-0.12, 0.08, 0.06), (-0.30, 0.95, 0.05))
_LOOSED = ((0.22, 0.42, -0.02), (0.45, 0.88, 0.10))
_DRAW = [(-3, (-0.40, 0.72, 0.0), (-0.45, 0.89, 0.0)), (-2, *_DRAWN), (-1, *_DRAWN), (0, *_LOOSED), (2, *_LOOSED)]
_PALM = ((-0.10, 0.98, 0.0), (-0.10, 1.0, 0.0))
_PUSH = [(-3, (0.20, -0.30, -0.10), (0.10, 0.90, 0.35)), (-2, (0.20, -0.35, -0.10), (0.10, 0.90, 0.35)),
         (0, *_PALM), (4, *_PALM)]
_FIST = ((-0.05, 0.98, 0.05), (-0.05, 1.0, 0.0))
_PUNCH = [(-3, (0.20, -0.30, -0.10), (0.10, 0.90, 0.35)), (-2, (0.20, -0.35, -0.10), (0.10, 0.90, 0.35)),
          (0, *_FIST), (2, *_FIST)]
_THROW = [(-3, (0.30, -0.45, 0.50), (0.20, -0.40, 0.85)), (-2, (0.30, -0.55, 0.50), (0.20, -0.55, 0.75)),
          (0, (0.0, 0.95, 0.35), (0.0, 1.0, -0.10)), (2, (0.0, 0.90, 0.05), (0.0, 0.90, -0.45))]
_TOOL = [(-2, *_HIGH), (0, (0.05, 0.75, -0.35), (0.0, 0.75, -0.65)), (1, (0.05, 0.75, -0.35), (0.0, 0.75, -0.65))]
# backhand: the arm cocks across the chest and rips outward, flat (a fan) or rising (a reverse grip)
_FLAT = ((0.60, 0.55, 0.05), (0.80, 0.55, 0.0))
_BACKHAND = [(-3, (-0.35, 0.40, 0.0), (-0.85, 0.35, 0.0)), (-2, (-0.40, 0.35, 0.0), (-0.90, 0.20, 0.0)),
             (-1, (0.15, 0.75, 0.02), (0.0, 1.0, 0.0)), (0, *_FLAT), (2, *_FLAT)]
_UP = ((0.55, 0.50, 0.55), (0.60, 0.45, 0.65))
_RISING = [(-3, (-0.40, 0.30, -0.40), (-0.60, 0.20, -0.75)), (-2, (-0.45, 0.25, -0.45), (-0.60, 0.05, -0.80)),
           (-1, (0.10, 0.75, 0.05), (0.0, 0.95, -0.25)), (0, *_UP), (2, *_UP)]
# a staff's head dips back and jabs at the target, level and low: from the hip, never over the shoulder
_AIMED = ((0.10, 0.62, -0.40), (0.0, 1.0, 0.10))
_POINT = [(-3, (0.20, -0.30, -0.40), (0.0, 0.80, 0.60)), (-2, (0.20, -0.40, -0.40), (0.0, 0.85, 0.50)),
          (0, *_AIMED), (2, *_AIMED)]
# a chained weight: one full circle overhead, released forward
_SLING = [(-4, (0.15, 0.10, 0.80), (0.60, 0.0, 0.80)), (-3, (0.15, 0.0, 0.80), (0.0, -0.60, 0.80)),
          (-2, (0.10, 0.10, 0.80), (-0.60, 0.0, 0.80)), (-1, (0.10, 0.30, 0.80), (0.0, 0.60, 0.80)),
          (0, (0.0, 0.90, 0.20), (0.0, 0.95, -0.30)), (2, (0.0, 0.90, 0.20), (0.0, 0.95, -0.30))]
# a gun or a nozzle at the hip: it stays on the target and shakes, a short pan left and right with the weapon
# jolting back on every other beat (a wide fan points it at the camera and through the gunner's own body)
_HIP, _HIP_BACK = (0.15, 0.46, -0.45), (0.15, 0.34, -0.45)
_SWEEP = [(0, _HIP, (0.32, 1.0, 0.0)), (2, _HIP_BACK, (-0.32, 1.0, 0.04)), (4, _HIP, (0.32, 1.0, 0.0)),
          (6, _HIP_BACK, (-0.32, 1.0, 0.04)), (8, _HIP, (0.32, 1.0, 0.0)), (10, _HIP_BACK, (-0.32, 1.0, 0.04)),
          (12, _HIP, (0.10, 1.0, 0.0))]
# a shield (or the free hand) punched out with the forearm across the body
# the forearm stays upright: a shield hangs along it, and turns into a roof when the forearm levels
_SHOVE = ((-0.05, 0.85, -0.30), (-0.10, 0.30, -0.95))
_BASH = [(-3, (0.20, -0.10, -0.50), (0.0, 0.0, -1.0)), (-2, (0.20, -0.20, -0.50), (0.0, -0.10, -1.0)),
         (0, *_SHOVE), (2, *_SHOVE)]
# a spin: the weapon sweeps across and back, level, at arm's length
_SPIN = _SLICE[:4] + [(3, *_ACROSS), (5, (0.50, 0.65, 0.02), (0.55, 0.85, 0.0)), (7, *_SIDE), (9, *_SIDE)]


# an axe swung from the side, down across the front: a builder's second tool must not repeat the hammer
_FELL = [(-2, (0.70, -0.10, 0.45), (0.75, -0.45, 0.50)), (0, (-0.20, 0.70, -0.30), (-0.50, 0.70, -0.50)),
         (1, (-0.20, 0.70, -0.30), (-0.50, 0.70, -0.50))]
# a pick swung from far behind the head, both hands, down to the ground ahead
_PICK = [(-2, (0.10, -0.35, 0.80), (0.0, -0.90, 0.40)), (0, (0.0, 0.70, -0.45), (0.0, 0.55, -0.85)),
         (1, (0.0, 0.70, -0.45), (0.0, 0.55, -0.85))]


# a tool swung level from the side: it stops ahead (a long tool swung on across the body points at the camera or
# hides its head against the worker)
_AHEAD = ((-0.10, 0.85, 0.0), (-0.35, 0.93, -0.05))
_FLAT_CUT = [(-2, *_SIDE), (0, *_AHEAD), (1, *_AHEAD)]


def _work(contacts, keys=_TOOL, hands="one"):
    """A builder's loop of blows: one strike per contact sample of the reference."""
    return {"hands": hands, "keys": keys, "contacts": contacts, "lead": 3, "tail": 3}


def _one(keys, **more):
    return {"hands": "one", "keys": keys, **more}


# "hands": one (the armed hand), two (and the other hand on the shaft), dual (both strike), off (the
# hand that does not hold the weapon: a shield), free (that hand too, or the bare striking hand of a unit that holds nothing), none (the arms only hang in: a kick). "free": "stance":
# the other arm waits in the stance (the reference's guard arm, pulled back as the fist goes out, reads
# as a second motion at this size and drags a cape or a pauldron skinned to it). "upright":
# the keys for a weapon carried upright (UPRIGHT). "contacts": fixed contact samples, the clip is
# not cut to start at the wind-up (a work loop, a spray). "root": body heights the root may travel
# where ROOT_MAX is too little.
STRIKES = {
    "chop": _one(_CHOP), "jump_chop": _one(_CHOP), "fist_slam": _one(_CHOP), "big_arm_slam": _one(_CHOP),
    "slice_diagonal": _one(_DIAGONAL, rider=_RIDER_SWEEP), "claw_rake": _one(_DIAGONAL),
    "slice_horizontal": _one(_SLICE), "big_arm_swipe": _one(_SLICE),
    "stab": _one(_STAB, upright=_OVERHAND, rider=_LANCE), "punch": _one(_PUNCH, free="stance"),
    "throw": _one(_THROW, free="stance"),
    "shoot_1h": _one(_SHOT, contacts=(3,), lead=3, tail=14, root=0.15), "burst_1h": _one(_SHOT, contacts=(3,), lead=3, tail=14, root=0.15),
    "shoot_2h": {"hands": "two", "keys": _SHOT, "contacts": (3,), "lead": 3, "tail": 14, "root": 0.15},
    "burst_2h": {"hands": "two", "keys": _SHOT, "contacts": (3,), "lead": 3, "tail": 14, "root": 0.15},
    "bow": {"hands": "pair", "keys": _BOW, "upright": _BOW_LOW, "bare": _BOW_HUNG, "off": _DRAW, "contacts": (5,), "lead": 5,
            "tail": 4},
    "bow_up": {"hands": "pair", "keys": _BOW, "upright": _BOW_LOW, "bare": _BOW_LOB, "off": _DRAW, "contacts": (5,), "lead": 5,
               "tail": 4},
    "reverse_slash": _one(_RISING), "fan_gust": _one(_BACKHAND), "staff_point": _one(_POINT),
    "flail_sling": _one(_SLING, lead=5),
    "chop_2h": {"hands": "two", "keys": _CHOP},
    "slice_2h": {"hands": "two", "keys": _SLICE},
    "stab_2h": {"hands": "two", "keys": _STAB, "upright": _OVERHAND, "rider": _LANCE},
    "spin_2h": {"hands": "two", "keys": _SPIN, "tail": 13},
    "hipfire_sweep": {"hands": "two", "keys": _SWEEP, "contacts": (1,), "lead": 1, "tail": 16},
    "dual_chop": {"hands": "dual", "keys": _CHOP},
    "dual_slice": {"hands": "dual", "keys": _DIAGONAL},
    "dual_stab": {"hands": "dual", "keys": _STAB},
    "shield_bash": {"hands": "off", "keys": _BASH, "root": 0.22},      # the body goes in behind the shield
    "kick": {"hands": "none", "keys": []},
    # the staff stays planted at the side and the free hand is thrust at the target, held (a staff brought down
    # from overhead ends where staff_point's jab does: two look-alikes); with nothing held the striking hand pushes
    "cast_shoot": {"hands": "free", "keys": _PUSH},
    "tool_chop": _work((4, 11, 18), _FLAT_CUT),
    "tool_hammer": _work((3, 10, 17)),
    "tool_pickaxe": _work((4, 11, 18), _PICK, "two"),
}
UPRIGHT = -0.5      # cosine of the angle blade / forearm under which a weapon is carried upright


# ---------------------------------------------------------------- which hand
def _still(blade):
    return blade is not None and tuple(blade) == STILL


def _moving(grip):
    """The grip without its STILL arms: they hold nothing and never strike alone."""
    return {s: None if _still(b) else b for s, b in (grip or {}).items()}


def hands(spec, grip):
    """(striking sides, main side) for a grip {side: blade or None}: both for a dual strike,
    else the armed hand (the longer weapon of two), the right when bare unless the grip names the
    left alone (an empty blade: a bare hand that strikes); "off" strikes with the other hand,
    "none" with neither."""
    grip = _moving(grip)
    length = {s: math.sqrt(sum(c * c for c in grip.get(s) or ())) for s in "LR"}
    left = grip.get("L") is not None and grip.get("R") is None
    main = "L" if length["L"] > length["R"] or (left and not length["R"]) else "R"
    other = "L" if main == "R" else "R"
    off = other if length[main] or spec["hands"] != "free" else main        # nothing held: the hand that strikes casts
    return {"dual": ("L", "R"), "pair": (main, other), "off": (other,), "free": (off,), "none": ()}.get(spec["hands"], (main,)), main


def left_handed(spec, grip):
    """True when the strike is the left arm's: the reference's motion, made for the right, is mirrored."""
    sides, main = hands(spec, grip)
    return (sides[0] if spec["hands"] == "free" else main) == "L"


def keys_for(spec, blade, riding=False, second=False):
    """The strike's keys for the blade that strikes: the upright set when it is carried upright, a
    rider's own where the strike has them, the other hand's of a "pair" (a bow's string hand)."""
    if second:
        return spec["off"]
    if riding and "rider" in spec:
        return spec["rider"]
    if not blade:
        return spec.get("bare", spec["keys"])
    return spec["upright"] if "upright" in spec and P.unit(blade)[1] < UPRIGHT else spec["keys"]


def _swap(bone):
    return bone[:-1] + {"L": "R", "R": "L"}[bone[-1]] if bone.endswith((".L", ".R")) else bone


def mirror(pose, bones):
    """The pose's `bones` mirrored left to right: sides swapped, the turns about the bone's own
    axis and its side axis reversed (the families' rest frames are mirror images)."""
    out = dict(pose)
    for bone in bones:
        rx, ry, rz, lift, up = P.pad(pose.get(_swap(bone), ()))
        out[bone] = (rx, -ry, -rz, lift, up)
    return out


# ---------------------------------------------------------------- the body under the strike
def _pitch_range(family, poses, bone):
    """Range in degrees of a bone's pitch (side view) over the poses, with no jump at +-180."""
    angles = []
    for pose in poses:
        head, tail = P.joints(family, pose)[bone]
        a = math.degrees(math.atan2(head[1] - tail[1], tail[2] - head[2]))
        angles.append(a - 360.0 * round((a - angles[-1]) / 360.0) if angles else a)
    return max(angles) - min(angles)


def _toward(value, base, k):
    """A posed bone's turns and lift scaled by k about the clip's first pose `base`."""
    return tuple(b + (v - b) * k for v, b in zip(value[:4], base[:4])) + (value[4],)


def calm(family, poses, legs, torso, root_max=ROOT_MAX):
    """The reference steps and leans into its strikes; ours stand: the root's travel and the legs'
    turns (`legs`: those bones and the root, none when another layer carries the body) are scaled
    together, so the feet stay where they are, to ROOT_MAX body heights; the pitch of the torso
    and of the bone under it to TORSO_MAX degrees of the torso's range. Both are scaled about the
    clip's first pose: a naga's torso stands on a bone that is not upright at rest."""
    lifts = [P.pad(p.get("root", ()))[3] for p in poses]
    travel = max(lifts) - min(lifts)        # the whole range: a strike's clip starts mid-step
    k = min(1.0, root_max * RF.top(family) / travel) if travel > 1e-9 and legs else 1.0
    lean = min(1.0, TORSO_MAX / max(_pitch_range(family, poses, torso), 1e-9)) if torso else 1.0
    parents = RF.parents(family)
    trunk = ([torso] + ([parents[torso]] if torso in parents else [])) if torso else []
    first = {bone: P.pad(poses[0].get(bone, ())) for bone in [*legs, *trunk]}
    out = []
    for pose in poses:
        pose = dict(pose)
        for bone in legs:
            pose[bone] = _toward(P.pad(pose.get(bone, ())), (0.0, 0.0, 0.0, 0.0), k)
        for bone in trunk:
            value = P.pad(pose.get(bone, ()))
            pose[bone] = (first[bone][0] + (value[0] - first[bone][0]) * lean, *value[1:])
        out.append(pose)
    return out


# ---------------------------------------------------------------- the arm
def _world(side, v):
    """(out, forward, up) of a side's arm -> armature axes (x toward .L, y back, z up)."""
    return [v[0] if side == "L" else -v[0], -v[1], v[2]]


def _cone(w, cos_g, sin_g, steps=36):
    """The directions at the grip angle from the unit vector w."""
    u = P.unit(P.cross(w, (0.0, 0.0, 1.0) if abs(w[2]) < 0.9 else (1.0, 0.0, 0.0)))
    v = P.cross(w, u)
    turns = [2 * math.pi * k / steps for k in range(steps)]
    return [[cos_g * w[i] + sin_g * (math.cos(a) * u[i] + math.sin(a) * v[i]) for i in range(3)] for a in turns]


def reach(shoulder, upper, fore, blade, hand, w, prev=None):
    """(upper arm direction, forearm direction) that point the blade along w with the wrist as
    near `hand` as the grip allows: the forearm lies on the cone the grip angle draws around w;
    of those directions the one that leaves the elbow an upper arm's length from the shoulder,
    low, and near the frame before (`prev`: its forearm direction)."""
    cos_g = max(-1.0, min(1.0, P.unit(blade)[1]))
    best = None
    for f in _cone(w, cos_g, math.sqrt(1.0 - cos_g * cos_g)):
        elbow = [hand[i] - fore * f[i] - shoulder[i] for i in range(3)]
        far = math.sqrt(sum(c * c for c in elbow)) or 1e-9
        cost = abs(far - upper) + 0.10 * upper * elbow[2] / far
        if prev is not None:
            cost += 0.15 * upper * math.dist(f, prev)
        if best is None or cost < best[0]:
            best = (cost, [c / far for c in elbow], f)
    return best[1], best[2]


def _limb(family, pose, limb):
    """(shoulder, upper arm length, forearm length, wrist, forearm frame) of a posed (upper, fore)."""
    js = P.joints(family, pose)
    arm, fore = js[limb[0]], js[limb[1]]
    return arm[0], math.dist(*arm), math.dist(*fore), fore[1], P.frames(family, pose)[limb[1]]


def stance(family, pose, limb, blade):
    """A posed arm as a key: (hand from the shoulder in arm lengths, where the blade points),
    both in armature axes."""
    shoulder, upper, fore, wrist, frame = _limb(family, pose, limb)
    b = P.unit(blade or (0.0, 1.0, 0.0))
    return ([(wrist[i] - shoulder[i]) / (upper + fore) for i in range(3)],
            [sum(frame[i][k] * b[k] for k in range(3)) for i in range(3)])


def _softened(rest, hand, weapon, soft):
    """A key `soft` of the way from the stance: a smaller arc for a mesh that tears on the full one."""
    return ([r + (h - r) * soft for r, h in zip(rest[0], hand)], P.unit(P.turn(rest[1], weapon, rest[1], soft)))


def track(spec, keys, contacts, count, rest, side, soft=1.0):
    """[(sample, hand, weapon, is contact)] of a side's arm: the stance, then per contact the
    strike's keys, the stance again. Keys that fall on a taken sample are pushed one later."""
    lead, tail = spec.get("lead", LEAD), spec.get("tail", TAIL)
    out = [(0, *rest, False)]
    for c in contacts:
        strike = [(c + at, *_softened(rest, _world(side, hand), P.unit(_world(side, weapon)), soft), at == 0)
                  for at, hand, weapon in keys]
        for at, *key in [(c - lead, *rest, False), *strike, (c + tail, *rest, False)]:
            out.append((min(max(at, out[-1][0] + 1), count - 1), *key))
    out.append((max(count - 1, out[-1][0] + 1), *rest, False))
    return out


def _swing(a, b, t):
    """The direction a weapon points at, `t` of the way from a to b. A turn wider than WIDE goes
    over the top and the front (through OVER), never the short way through the body or the ground."""
    if sum(p * q for p, q in zip(a, b)) > math.cos(WIDE):
        return P.unit(P.turn(a, b, a, t))
    over = P.unit([p + q + o for p, q, o in zip(a, b, OVER)])
    return _swing(a, over, 2 * t) if t < 0.5 else _swing(over, b, 2 * t - 1)


def at(keys, sample):
    """(hand, weapon) at a sample between the track's keys: eased, accelerating into a contact."""
    b = next((k for k in keys if k[0] >= sample), keys[-1])
    a = next((k for k in reversed(keys) if k[0] <= sample), keys[0])
    if a[0] == b[0]:
        return a[1], a[2]
    t = (sample - a[0]) / (b[0] - a[0])
    t = t * t if b[3] else t * t * (3 - 2 * t)
    return [p + (q - p) * t for p, q in zip(a[1], b[1])], _swing(a[2], b[2], t)


def contact(family, poses, limbs, sides):
    """The sample a retargeted strike lands on: the end of the hands' fastest run (the samples
    around the fastest one that move at half its speed or more)."""
    tips = [[P.joints(family, p)[limbs[s][1]][1] for s in sides or "LR"] for p in poses]
    speed = [0.0] + [max(math.dist(a, b) for a, b in zip(now, then)) for then, now in zip(tips, tips[1:])]
    peak = speed.index(max(speed))
    while peak + 1 < len(speed) and speed[peak + 1] >= 0.5 * max(speed):
        peak += 1
    return peak


def contact_free(family, poses):
    """True when a clip has no forward move of the body to hang a head snap on (it stands still)."""
    lifts = [P.pad(p.get("root", ()))[3] for p in poses]
    return max(lifts) - min(lifts) < 0.02 * RF.top(family)


def _free_arm(family, pose, limb):
    """The arm that does not strike keeps the reference's swing, drawn in from KayKit's open stance."""
    js = P.joints(family, pose)
    out = {}
    for bone, bend in zip(limb, (1.0, NARROW)):
        h, t = js[bone]
        out[bone] = [(t[0] - h[0]) * NARROW, (t[1] - h[1]) * bend, t[2] - h[2]]
    return out


def _second_hand(family, pose, limb, side, main, w):
    """A two-handed grip: the other hand goes to the shaft, below the main hand."""
    shoulder, upper, fore, _, _ = _limb(family, pose, limb)
    grip = _limb(family, pose, main)[3]
    target = [grip[i] - OFF_GRIP * fore * w[i] for i in range(3)]
    bend = [0.5 if side == "L" else -0.5, 0.3, -1.0]
    elbow, end = P.two_bone(shoulder, target, upper, fore, bend)
    return {limb[0]: [elbow[i] - shoulder[i] for i in range(3)], limb[1]: [end[i] - elbow[i] for i in range(3)]}


def _strike_arm(family, pose, limb, blade, key, prev):
    """repose targets of a striking arm for a key (hand, weapon), and its forearm direction."""
    shoulder, upper, fore, _, _ = _limb(family, pose, limb)
    hand, w = key
    b = P.unit(blade or (0.0, 1.0, 0.0))
    target = [shoulder[i] + hand[i] * (upper + fore) for i in range(3)]
    up, f = reach(shoulder, upper, fore, b, target, w, prev)
    return {limb[0]: up, limb[1]: ((b, w), ((0.0, 1.0, 0.0), f))}, f


def _free(family, pose, spec, limbs, side, main, tracks, i, idle):
    """Targets (or posed values) of an arm that does not strike: on the shaft for a two-handed
    grip, standing as in the idle for a beast's foreleg, else the reference's swing drawn in."""
    if spec["hands"] == "two":
        return _second_hand(family, pose, limbs[side], side, limbs[main], at(tracks[main], i)[1])
    if spec["hands"] in ("off", "free") or spec.get("free") == "stance" or not limbs[side][0].endswith(("arm.L", "arm.R")):
        return None             # the weapon arm of a shield bash waits in the stance: the shield is the strike
    return _free_arm(family, pose, limbs[side])


def arms(family, poses, spec, grip, idle, limbs, soft=1.0):
    """(poses with the arms keyed for the strike, contact sample). `poses` are the reference's
    (already mirrored for a left-handed grip), `idle` the stance pose the arms start from and
    return to, `limbs` {side: (upper bone, fore bone)}. Unless the strike names its contacts the
    clip starts LEAD samples before the contact: the game starts a swing when the hit lands, so
    the wind-up is the clip's first frames."""
    still = {s for s, b in (grip or {}).items() if _still(b)}
    grip = _moving(grip)
    sides, main = hands(spec, grip)
    lead = spec.get("lead", LEAD)
    if "contacts" not in spec:
        hit = min(max(contact(family, poses, limbs, sides), lead), len(poses) - 4)
        poses, contacts = poses[hit - lead:], (lead,)
    else:
        contacts = spec["contacts"]
    riding = limbs["R"][0].startswith("rider.")
    held = {s: None if spec["hands"] == "pair" and s != main else grip.get(s) for s in "LR"}
    tracks = {s: track(spec, keys_for(spec, held[s], riding, spec["hands"] == "pair" and s != main), contacts, len(poses),
                       stance(family, idle, limbs[s], held[s]), s, soft) for s in sides}
    out, prev = [], {}
    for i, pose in enumerate(poses):
        for side in sides:
            targets, prev[side] = _strike_arm(family, pose, limbs[side], held[side], at(tracks[side], i),
                                              prev.get(side))
            pose = P.repose(family, pose, targets)
        for side in set("LR") - set(sides):
            free = None if side in still else _free(family, pose, spec, limbs, side, main, tracks, i, idle)
            pose = P.repose(family, pose, free) if free else {**pose, **{b: P.pad(idle.get(b, ())) for b in limbs[side]}}
        out.append(pose)
    return out, contacts[0]
