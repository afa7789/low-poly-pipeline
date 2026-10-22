# Reference animations

`tools/blender/ref_capture.py` records these models' clips as joint positions
(`<model>/joints.json`); `rig_retarget.py` transfers them onto our rig families. The motion
in a unit built from them is an adaptation of the clip, so each source's license applies.

| model | source | license | used for |
|---|---|---|---|
| `hfoo` | KayKit Character Pack: Adventurers (Knight), Kay Lousberg | CC0-1.0 | biped, the rider of every mounted family, naga/centaur/wraith upper bodies, ghoul forelegs |
| `u005` | KayKit Character Pack: Skeletons (Skeleton Mage), Kay Lousberg | CC0-1.0 | captured, not used yet (Spellcast_Summon, Taunt) |
| `e006` | Quaternius animal (poly.pizza) | CC0-1.0 | quadruped, mounts, centaur body, drake body |
| `n017` | Quaternius wolf (poly.pizza) | CC0-1.0 | quadruped and drake bite |
| `n00U` | Quaternius spider (poly.pizza) | CC0-1.0 | spider, crustacean |
| `n01N` | "Spider animated character" by TheGameAssets, https://sketchfab.com/3d-models/746f5c5173ce4f47ad0970b62ee4106e | **CC-BY-4.0**: credit TheGameAssets | spider `rear_strike`, `lunge` |
| `h009` | Quaternius dragon (poly.pizza) | CC0-1.0 | wings of drake/harpy/wyrm, bird and bird_rider bodies, ray, shard |
| `o009` | "Wyvern" by clintbellanger, https://sketchfab.com/3d-models/3f11883f300842878e46b22fce554e81 | **CC-BY-SA-4.0**: credit, and an adaptation must stay CC-BY-SA | only the optional `wyvern_*` motions; no default uses it |
| `n00H` | Quaternius snake (poly.pizza) | CC0-1.0 | serpent, sled, wyrm, hydra body, naga tail |
| `n01P` | Quaternius apatosaurus (poly.pizza) | CC0-1.0 | hydra necks |
| `cr_rat` | Rat by Quaternius, https://poly.pizza/m/iltq5bVNaV | CC0-1.0 | crawler |
| `h097` | Quaternius robot (poly.pizza) | CC0-1.0 | walker |

Hand-keyed (no reference): the machines (vehicle, tracked, aircraft, crew), the pod, and the
`keyed_*` motions of biped, quadruped and spider.
