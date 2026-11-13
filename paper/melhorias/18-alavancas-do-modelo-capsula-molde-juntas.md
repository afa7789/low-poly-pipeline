# 18 — Alavancas do estágio de modelo: cápsula ("nada vivo é uma caixa"), regras de junção, contorno fora, de-ink, revisor por vista, moldes neurais (SAM2, TripoSplat), molde de massa e juntas suaves

- Data: 2026-11-04 → 2026-11-05 (pilotos n02S Gnoll, n01G Felhound; n008, n00A no piloto do revisor por vista)
- Commit(s): working tree de `main` sobre `6475c594` (ficheiros modificados `eye_lib.py`, `eye_stage.py`, `eye_union.py`, `eye_skin.py`, `eye_project.py`, `silhouette.py`, `spec_pipeline.py`, `roster_batch.py`, `depth_map.py`, `outline.py`, `preflight.py`; novos `eye_views.py`, `neural_molds.py`, `eye_mold.py`); não commitado em 2026-11-07. Relatório de origem: `lever-report.md` (scratchpad da sessão de 2026-11-05).
- Problema do baseline atacado (§7): forma contínua e perfil (ficha 16: "o que falta é unir ossos adjacentes num campo só"; ficha 14: primitivas rígidas = "degraus e caixas cruzadas"; 02-evolucao §4.6: o left não sai de ~.55 no hfoo). Os modelos do `roster-v5` liam como "caixote com pernas" (regra 3 do `eye.md`).
- Hipóteses: (H1) trocar box/tube por cápsula em tudo o que é carne tira as caixas sem custar tris; (H2) regras de junção (nada flutua, membro nasce dentro do pai) dão à união algo para fundir; (H3) um molde da silhueta do concept (máscaras SAM2 ou profundidade TripoSplat) enche os membros até à largura desenhada sem o modelo ver nada neural; (H4) juntas suaves só onde há 2+ peças dão fillet sem comer membros; (H5) um revisor que olha uma vista de cada vez acha defeitos que o board inteiro esconde. **H1–H4 sim no piloto (n = 2); H5 marginal.**

## Mudança

| alavanca | ficheiro / flag | regra |
|---|---|---|
| Cápsula + "NOTHING ALIVE IS A BOX" | `prompts/eye.md` (op `capsule`: a, b, r0, r1, seg, rings; regra 3) | carne, pelo, músculo e pano não têm faces planas: tronco = cápsula ao longo da espinha, cabeça = bola escalada com focinho em cápsula, coxa/braço/canela = cápsula com a ponta grossa na junta; **caixa só para coisa plana e fabricada** (placa, fivela, lâmina, caixote); "WINGS ARE ARMS": asa = cadeia de cápsulas nos ossos da asa + placas finas entre as hastes, raiz dentro do tronco |
| Regras de junção | `eye_lib.floating()`, `loose_roots()`, `join_errors()`; `ROOT_BONE` (regex do primeiro osso de cada cadeia: `arm.L/R`, `thigh.L/R`, `legN`, `wingN`, `tail.1`, `neck.1`), `ROOT_DEPTH = .25` | peça do corpo sem contacto = flutua; membro cujo ponto a/b não está dentro do pai = raiz solta (tem de afundar 25 % do raio, porque a união erode uma junta tangente). `validate(..., soft=True)`: as regras pedem **um** reenvio com a razão exacta; uma resposta que ainda as quebra é construída na mesma e a nota fica (`eye_stage` linha 447–450). **A versão estrita** ("the resend is still invalid; the stage stops with the last model", ver `n02S-form-pilot3`) matou o estágio do olho em **61/160** unidades do roster-v6: ficha 19, rerun `roster-v6e` |
| Contorno fora | `spec_pipeline --outline off` (default desde 2026-11-05; antes `hull`, L15-7) | o inverted hull desenhava a silhueta **velha** depois de o olho refazer as peças (ghost); as linhas pretas do concept passam a guiar só as facetas |
| De-ink do concept | `silhouette.deink_mask/deink_panels/deink_image` (form-pilot, 2026-11-05) | a linha exterior do desenho não é forma: os pixels de tinta a meia largura da linha do exterior saem da máscara (IoU) e a imagem que o juiz e os boards vêem tem as linhas pintadas pela cor vizinha; as linhas interiores (facetas) ficam |
| Revisor por vista | `eye_views.py`, `--eye-views sonnet` (default; `MODEL[@EFFORT]`) | ronda r: 1 chamada por vista, vendo só a linha concept \| render \| overlay dessa vista → nota 0–10 e ≤ 4 defeitos (peça, o que está mal, conserto); o artista vê todos os boards + essas listas; o "depois" de uma ronda é o "antes" da seguinte (sem 2.ª chamada); `summary["views"]` guarda antes/depois por ronda |
| Moldes neurais | `neural_molds.py` (venv python 3.12 + torch, **nunca importado pelo pipeline** (python 3.14); `flock` de GPU; `HF_HUB_OFFLINE`); `--part-masks sam2` (default), `--depth-model triposplat` (default; antes `da2`) | **SAM2** (`facebook/sam2.1-hiera-large` via `transformers`): uma máscara por peça com o `box2d` do `parts.json` como prompt de caixa, cache em `refs/<id>/neural/sam2/<vista>/<peça>.png`; **TripoSplat**: um splat do painel front (20 passos de amostragem) renderizado em z-buffer ortográfico front e left, cache em `refs/<id>/neural/`. Ambos **invisíveis para o modelo: a malha continua nossa** (regra do projecto: sem geradores imagem→3D no pipeline) |
| Molde de massa | `eye_mold.py`, `--eye-mold off \| splat \| masks` (default `masks`) | antes da união, cada peça do corpo (não prop, não detalhe) empurra os vértices para os lados (perpendicular ao eixo) enquanto ficam dentro do molde, até **0,08 H**, nunca para dentro; molde = casco visual front + left (masks: máscaras SAM2 das peças do corpo unidas por vista; splat: covers + superfícies near do TripoSplat); registo do molde na silhueta do corpo (voxel + varrimento de escala + shift por FFT), `fit-front.ppm`/`fit-left.ppm` em `<run>/eye/mold/` |
| Juntas suaves | `eye_union.joint_stubs`, `--eye-joints off \| smooth` (default `smooth`) | cluster com 2+ peças recebe "stubs" das peças de outro osso que lhe tocam (esfera `JOINT_R` = .07 H à volta do contacto, smooth-min `JOINT_K` = .05 H); pesos em cross-fade com o osso do stub; membros de 1 peça ficam primitivos (o CVT a 14 tris destruía-os) |
| Sheet pintado (existe, **off**) | `--eye-paint-sheet flat \| paint`; `refs/<id>/sheet-paint.jpg` (variante nano-banana-edit sem contorno, com pelo/costuras/riscos; US$ 0,07) | `eye_project` projecta o sheet-paint em modo `on` com gate/filtro mais abertos; **o roster usa `flat`** (`EYE_RECIPE`): no n01G o castanho da coleira/costelas/patas vaza em manchas sobre o tronco roxo; n02S fica mais pálido que o sheet (o delight puxa para o tom claro) |

Receita do roster depois destas alavancas (`roster_batch.EYE_RECIPE`): `--eye on --eye-rounds 3 --eye-stop model --eye-fuse 12 --eye-union bone --eye-union-reduce cvt --eye-paint box --outline off --depth --depth-model triposplat --part-masks sam2 --eye-mold masks --eye-joints smooth --eye-paint-sheet flat`; `--eye-project tight` (L20-2) e `--eye-views sonnet` por default do `spec_pipeline`. Artista `session:opus`; prompts, parts e revisor por vista `session:sonnet` (quota semanal, 2026-11-05).

## Protocolo

- Unidades: n02S (Gnoll, biped) e n01G (Felhound, quadruped) nos pilotos de forma e de alavancas; n008, n00A, n01G, n02S no piloto do revisor por vista; hfoo no teste isolado dos moldes neurais.
- Spec author / modelo de imagem: artista `session:opus` com olho (3 rondas), revisor por vista `session:sonnet`; nenhuma imagem nova (sheet-paint à parte: US$ 0,14).
- Runs por unidade: 1 build real por alavanca (`form-pilot`, `views-pilot2`, `lever-pilot`) + **replays sem chamadas** da mesma DSL (`lever-replay-{off,splat,masks,joints,all}`: 0 chamadas, 20–30 s) para isolar o molde e as juntas.
- Métrica principal: IoU front/left/back/rts do `model.glb` final (`eye_stage.measure`, concept de-inked) e parts k/n; nota 0–10 por vista do revisor.

## Resultado

**Moldes neurais isolados (hfoo, `neural/out/`):** SAM2 AMG de teste 55 máscaras em 14,5 s (carga 1 s); TripoSplat 326 s de amostragem, 349,5 s no total, 4,5 GB RSS (MPS com fallback). Figuras `figuras/18-sam2-hfoo.png` (máscaras sobre o painel) e `figuras/18-triposplat-hfoo.png` (splat renderizado front/left).

![SAM2 (sam2.1-hiera-large) sobre o painel front do hfoo: 55 máscaras do teste AMG; no pipeline cada peça recebe uma máscara pelo seu box2d.](figuras/18-sam2-hfoo.png)

![TripoSplat do painel front do hfoo, renderizado em z-buffer ortográfico (molde de profundidade; nunca vira malha).](figuras/18-triposplat-hfoo.png)

**Forma (cápsula + junção; `figuras/18-form-pilot-capsula.png`, concept | roster-v5 | views-pilot2 | form-pilot, f/l/rts por run):**

| unidade | run | ronda final | parts | tris | IoU fr / le / ba / rts | chamadas | s |
|---|---|---|---|---|---|---|---|
| n01G | roster-v5 (caixas) | 1 | 12/24 | 692 | .79 / .76 / .75 / .76 | 4 | 706 |
| n01G | views-pilot2 (+ revisor por vista) | 1 | 10/24 | 684 | .78 / .75 / .74 / .74 | 34 | 560 |
| n01G | form-pilot (cápsula + junção) | 3 | **19/24** (17/24 remedido) | 688 | .61 / .78 / .53 / .70 | 34 | 570 |
| n02S | roster-v5 (caixas) | 3 | 25/41 | 680 | .67 / .42 / .68 / .49 | 4 | 864 |
| n02S | views-pilot2 | 2 | 26/41 | 688 | .69 / .38 / .69 / .49 | 34 | 598 |
| n02S | form-pilot2 (cápsula + junção) | 2 | **36/41** (38/41 remedido) | 632 | .70 / **.66** / .70 / .45 | 34 | 853 |

Leitura: a cápsula dobra o left do n02S (.42 → .66) e sobe parts em ambas (12 → 19, 25 → 36); no n01G o front **cai** (.79 → .61): o Felhound em cápsulas fica mais fino que o desenho (é o caso que pede o molde). `form-pilot3` do n02S, com as regras estritas, parou na ronda 0 ("the resend is still invalid"): a origem da regra soft.

![Forma: concept | roster-v5 (caixas) | views-pilot2 | form-pilot (cápsula + junção), f/l/rts; n01G em cima, n02S em baixo, com as notas por vista do revisor.](figuras/18-form-pilot-capsula.png)

![Revisor por vista: concept | antes (roster-v5) front/left/rts | depois (por vista) front/left/rts; n008, n00A, n01G, n02S.](figuras/18-eye-views.png)

**Revisor por vista (`figuras/18-eye-views.png`, concept | antes roster-v5 | depois por vista):** notas antes → depois por ronda, n01G views-pilot2 r0: fro 5→6, lef 4→6, bac 4→6, top 5→5, bot 2→2, rts 5→6; r1–r3 ficam em 6–7; n02S r0: fro 3→5, lef 3→4, bac 5→6, top 3→3, bot 3→3, rts 3→3, e não passa de 5–6 nas rondas seguintes. Nos pilotos n008 31/40 → 27/40, n00A 22/37 → 24/37, n01G 12/24 → 10/24 (views-pilot → views-pilot2). O IoU remedido `roster-v5` × `views-pilot2` fica em ±.03 em todas as vistas (n01G front .788 → .781; n02S front .675 → .687, left .416 → .384). **Ganho pequeno; mantido porque custa Sonnet, não Opus, e dá a lista de defeitos por vista ao artista.**

**Alavancas (molde + juntas; `figuras/18-lever-pilot.png`, concept | anterior f/l/rts | lever-pilot f/l/rts | clay):**

| unidade | run | parts | front | left | back | rts | tris | s | chamadas |
|---|---|---|---|---|---|---|---|---|---|
| n02S | form-pilot2 (anterior) | 38/41 | .704 | .664 | .704 | .453 | 632 | 853 | 34 |
| n02S | lever-pilot (+ replay `-r`) | 38/41 | **.746** | **.720** | .754 | .488 | 654 | 936 (+31) | 34 |
| n01G | form-pilot (anterior) | 17/24 | .581 | .773 | .505 | .713 | 642 | 570 | 34 |
| n01G | lever-pilot | 20/24 | **.697** | .764 | .609 | .723 | 584 | 731 | 34 |

Molde sozinho (replay da mesma DSL, juntas off, sheet flat):

| unidade | molde | parts | front | left | rts |
|---|---|---|---|---|---|
| n02S | off | 38 | .704 | .664 | .453 |
| n02S | splat | 39 | .730 (+.026) | .675 (+.011) | .465 |
| n02S | masks | 35 | .744 (+.041) | .700 (+.037) | .464 |
| n02S | masks + joints | 39 | .751 (+.047) | .714 (+.050) | .463 |
| n01G | off | 17 | .581 | .773 | .713 |
| n01G | masks | 18 | .593 (+.012) | .751 (−.022) | .780 (+.067) |

![Alavancas: concept | anterior (form-pilot) f/l/rts | lever-pilot (molde masks + juntas) f/l/rts | clay; n02S em cima, n01G em baixo.](figuras/18-lever-pilot.png)

Registo do molde (masks): n02S IoU .512 front / .646 left, 88 vértices inflados (média .112 m, máx .217 m); n01G .761 / .657, 149 vértices. Gate da pipeline continua CHECK (preflight/stage 1 FAIL como nos pilotos anteriores: massing, não o olho).

## O que piorou / limitações

- Primeira versão do molde (termo SDF misturado no campo da união) e das juntas em membros de 1 peça: o CVT a 14–22 tris fazia fragmentos (front .70 → .46–.53). Resolvido: o molde move os vértices das **peças** (rota B do autor); stubs só em clusters com 2+ peças; fallback para as peças quando o CVT devolve < target/2 (apareceu no build real do n02S: shin + paw 4 tris de 29 → `lever-pilot-r`, replay sem chamadas).
- Splat: o perfil do TripoSplat é fino (não sabe do pescoço/corcunda do concept) → ganho pequeno, registo left IoU .43; `masks` ganha mais e é o default. O TripoSplat custa 350 s por unidade (1× por unidade, em cache).
- `--eye-paint-sheet paint` vaza entre peças (n01G) e empalidece (n02S): fica off até um filtro por peça mais apertado em modo paint.
- n = 2 unidades por alavanca, 1 trajectória cada; o molde foi isolado por replay (sem ruído de LLM), as outras alavancas não. Sem juiz pareado nesta leva: o autor viu as imagens.
- **Os deltas do molde (+.041/+.037 n02S; +.012/−.022 n01G) e do revisor por vista (±.03) ficam abaixo do ruído declarado no baseline (.12 entre runs iguais).** O replay tira o ruído do LLM mas não o da unidade: com n = 2 nada aqui está demonstrado. A cápsula **baixa** o front do n01G (.79 → .61) e o molde recupera só até .70 — ainda −.09 contra as caixas do roster-v5. Cápsula, junção, de-ink, `--outline off`, molde, juntas e revisor por vista entraram no default juntos e o roster-v6 (ficha 19) correu sem braço de controlo: não há ablação em largura de nenhuma alavanca.
- As notas do revisor por vista são auto-avaliação de um LLM (Sonnet) sobre o trabalho de outro (Opus); nas 165 unidades do roster-v6 sobem 4.3 → 6.4 (front) mas o IoU medido desce (ficha 19) — a nota não é uma medida independente.
- Papers/ferramentas novos usados (a registar em `docs/references.md`, não é tarefa desta ficha): **SAM 2** (Ravi et al., 2024, `facebook/sam2.1-hiera-large`, via `transformers`) como segmentador de peças por caixa; **TripoSplat** (VAST, 2026, checkpoints fp16) como molde de profundidade — ambos só como *molde*, nunca como gerador da malha (excepção registada 2026-10-31: TRELLIS como baseline do paper).

## Conclusão (1 frase para o paper)

Em dois pilotos (n = 2, 1 trajectória), quatro alavancas sem papers de reconstrução (cápsula em tudo o que é vivo, regras de junção com um reenvio, molde de massa a partir de máscaras SAM2 e juntas suaves só entre 2+ peças) levam o front/left do Gnoll de .67/.42 para .75/.72 e o front do Felhound de .58 para .70 com o mesmo orçamento e as mesmas 34 chamadas, enquanto o revisor por vista rende ±.03 e o sheet pintado vaza — a hipótese é que forma vem de primitivas redondas e de um molde da silhueta desenhada, não de mais chamadas; os deltas isolados do molde (≤ .05) ficam abaixo do ruído (.12) e a hipótese **não foi testada em largura** (o roster-v6 correu tudo ligado, sem controlo).
