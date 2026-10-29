# Roadmap — mudanças do pipeline tiradas dos papers (2026-10-27)

**Estado (2026-10-27, fim do dia):** os 14 itens estão integrados (PIPELINE §19). Ligados por default: A1, A2, A3, B1, B2, E1. Opt-in: B3 (`clean`), B4 (`cut: sheet`), C1 (`ramp=`), C2 (`--ramp`, `--space oklab`), D1 (`--fit`), D2 (`--variants N`). Relatório sem gate: B5 (`HULL_BLOCKING=False`). Fora do fluxo: E2 (`clip_score.py`). Resultado da bateria v5 em §19 e `history/2026-10-27-v5/`.

Fonte: 10 PDFs em `~/Desktop/genAI/` (`MANIFEST.md`, `references.bib`). Cada item cita o paper
e o lugar do pipeline. Ordem = ordem de desenvolvimento (fundação → forma → cor → refino → protocolo).
Regra do projeto: nada de treinar redes, nada de gerador image-to-3D como produto; DSL + Blender + gates.
Tudo que vira número entra em `review.md`; só vira gate depois de calibrado nos runs existentes
(`runs/draft/*/{hard-v1,v2-hard-r*,v3-stages-r*,v4-oneshot-r1}`).

## Fase A — medir a malha e o contorno (sem LLM)

### A1 `mesh_lint.py` + bloco "Readiness" no review
Papers: Chen 2023 (Tab. 3: manifold/watertight/self-int), Wiersma 2026 (sliver <10°, fairness),
Begemann & Hutson 2026 (matriz técnica, 4 status), MeshGPT 2024 (compacidade |V|/|F|, área de face),
EdgeRunner 2024 (orientação de face, degeneradas, componentes; watertight NÃO exigir).
- Novo `tools/blender/mesh_lint.py`: lê o GLB em numpy puro (JSON+BIN; `check_gates.stats` já parseia) e devolve dict:
  `verts, faces, tris, nodes, meshes, skins, face_area{median,p90,max_over_median}, sliver_pct (menor ângulo <10°),
  degenerate (área ~0), flipped (normal do accessor vs normal geométrica, dot<0), boundary_edges, nonmanifold_edges,
  components, uv_out_of_range, uv_overlap_pct (raster 1024², excluir célula de decal), atlas_used_pct,
  texel{min,max,ratio}, materials, images, image_size, unique_colours, pivot{min_y, height}, root_scale`.
- `check_gates.py` imprime as colunas novas; `spec_pipeline.write_review` ganha `## Readiness` (tabela critério|valor|gate)
  e `status: placeholder | prototype-safe | final-use | rejected` (SHAPE-PASS→prototype-safe; PASS+lint ok→final-use;
  CHECK com front < gate−0.10→rejected; outro CHECK→placeholder).
- Gates ligados já (óbvios): `flipped == 0`, `uv_out_of_range == 0`, `images == 1`, `image_size ≤ 512`, `|min_y| ≤ 0.01 H`,
  `root_scale == 1`. O resto só reporta até calibrar.
- Prova: rodar nos GLBs dos runs commitados e anexar tabela no PIPELINE §19.A.

### A2 Chamfer 2D de contorno por vista
Papers: Sketch2Mesh 2021 (Eq. 5, Chamfer bidirecional entre contornos externos), Chen 2023 (SD média multi-vista).
- `silhouette.py`: `chamfer(mask_a, mask_b)` com `scipy.ndimage.distance_transform_edt` sobre pixels de borda;
  normalizado por H (px). Coluna `chamfer` em `silhouette.json`, linha "SD mean" (média das 6 vistas) no review
  e rodapé do `make_compare.py`. Não é gate.
- Prova: correlação chamfer × veredito nas runs existentes (n00U/n005 separam melhor que IoU?). Registrar resultado.

### A3 Compare profissional v2 + eixos de avaliação
Papers: MeshGPT (user study forma × triangulação), EdgeRunner (Input Consistency / Triangle Aesthetic / Overall 1-5),
Begemann (asset-readiness report com UV screenshot).
- `make_compare.py`/`compare_runs.py`: coluna `wire` (clay + arestas, render Blender `wireframe` overlay) e coluna `uv`
  (atlas com triângulos UV desenhados em PIL, sobreposição em vermelho). Header mostra `verdict` e `status`.
- `review.md`: cabeçalho "Avaliação" com 3 eixos 1-5 (consistência com o sheet, estética da triangulação, qualidade geral),
  preenchido pelo reviewer de visão quando existir; vazio caso contrário.
- Depende de A1 (status) e A2 (chamfer no rodapé).

## Fase B — forma no one-shot (brief, preflight, build)

### B1 Contorno simplificado do sheet no brief
Paper: Sano 2026 (§3.3-3.4: morfologia → contorno → Douglas-Peucker → regularização).
- `silhouette.measure()` devolve polígono exterior por vista (front/left/back) com DP ε≈0.012 H (12-24 vértices),
  snap de segmentos quase verticais/horizontais; `measured_text` injeta como lista `(x/H, y/H)` por vista no brief
  ("the outline you must fill"). Sem dependências novas.
- Prova: brief do n005 mostra o A-pose dos braços e a lanterna como vértices; teste unitário do DP.

### B2 Orçamento por região, simetria, grade e ordem
Papers: EdgeRunner (bucket de faces por região), Wiersma (simetria como restrição dura), MeshGPT (coordenadas discretas,
ordenação canônica), EdgeRunner (quantização ≥ 1/256).
- Brief/DSL: tabela "tris por grupo de ossos" (torso+pelvis, cabeça, braços, pernas, props) com faixa ±25 % derivada da área
  da banda no sheet; `preflight` regra `budget_split`.
- `preflight` regra `symmetry`: pares `.L/.R` com mesmos `dims` e `rot` espelhado (tolerância 5 %); exceção explícita
  `opts.asym: true` para arma/escudo.
- `preflight.normalise`: snap de `at/dims/from/to` a H/256; ordenar `parts` pela ordem do rig e y; pares simétricos adjacentes.
- Prova: 22 specs existentes: taxa de FAIL antes/depois em overlap/floating; n01X hard-v1 continua 17/17.

### B3 Limpeza da malha no join padrão
Paper: MeshGPT (pré-processo: merge de vértices + decimação planar).
- `build_unit.main` depois do `join`: `remove_doubles` (1 mm) + DECIMATE DISSOLVE 6° (já existe no ramo `union`), antes de `soften`.
- Prova: n01X hard-v1 e n005 v4: IoU das 6 vistas inalterado (±0.005), tris caem; registrar quanto.

### B4 Peça cortada pela silhueta (kind `hull`)
Paper: Sano 2026 (§3.5: extrude contorno front ∩ extrude contorno left = visual hull).
- DSL: `opts {"cut": "sheet"}` em box/prism/frustum (ou kind `hull`): o builder pega a faixa `[y0,y1]` da peça nas máscaras
  front e left do sheet aprovado, simplifica cada uma a ≤ 8 vértices, extrude, `BOOLEAN INTERSECT` EXACT, encaixa no bbox.
  `preflight.part_tris/bbox` tratam como prisma de n lados. Brief explica quando usar (torso, pelvis, capuz, carapaça).
- Prova: n005 torso+capuz com `cut` → IoU front sobe sem passes; tris dentro do orçamento.

### B5 Regra `outside_hull` no preflight
Paper: Sano 2026 (visual hull como volume válido).
- Voxelizar `front ⊗ left` (64³, numpy) do sheet aprovado; por peça, fração do bbox rotacionado fora do hull; FAIL se > 25 %.
  Linha REPAIR nomeia a peça. Fecha o "closed-loop part-box gate" de §13.3 sem renderizar.
- Prova: 22 specs: a regra pega as migrações de massa conhecidas (torso 2× largo com IoU igual) e não falha n01X hard-v1.

## Fase C — textura

### C1 Rampa contínua no cel, nearest, altura, chanfro
Paper: Le 2026 (gradient texturing: rampa vertical escuro→claro, ilha esticada, chanfro no topo, point filter).
- `surfaces.paint_cel`: cada célula de tom vira rampa vertical; `build_unit.atlas_uvs` (ramo cel) amostra
  v = 0.6·(0.5+0.5·nz) + 0.4·altura relativa na peça (centro da face: fica chapada, ink line mantida).
- Faces de chanfro (`chamfer_cube`, normal com 3 componentes > 0.3) → topo da rampa.
- `bind_atlas`: `interpolation="Closest"` (exportado no sampler glTF); margem de célula pode cair de 4 % para 2 %.
- Prova: n01X hard-v1 e n005 rebuild com `--texture cel`: luma por vista ≥ atual (§18.H), zone mean não cai; compare lado a lado.

### C2 Rampa medida do sheet + luma por zona + Oklab
Papers: Le 2026 (rampa da arte), Wiersma (paleta em Oklab).
- `silhouette.zone_palette` devolve `(lo, hi)` = p10/p90 de luma dos pixels da zona no sheet; `colour_stage` passa `ramp`
  por slot; validador aceita o campo.
- Métrica nova: L1 entre quantis de luma render × sheet por zona, medida antes de `match_luma`; linha no review.
- `zone_feature`: Oklab real (3 linhas numpy) em vez do r-g/yb/0.35·luma caseiro. Manter o antigo se a variância do zone mean
  nos runs r2 não melhorar (registrar).

## Fase D — refino numérico (sem LLM, sem visão)

### D1 `fit_spec.py`: ajustar dims/at contra a silhueta
Papers: Sketch2Mesh (refinar parâmetros com Chamfer 2D de contorno; Eq. 6 só mexe perto da região que falha),
Wiersma (regularizadores como restrição dura), MeshGPT (completion = congelar o que está bom).
- Proxy raster (numpy, ms): bbox rotacionado de cada peça projetado em front/left/back (elipse para cyl/dome/wheel),
  normalizado como `silhouette.normalize`. Objetivo: Chamfer + (1−IoU) por vista. Otimizador `scipy.optimize` Nelder-Mead/Powell
  em dims ±20 %, at ±0.05 H, só nas peças que tocam a faixa que falha; regras do preflight como penalidade dura (`rules_hold`).
- Chamado em `spec_pipeline` antes do primeiro build Blender; aceito só se no clay real nenhuma vista que passava cai.
- Prova: validar proxy × render Blender (correlação ≥ 0.9 nas 22 specs); IoU antes/depois nos 3 de teste.

### D2 Melhor-de-N no estágio 1
Papers: EdgeRunner (Fig. 15: variância por seed), Zhao 2026 (K variantes + curadoria), Begemann (curadoria automática).
- `--variants N` (default 1): N specs em paralelo, preflight + clay + silhueta em cada, escolhe pela soma das margens sobre
  os gates; os perdedores ficam em `variants/` (nunca apagar). `review.md` lista as N margens.
- Prova: n005 e n00U com N=3, uma rodada, vs v4-oneshot-r1.

## Fase E — protocolo de avaliação

### E1 Tempos e score ponderado
Papers: Begemann (geração / integração / prontidão separados), Zhao (30 % tempo / 70 % qualidade, juízes cegos).
- `review.md`: `t_gen` (LLM+preflight), `t_build` (Blender+render+silhueta), `t_colour`, passes; `compare_runs.py` soma e
  mostra `score = 0.3·f(t) + 0.7·g(IoU médio, zonas)` para ranking entre autores/configurações.

### E2 CLIP render × concept (experimento, não gate)
Paper: ULIP 2023 (CLIP como juiz cross-modal; ensemble multi-vista; templates de texto).
- `tools/blender/clip_score.py` com `open_clip` ViT-B/32 em CPU (torch já instalado): cosine render×painel, render×texto da
  card, top-k zero-shot entre o roster; reportar sempre pos − neg (negativo = concept de outra unidade).
- Só entra no review se correlacionar com as notas humanas das runs existentes; caso contrário registrar resultado negativo
  no PIPELINE e deixar o script fora do fluxo.

## Fora (e por quê)
- MC33/iso-surface, mesh flow 3D (Chen): precisam de high-poly de entrada. Casca única: já rejeitada (§11).
- SDS/difusão, treino de MeshGPT/EdgeRunner/ULIP/MeshSDF: GPU e treino, vetados.
- Meshy/Tripo/Hunyuan como gerador; decimação como otimização final (Begemann Fig. 4 confirma).
- Faces escondidas por render-ID (MeshGPT-3), massing de edifícios por hull (Sano/Gao 2022), atlas 1 px partilhado (Le):
  válidos, ficam para depois.

## Registro
- `docs/references.md`: seção "Modelos 3D por IA (pipeline de specs)" com as 10 linhas.
- `PIPELINE.md` §19 com subseções 19.A1…19.E2 (uma por item, com a medida antes/depois).
- `~/Developer/arthur/IA_gen_paper/melhorias/`: uma ficha por fase.

---

# Leva 2 (2026-10-27, tarde) — o que ficou de fora + o que a bateria v5 ensinou

**Estado (2026-10-27, noite):** os 20 itens estão integrados (PIPELINE §20). Ligados por default: N1 (`attach.json`, `overlap_80` relatório), N2 (fit com âncora), **S2 (`--fit` default, `--no-fit` desliga)**, S1 (schema + reenvio), S3/M11 (REFINE/REPAIR com `[FROZEN]`), E15 (facetas no brief, edge chamfer no review), S5/S7/S6 (estabilidade, KB/texel, engine import), M8 (tris visíveis, relatório), N3 (`zones_clay`, relatório), L14 (rig spider medido do sheet). Opt-in: M8 `--cull`, M10 `--decimate`, M12 `toldec`, L13 `--hull`, S4/N5 `--pair`, N4 `sheet-ortho.jpg`. Negativos registrados: M9 saliência no `budget_split` (45/49 FAIL), M12 (perde forma), N4 (modelo de imagem não faz planta ortográfica), viés de posição no review pareado (detectado, vira empate).

Regras iguais às da leva 1: medir antes de gatear (regra nova nasce como relatório), opt-in quando não houver ganho medido, nunca apagar runs, sem trailer no commit.

## Onda 1
- **N1+N2 conexão na malha e fit com âncora.** `preflight.overlap` passa a testar as caixas reduzidas a 80 % (caixa que só encosta no canto não conta); `build_unit` confere com BVH (`mathutils.bvhtree`) que cada peça cruza a malha do pai e grava `attach.json` (peças soltas); `fit_spec`: limites 10 % em dims / 0.03 H em `at`, torso/pelvis/capuz não crescem em x/z, ligação com o pai como restrição dura (caixa 80 % continua cruzando). Prova: n00U v5-fit-r2 e n005 v5-fit-r3 reconstruídos: zero peça solta no `attach.json`, IoU não cai mais que 0.03.
- **S1+S3+M11 autor com schema, repair parcial, bandas congeladas.** `ask()`: `response_schema` (Gemini) e tool com JSON schema (`claude -p`), medido por taxa de spec malformado; REFINE/REPAIR: a lista de peças editáveis é só a que toca a faixa (banda de altura) onde a silhueta falha ou a regra reclama; o resto vai como "frozen" e `apply_patch` rejeita edição fora da lista.
- **E15+M9 arestas do hard sheet e orçamento por saliência.** `silhouette.edges(hard)`: Sobel/Laplaciano sobre luma, menos a borda da máscara dilatada = arestas internas; por faixa de altura: contagem e direção dominante → `measured_text` ("torso: 6 facetas verticais"); `budget_split` usa 50 % área + 50 % saliência (densidade de arestas) no lugar do prior fixo; medida nova no review: Chamfer entre `edges(hard)` e o `wire-<view>.png` do clay ("facetou onde o desenho faceta").
- **S5+S7+S6+M10 medidas de protocolo.** `compare_runs.py --stability`: Chamfer 3D (pontos amostrados do GLB) e |ΔIoU| entre runs iguais; review: KB do atlas, texel/altura; `engine_import`: carregar o GLB no loader do jogo headless (achar o entry point em `src/`; se precisar de binário, `make` o alvo de teste) e reportar ok/erro no Readiness; `mesh_lint --decimate`: decimar 50 % (Blender) e remedir IoU → "IoU perdido por 100 tris".
- **M8+M12 faces escondidas e decimate com tolerância de tela.** `build_unit ... cull`: render-ID em 12 vistas, apagar faces nunca vistas, medir "tris visíveis/total" (relatório sempre; remoção opt-in); no ramo `union`: collapse iterativo parando quando a distância máxima à malha pré-decimate passa de `d = H/32` (BVH find_nearest amostrado).
- **N3 gate de zonas no estágio 1.** Render "ID" do clay com uma cor chapada por material (`render_silhouette` com `--ids`), comparar com as zonas de cor do sheet (`silhouette.zone_*`) em front/left/back; relatório no estágio 1 (`zones_clay`), gate só depois de calibrar nos runs v5.

## Onda 2
- **S2** `--fit` default (depois de N1+N2); `--no-fit` para desligar.
- **S4+N5 review pareado de visão como gate.** `review_pair.py`: duas runs (ou run × run anterior) lado a lado, mesma vista; o reviewer (session:opus com Read de imagem) responde "A ou B" em 2 eixos (parece o sheet; parece feito por artista) com 1 frase cada; 3 repetições, maioria; gravado em `review.md` ("pairwise vs <run>: A 2-1 / B 3-0"). Gate: uma run nova só substitui a anterior se vencer ou empatar.
- **N4 sheets top/bottom ortográficos.** Prompt dos 5 painéis com "câmera exatamente acima/abaixo, projeção ortográfica, sem perspectiva, sem inclinação"; regenerar só top/bottom das 3 unidades de teste (nano banana, API), guardar os antigos em `refs/<id>/old/`; medir o tilt que `silhouette` escolhe antes/depois (meta 0 ± 5°).
- **L13 massing de edifícios por hull.** `building_hull.py`: volume base = extrude(front) ∩ extrude(left) regularizado (Sano §3.4: DP, ortogonalidade), QEM até o orçamento; o LLM recebe o volume pronto e só coloca props/telhado. Prova em 2 edifícios com sheet.
- **L14 rig spider medido do sheet.** `silhouette.measure` para spider: comprimento de perna, raio do corpo, altura do joelho; `rig_families.spider`/`spider_high` escalados por esses números em vez de fixos; prova no n00U (front/back ≥ 0.65 é a meta).

## Onda 3
- Bateria v6 nas 3 unidades (one-shot com tudo ligado), compares em `history/2026-10-27-v6/`, §20 no PIPELINE, ficha 02 no IA_gen_paper.

---

# Leva 3 (2026-10-27, noite) — acoplamento apertado: o autor edita, não inventa

**Estado (2026-10-27, madrugada):** F1-F7 integrados (PIPELINE §21), bateria v7 (+ v7-r2 com o vermelho decidindo) e generalidade em n02X (PASS) e hfoo (CHECK). Defaults: massing ligado (4 fatias), fit largo, variants 3, few-shot, vermelho em margem/fit/status. Opt-in: `LATHE_MASSING`, `LEG_GROW`, `--fit-edges`, `--fit-fast`, turntable (só n01X coerente).

Diagnóstico do v6: as áreas vermelhas (sheet sem modelo) e verdes (modelo fora do sheet) ainda são grandes porque
(1) o autor escreve a massa do zero, (2) caixa/prisma não fazem capuz, manga, abdômen, (3) o fit é estreito
(3 vistas, dims/at ±10 %), (4) só medimos IoU, não "quanto sobrou vermelho". Ordem nova do pipeline:

```
sheet (front/left/back + top/bottom + turntable 8 vistas)
  → medidas (silhouette.measure, measure_spider, leg_w, perfis de largura por faixa)
  → MASSING determinístico: pré-spec com lathe/limb/box por osso, direto das silhuetas   [novo estágio 0]
  → autor EDITA o pré-spec (props, materiais, decals, ajustes pequenos; few-shot no brief; --variants 3)
  → preflight → fit largo (8 vistas, rot, top/bottom/rts, zonas, cut)  → gates: IoU + uncovered + spill
  → cor (inalterado)
```

## Frentes (uma leva, em paralelo)
- **F1 massing (`massing.py`, estágio 0).** Do perfil de largura do sheet por faixa (front e left) e do rig: um pré-spec
  com uma peça por osso — bípede: cabeça (lathe), torso (lathe ou frustum), pelvis, braços/coxas/canelas (limb), pés
  (frustum); aranha: corpo/abdômen (lathe), cabeça, 8 pernas (limb com joelho, raio = leg_w). Materiais = slots da
  paleta do sheet (`zone_palette`) pela zona dominante da faixa. O brief passa a ter o pré-spec em JSON e o modo
  "EDIT: keep every part unless the sheet says otherwise; add props, decals, materials; ≤ 8 changes". `--no-massing`
  volta ao brief antigo. Prova sem LLM: só o pré-spec, nas 3 unidades, IoU 6 vistas (meta: ≥ v6 só com o massing).
- **F2 kinds `lathe` e `limb`.** `lathe`: revolve o perfil de largura da faixa `[y0,y1]` do sheet (front ou left, o
  autor escolhe `axis`) em volta do eixo do osso, N lados (6-8), opcional `squash` (razão x/z vinda do top); 40-80 tris.
  `limb`: dois segmentos afunilados (upper/lower) de `from` ao `to` com `knee` (fração e deslocamento) e raios dos
  contornos; substitui "dois cilindros". Em `build_unit`, `preflight` (tris, bbox), DSL text, `fit_spec` (parâmetros
  contínuos: raios, knee, squash), `cut_hull` ignora. Prova: n005 capuz+torso em lathe, n00U abdômen lathe + pernas
  limb, IoU antes/depois.
- **F3 `leg_w` da aranha.** `measure_spider` ganha espessura de perna (mediana da largura das pernas no front/top);
  rig/brief/preflight (`spider_leg_w` relatório); massing usa. Prova: n00U front/back.
- **F4 fit largo.** `fit_spec`: parâmetros `rot` (±20°) para braços/pernas/capuz; top/bottom/rts no objetivo (proxy
  com projeção inclinada pela tilt do run); dims até 20 % quando a peça está ligada ao pai (attach); termo de zonas
  (`zones_clay`: peça do material X dentro da cor X); `cut: sheet` decidido pelo fit para torso/pelvis/capuz; usa as
  vistas do turntable quando existirem (F6). Prova: v6 specs refitados, 6 vistas + uncovered/spill.
- **F5 few-shot + variants.** Brief com 1-2 pares spec→render aprovados (n01X hard-v1; e o melhor da mesma família);
  `--variants 3` default (`--variants 1` desliga). Prova: 1 run n005.
- **F6 turntable 8 vistas.** `redo_turntable.py` (nano banana, 1 chamada por unidade de teste): sheet-turn.jpg com 8
  painéis a 45°, mesma figura, mesma escala, linha de chão. Teste de coerência (altura/largura ±10 %, front×back
  espelhados) antes de usar; `silhouette` ganha varredura de azimute (±20°) como tem de tilt; vistas 3/4 entram como
  relatório no review e como vistas extras no fit (F4). Se incoerente: registrar negativo, manter 3+2.
- **F7 acoplamento apertado (métricas e gates).** `silhouette`: por vista, `uncovered` (vermelho / área do sheet) e
  `spill` (verde / área do modelo), por faixa de altura também (onde está o vermelho); review, compare (rodapé e
  overlay com os números), `compare_runs`. Calibrar nos runs v4-v6 e propor gates (`UNCOVERED_MAX`, `SPILL_MAX`,
  relatório até calibrar). `edge_chamfer` entra como termo opcional do fit.

## Onda final
- Bateria v7 nas 3 unidades (massing + autor edita + fit largo + variants 3), compares `history/2026-10-27-v7/`,
  §21 no PIPELINE, ficha 03.

---

# Leva 4 (candidata, 2026-10-27) — de `analysis/2026-10-27-input-externo-analise.md`

**Estado (2026-10-28):** onda 1 integrada (PIPELINE §22): L4-1 `chain` (8 lados), L4-2 `plate` (opt-in; neutro na aranha), L4-3 fit hierárquico (negativo, opt-in) + `VIEW_FLOOR` ligado, L4-6 `joint_place` (relatório; massing/fit com junta opt-in), L4-4a sheets n017/n00H/n010, L4-8 diagnóstico LLM como saída (`--diagnose`, default nos CHECK), L4-9 orientação do top/bottom detectada pelo modelo. Gate de acoplamento ligado. Bateria v8-r1 em `history/2026-10-28-v8/`: 1/5 PASS com o gate novo (n005 e n02X caem por 1-2 pontos de uncovered/spill no left). Em curso: L4-4b massing/medidas de quadruped/wyrm/drake. Depois: L4-5 baseline cruzado (8 unidades), L4-7 baseline × procedural, ficha 04.

Cinco geradores geométricos cobrem as 28 famílias de rig: `lathe` (existe), `limb` (existe), **`chain`** (novo: 14 famílias com `_chain`), **`plate`** (novo: asas em 8 famílias, placas, lagartas, carapaça), `wheel/ring` (existe). Ordem: L4-1 `chain` → L4-2 `plate` → L4-3 fit hierárquico + piso por vista/família (independente) → L4-4 sheets + massing de quadruped/serpent/drake → L4-5 baseline cruzado 6-10 unidades → L4-6 `joint_place` (landmarks de junta) → L4-7 experimento 2 caminhos (baseline × procedural, mesma sheet/câmeras/gates) → DFS: diagnóstico LLM só em CHECK.

**Decisão do usuário (2026-10-27):** nenhum gerador image-to-3D (TRELLIS, Hunyuan3D, TripoSR), nem como experimento de registro. O pipeline é nosso e evolui por representação própria + fit + gates. Briefs dos 3 primeiros no arquivo de análise.

---

# Leva 5 (2026-10-28) — FORMA: partes, profundidade e props separados

**Estado (2026-10-28):** L5-1..L5-7 integrados (PIPELINE §23). Default: segmentação (`refs/<id>/parts.json` nas 8 unidades), massing por partes (simetria, clamps, contato, fallback por grupo), props com `prop`/`anchor` e `overlap` pela âncora, 8 lados + chanfro + cabeça lathe com decal do sheet + botas redondas, identidade (relatório, status), juiz com 4 votos e eixo wc3. Opt-in: `--fit-parts` (máscara por parte + ordem z: baixa o vermelho do left do n005 21→14 % mas sobe o top), `--depth` (Depth Anything: correlação fraca com o left), `TRUNK_SIDES`, `LIMB_KNEE`. Não aplicado: corte dos painéis por vãos interiores (misto). Bateria v9 nas 8 unidades em `history/2026-10-28-v9/`.

Fonte: feedback do usuário ("forma principalmente; props mergeados com o corpo; parece outra coisa"),
`analysis/2026-10-28-feedback-n005.md` (arma fundida, tanque em bloco, máscara plana, top assimétrico,
detalhes inconsistentes; sugestões: profundidade monocular, VLM como segmentador/Point QA, renderização
diferenciável) e a leitura do v8. Diagnóstico comum: o pipeline mede largura por faixa e silhueta, sem saber
**que parte** é cada coisa nem **em que profundidade** está; a oclusão (arma na frente, tanque atrás) vira
volume em bloco e o `overlap` obriga o prop a afundar no corpo. Regras do projeto mantidas: BFS, nada de gerador
image-to-3D, nenhum loop de volta ao modelo.

## Ordem de desenvolvimento
- **L5-1 Segmentação semântica do sheet (VLM como segmentador, não autor).** Uma chamada por sheet
  (session:opus, Point QA): para front e left, as coordenadas 2D das juntas do rig (ombro, cotovelo, punho,
  quadril, joelho, tornozelo, topo da cabeça, queixo; para aranha: raiz e joelho de cada perna) e as caixas 2D
  de cada parte semântica (cabeça/capuz, máscara, torso, pelvis/saia, braços, pernas, pés, cada prop da card:
  tanque, arma, lanterna, crachá). Triangulação front×left → juntas 3D e caixa 3D por parte. Saída
  `refs/<id>/parts.json` (versionado; gerado uma vez por sheet). Máscaras por parte = caixa 2D ∩ zona de cor.
  Prova: overlay das juntas/caixas sobre o sheet nas 5 unidades; `joint_place` passa a usar isto (lê 8/8
  juntas, não 2/8).
- **L5-2 Massing por partes.** O pré-spec nasce das caixas 3D de L5-1, uma peça (ou lathe/limb/plate) por
  parte semântica com o material da zona: tanque é tanque (lathe atrás do torso), capuz é capuz, arma é arma.
  Largura por faixa só como refino dentro da parte. Substitui o massing por faixa quando `parts.json` existe.
  Prova sem LLM: massing sozinho nas 5 unidades; `zones_clay` por parte (a peça do material X dentro da zona X)
  sobe; o tanque e a arma aparecem como peças próprias no `attach.json`.
- **L5-3 Props separados do corpo.** Prop é um objeto: ancorado num ponto (mão, costas, cinto) com folga
  mínima (`prop_clearance`: fração do volume do prop dentro do corpo ≤ 20 %), material próprio, textura do
  `sheet-props` projetada na peça. O `overlap` exige só o ponto de ancoragem. Regra `prop_reads`: no render ID,
  a zona do prop é visível e separada (componente próprio) nas vistas onde o sheet o mostra. Fit: prop move
  junto com a âncora, não escala para encher silhueta. Prova: n005 (tanque, arma, lanterna), hfoo (lança,
  mochila), n02X (clava): compare antes/depois; juiz pareado.
- **L5-4 Profundidade e oclusão no fit (sem rede, sem GPU).** Ordem de profundidade por parte vinda de L5-1
  (left view diz o z de cada parte) vira restrição do fit: cada peça projeta dentro da própria máscara de parte
  (zones_clay generalizado para partes) e a ordem z entre pares (arma na frente do peito, tanque atrás) é dura.
  Isso é o que a renderização diferenciável resolveria; aqui entra no proxy raster que já existe. Prova: n005
  left uncovered 21 % → < 15 %; arma e máscara deixam de fundir.
  - **L5-4b (decisão do usuário):** profundidade monocular (Depth Anything V2 small, open-source, só inferência,
    CPU/MPS). Não é gerador 3D, mas é rede pré-treinada: só entra se você aprovar. Uso: mapa Z por parte para
    inicializar `at.z` e a ordem de oclusão onde o left não resolve (partes alinhadas no eixo).
- **L5-5 Superfície por default.** 8 lados em tudo, bevel, `lathe` em cabeça/máscara/tanque (perfil do sheet,
  squash), `limb` com joelho (de L5-1) nos membros, pés em lathe/frustum arredondado; máscara/rosto com volume
  (lathe do perfil left) e o decal dos olhos sempre do sheet (dois pontos, não fenda). Prova: tris dentro do
  orçamento; juiz pareado contra o run anterior; `edge_chamfer` e `spill` top/bottom caem.
- **L5-6 Consistência de detalhes.** Checklist de identidade por sheet (de L5-1: props, olhos, crachá, válvula)
  e regra `identity_present` (relatório → gate): cada item tem peça ou decal e aparece no render ID. Prova: o
  crachá do n005 não some entre runs.
- **L5-7 Juiz.** Pareado com 4 votos (2+2, sem viés de posição) e, além do run anterior, contra um modelo WC3
  de referência da mesma classe (silhueta e leitura), eixo "parece WC3". Métrica principal de "parece".

## Fora
- Renderização diferenciável (PyTorch3D/nvdiffrast/Kaolin): sem CUDA; L5-4 põe profundidade e partes no proxy
  que já roda em ms. Reavaliar só se L5-4 não resolver a fusão.
- VLM escrevendo o modelo inteiro: continua só editando o pré-spec (massing por partes).

---

# Leva 6 (2026-10-28) — APLICAR OS PAPERS DE FORMA COMO MÉTODO

**Estado (2026-10-28, noite):** 11 de 12 integrados (PIPELINE §24); L6-7 (vértices) em curso, opt-in. Default: L6-1 superfície contínua (`STACK_LATHE`), L6-3 props por tipo com folga (`CLEARANCE_BLOCKING`), L6-4 `UNION_BODY` (corpo = 1 casca; componentes do corpo e slivers viram gate), L6-5 `DEFORM` (contorno → desenho), L6-6 gates de forma (normal_diff, fairness, components_body; termo de forma na margem e no fit; eixo form no juiz), L6-9 r_sym/coerência (vista incoerente vira relatório), L6-10 `--budgets`. Opt-in/negativos: L6-2 `CUT_DEFAULT` (n02X left −0.058), L6-11 rampa e cull na malha unida (negativos), `--atlas shared`, L6-12 `--align` (ruído). Bateria v10 em `history/2026-10-28-v10/`.

Fonte: `analysis/2026-10-28-auditoria-papers-vs-codigo.md`. Até aqui Sano, Chen, Sketch2Mesh e Wiersma entraram como
métrica/gate; a forma continua sendo frustums empilhados de 4 lados, 25 cascas se atravessando, props afogados. Esta
leva muda a REPRESENTAÇÃO e o BUILD, e troca o juiz de aceite para a forma (wire, normais, componentes), não só a
máscara 2-D. Regras: BFS, sem GPU/treino, sem gerador image-to-3D, nenhum loop de volta ao modelo. Critério de
aceite comum: compare lado a lado (clay + wire + overlay) julgado pelo pareado de 4 votos; IoU 6 vistas não pode cair
mais que 0.02; `mesh_lint` componentes do corpo = 1 (+ props), slivers < 5 %.

## Dependências
```
L6-1 superfície contínua ──┐
L6-2 hull visual (Sano) ───┼──> L6-4 união + limpeza (Chen) ──> L6-5 deformação ao contorno (Sketch2Mesh) ──> L6-7 vértices (Wiersma, opcional)
L6-3 props ancorados ──────┘                                    L6-6 gates de forma (paralelo a tudo)
```

## Tarefas

### L6-1 Tronco, pelve, carapaça e cabeça como UMA superfície contínua (anéis compartilhados)
- **Problema:** `massing._frustum_stack`/`_slab` emitem uma peça por fatia; anéis vizinhos não compartilham largura
  → degraus em toda junta; 4 lados. `lathe_rings` é revolução pura (raio escalar + squash global, eixo reto): não faz
  capuz que avança em z, nem barriga.
- **Mudança:** `lathe_limb.lathe_rings` aceita `profile` como lista de anéis `[w, d, zc, xc]` (largura, profundidade,
  centro z e x por anel, em fração de `r`/metros), 8 lados, tampas; `massing._frustum_stack`/`_slab`/`lathe_part`
  emitem UM `lathe` por papel (torso, pelvis, cabeça, carapaça, abdômen) com os anéis nos breakpoints que já calcula
  (`breakpoints`), lendo w/d/zc do sheet. `preflight.part_tris`/`bbox`, `fit_spec.PARAMS["lathe"]` (raios por anel
  ±15 %), `cut_hull.lathe_profiles` atualizados. Flag `STACK_LATHE = True` (volta às fatias com `False`).
- **Prova sem LLM:** massing sozinho em n005, n02X, hfoo, n00U, n017: wire sem degraus (compare), IoU 6 vistas
  ±0.02, tris dentro do orçamento (ajustar anéis: 4-6 por tronco), `mesh_lint` slivers; julgar no wire e no pareado,
  não no spill de bottom. PIPELINE §24.L6-1.

### L6-2 Hull visual de Sano por default (3 vistas, por parte, regularizado)
- **Problema:** `cut: sheet` é opt-in, 2 vistas, 8 vértices, decidido pelo fit e vetado pelo vermelho médio.
- **Mudança:** `cut_hull`: contorno por parte (faixa da `box3d` de `parts.json`) em front, left E top (`top_outline`
  existe), DP 12-16 vértices + `snap_axes` + arcos (ajuste de círculo em 3 vértices consecutivos quando o resíduo
  cai), interseção dos 3 prismas (`BOOLEAN INTERSECT` EXACT já existe em `cut_part`), QEM até o orçamento da parte;
  `massing` marca `cut: sheet` por default em capuz/torso/pelve/saia/carapaça; `CUT_MAX` por parte; `fit_accepted`
  deixa de vetar `cut` pelo vermelho médio (compara só IoU + slivers). Mantém L6-1 como base (o hull corta o lathe).
- **Prova sem LLM:** n005 (capuz, torso, saia), n00U (carapaça), n02X (barriga): top/bottom IoU e uncovered
  antes/depois; o contorno do capuz no left deixa de ser retângulo (overlay); tris por parte. PIPELINE §24.L6-2.

### L6-3 Props ancorados com folga, por default
- **Problema:** `prop_clearance` 83 % OUT só relatório; `block_part` força o pique inclinado para frente; tanque e
  vaporizador afundam no corpo; props viram caixa.
- **Mudança:** `massing`: prop vira `lathe`/`plate`/`chain` conforme o nome (tanque → lathe, arma → plate do
  recorte do `sheet-props`, pique → chain de 2 anéis com o ângulo lido do sheet front/left, lanterna → lathe), posto
  no ponto de ancoragem com folga ≥ 0.02 H para fora do corpo (`gap_move` ao contrário: afasta); `prop_clearance`
  vira gate (≤ 20 %) e `overlap` pela âncora é o único contato; `fit_spec` nunca move prop para dentro.
- **Prova sem LLM:** n005 (tanque, vaporizador, lanterna), hfoo (pique, mochila), n02X (clava): `prop_clearance`
  ≤ 20 % em todos, prop lê como objeto no compare, IoU ±0.02. PIPELINE §24.L6-3.

### L6-4 Chen por default: união do corpo + limpeza + decimate com tolerância + features
- **Problema:** build em `join`: 25 cascas se atravessando; `union`/`clean_mesh`/`toldec` existem e ficam opt-in.
- **Mudança:** `build_unit.main`: corpo (peças não-prop) → `union_parts` (BOOLEAN EXACT) → `clean_mesh` (merge
  1 mm + dissolve planar 6°) → `union_decimate` com Hausdorff ≤ H/32 e piso de faces (não cair abaixo de 60 % do
  orçamento) → sharp por ângulo (`soften` marca arestas > 35° como sharp; chanfro só nelas) → skin por proximidade
  do osso (já existe no `fuse`); props continuam componentes próprios (L6-3). Flag `UNION_BODY = True`.
  `mesh_lint`: componentes do corpo = 1 vira GATE.
- **Prova sem LLM:** rebuild dos 8 `v9-r1/spec.json`: componentes 25 → 1 + props, slivers < 5 %, IoU ±0.01,
  animação (`walkleft`, 5-7 clips) sem rasgar (render dos clips); compare clay/wire. PIPELINE §24.L6-4.

### L6-5 Sketch2Mesh por default: deformação da malha unida ao contorno (sem LLM)
- **Problema:** o fit move dims de caixas com proxy de casco convexo; não cria forma.
- **Mudança:** novo `tools/blender/deform_to_sheet.py`: na malha unida (L6-4), vértices do contorno externo de cada
  vista (ray-cast das bordas, como Sketch2Mesh Fig. 2c) recebem deslocamento ao ponto mais próximo do contorno do
  sheet (front, left, back; top/bottom opcionais), o interior segue por suavização Laplaciana (scipy sparse,
  `cotangent` ou uniforme), 3-5 iterações; só na banda que falha (Eq. 6: pesos caem a zero longe do vermelho/verde);
  limite de deslocamento 0.05 H por iteração; rejeita se slivers > 5 % ou inversão de normal. Entra DEPOIS do fit e
  antes da textura; `fit_accepted` igual.
- **Prova sem LLM:** 8 clays v9: uncovered/spill por vista antes/depois (meta: vermelho e verde < 8 % em front/left/
  back), IoU, slivers; overlay quase cinza. PIPELINE §24.L6-5.

### L6-6 Gates de FORMA (paralelo a tudo)
- **Problema:** IoU/uncovered/spill/zonas medem máscara 2-D; nada mede continuidade de normal, curvatura, componentes;
  decisões de visual foram vetadas por décimos de IoU.
- **Mudança:** `mesh_lint`: `normal_diff` (Chen: ângulo médio entre normais de faces vizinhas; degrau = pico),
  `fairness` (Wiersma), `components_body`, `slivers`; `review.md` ganha bloco "Forma" e o status passa a exigir
  componentes = 1 + props e slivers < 5 % para final-use; `compare_runs --show wire` default no histórico; o
  pareado ganha o eixo "forma contínua" (sem degraus/caixas atravessadas). `fit_accepted`/`best_of_n` somam um termo
  de forma (−slivers, −normal_diff) ao lado do vermelho.
- **Prova:** calibrar nos 65 runs guardados; mostrar que v6-r4 (feio, PASS) e v9 (juiz prefere) se separam por estas
  medidas onde o IoU empata. PIPELINE §24.L6-6.

### L6-7 Wiersma (opcional, depois de L6-5): otimização de vértices de topologia fixa
- Malha unida e decimada (~600 tris) como vetor de vértices; objetivo = silhuetas 6 vistas + chamfer + fairness +
  penalidade de inversão (line search que rejeita); Powell/L-BFGS em blocos de vértices por banda; sem SDS. Custo L;
  só se L6-5 deixar vermelho/verde > 8 %. PIPELINE §24.L6-7.

### L6-9 Sano: simetria e coerência entre painéis do sheet
- `silhouette`: `r_sym` por vista (IoU da máscara com o espelho) e coerência do sheet (hull de 2 vistas projetado na
  terceira vs o painel desenhado: front⊗left → top, front⊗left → back); vão ao brief ("a figura é assimétrica no
  front: clava na mão direita") e ao review como diagnóstico antes de culpar o modelo (n00U/n010 têm painéis
  incoerentes). `massing` usa `r_sym` para não espelhar um prop assimétrico. Prova: 11 sheets, tabela; n010 e n00H
  marcados incoerentes. PIPELINE §24.L6-9. Custo S.

### L6-10 Wiersma/Chen: protocolo de ablação por orçamento de triângulos
- `spec_pipeline --budgets 400,700,1000`: o mesmo spec construído em 3 orçamentos (decimate com tolerância de L6-4),
  curva IoU × tris × slivers no review e no compare (`--show budgets`); calibra `BUDGETS` por classe e o piso de
  faces de L6-4 ("IoU perdido por 100 tris" já existe em `--decimate`). Prova nos 8 v9. PIPELINE §24.L6-10. Custo S.

### L6-11 Le/MeshGPT na malha unida: rampa por altura, faces escondidas, atlas partilhado
- Depois de L6-4 (uma casca): reavaliar `ramp` (v por normal + altura) e `edge glow` nos chanfros sobre a malha unida
  (na pilha de caixas a rampa não aparecia; numa superfície contínua é a "AO pintada" do WC3) — ligar por default se
  o juiz pareado preferir e as zonas não caírem; `cull=remove` (faces nunca vistas) por default depois da união
  (medir tris visíveis/total antes e depois; não pode rasgar animação); atlas de rampas de 1 px por coluna partilhado
  por raça (Le) como opção de exportação (`--atlas shared`) com teste de import no engine. PIPELINE §24.L6-11. Custo S-M.

### L6-12 Chen/Sketch2Mesh: alinhamento de features ao desenho
- Na malha unida (L6-4) e deformada (L6-5): arestas vivas (ângulo > 35°) são puxadas para o mapa de arestas internas
  do hard sheet (`silhouette.edges`, E15) na vista onde a aresta é visível — o termo `edge_term` já existe no fit;
  aqui vira passo de pós-deformação com peso pequeno e limite 0.02 H; `edge_chamfer` deve cair. Prova: n01X (placas),
  n005 (capuz/saia), n02X (cinto): `edge_chamfer` antes/depois, wire. PIPELINE §24.L6-12. Custo M.

## Cobertura final por paper (o que fica de fora e por quê)
- Chen: iso-surface MC33 (precisa de high-poly de entrada: fora), cage/offset shell (sem uso), PSNR/LFD (sem GT 3D).
- Sano: tudo coberto (DP, regularização, arcos, interseção, r_sym, coerência, massing de edifício).
- Sketch2Mesh: encoder MeshSDF (treino: fora); o resto coberto (chamfer, deformação, contorno externo, Eq. 6).
- Wiersma: SDS/difusão (GPU: fora), fabricação (fora); vértices (L6-7), fairness/slivers (L6-6), ablação (L6-10),
  simetria, Oklab, pareado: cobertos.
- MeshGPT/EdgeRunner: geração por transformer (treino: fora); pré-processo, faces escondidas, compacidade,
  orientação, componentes, best-of-N, schema, 3 eixos: cobertos.
- Le: cobertos (rampa, altura, chanfro, nearest, rampa do sheet, luma por zona, atlas partilhado em L6-11).
- ULIP: CLIP medido e negativo (fica fora do fluxo, script mantido).
- Begemann/Zhao: cobertos (Readiness, status, tempos, engine import, UV, pareado cego, K variantes, score 30/70).

### L6-8 Bateria v10 e fechamento
- 8 unidades, compares `clay+wire+overlay+textured`, pareado contra v9 nos 4 eixos, ficha 05, §24 com a tabela.
  Critério de sucesso da leva: pareado ≥ 4-0 "forma contínua" em 6 de 8; vermelho+verde < 8 % em front/left/back em
  6 de 8; componentes do corpo = 1 em 8 de 8.

---

# Leva 7 (2026-10-29) — RTS e laterais

**Estado (2026-10-29):** L7-2 (coerência do rts, `--redo-rts`) e L7-4 (lathe deitado default; `LEAN_PROPS` opt-in) integrados e medidos na bateria v11 (n017 PASS, juiz 4-0); L7-3 integrado opt-in (`TOP_LEGS`, `LEG_SPILL_W`); L7-1 e L7-5 integrados depois da bateria (ver §25). Recalibração de `budget`: feita na leva 8 (§26.L8-9, `SOFT_RULES`).

Diagnóstico do v10: front/back passam em 7 de 8; o erro ficou no rts (n00U .617, n017 .692, n00H .232, n010 .547) e
no left (hfoo .450, n00H .681, n017 .719). Causas: fit/deformação só em front/left/back; rts do sheet gerado à parte
sem coerência; pernas da aranha/lobo não medidas no rts/top; tronco horizontal em tijolos; prop longo com ângulo
lido só do left. Prova de cada item: rerodar n00U, n017, n00H, hfoo (e n005 como controle) e comparar com v10.

- **L7-1 seis vistas no fit e na deformação.** `deform_to_sheet` e `fit_spec` puxam também rts (câmera do run:
  tilt/azimute de `silhouette.json`), top e bottom; pesos por família (`VIEW_WEIGHTS[rig]`: spider/quadruped
  rts+top+bottom ×2). Guardas: nenhuma das 3 ortográficas cai > 0.01. Meta: rts +0.05 em n00U/n017 sem perder front.
- **L7-2 coerência do rts.** `silhouette.sheet_report` ganha rts: hull front⊗left⊗top projetado na câmera rts (a que
  a varredura escolhe) vs o painel; < 0.6 = incoerente (relatório, veredito ignora) e `ensure_rts --redo` regenera o
  rts com prompt amarrado aos 3 painéis (nano banana, só nas 4 unidades de prova). n00H rts .232 é o caso.
- **L7-3 pernas no rts e no top.** `measure_spider`/`measure_quadruped`: comprimento, espessura e abertura das pernas
  lidos também no rts e no top; `massing`: pernas da aranha como `limb` com joelho do top (não do rig fixo), raio
  por segmento; `fit_spec`: verde do rts (spill) como restrição dura para peças `leg*`. Meta: spill rts n00U 31 % → < 15 %.
- **L7-4 lathe deitado e prop inclinado.** `lathe_limb`: `axis: z` (anéis ao longo de z) para tronco de
  quadrúpede/wyrm/drake (massing `_brick` → um lathe deitado por tronco/abdômen); prop longo (lança, pique, clava):
  ângulo lido de front E left (eixo maior da máscara do prop em cada vista) → `rot` do prop; hfoo left .450 → > .65.
- **L7-5 deformar o corpo contra o corpo, props contra os props.** Achado nos overlays do hfoo v10: a deformação puxa
  as pernas para o contorno mais próximo do sheet, que é a lança diagonal (uma parte que a malha não tem), e o modelo
  estica corpo e pés (vermelho embaixo no left/rts). `deform_to_sheet` e `fit_spec` passam a usar a silhueta do CORPO
  (painel do sheet menos as máscaras dos props de `parts.json`/`props.json`, dilatadas 2 px) como alvo do corpo; cada
  prop (componente próprio) casa só com a própria máscara; vértice sem alvo na máscara certa não se move. Meta: hfoo
  left/rts sem o arrasto dos pés; n005 igual ou melhor; `uncovered` do corpo e do prop reportados separados.

# Leva 8 (2026-10-29) — renderização diferenciável como otimizador

Fonte: 12 papers de `~/Desktop/Differentiable_Rendering_DOIs_20261021/`; análise em `analysis/2026-10-29-papers-diffrender.md`.
Aprovada pelo usuário em 2026-10-29.

**Estado (2026-10-29, fim da leva):** L8-1, L8-2 (default), L8-3, L8-4, L8-5, L8-7, L8-8 integrados; L8-6 medido (v12: PASS 2/5,
left +.03 a +.13 em 5/5, juiz dividido 2×2); ablação L8-6b: o ganho é do `--fit-verts` (6/6 vistas em 5/5) → **`FIT_VERTS=True` default**, `--fit-grad` opt-in. Pendente:
~~recalibrar `budget`/`shoulder_span`~~ feito (§26.L8-9: preflight só com regras soft não derruba clay que cobre o sheet; n005 v11 e n02X v12 CHECK -> PASS offline, hfoo v11 segue CHECK); limitar threads do torch já feito (`soft_sil.THREADS`).

Diagnóstico: o pipeline já otimiza por silhueta (fit Powell, deformação, vértices) mas com
raster duro e gradiente numérico (`optimize_verts.iou_gradient` 1–2 s por gradiente, 120 s/unidade, por isso desligado). Um
soft rasterizer (SoftRas/DIB-R/GenDR) dá o mesmo objetivo com gradiente analítico 10–50× mais barato e sinal para vértices
longe do contorno. Regras: gates continuam no raster duro (Blender); o suave é só para o gradiente; opt-in até ganho medido;
torch 2.14.1 instalado no `python3.14` (MPS disponível; CPU basta). Unidades de prova: n005, n00U, hfoo, n017, n02X.

| # | Item | Papers | Aceite |
|---|---|---|---|
| L8-1 | `soft_sil.py`: raster suave de silhueta em torch (projeção = `deform_to_sheet.View`; `F(d/τ)` uniforme/logística; agregação probabilística; IoU suave; autograd) | 01, 03, 12 | nos 5 clays v11-r1, 6 vistas: \|IoU suave(τ=0.5 px) − IoU duro\| ≤ 0.01; forward+backward ≤ 50 ms CPU para 800 tris |
| L8-2 | `optimize_verts` com gradiente analítico (`iou_gradient` → backward; line search, recusa flip/sliver, settled intactos; aceite com raster duro) | 01, 11 | IoU f/l/b ≥ tabela L6-7 em ≤ 30 s; flipped 0; slivers não sobem |
| L8-3 | anelamento de τ (4 px → 0.5 px) + ablação uniforme × logística × Gamma-inv, probabilística × Yager(2) | 12, 01 | f/l/b com vermelho+verde < 8 % em ≥ 12 de 15; n017 left ≥ .75 |
| L8-4 | regularizador de diedro `λ Σ(cos θ + 1)²` em arestas < 35° (vivas preservadas) | 02, 11 | `normal_diff` depois ≤ antes nas 5; IoU dentro de −0.005 |
| L8-5 | perda assimétrica vermelho/verde com pesos por vista de `UNCOVERED_MAX`/`SPILL_MAX` | 04, 11 | n005 e n02X passam acoplamento no left; n005 f/l/b não cai |
| L8-6 | `--fit-verts` default se ≤ 30 s; bateria v12 nas 5 unidades contra v11 | 01 | ≥ 3 de 5 PASS; juiz ≥ 3-1 em forma para n005 e n017; nenhuma vista cai > 0.01 — **Estado:** v12 PASS 2/5; forma v12 4-0 em n00U/n017, v11 4-0 em hfoo; hfoo top −.09. Opt-in (§26.L8-6) |
| L8-7 | `fit_spec` por gradiente: proxy paramétrico diferenciável em torch, união pela agregação, Adam com τ anelado; Powell fallback `--fit-powell` | 01, 12 | mesmo `fit_accepted` e IoU ±0.01 em ≤ 1/3 do tempo, ou IoU maior no mesmo tempo |
| L8-8 | luma por shading diferido: G-buffer (ID + normais) → tons por material + luz por `least_squares` contra a luma do sheet | 10 | `luma_l1` f/l/b < .029/.031/.024 e zone mean não cai em n005/n01X |

**Estado L8-8 (2026-10-29):** `fit_luma.py` + `--fit-luma` (opt-in, `colour_stage.FIT_LUMA = False`) integrado (PIPELINE §26.L8-8). Aceite NÃO atendido: n005 luma_l1 f/l/b .049/.035/.035 -> .037/.022/.022 (l e b passam, f não), n01X .024/.024/.059 -> .039/.024/.046 e zone mean do back .41 -> .24. Fica desligado.

Ordem: L8-1 → L8-2 → (L8-3, L8-4, L8-5 em paralelo) → L8-6 → L8-7; L8-8 independente. Não aplicar: PyTorch3D como
dependência, câmera por gradiente, textura por raster suave, redes implícitas, difusão/SDS (05–09 fora de domínio ou vetados).

**Estado L8-1 (2026-10-29):** `soft_sil.py` integrado (PIPELINE §26.L8-1), sem flag, ainda não usado por nada. |IoU suave(τ=0.5) − IoU duro| ≤ 0.0075 vs `Ctx` (≤ 0.0080 vs `silhouette.iou`) nos 5 clays × 6 vistas; forward+backward ~630 tris: CPU mediana 33–59 ms (meta 50: n00U passa, 59), MPS 8–18 ms.

**Estado L8-2 (2026-10-29):** `optimize_verts` usa `loss.backward()` de `soft_sil` (`GRAD = "soft"`, `TAU = 0.5`, `DEVICE` cpu|mps; `GRAD = "fd"` guarda o antigo), PIPELINE §26.L8-2. Gradiente completo 0.46 s vs 1.52 s; soft-30 ≥ tabela L6-7 em n005, hfoo, n017; n00U e n02X não (entradas v11/v10 começam abaixo do clay da L6-7); soft-120 ≥ fd-120 (±.003) em 13 de 15 f/l/b; flipped 0, slivers caem. `normal_diff` ainda sobe (L8-4). `FIT_VERTS` segue False.

**Estado L8-5 (2026-10-29):** `soft_sil.soft_asym`/`asym_weights` + `optimize_verts.LOSS = "iou" | "asym"` (`--loss`, `--red-boost`), opt-in (PIPELINE §26.L8-5). Gate do left passa em n005 e n02X, mas já passava com `iou`; asym baixa o uncovered em 15 de 15 vistas f/l/b e sobe o IoU em n00U/hfoo/n017 left, mas n005 f/l/b perde .002/.005/.002 contra `iou` e o spill sobe +.003..+.007. Nenhum veredito muda: fica desligado.

**Estado L8-4 (2026-10-29):** `LAMBDA["dihedral"]` + `--dihedral` em `optimize_verts` (PIPELINE §26.L8-4), default 0. Aceite NÃO atendido: só λ=30 baixa `normal_diff` abaixo da entrada nas 5 (n005 42.6 > 41.9, n017 45.5 > 45.2, ...), mas o IoU f/l/b cai 0.010-0.020 vs λ=0 (limite -0.005); λ<=3 mantém o IoU e o `normal_diff` ainda sobe 0.2-1.4. Fica desligado.

**Estado L8-3 (2026-10-29):** `TAU_SCHEDULE`/`DIST`/`AGG` + `--tau-schedule/--dist/--agg` em `optimize_verts`, `soft_sil.gamma_inv` (PIPELINE §26.L8-3). Ablação 3 schedules × 3 distribuições × 2 agregações (n005, n00U) e confirmação nas outras três: tudo dentro de ±.005 de IoU duro; anelar 4→.5 ou 2→.5 não ganha do τ constante 0.5. Aceite (verm+verd < 8 % em ≥ 12 de 15) NÃO atendido (melhor: 3 de 15, só n005); n017 left ≥ .75 passa (.77-.78). Defaults inalterados (const, logistic, prob), demais opt-in. `COARSE=0` perde ~.005: âncoras ficam.

**Estado L8-7 (2026-10-29):** `fit_grad.py` + `--fit-grad` em `fit_spec`/`spec_pipeline` (PIPELINE §26.L8-7), opt-in, Powell segue default (a coluna "Powell fallback `--fit-powell`" da tabela não foi preciso: é o default). IoU duro do clay real f/l/b maior que o Powell em 4 de 5 unidades (n017 +.05/+.02/+.08, n02X +.00..+.01, n00U +.02/+.05/+.02, n005 +.01..+.02) em 20-47 s contra 24-153 s; hfoo perde .015/.064/.018. `fit_accepted` igual em todas. Falta: fechar hfoo (polimento Powell) antes de propor default.


**Estado L8-6b (2026-10-29):** ablação grad × verts sem LLM (PIPELINE §26.L8-6b, `history/2026-10-29-l8-abl/`): o ganho do left/rts vem do `--fit-verts` (5/5; left +.012..+.046, rts +.012..+.041); `--fit-grad` é nulo em n005/hfoo/n02X, +.01..+.02 em n00U (3x mais rápido), recusado em n017; a perda de top/bottom do hfoo não é de nenhum flag (já em `none`: autor). Recomendação: `--fit-verts` default, `--fit-grad` opt-in (talvez spider); defaults NÃO mudados no código.

# Leva 9 (2026-10-29) — textura: atlas compacto, paleta partilhada, 1 material

**Estado (2026-10-29, fechada):** T1/T6/T5 default (atlas 84 KB → 5 KB; 7 → 1–2 materiais); T2/T4 relatório; T3+T7 opt-in
(`--atlas shared`: juiz prefere em 3/5, falta a imagem única por raça no engine). Detalhe em PIPELINE §27.

Fonte: lista de papers/tutoriais de atlas e packing (`analysis/2026-10-29-papers-atlas.md`; referências em
`IA_gen_paper/papers/atlas/referencias_atlas.md`). Aprovada pelo usuário em 2026-10-29 ("autorizar execução do plano ao fim").
Diagnóstico: o cel plano guarda ~40 cores úteis num PNG de 768² (84 KB) com 7 materiais = 7 draws; o `--atlas shared` (64², 1 KB)
já existe mas perde decais e ink. Regras: textura procedural sempre; gates no raster duro; nada muda a forma.

| # | item | aceite |
|---|---|---|
| T1 | atlas cel compacto: slot de rampa 2 px, decal 16 px, `pack_cells` shelf FFD | n005 ≤ 128², `atlas_kb` ≤ 8; `luma_l1` ±0.003; `zones mean` não cai > 0.01; decal legível |
| T6 | mip-safe medido (`mesh_lint.mip_bleed`, células POT + padding 2 px) | 0 texels mistos até 1/4; relatório só |
| T2 | paleta mínima partilhada (Oklab ΔE < 0.02, coluna 2 px) | Human 12 → ≤ 9 colunas; 64² cobre ≥ 16 unidades/raça; render texel-igual sem fusão |
| T3 | decais no atlas partilhado (1 imagem, MaxRects 16 px) | `images == 1`; pareado sheet não perde 4-0; ≤ 128², ≤ 4 KB |
| T5 | 1 material no export (`merge_materials`) | n005 prims 7 → 1; engine importa; 1 draw/tipo; render pixel-igual |
| T4 | espelho L/R já partilha célula: prova + `uv_overlap_pct` esperado | linha no PIPELINE + teste |

Estado T2 (2026-10-29): feito atrás do `--atlas shared` (PIPELINE §27.T2): fusão ΔE .02 + coluna 2 px (32 col); aceite NÃO atingido (Human 13 -> 12 col, ~5-8 unidades/raça em 64²).

Estado T4 (2026-10-29): **feito, já existia** — gêmeos `.L/.R` partilham célula e tom (25-36 % dos pixels cobertos em n005/hfoo); `mesh_lint.uv_overlap_mirror_pct` (relatório) = 2-3 %, o resto da sobreposição (64-81 %) é o cel "1 texel por tom". Único par desigual: `forearm` com prop na mão. PIPELINE §27.T4.

Ordem: (T1+T6, T2, T4 em paralelo) → (T3, T5). Não vale: packing aprendido, joint UV baking, carving por OT, modulo-valid, TABI.
| T7 | paleta por raça: atlas partilhado 128² (64 colunas de 2 px) + paleta fixa da raça (das 14 cores dos ícones/compêndio) oferecida ao autor como restrição suave (`palette_hint`), para caber ≥ 16 unidades/raça (T2 mostrou que fusão por ΔE rende 1 coluna) | 128² por raça ≤ 4 KB; ≥ 16 unidades/raça na simulação; `zones mean` não cai > 0.01 nas 5 unidades |

# Leva 10 (2026-10-29) — CSG → SDF → malha → retopologia guardada (aprovada pelo usuário em 2026-10-29)

Plano completo em `analysis/2026-10-29-leva10-sdf.md`. Diagnóstico: a união booleana deixa 9–33 % de slivers e nd 38–41° já no
`clay-raw` (v12: `sliver_pct < 5` falha 5/5; n00U 2 corpos), e isso é o que o `optimize_verts` recusa. Rota: SDF analítico por kind
(cascos convexos dos anéis já emitidos), `smin` só pai/filho, extração por `openvdb` do Blender (ms), retopologia QEM própria com
arestas vivas + reprojeção no SDF (passo crítico), ownership de osso por SDF, métricas Chamfer/Hausdorff/euler contra o campo.
Fase D (VLM no loop) = DFS futuro; geradores (Meshy T2 e cia) só como ideias.

| # | item | aceite |
|---|---|---|
| L10-1 | `sdf_body.py` (SDF por kind, smin por junta, grade 96³) | paridade \|d\| ≤ 1e-6 em todos os kinds e 17 specs; ≤ 1.5 s |
| L10-2 | extração openvdb + ablação REMESH SHARP | malha fechada 5/5; slivers brutos < 4 %; `sdf_dev` p95 ≤ 0.5 voxel |
| L10-3 (peso 2) | `retopo.py` QEM com guarda, features, reprojeção, V* = (B+4)/2 | `sliver_pct < 5` 5/5; `sdf_dev` p95 ≤ H/64; nd ≤ união −10°; IoU ≥ união −0.01; euler 0; ≤ 3 s |
| L10-4 | remalhagem isotrópica (Botsch–Kobbelt) vs QEM | fairness ≤ 15°, slivers < 2 %; juiz forma decide |
| L10-5 | ownership/skin/material por SDF; clips | 7 clipes importam; esticão ≤ 1.1×; comp 1 em 5/5 |
| L10-6 | `mesh_lint` sdf_dev / normal_consistency / euler | relatório nos 5 clays v12 e SDF |
| L10-7 | integração `BODY=sdf`, `--body`, peça fina, k | IoU ≥ v12 −0.01; `unsafe` −50 %; build ≤ 60 s; `--body union` idêntico |
| L10-8 | robustez em lote: 17 specs, por rig | 17/17; build ≤ 15 s médio; critérios por rig |
| L10-9 | bateria v13 pareada contra v12 | PASS ≥ 3/5; slivers < 5 % ≥ 4/5; default só se tudo passar — **feito: PASS 3/5, slivers 4/5, default sdf por decisão (ver Estado)** |

**Estado L10-1 (2026-10-29): feito** — `tools/blender/sdf_body.py` + `part_geom.py` (geometria numpy-pura extraída do `fit_spec`), `tests/tools/blender/test_sdf_body.py`; paridade |d| ≤ 1e-6 nos 14 casos sintéticos e nas 17 specs, 96³ em 0.04–0.39 s nas 5 unidades (PIPELINE §28.L10-1).

**Estado L10-2 (2026-10-29): feito** — `build_unit.sdf_mesh` (openvdb `convertToPolygons`), `tools/blender/sdf_extract.py` + `sdf_extract_report.py`, `tests/tools/blender/test_sdf_extract.py`; malha fechada 5/5, slivers brutos ≤ 3.3 %, `sdf_dev` p95 ≤ 0.35 voxel; default 96³ adapt 0.5 (6.8 k–24 k tris); REMESH SHARP descartado (non-manifold, `sdf_dev` p95 3–34 voxels); nenhuma peça < 2 voxels nas 5 (PIPELINE §28.L10-2).

**Estado L10-6 (2026-10-29): feito** — `mesh_lint.shape_report`/`sdf_field`, `lint(sdf=True)` em `review.md ### Forma` e `compare_runs` FORM; baseline nos 5 clays v12 (p95 `sdf_dev`: união crua 0.35-1.1 % H, clay final 2.4-3.9 % H; PIPELINE §28.L10-6). Só relatório, sem gate.

**Estado L10-3 (2026-10-29): feito, aceite parcial** — `tools/blender/retopo.py` (QEM em rodadas de conjuntos independentes + guarda 15°/normal/link + reprojeção SDF + guarda de desvio H/50), `retopo_mc.py`, `retopo_blender.py`, `retopo_ablate.py`, `tests/tools/blender/test_retopo.py` (PIPELINE §28.L10-3). 600 tris em 0.8–2.7 s (n00U 123 k tris); sliver 0.0–0.5 % (5/5; COLLAPSE cego 6–24 %), sdf_dev p95 ≤ 1.44 % e máx ≤ 2.87 % de H (5/5), nd −15/−7/−13/−19/−15° vs união (4/5), IoU ≥ raw −0.01 em 4/5 (hfoo left −0.013), euler = o da entrada (0/12/0/0/8). Faixa 60–100° 20.6–27 % (alvo 10–20 %: não). Features de aresta viva (35°) pioram tudo e ficam desligadas por default; heap trocado por rodadas (9.7 s → 0.8 s).

**Estado L10-5 (2026-10-29): feito** — `sdf_body.weights` / `materials` / `near_distances`, `build_unit.sdf_body_object` + `skin_sdf` (não chamados pelo `main()`, L10-7), `sdf_extract.py skin=1`, testes `Skin`; nas 5 unidades `skins 1`, `components_body 1`, fechada, `max_dup_split 0`, 7 clipes/engine_import ok, zonas dentro de ±0.01 (dois ganhos de +0.012/+0.014); esticão p99.5 ≤ 1.1× a união em 14 de 15 medidas, exceção n017 `walk` 1.22× (PIPELINE §28.L10-5).

**Estado L10-4 (2026-10-29): feito, aceite parcial; default NÃO muda** — `retopo.remesh` / `retopo.retopo(method=)` (PIPELINE §28.L10-4): remalhagem isotrópica Botsch–Kobbelt (split/collapse/flip/relax/projeção SDF, rodadas vetorizadas, `Shorts` reaproveita o `Reducer`), 600 tris em 1.1–5.2 s. fairness 24.0 → 12.1 (n00U 20.1), slivers 0, nd 34.5 → 29.8, faixa 60–100° 13.4 %; mas sdf_dev p95 1.47 % / máx até 3.31 % (n00U) e IoU hfoo `left` −0.056: aceite completo só em 2/5 (n005, n02X). Híbrido (remesh + QEM curto) fairness 15.4, máx 4.1 % no n00U. `METHOD = "qem"`; juiz `review_pair` não rodado (retopo ainda fora do `build_unit`).

**Estado L10-7 (2026-10-29): feito, default segue `union`** — `build_unit.BODY` / `body=` / `sdf_union` (`sdf_dense` → `sdf_retopo` → `skin_sdf`), `sdf_body.thin_inflation` + `field(thin=)`, `spec_pipeline --body`, `colour_stage.body_args`, `tests/tools/blender/test_body_sdf.py` (PIPELINE §28.L10-7). Nas 5 unidades (sem LLM, deform + fit-verts): IoU f/l/b ≥ v12 −0.01 5/5 (left ≥ em 5/5, rts ≥ em 3/5, média 6 vistas +0.002…+0.018), slivers crus 0–2.3 % e finais 0.3–5.7 % (hfoo 5.7: 4/5 < 5 %), nd −6…−12°, build 1–3.6 s, `--body union` byte-idêntico (5/5), esticão ≤ união em 14/15. `unsafe` 0 → 0 (−50 % não mensurável). Peça fina: `inflate` default (n00H/n010), `keep` custa 229 tris; k = 1 (k0/k2 ≤ 0.003 de IoU). Texturizado (T1 compacto, T5 merge) confirmado sobre materiais por face. Default `sdf` recomendado para a v13 (L10-9).

**Estado L10-8 (2026-10-29): feito** — `tools/blender/sdf_batch.py` (`--units/--body/--jobs/--grid/--collect-only/--compare`, tabela markdown + `l10-batch.json`), `anim_check.py`, `spec_pipeline --tilts/--sdf-grid`, `build_unit.drop_specks` (ilha de 12 tris do n00U), `tests/tools/blender/test_sdf_batch.py` (PIPELINE §28.L10-8). Existem 10 unidades (17 specs = versões de 8 + n01I/n01N), **10/10 constroem**, build médio 1.9 s (máx 3.5 s); slivers finais 0.0–5.7 % (união 8–32 %), nd −2…−13°, componentes ≤ união 10/10, IoU médio das 6 vistas sdf − união +0.002…+0.023 (10/10 ≥ 0), esticão ≤ união em 23/30. Aceite por rig: 5/10 (n005 nd −9.5° em vez de −10; n01X −7.6 e n01I −5.4; hfoo sliver 5.7 % do deform; n00U rts −0.0009 = empate); wyrm/drake: plates todas presentes (a plate 7 do n010 está enterrada no spec, igual na união) e left/top ≥ união −0.01 a 96³ e 128³. Default segue `union` (L10-9).

Ordem: L10-1 → L10-2 → {L10-3 ∥ L10-5 ∥ L10-6} → {L10-4 ∥ L10-7} → L10-8 → L10-9 (~8–9 h + bateria).

**Estado L10-9 (2026-10-29): feito, `BODY = "sdf"` default** — bateria `v13-r1` (5 unidades, session:opus, `--body sdf`, pareada contra v12) + controle `v13-r1-union` no mesmo spec (PIPELINE §28.L10-9, `history/2026-10-29-v13/`). PASS 3/5 (v12 2/5), slivers 0.9–5.4 % (v12 9–32 %), nd −5…−16°, lint limpo 3/5 (v12 0/5), juiz forma pró v13 5/5, artista 4-0 5/5. No mesmo spec a média das 6 vistas sobe em 3/5 (até +.025) e desce ≤ .004 em 2/5; custo real: rts −.03 em hfoo/n017 (smin engorda juntas). hfoo left .415 e n02X left −.048 são do spec (união igual). Critérios estritos 3/5 (comp do n00U é do spec; vista −.03); decisão de líder: default sdf, `--body union` opcional. Bug corrigido: pré-spec de massing sem `rig` para aranha (construía como biped).

**Leva 10 fechada (2026-10-29).** Ficha `IA_gen_paper/melhorias/09-leva10-2026-10-29.md`. Aberto para a Leva 11: `k` por junta, deform/fit-verts sobre a malha SDF (sliver hfoo, nd n005), peças do spec sem contacto, fit_stage/zonas/propid ainda em união.

# Leva 11 (a planejar depois da Leva 10) — DFS: VLM no loop sobre o modelo

Decisão do usuário (2026-10-29): a fase D da proposta externa (renderizar clay/wire/overlay → VLM compara com o sheet → deltas
semânticos `{"part","action","value"}` aplicados como restrições de volume → mais passos de otimização) vira a Leva 11, só depois
de a Leva 10 fechar a forma one-shot (BFS). Ideias dos geradores (Meshy T2 e cia) continuam só como ideias. Planejar com: saída
estruturada por parte (escala/translação/rotação por eixo), N rodadas máximas, juiz pareado contra a rodada 0, custo por unidade,
e critério de parada (nenhuma vista cai, forma sobe no juiz).

**Plano (2026-10-29, aguarda aprovação do usuário):** `analysis/2026-10-29-leva11-vlm-loop.md`. Laço guardado sobre o que já
existe (`diagnose.py`, `repair`, `fit_grad`, corpo sdf em 1–4 s, câmeras fixas): o VLM devolve deltas por peça num schema fechado
com limites, cada rodada só é aceite se nenhuma vista cair > 0.01, N ≤ 2, juiz pareado contra a rodada 0.

| # | item | aceite |
|---|---|---|
| L11-0 | flip lateral medido em `silhouette.py` (BFS, pré-requisito: hfoo left é sheet espelhado) | hfoo left .415 → ≥ .60 sem mudar o spec; outras 4 ± 0.005 |
| L11-1 | schema de deltas + `apply_deltas.py` com peças congeladas e limites | 10 deltas sintéticos aplicam; fora de limite rejeitado |
| L11-2 | laço guardado `--loop N` (rebuild sdf, aceite por rodada, log por delta) | nenhuma vista cai na rodada aceite; ≤ 3 min/rodada |
| L11-3 | deltas como restrições do `fit_grad` (ablação contra edição do spec) | vence a via que sobe a média sem queda |
| L11-4 | bateria v14 (`--loop 2`, pareada contra v13) + ficha 10 | PASS ≥ 4/5; média ≥ v13 5/5; juiz forma ≥ 3-1 em ≥ 3/5; ≤ +4 min/unidade |
| L11-5 | `k` do smin por junta (custo real do sdf: rts −.03 em hfoo/n017) | rts ≥ união −0.01 no controle `v13-r1-union` |
| L11-6 | retopologia Voronoi/CVT guiada por curvatura (`retopo.cvt`, Chatterjee et al. ICVGIP'22) | slivers finais < 5 % 5/5, nd ≤ qem +1°, IoU ≥ qem −0.01 em todas as vistas, euler = entrada, ≤ 5 s |

Ordem: L11-0 → L11-1 → L11-2 → {L11-3 ∥ L11-5} → L11-4.

**Estado L11-4 (2026-10-29): feito, `--loop` opt-in** — bateria `v14-r1` (5 unidades, session:opus, `--loop 2`, pareada contra v13) + controle `v14-r1-clock` (PIPELINE §29.L11-4, `history/2026-10-29-v14/`). PASS 3/5 (= v13); laço aceitou 1 delta em 19 (hfoo +.033), 14 rejeitados por queda de vista; juiz forma pró-v13 em 3/5 (4-0); `--deterministic` (8 iterações) custa +.020 (n00U) e +.012 (n017) de média contra o relógio. Critérios do L11-4: 0 de 4. Decisão: laço e determinístico opt-in; abertos: iterações = passos do relógio, magnitude dos deltas por busca de linha, laço depois do polimento MCP (Leva 12).

Extras pedidos pelo usuário (2026-10-29): **L11-6** retopologia CVT por curvatura (Chatterjee, Soni, Bhowmick, ICVGIP 2022, DOI 10.1145/3571600.3571623) como 3ª via contra QEM/remesh; **L11-7** matriz de ablação de TODOS os opt-ins (sozinhos, depois vencedores combinados; tabela para o paper em `IA_gen_paper/ablation-matrix-2026-10-29.{csv,md}`).

**Estado L11-1 (2026-10-29): feito, atrás de nada (módulo novo + `deltas`/`expected` no diagnose).** `tools/blender/apply_deltas.py`
(`apply(spec, deltas, height) -> (spec2, log)`, endereço `<osso>#<k>`), 10 testes sintéticos, diagnose pede `deltas`+`expected`.
4 diagnoses reais: 18 de 19 deltas aplicam, 1 rejeitado (axis scale em peça from/to). Rebuild sdf sem LLM em hfoo e n02X: média das
6 vistas −.004 e −.007 contra o rebuild do spec original; o guarda de L11-2 rejeitaria as duas rodadas (vista cai > .01).
Detalhe: PIPELINE §29.L11-1.

**Estado L11-5 (2026-10-29):** `sdf_k_mode=base|class|hard|ext` / `--sdf-k-mode` (PIPELINE §29.L11-5). Nenhuma variante passa o aceite limpo: `hard` (k = 0) é a melhor (slivers < 5 % em 5/5, hfoo/n017 dentro de −.01 da união) mas piora nd +2.4…2.7° e n00U top −.015; `class` perde hfoo rts −.015; `ext` tem a mesma malha que `base` (no-op). A queda de rts −.03 não se reproduz na linha mínima (D já a −.011 no pior caso; ruído entre builds ±.02). Default segue `base`; `hard` opt-in.

**Estado L11-0 (2026-10-29):** causa medida = nem (a) nem (b)/(c): o `silhouette.py` já escolhia o espelho no left e fit/deform/verts já usavam a mesma escolha, mas a escolha era ERRADA — o pique diagonal do sheet alarga o bbox e a variante espelhada ganha por alinhamento de bbox (hfoo left espelho .409 × normal .344; com deslocamento livre normal .664 × espelho .530; pack atrás no normal). Implementado `silhouette.pick_variant` (IoU no melhor deslocamento, margem .05) + `"flipped"` no `silhouette.json`/`review.md`, opt-in `--flip-side` (PIPELINE §29.L11-0). NÃO atendido: hfoo left ≥ .60 (com orientação certa .32–.43 sem deslocar: o enquadramento por bbox + pique vertical × diagonal domina; pique diagonal no spec, .321 → .464 mas rts .711 → .588). Outras 4 unidades: mesma decisão em 12/12 vistas. Fica desligado; a correção real é de spec (pose do pique) e de enquadramento pelo corpo, para L11-1/2.


**Estado T1 (2026-10-29):** `--atlas compact` (`build_unit.COMPACT_ATLAS`, `surfaces.pack_cells/tone_cell`), opt-in (PIPELINE §27.T1). Imagem ≤ 128² e `atlas_kb` ≤ 8 nas 5 unidades (n005 768² 83.9 KB → 128² 5.2 KB), `uv_out_of_range 0`, olhos legíveis; `zones mean` cai no máximo .011 (n005 left) e `luma_l1` sai de ±.003 em 8 de 15 vistas (6 melhoram, 2 pioram .004/.007): default NÃO virou, falta decisão sobre o decal de figura (32 px).

**Estado T6 (2026-10-29):** `mesh_lint.mip_bleed` (PIPELINE §27.T6): 0 texels mistos em 1/2 e 1/4 nas 5 unidades compactas; 1/8 tem 12-20 (células planas de 4 linhas), zerado com `pack_cells(align=8, pad=2)`. Só relatório.

**Estado T5 (2026-10-29):** `build_unit.merge_materials` + `surfaces.merge_groups`, default ligado em cel (`--materials split` restaura; PIPELINE §27.T5). Prims 7 -> 2 (n005), 8 -> 2, 4 -> 1, 5 -> 2, 7 -> 1; fica 2 onde há flame/glow (emissivo próprio, não funde); gates e clipes iguais, render com ruído <= 7/255 em <= 16 px. Aceite "1" só onde não há emissivo.


**Estado T3 (2026-10-29):** `--atlas shared` agora 128² com decais (PIPELINE §27.T3): faixa de tom 64 colunas de 2 px + células de decal first-fit (append-only, hash do decal + coluna). `images == 1`, `luma_l1` ±.008 (14 de 15 vistas; n017 l/b +.006/+.007), `zones mean` ≥ −.0001; juiz sem 4-0 contra no eixo sheet (n005/n02X empate; hfoo/n00U/n017 B 4-0). NÃO atendido: ≤ 4 KB por raça no Human (união ~5 KB com PIL). Segue opt-in.

**Estado T7 (2026-10-29):** `race_palettes.json` (dos ícones) + `palette_hint` no brief de cor (só com `--atlas shared`) + `snap`/`palette_snap` (opt-in, desligado: junta 0 colunas e trocou a cor das botas do hfoo). Simulação: 10-16 unidades/raça em 128², NÃO ≥ 16 (PIPELINE §27.T7).

**Estado L11-3 (2026-10-29): feito, atrás de flag (`--constraints`); resultado negativo.** `apply_deltas.fit_limits` + `fit_spec.fit(constraints=)` traduzem
scale/radius/move em limites por peça; ablação A (edição do spec) × B (limites do fit) × base em 4 unidades: nenhuma via sobe a média de forma
confiável (A +.0072, B +.0042 somadas; quedas > .01 em 3 unidades nas duas). Recomendação ao L11-2: via A como default. Detalhe: PIPELINE §29.L11-3.

**Estado L11-2 (2026-10-29): feito, atrás de `--loop N` (default 0).** `tools/blender/loop_stage.py` + `spec_pipeline --loop`; rebuild pelo caminho da
rodada 0 com `--deterministic` (fit-verts por iterações: o relógio dava +-.013 por vista; dois rebuilds agora idênticos). Prova hfoo/n017/n02X:
1 delta aceito em 9 (hfoo média .7517 -> .7600, nenhuma vista cai > .01); n017 e n02X 0 aceitos. 85-306 s por delta. Detalhe: PIPELINE §29.L11-2.

- **L11-0b (2026-10-29) Estado:** `--frame body` implementado e medido (5 un., PIPELINE §29.L11-0b), opt-in. NÃO atendido: hfoo left .428 -> .458 (alvo .60), n005 left -.34, n02X front -.19: o corpo do modelo (maior componente) não é o corpo do sheet (props de parts.json). Default segue `bbox`.

# Leva 12 (a planejar depois da Leva 11) — polimento final por Blender MCP, alguns minutos por modelo

Decisão do usuário (2026-10-29): todo modelo recebe no fim alguns minutos de melhorias grossas feitas por um agente ligado ao Blender
via MCP, com brief fixo, orçamento de tempo, script `polish.py` gravado e os mesmos gates (nenhuma vista cai > 0.01). Plano:
`analysis/2026-10-29-leva12-mcp-polish.md` (L12-0 instalar/ligar MCP + cena de revisão; L12-1 contrato do estágio; L12-2 prova em 3
unidades; L12-3 bateria v15). Fonte: Pokorný, WSCG 2026 (`docs/references.md`). Aguarda o fecho da Leva 11 e o "aprovado".

**Estado L11-6 (2026-10-29): feito, atrás de `--sdf-retopo cvt` / `retopo(method="cvt")`; aceite NÃO atendido.** `retopo.cvt` (Lloyd geodésico, ρ = (ε+κ)^α, dual das células, qef + projeção no SDF; numpy puro, 0.2–2 s). Contra o rebuild qem nas 5 unidades: slivers finais < 5 % 5/5, nd −3…−5°, fairness 24–27 → 17–19; mas 6 vistas caem > .01 (até −.028) e o euler muda em 3/5 (alças finas se perdem). Default segue `qem`. Detalhe: PIPELINE §29.L11-6.
