# Análise do input externo (2026-10-27) × estado real do pipeline

Input: `2026-10-27-input-externo.md` (3 partes). Fontes do estado: ROADMAP-papers.md, PIPELINE.md §12-13, §18-§21, código em tools/blender.

## A. Já feito (e o que o input assume errado)

| Ponto do input | Onde já está | O que o input erra |
|---|---|---|
| 2A "parar de tratar como caixas" | `box_ceiling` ≤ 1/3 (§18.B2); kinds frustum/prism/dome/cyl/ring; `lathe` (perfil do sheet, squash) e `limb` (2 segmentos + joelho) em `lathe_limb.py` (§21.F2); `cut: sheet` (§19.B4) | n005 massing tem 0/30 boxes. F2 mostrou que trocar kind SEM fit não move IoU (n00U .688→.687): representação sozinha não é o gargalo |
| 2B "reconstruir das 6 vistas" | `fit_spec` F4: (1−IoU)+chamfer em front/left/back/top/bottom/rts (+turntable 3/4), rot ±20°, dims 20 % se ligada, zonas, `cut` decidido no clay real (§21.F4) | "r≈0.998 só prova que o proxy reproduz o render": correto, e já é tratado assim (proxy = ranking; `fit_accepted` só aceita pelo clay real). Falta landmarks no loss |
| 2C top/bottom da aranha | L14 rig medido, F3 `leg_w`, F4: n00U top .653→.707, bottom .618→.675; rts .659 (< .70) | front/back já passam (.783/.790); o resto é rts + top |
| 2D Powell | D1/F4: n00U bate 4000 avaliações/150 s; melhor ponto guardado | Ninguém comparou CMA-ES/hierárquico: novo (B3) |
| 3 divisão de papéis | análise = código (`measure`, `measure_spider`, `outline`, `zone_palette`, `edges`); autor com schema + `[FROZEN]`; fitting determinístico; validação (preflight, silhouette, mesh_lint, engine_import, review_pair) | Já é esta arquitetura. Falta só "diagnóstico LLM" separado (DFS) |
| 4.1 landmarks semânticos | parcial: `zones_clay` por peça (§20.N3), `attach.json`, `spider_leg/body/reach`, `shoulder_span`… | Não há "perna presa na junta certa" medido do sheet (B5) |
| 4.2 RTS primeira classe | gate rts 0.70 desde §14; no objetivo do fit (F4) | — |
| 4.3 aceite de geometria antes da textura | estágio 1/2, `--shape-only`, status placeholder/prototype-safe/final-use | — |
| 4.4 test set | n01X (mech), n005 (humanoide), n00U/n01N (orgânico), hfoo/n02X (prop) | Falta quadrúpede/serpente/voador: 0 runs em 24 das 28 famílias |
| 4.5 custo por modelo | t_gen/t_build/t_colour, passes, asked.json, components, `--stability` | "intervenção manual" é zero por definição no BFS |
| 5 "família orgânica antes de IA" | = F1 massing + F2 lathe/limb. Massing sozinho (sem LLM, sem fit): n01X .847/.843/.846/.795/.735/.778 6/6; n005 .756/.810/.809/.701/.764/.729 6/6; n00U .760/.723/.766/.626/.620/.603 3/6 | O "upgrade procedural" já existe; falta rodá-lo em protocolo (E) |
| P3 não-regressão | `fit_accepted`: vista que passava ≥ gate−FIT_SLIP, soma de margens sobe, `rules_hold`; `accepted()` nos passes | Falta peso por família e piso por região (B4) |
| P3 "cada falha vira experimento" | runs nunca apagados, fit.json, passes.json, history/, provas sem LLM | — |

## B. Válido e novo
1. **Kind `chain`** (sweep ao longo de cadeia de ossos, raio por junta do sheet): `lathe_limb.py` + `PARAMS` do fit. M. Medida: IoU 6 vistas vs prisms por osso; attach loose=0; tris. BFS. Destrava 14 famílias que usam `_chain`.
2. **Kind `plate`/perfil extrudado** (máscara de faixa extrudada com espessura): asas, placas, lagartas, carapaça com overhang. M. BFS.
3. **Fit hierárquico** (tronco → membros/rot/knee → perfis), mesmo Powell, orçamento dividido, vs Powell único. S/M. CMA-ES só se o hierárquico não ganhar (dep nova `cma`).
4. **Piso por vista/região em `fit_accepted`** com peso por família (spider: top/bottom/rts; voador: top). S.
5. **Landmarks de junta do sheet** (joelho/cotovelo; biped/quad) → regra `joint_place` relatório + termo opcional no fit. M.
6. **Massing por família composta** (quad body + chain + plate + rider) via composição de `rig_families`. L. Deps 1, 2, sheets novos.
7. **Baseline cruzado 6-10 unidades** (checklist 0). M, depende de sheets.
8. **Diagnóstico LLM só em CHECK**: é DFS, fica para depois por regra do usuário.

## C. Não vale / conflita
- TRELLIS/Hunyuan como gerador: vetado; como experimento, ver E.
- Loss com landmarks+contorno+IoU como novidade: chamfer já está; landmarks = B5.
- Ellipsoid/superelipsoide como kind: `lathe` com profile+squash já é isso.
- Rendering diferenciável: torch no loop do fit por nada medido (proxy numpy roda em ms).
- Separar geometria de apresentação: já é estágio 1/2.
- Powell → CMA-ES antes do hierárquico: ordem errada.
- Mais regras de preflight: as novas da leva 2-3 ficaram todas em relatório (overlap_80 76 % FAIL, caps uncovered 43 %).

## P2. Quanto as 27 famílias compartilham (`rig_families.FAMILIES`, 28 com `building`)
Seis geradores de ossos: `BIPED`, `_legs(n)`, `QUADRUPED`, `_chain`, `_wings`, `_upper_body`/`_rider`, mais rígidos de 1 osso.

| grupo | famílias |
|---|---|
| bípede | biped, harpy (+wings), walker, crew |
| anel de pernas `_legs(n)` | spider (8), spider_high (8), crawler (4), crustacean (6 + claw/pincer + tail) |
| quadrúpede | quadruped, drake (+neck, tail, wings), mounted, mounted_flyer, centaur (+upper_body), bird |
| cadeia `_chain` | serpent, wyrm (+wings), sled, hydra (3 necks), naga (tail + upper_body), pod (stalk + 3 tendrils) |
| flutuante + upper_body/asas | wraith, shard, ray |
| rígido 1 osso + anexos | vehicle (wheels), tracked, aircraft, building |
| rider | mounted, mounted_flyer, bird_rider |

**Bastam 5 geradores geométricos:** (1) tronco por perfil = `lathe` (existe); (2) membro 2 segmentos = `limb` (existe); (3) cadeia/sweep (novo; 14 famílias); (4) placa/perfil extrudado (novo; asas em 8 famílias, plates, tracks, rudder, carapaça); (5) disco revolvido = `wheel/ring` (existe). É um sistema de superfícies condicionado pela hierarquia, não 27 geradores.

## D. Leva 4 candidata (ordem)
1. L4-1 `chain` → 2. L4-2 `plate` → 3. L4-3 fit hierárquico + pisos por vista (independente de 1-2) → 4. L4-4 sheets + massing de quadruped/serpent/drake (dep 1, 2) → 5. L4-5 baseline 6-10 unidades (dep 4) → 6. L4-6 `joint_place` → 7. L4-7 experimento 3 caminhos (E; dep 3) → 8. DFS: diagnóstico LLM.

**L4-1 `chain`.** `lathe_limb.py` (`chain_rings`, tris, `bad_opts`, `chain_bones`), `build_unit.swept_part`, `preflight.part_tris/bbox/bones`, `spec_pipeline.KINDS/validate/DSL`, `fit_spec.PARAMS["chain"]=("radii",)`, `cut_hull.lathe_profiles` (perfil por osso). Interface: `[bone0, "chain", [r0..rN], at_ignored, mat, {"bones": N, "sides": 6, "profile_axis": "left"}]`: passa pelos ossos `prefix.1..N` (head→tail), raio por junta, anel na junta, tampas; peso anel i no osso i. Prova: serpent sintético (8 ossos) e drake tail (3): attach loose=0, tris = 2·sides·N + 2·(sides−2), IoU 6 vistas vs N prisms (≥ −0.01, tris −30 %).

**L4-2 `plate`.** `[bone, "plate", [w, h, t], at, mat, {"axis": "front|left|top", "profile": ≤ 8 pts (senão lido do sheet como cut), "bevel": 0-0.3}]`: polígono extrudado t. Prova: harpy/drake sintético (wings); n00U carapaça como plate sobre o lathe do abdômen vs v6-r3 F4 (.783/.705/.790/.707/.675/.659): top/bottom +0.02 sem perder front; `uncovered` top/bottom cai.

**L4-3 fit hierárquico.** `fit_spec.fit()` ganha `stages=("trunk","limbs","profiles")`, cada estágio = `free` filtrado, orçamento 1/3; `spec_pipeline.fit_accepted` ganha `VIEW_FLOOR[rig]`. Prova: `fit/before.json` ×3 unidades, tabela antes/F4/hierárquico (IoU 6 vistas no clay real, soma de margens, evals, s); critério: ≥ F4 em margens com ≤ 2/3 das avaliações no n00U.

## E. Experimento 3 caminhos (n00U, mesma sheet, câmeras, gates)

> **Decisão do usuário (2026-10-27): o caminho "IA" não será executado, nem como registro.** Fica só baseline × procedural. O texto abaixo é mantido como registro da avaliação de viabilidade.
| caminho | run | custo |
|---|---|---|
| baseline | `--spec runs/draft/n00U/v6-r1/fit/before.json --no-repair --shape-only --fit` (= F4) | 3 min, $0 |
| procedural | massing (F1) + F4; depois + plate | 3 min, $0 |
| IA | mesh → `silhouette.py --shape <glb>` | abaixo |

Métricas iguais: IoU 6 vistas, uncovered/spill, zones_clay (IA n/a), attach (IA n/a), mesh_lint, pairwise clay×clay (4 votos 2+2). IA não pode passar orçamento (400-700 tris; decimar 50 % já perde forma), rig, materiais.

Viabilidade (M4 Pro 24 GB, torch 2.14 + MPS em python3.14): TripoSR (MIT, segundos-minutos em MPS, 1 vista → top/bottom inventados; piso); TRELLIS.2 (port não oficial `trellis-mac`, ~3,5 min/malha, 24 GB = toda a RAM, 15 GB de pesos, vertex colors; executável serial, máquina saturada); Hunyuan3D 2.1 (shape 10 GB, textura fora; licença Tencent Community com restrições: verificar).

**Veredito:** um experimento de registro (TripoSR + TRELLIS.2, só n00U e n01X, só IoU/uncovered 6 vistas) como teto de "o que uma malha livre tira destas imagens". Se der top/bottom < .707/.675 do F4, "a representação é o gargalo" perde força; se > .80, o alvo é atingível e aponta para chain/plate. Nada entra no fluxo. Prioridade abaixo de L4-1..L4-3.

Fontes: TRELLIS.2 no Apple Silicon (lilting.ch), trellis-mac (HN), Hunyuan3D-2.1 Space README, hunyuan3d-2.1-mac, TripoSR CoreML.
