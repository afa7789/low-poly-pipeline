# Melee units whose props name a ranged weapon

Range from `data/compendium.json` (`stats.range`, null = melee).

| race | id | name | tier | range | prop words |
|---|---|---|---|---|---|
| Human | `hfoo` | Footman | Q | 90 | gunner, rifle, sniper |
| Mech | `z003` | Flamegunner Sergeant | R | 70 | flamethrower |
| Mech | `h06U` | Mine Layer | W | 100 | carbine |
| Naga | `n002` | Naga Guardian | R | 128 | harpoon |
| Pandaren Empire | `n03G` | Ironpaw Militia | W | 60 | rifle |

Totals: 162 units, 72 melee, 90 ranged. 5 melee units carry a ranged weapon word.
Reverse check: 64 ranged units name no ranged weapon in the props line — these use claws, jaws, spit, gas or flame and need a manual read.
