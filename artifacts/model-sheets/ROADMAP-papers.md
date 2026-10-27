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

Cinco geradores geométricos cobrem as 28 famílias de rig: `lathe` (existe), `limb` (existe), **`chain`** (novo: 14 famílias com `_chain`), **`plate`** (novo: asas em 8 famílias, placas, lagartas, carapaça), `wheel/ring` (existe). Ordem: L4-1 `chain` → L4-2 `plate` → L4-3 fit hierárquico + piso por vista/família (independente) → L4-4 sheets + massing de quadruped/serpent/drake → L4-5 baseline cruzado 6-10 unidades → L4-6 `joint_place` (landmarks de junta) → L4-7 experimento 3 caminhos (baseline / procedural / IA como registro, TripoSR+TRELLIS.2 só n00U e n01X) → DFS: diagnóstico LLM só em CHECK. Briefs dos 3 primeiros no arquivo de análise.
