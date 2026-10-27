# Auditoria (2026-10-28): papers × pipeline × "massas disformes" (v8/v9) — somente leitura

Pergunta do usuário: "as unidades parecem massas disformes; as mudanças dos papers foram aplicadas corretamente?"
Resposta curta: **não como método**. Dos 4 papers de forma (Sano, Chen, Wiersma, Sketch2Mesh), nenhum entrou como
o método do paper; entraram como medida, gate ou botão de caixa. Le/Begemann/Zhao entraram fiéis (textura opt-in e
protocolo), ULIP foi negativo, MeshGPT/EdgeRunner só métricas (exigem treino).

## A. Leitura visual (v8 → v9): v9 não muda a classe de forma do v8; mudou onde cada caixa está
1. Tronco/pelve em fatias com degraus (n005 top/bottom: retângulos concêntricos; n02X: torre de lajes; hfoo: pelve bloco).
   Causa: `massing._frustum_stack` — anéis vizinhos não compartilham largura, fatia < THIN vira laje, 4 lados; `_slab` na aranha.
2. Props fundidos/afogados (vaporizador dentro do antebraço, tanque enterrado, pique "sempre inclinado pra frente").
   Causa: `build_unit.main` default `join` (25 componentes interpenetrados; `union` opt-in), `block_part`, `prop_clearance` só relatório.
3. Botas e punhos = tambores octogonais em bloco (`leg_side` FOOT_FIT/BOOT_FIT, `arm_side` mão cúbica).
4. Cabeça/máscara sem leitura: balde revolvido (`box_profile` inclui pescoço; `lathe_rings` é revolução pura com squash; capuz que avança em z não existe; olhos só decal).
5. Aranha em patamares (`_slab` DOME_AT × 8 slabs), pernas tubos retos (`LIMB_KNEE=False`), assimetria do vaporizador.

## B. Paper × prescrição × implementado × fidelidade
| Paper | O que o paper faz | O que entrou | Fidelidade |
|---|---|---|---|
| Chen 2023 | iso-surface offset → malha manifold limpa → QEM + mesh flow + alinhamento de features (Hausdorff ≤ d) | `mesh_lint` (relatório), SD mean, `toldec` opt-in | só métrica |
| Sano 2025 | silhuetas 3 projeções → DP → regularização (paralelo/ortogonal/arcos) → Delaunay → varredura → **interseção dos 3 prismas** → QEM | `outline` no brief, `cut: sheet` opt-in (2 vistas, 8 vértices, rejeitado pelo fit no n005 v9), massing lê largura 1-D por faixa | proxy fraco |
| Sketch2Mesh 2021 | deforma malha contínua por Chamfer 2D de contornos externos; congela longe do traço | `chamfer` (sinal), `fit_spec` Powell em dims/at/rot de caixas, proxy casco convexo; no n005 v9 o fit nem rodou | proxy fraco |
| Wiersma 2026 | otimiza vértices + cores com orçamento fixo, line search anti-inversão, fairness | symmetry, penalidades no fit, sliver no lint (relatório; 15,9 % vs 1,4 % no paper) | só métrica |
| MeshGPT / EdgeRunner | geração de triângulos de artista (treino) | compacidade, normalise, variants, budget_split | só métrica/protocolo |
| Le 2026 | rampa de gradiente | `ramp` opt-in | fiel (não afeta forma) |
| ULIP | CLIP juiz | `clip_score` fora do fluxo | negativo |
| Begemann / Zhao | prontidão, K variantes, juízes | Readiness, status, engine_import, best_of_n, score | fiel (protocolo) |

## C. De onde vêm as massas disformes, por impacto
1. **Representação** (`_frustum_stack`/`_slab`, caixas por faixa): o resultado final é visualmente o massing; trocas de visual (octógono, lathe no tronco, joelho medido) foram vetadas por décimos de IoU/spill.
2. **Gates que medem máscara, não forma**: IoU/uncovered/spill/zonas são 2-D; nada mede continuidade de normal/curvatura (Chen "normal difference", Wiersma fairness); `edge_chamfer`, slivers, componentes só relatório.
3. **Join sem união nem limpeza**: 25 cascas se atravessando lê como "massa"; `union`/`fuse`/`toldec` existem, opt-in.
4. **Autor editando**: n005 v9 7/20 peças editadas, tris 592→716; few-shot com n01X (mech) → viés de caixa.
5. **Fit**: só infla/desinfla caixas ±10 % com casco convexo; não cria forma.
6. Outros: pique forçado pra frente, `box_profile` com pescoço, painel que fatiava a arma (corrigido em 23.Y).

## O que seria "aplicar o paper de verdade" (sem GPU/treino)
| Paper | Faria | Custo |
|---|---|---|
| Sano | hull visual **por parte semântica** (box3d de parts.json), front∩left∩top, contorno regularizado (DP 12-16 v + snap + arcos), QEM até o orçamento; default para tronco/capuz/carapaça/saia | M |
| Chen | união das peças como high-poly: remesh (`fuse`) → QEM com Hausdorff ≤ H/32 (`toldec`) → sharp por ângulo; falta alinhamento de features | S-M |
| Sketch2Mesh | deformação Laplaciana/ARAP da malha unida: vértices do contorno externo vão ao contorno do sheet, interior segue, só na banda que falha | M |
| Wiersma | otimizar vértices de uma malha de topologia fixa (~600 tris) contra silhuetas + chamfer + fairness | L (lento sem rasterizador diferenciável) |

## D. Três ações que mudam o visual (não métricas)
1. Tronco/pelve/carapaça como **uma superfície contínua com anéis compartilhados**: `_frustum_stack`/`_slab` emitem um `lathe` com perfil por anel `[w, d, zc]` (anel elíptico com centro z por anel em `lathe_rings`), 8 lados. Julgar no wire do compare, não no spill de bottom.
2. **`union` + `clean_mesh` + `toldec` (H/32) por default para o corpo**; props ficam componentes próprios. Meta: componentes 25 → 1 + props, slivers < 5 %, IoU ±0.01.
3. **Hull visual (Sano) por default** para capuz/torso/pelve a partir de `parts.json`: `cut_hull.LIMIT` 8→14, soma a vista top, por parte; `fit_accepted` deixa de vetar `cut` pelo vermelho médio.
