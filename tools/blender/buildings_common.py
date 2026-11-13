"""Prédios comuns a todas as raças, modelados por script: um GLB por prédio em assets/buildings/common/.

Uso:
    blender -b --factory-startup --python tools/blender/buildings_common.py -- <id|all> [--out DIR] [--render DIR]

Mesmo kit e mesmas regras dos prédios de raça (tools/blender/buildings_human.py): pegada ~3,5 x 3,5, frente em
+x, cor chapada por peça, sem cor de time.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_paths  # noqa: E402
import map_castles as kit
from map_castles import beam, box, cyl, mat, ring


def h008_treasure_box():
    """Cofre de campanha: arca de carvalho cintada de ferro sobre estrado, tampa abaulada entreaberta e o
    ouro à vista, com cadeado de latão, caixa de moedas e uma lanterna."""
    plank = mat("oak", 0x9A7448)
    plank_dk = mat("oak_dark", 0x6A4E30)
    iron = mat("iron", 0x4A5058)
    iron_dk = mat("iron_dark", 0x2E3136)
    brass = mat("brass", 0xDDA338)
    gold = mat("gold", 0xE9BC3A)
    mud = mat("mud", 0x66543F)
    flame = mat("flame", 0xFFC658, emit=3.0)

    box("pad", mud, (0, 0, 0), (3.5, 3.5, 0.1), bevel=0.03)
    box("skid", plank_dk, (0, 0, 0.1), (2.9, 2.5, 0.16), bevel=0.03)
    for y in (-0.9, 0.0, 0.9):
        box("skid_rail", plank_dk, (0, y, 0.1), (3.1, 0.22, 0.24), bevel=0.02)
    # Corpo da arca e as cintas de ferro com rebites.
    box("chest", plank, (0, 0, 0.3), (2.5, 2.0, 1.3), bevel=0.06, taper=0.97, taper_y=0.97)
    for x in (-0.85, 0.0, 0.85):
        box("strap", iron, (x, 0, 0.3), (0.2, 2.06, 1.34), bevel=0.01)
        for z in (0.5, 1.0, 1.45):
            box("rivet", iron_dk, (x, 1.04, z), (0.09, 0.04, 0.09), bevel=0.0)
            box("rivet", iron_dk, (x, -1.04, z), (0.09, 0.04, 0.09), bevel=0.0)
    box("rim", iron, (0, 0, 1.56), (2.56, 2.06, 0.1), bevel=0.02)
    # O ouro: monte de moedas e lingotes passando da borda.
    box("gold_bed", gold, (0, 0, 1.6), (2.2, 1.7, 0.16), bevel=0.04, taper=0.8, taper_y=0.8)
    for i, (x, y, r) in enumerate(((-0.5, 0.3, 0.3), (0.4, -0.3, 0.34), (0.1, 0.5, 0.26), (-0.2, -0.45, 0.24))):
        cyl("coin_pile", gold, (x, y, 1.72), r, 0.12 + 0.05 * (i % 2), sides=8, bevel=0.0)
    for x, y, rz in ((0.7, 0.35, 0.3), (-0.75, -0.15, 1.1)):
        box("ingot", brass, (x, y, 1.74), (0.5, 0.22, 0.14), bevel=0.02, taper=0.8, taper_y=0.7, rot_z=rz)
    # Tampa abaulada em três tábuas, aberta para trás.
    lid_x = -1.2
    for i in range(3):
        # três tábuas em degrau: a tampa abaulada inclinada para trás, sem girar peça (a origem é o mundo)
        box("lid", plank, (lid_x - 0.1 - i * 0.17, 0, 1.62 + i * 0.38), (0.18 + 0.05 * (i == 1), 2.04, 0.42), bevel=0.02)
    for y in (-0.85, 0.0, 0.85):
        beam("lid_strap", iron, (lid_x, y, 1.62), (lid_x - 0.5, y, 2.78), thick=0.12)
    beam("lid_stay", iron_dk, (lid_x + 0.1, 0.98, 1.6), (lid_x - 0.36, 0.98, 2.5), thick=0.05)
    # Fecho e cadeado de latão na frente, alças de ferro nos lados.
    box("hasp", iron_dk, (1.27, 0, 1.0), (0.05, 0.3, 0.5), bevel=0.0)
    box("padlock", brass, (1.33, 0, 0.82), (0.12, 0.34, 0.3), bevel=0.03)
    ring("padlock_bow", iron_dk, (1.33, 0, 1.12), 0.1, 0.05, thick=0.03, sides=8)
    for s in (-1, 1):
        beam("handle", iron_dk, (-0.3, s * 1.06, 0.95), (0.3, s * 1.06, 0.95), thick=0.07)
    # No estrado: caixa de moedas, saco e a lanterna.
    box("cashbox", iron, (1.45, -0.95, 0.26), (0.5, 0.4, 0.3), bevel=0.03)
    box("cashbox_lid", brass, (1.45, -0.95, 0.56), (0.52, 0.42, 0.05), bevel=0.0)
    cyl("sack", mat("sack", 0xB9A27A), (1.4, 0.95, 0.26), 0.26, 0.4, sides=8, top_radius=0.12, bevel=0.0)
    cyl("sack_coin", gold, (1.62, 0.7, 0.26), 0.1, 0.05, sides=8, bevel=0.0)
    box("lantern_post", plank_dk, (-1.5, -1.45, 0.1), (0.07, 0.07, 0.8), bevel=0.0)
    box("lantern", flame, (-1.5, -1.45, 0.9), (0.13, 0.13, 0.16), bevel=0.0)
    box("lantern_cap", brass, (-1.5, -1.45, 1.06), (0.2, 0.2, 0.05), bevel=0.0, taper=0.4, taper_y=0.4)


BUILDINGS = {"h008": h008_treasure_box}


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["all"]
    names = list(BUILDINGS) if args[0] == "all" else [args[0]]
    out_dir = game_paths.out_arg(args, "--out", "buildings", "common")
    render_dir = args[args.index("--render") + 1] if "--render" in args else ""
    for name in names:
        kit.build(name, out_dir, render_dir, make=BUILDINGS[name], views=(("front", -35.0),))


if __name__ == "__main__":
    main()
