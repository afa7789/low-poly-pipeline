# Papers de renderização diferenciável × pipeline de modelos (2026-10-27)

Fonte: 12 PDFs em `~/Desktop/Differentiable_Rendering_DOIs_20261021/` (lidos com `pdftotext`). Estado do pipeline lido de
`PIPELINE.md` §19–§25, `ROADMAP-papers.md`, `docs/references.md` e dos módulos `fit_spec.py`, `deform_to_sheet.py`,
`optimize_verts.py`, `align_features.py`, `silhouette.py`, `spec_pipeline.py`. Restrições respeitadas: BFS one-shot, nenhum
gerador image-to-3D, nenhum treino de rede, nenhum loop LLM→modelo; renderização diferenciável **como otimizador interno** é bem-vinda.

## 0. Diagnóstico em uma frase

O pipeline **já faz** otimização por silhueta (fit paramétrico `fit_spec` com Powell, deformação `deform_to_sheet`, vértices
`optimize_verts`), mas todas usam **raster duro + gradiente numérico**: `optimize_verts.iou_gradient` re-rasteriza o 1-anel de
cada vértice por diferença finita (1–2 s por gradiente, 120 s/unidade, por isso `FIT_VERTS = False`); `fit_spec` gasta até
4000 avaliações Powell (~10 ms cada, 30–150 s). Os papers 01/02/03/11/12 dizem exatamente como trocar isso por um
**gradiente analítico** (soft rasterizer): mesma função objetivo, 10–50× mais barato, com sinal também para vértices longe do
contorno. É o único ganho grande e seguro desta lista; o resto são ideias pontuais (regularizador de diedro, perda
assimétrica vermelho/verde, shading diferido para a luma) ou ruído (5 papers fora de domínio).

Ambiente medido: Apple M4 Pro, 24 GB; `python3` tem **torch 2.14.1 com MPS**; `python3.14` (o que roda `tools/blender/*.py` sem
Blender) **não tem torch**; PyTorch3D, nvdiffrast, Mitsuba, JAX ausentes. nvdiffrast = CUDA (não roda no Mac). PyTorch3D compila
em CPU no Mac, mas é pesado e CUDA-cêntrico. Recomendação: **soft rasterizer próprio em torch puro** (~150 linhas; malhas de
600–800 tris, canvas 256×384, janela por triângulo), chamado via subprocess do `python3` com torch ou instalando torch no 3.14.

## 1. Tabela: paper → técnica → cobertura no pipeline

| # | Paper (ano) | Técnica central | Já coberto? | Onde |
|---|---|---|---|---|
| 01 | Soft Rasterizer, Liu et al. (ICCV 2019) | Mapa de probabilidade por triângulo `D_j = sigmoid(δ·d²/σ)`; silhueta = `1 − ∏(1 − D_j)`; cor por softmax em profundidade (γ); gradiente flui a triângulos ocultos e distantes; σ/γ grandes suavizam a paisagem (scheduling) | **parcial** | `optimize_verts` tem o mesmo objetivo (1 − IoU + chamfer + Laplaciano) mas gradiente por diferença finita local; nenhum `σ` (raster duro 4×) |
| 02 | Neural 3D Mesh Renderer, Kato et al. (CVPR 2018) | Forward duro, gradiente aproximado por interpolação linear até a próxima aresta, só na direção que reduz a perda; perda IoU (Eq. 5) + suavidade de diedro `Σ(cos θ + 1)²` (Eq. 6); edição de malha por gradiente | **parcial** | A diferença finita de `optimize_verts.iou_gradient` é o NMR na prática (GenDR §4: NMR ≈ distribuição uniforme). O regularizador de diedro **não** está no objetivo (só o gate `normal_diff`, L6-6) |
| 03 | PyTorch3D, Ravi et al. (2020) | Rasterizador modular: K faces mais próximas por pixel, `Fragments` (face id, baricêntricas, distância assinada), shaders em Python (silhueta em 2 linhas: `prob = sigmoid(−dist/σ); alpha = 1 − ∏(1 − prob)`), câmeras ortográficas/perspectivas, perdas Laplaciano/normal consistency | **não** | Nada em torch no pipeline de forma (`clip_score.py` usa torch só para o CLIP) |
| 04 | DVR, Niemeyer et al. (CVPR 2020) | Rede implícita de ocupação; gradiente da profundidade por diferenciação implícita; perdas por pixel: RGB (dentro da máscara com superfície), **freespace** (fora da máscara com superfície → remover), **occupancy** (dentro sem superfície → criar) | **parcial (ideia)** | `silhouette.uncovered/spill` + gates `UNCOVERED_MAX`/`SPILL_MAX` separam vermelho e verde, mas o objetivo do fit/vértices é IoU simétrico |
| 05 | MCViNE, Lin et al. (NIMA 2016) | Ray tracing Monte Carlo de **nêutrons** (espectroscopia) | **n/a** | Fora de domínio (provável DOI errado na lista) |
| 06 | DiffusionAvatars, Kirschstein et al. (CVPR 2024) | Difusão latente + ControlNet condicionada no render de uma malha proxy (NPHM); features aprendidas na superfície | **não** | Difusão + treino + GPU; viola "sem gerador" |
| 07 | AvatarStudio, Zhang et al. (2023) | Texto→avatar por SDS, NeRF→DMTet, nvdiffrast, ControlNet DensePose, otimização conjunta canônico/posado | **não** | SDS/difusão/GPU; vetado |
| 08 | Inverse rendering translúcido, Li et al. (CVPR 2023) | Mitsuba + renderer neural, flash/no-flash, SSS homogêneo, dataset 117 K | **não** | Fotorealismo/SSS; irrelevante para cel low-poly |
| 09 | Polarimetric Inverse Rendering, Shao et al. (TMM 2024) | IDR implícito + renderer polarimétrico, peso por percentagem de reflexão | **não** | Captura polarimétrica; irrelevante |
| 10 | DIB-R++, Chen et al. (NeurIPS 2021) | **Shading diferido**: raster → G-buffers (normal, albedo, máscara); shading diferenciável por Monte Carlo ou Gaussianas esféricas; BRDF Disney simplificada | **parcial (ideia)** | Já existe o G-buffer: render ID por material (`render_silhouette --ids`, `zones_clay`) e normais; a luma por zona só é medida (`luma_l1`, C2), nunca ajustada |
| 11 | DIB-R, Chen et al. (NeurIPS 2019) | Foreground: interpolação baricêntrica dura (z-buffer); background: alpha suave `A = 1 − ∏(1 − exp(−d/δ))`; perda IoU (Eq. 12) + Laplaciano + suavidade; otimiza posição, cor, UV, luz, **câmera** | **parcial** | Mesma perda IoU de `optimize_verts`; o alpha só no fundo é a versão barata do SoftRas para silhueta |
| 12 | GenDR, Petersen et al. (CVPR 2022) | Família geral: sigmoide `F(d/τ)` (distribuição) × T-conorma de agregação. Em 1242 variantes: **uniforme** melhor na média para forma; convergência exponencial (logística, Gauss, Laplace) boa, linear (Cauchy) ruim; Gamma(p=0.5, invertida) mais robusta; T-conormas Yager(2)/Dombi(0.5) > probabilística ≈ Einstein ≫ máximo/média; para pose, anelar τ de 1e-1 a 1e-7 | **não** | Nenhum raster suave; a escolha de distribuição/agregação é configuração de 1 linha quando houver um |

## 2. Onde aplicar, por paper

Legenda de métricas: IoU por vista (`silhouette.GATES`: f .75 / l .65 / b .70 / top .65 / bottom .65 / rts .70), vermelho =
`uncovered`, verde = `spill`, `normal_diff`/`slivers`/`flipped` (`mesh_lint`), orçamento de tris (`preflight.part_tris`).

### 01 SoftRas — gradiente analítico da silhueta
- **Estágio/módulo:** `optimize_verts.py` (`Ctx`, `iou_gradient`) e, depois, `fit_spec.py` (`Proxy.loss`, `Objective`).
- **Mudança:** novo `tools/blender/soft_sil.py` (torch): por vista, projeta os vértices com os mesmos eixos/câmeras de
  `deform_to_sheet.View`/`optimize_verts.rts_view`, calcula a distância assinada pixel→triângulo numa janela (bbox + 3σ) e agrega
  `S = 1 − ∏(1 − sigmoid(δ d²/σ))` (Eq. 1 e 4); perda `1 − Σmin(S,C)/Σmax(S,C)` (IoU suave, igual à de hoje) com `autograd`.
  `iou_gradient` passa a ser `loss.backward()`; o resto (line search `SHRINK`, recusa de face virada/sliver, `settled`, blocos,
  âncoras) fica igual. `σ` em px do canvas (2–3 px no início, 0.5 no fim).
- **Efeito esperado:** tempo de gradiente 1–2 s → < 50 ms; mesmo IoU f/l/b ou melhor (sinal para vértices que hoje não tocam o
  contorno: SoftRas Fig. 5b "far-range"); `--fit-verts` vira candidato a default (hoje 120 s/unidade). Vermelho/verde f/l/b caem
  nas unidades que L6-5 deixou > 8 % (n00U, hfoo, n017).
- **Custo/risco:** M (1 módulo + testes). Risco: a transparência do raster suave infla a silhueta; mitigar medindo o aceite
  (`accept`) sempre com o raster duro de `silhouette.iou`, como hoje. Dependência: torch (CPU basta; MPS opcional). Não viola nada.

### 02 NMR — regularizador de diedro e a leitura do nosso gradiente atual
- **Módulo:** `optimize_verts.Problem` (objetivo), `LAMBDA`.
- **Mudança:** termo `λ_sm · Σ_arestas (cos θ + 1)²` (Eq. 6) sobre as arestas internas do corpo soldado (temos `laplacian(tri, n)`
  e `live_edges` em `align_features`), gradiente analítico em torch junto com a silhueta. Hoje `normal_diff` sobe depois do L6-7
  (n005 44 → 48, n00H 47 → 54) porque nada no objetivo o segura.
- **Efeito:** `normal_diff` ≤ antes; slivers caem (ângulos de diedro perto de 180° evitam faces dobradas); IoU dentro de −0.005.
- **Custo/risco:** S. Risco: alisar demais as arestas vivas do WC3 (caixas facetadas): aplicar só em arestas com diedro < 35°
  (`align_features.FEATURE_DEG`), preservando as vivas.
- Fora: style transfer / DeepDream (features VGG, não mede forma).

### 03 PyTorch3D — padrão de implementação, não dependência
- **Uso:** copiar o desenho (rasterizador → `Fragments` → shader de 2 linhas; K faces por pixel; câmera ortográfica como objeto;
  perdas `mesh_laplacian_smoothing`/`mesh_normal_consistency` como referência de fórmula) no `soft_sil.py`. Não instalar a lib:
  CUDA-cêntrica, compilação longa no Mac, nossas malhas têm 600–800 tris (a janela por triângulo em torch puro basta).
- **Efeito:** nenhum direto; reduz o risco de L8-1.

### 04 DVR — perda assimétrica vermelho/verde
- **Módulo:** `soft_sil` (perda), `optimize_verts.Problem`, `fit_spec.Proxy.loss`.
- **Mudança:** em vez de `1 − IoU`, `w_red · Σ C(1−S) / ΣC + w_green · Σ S(1−C) / ΣS` (freespace = verde, occupancy = vermelho,
  DVR Eq. 14–15 em versão de máscara), com pesos por vista derivados dos gates (`UNCOVERED_MAX` vs `SPILL_MAX`: no left o verde é
  mais caro, no top o vermelho). Hoje o veredito usa os dois gates separados mas o otimizador vê só IoU.
- **Efeito:** o veredito (gate de acoplamento) e o otimizador passam a medir a mesma coisa; n005/n02X caíam "por 1–2 pontos de
  uncovered/spill no left" (v8) — alvo direto.
- **Custo:** S depois de L8-1. Sem rede, sem GPU. Fora: rede implícita, treino.

### 05 MCViNE — nada
- Monte Carlo de nêutrons. Não aplicar.

### 06 DiffusionAvatars — nada aplicável; uma ideia marcada
- A única transferência seria "render do clay como condição (ControlNet-like) para regenerar o painel rts" — melhoraria a coerência
  do rts (L7-2: nenhuma regeneração passou de 0.6) **mas é loop modelo→input**, fora da estratégia BFS; e exigiria ControlNet (GPU).
  **Não aplicar.** Difusão/treino vetados.

### 07 AvatarStudio — nada aplicável
- SDS, nvdiffrast, DMTet, DensePose: tudo vetado (gerador/difusão/GPU). A ideia "otimizar em canônico e checar posado" já existe de
  forma manual (`render_anim walk` sem rasgo, L6-4); não vale um item.

### 08 / 09 — nada
- Fotorealismo (SSS, polarização). Não aplicar.

### 10 DIB-R++ — shading diferido para acertar a luma do cel
- **Estágio/módulo:** estágio 2 (cor): `colour_stage`, `surfaces.paint_cel`, `silhouette.luma_l1`/`zone_palette`.
- **Mudança:** G-buffer já existe (render ID por material + normais do clay). Modelo de shading mínimo e diferenciável:
  `luma(p) = tom[material(p)] · (a + b · max(0, n·L))`, com L (direção de luz, 2 parâmetros), a/b e os 3 tons por material como
  incógnitas; minimizar `luma_l1` contra o sheet por zona (numpy `least_squares`, sem rasterizador porque o G-buffer é fixo).
  Saída: tons claro/médio/escuro por slot e `RAMP_SLOPE` medidos do sheet em vez de fixos (C1/C2 foram negativos com rampa fixa).
- **Efeito:** `luma_l1` f/l/b abaixo da referência (n01X .029/.031/.024) sem derrubar zone mean; o "AO pintado" do WC3 ganha direção.
- **Custo/risco:** S–M; é cosmético, só depois da forma. Fora: Monte Carlo, Gaussianas esféricas, BRDF Disney (cel é chapado por design).

### 11 DIB-R — alpha só no fundo; câmera diferenciável
- **Módulo:** `soft_sil` (variante barata): foreground duro (z-buffer) + alpha `exp(−d/δ)` só em pixels de fundo (Eq. 5–6). Para
  silhueta pura equivale ao SoftRas com distribuição exponencial; GenDR mostra que a exponencial **não invertida** rende pior que
  logística/uniforme — então DIB-R entra como **opção de distribuição**, não como padrão.
- Câmera (Fig. 2f): o tilt/azimute do rts/top/bottom hoje é varredura em grade (`silhouette`, `TURN_STEPS`); poderia ser otimizado por
  gradiente. **Não vale**: a grade já é exata e barata (<1 s) e o render usa a câmera escolhida.
- Perda IoU Eq. 12 = a nossa; regularizadores Laplaciano + suavidade = L8-4.

### 12 GenDR — qual sigmoide e qual agregação usar
- **Módulo:** `soft_sil` (config `DIST`, `TCONORM`, `TAU`, schedule).
- **Mudança:** implementar 3 distribuições (uniforme = rampa linear com suporte finito; logística; Gamma p=0.5 invertida) e 2
  agregações (probabilística `1−∏(1−p)`, Yager p=2 `min(1, (Σ p²)^½)`); anelar `τ` de ~4 px para 0.5 px ao longo das iterações
  (substitui ou complementa a fase de âncoras `ANCHOR_EVERY`; SoftRas §5.2 e GenDR §5.2 mostram que a paisagem suave evita mínimos
  locais, essencial no `fit_spec` onde as peças se movem muito). Ablação de 1 rodada nas 5 unidades e fixar o default.
- **Efeito:** convergência em menos passos (GenDR: 100 passos bastam com a distribuição certa), menos vistas presas em mínimo local
  (left do hfoo, rts do n00U).
- **Custo:** S depois de L8-1.

## 3. Leva 8 proposta (ordem de desenvolvimento)

Regras iguais às levas anteriores: medir sem LLM nos clays guardados, opt-in até ganho medido, nenhum run apagado. Unidades de
prova: n005 (bípede controle), n00U (aranha), hfoo (footman, lança), n017 (lobo quadrúpede), n02X. Antes de cada item: rebuild dos
specs v11-r1 com `--shape-only --no-repair`.

| # | Item | Paper | O que fazer (30–60 min de agente) | Aceite (1 linha) |
|---|---|---|---|---|
| L8-1 | `soft_sil.py`: raster suave de silhueta em torch | 01, 03, 12 | Módulo novo: projeção = `deform_to_sheet.View`/`optimize_verts.rts_view`; distância pixel→triângulo por janela; `F(d/τ)` configurável (uniforme, logística); agregação probabilística; perda IoU suave; `autograd`. Teste: τ→0 reproduz `silhouette.iou` | Nos 5 clays v11-r1, 6 vistas: \|IoU suave(τ=0.5 px) − IoU duro\| ≤ 0.01; forward+backward ≤ 50 ms (CPU) para 800 tris |
| L8-2 | `optimize_verts` com gradiente analítico | 01, 11 | `iou_gradient` → `soft_sil` backward; chamfer/Laplaciano/fairness iguais; line search, recusa de flip/sliver, `settled` intactos; aceite final sempre com raster duro | IoU f/l/b ≥ tabela L6-7 (n005 .893/.923/.906; n00U .875/.788/.869) em ≤ 30 s (hoje 120 s); flipped 0; slivers não sobem |
| L8-3 | Anelamento de τ e ablação de distribuição | 12, 01 | `TAU` de 4 px → 0.5 px em 5 degraus; comparar uniforme × logística × Gamma-inv, probabilística × Yager(2) numa rodada nas 5 unidades; fixar default; decidir se a fase de âncoras fica | Vistas f/l/b com vermelho+verde < 8 %: ≥ 12 de 15 (hoje n00U/hfoo/n017 falham); n017 left ≥ .75 |
| L8-4 | Regularizador de diedro no objetivo | 02, 11 | `λ_sm · Σ(cos θ + 1)²` em arestas com diedro < 35° (arestas vivas preservadas); gradiente analítico; `normal_diff` no `clay.verts.json` | `normal_diff` depois ≤ antes nas 5 unidades (L6-7 subia +4 a +6); IoU dentro de −0.005 |
| L8-5 | Perda assimétrica vermelho/verde | 04, 11 | `soft_sil.loss(mode="asym")` com pesos por vista de `UNCOVERED_MAX`/`SPILL_MAX`; ligar em `optimize_verts` e medir; `uncovered_body`/`spill_body` por vista no relatório | n005 e n02X passam o gate de acoplamento no left (uncovered ≤ .20, spill ≤ .15); n005 f/l/b não cai |
| L8-6 | Tornar `--fit-verts` default | 01 | Se L8-2/3 ≤ 30 s: `FIT_VERTS = True` (`--no-fit-verts`), roda em `stage_shape` e `build_textured`; bateria v12 nas 5 unidades, pareada contra v11 | ≥ 3 de 5 PASS (v11: 1 de 4); juiz pareado ≥ 3-1 em "forma" para n005 e n017; nenhuma vista cai > 0.01 |
| L8-7 | `fit_spec` por gradiente (proxy paramétrico diferenciável) | 01, 12 | Versão torch de `part_points`/`local_shape` (box/prism/frustum/cyl/dome/lathe/limb; dims, at, rot, profile, knee contínuos) → triângulos → `soft_sil` (a união sai da agregação, sem `hull2d`); Adam com `τ` anelado e bounds por reparametrização; regras do preflight/attach checadas a cada passo (rejeita como hoje); Powell fica como fallback (`--fit-powell`) | Mesmo `fit_accepted` e IoU ±0.01 que Powell em n005/n00U/n017 em ≤ 1/3 do tempo (hoje 30–150 s), ou IoU f/l/b maior no mesmo tempo |
| L8-8 (opcional) | Luma por shading diferido | 10 | `colour_stage.fit_luma`: G-buffer (ID + normais) → tons por material + direção de luz por `least_squares` contra a luma do sheet por zona; alimenta `paint_cel`/`ramp` | `luma_l1` f/l/b < referência (n01X .029/.031/.024) e zone mean não cai em n005/n01X |

Dependência de execução: L8-1 → L8-2 → (L8-3, L8-4, L8-5 em paralelo, worktrees separados; todos tocam só `optimize_verts.py`,
`soft_sil.py` e testes) → L8-6 → L8-7 (independente após L8-1; worktree próprio: toca `fit_spec.py`) → L8-8 (independente de tudo).
Nota: a leva 7 ainda tem merge pendente em `deform_to_sheet.py`/`fit_spec.py`/`PIPELINE.md` (L7-1 seis vistas); resolver antes de
abrir L8-7.

Infra a decidir no L8-1: (a) instalar torch no `python3.14` (ver se há wheel 2.14 para 3.14) ou (b) `soft_sil` roda como subprocess
no `python3` com torch, trocando arrays `.npy` — (b) é mais seguro para o primeiro item; (c) alternativa sem torch: gradiente
analítico à mão em numpy (sigmoide da distância a aresta tem derivada fechada; ∂/∂D_j do produto é `∏_{k≠j}(1−D_k)`), ~2× o
trabalho mas zero dependência. Registrar os 12 DOIs em `docs/references.md` no mesmo commit do L8-1 (regra do projeto).

## 4. Não vale aplicar (e por quê)

| Item | Motivo |
|---|---|
| 05 MCViNE | Ray tracing de nêutrons; fora de domínio. |
| 06 DiffusionAvatars | Difusão + treino + GPU; a única ideia transferível (render do clay condiciona o painel rts) é loop modelo→input e precisa de ControlNet. |
| 07 AvatarStudio | SDS, nvdiffrast (CUDA), DMTet, gerador texto→3D: tudo vetado. |
| 08 Translúcidos (Mitsuba + rede) | SSS/fotorealismo e dataset de 117 K cenas; cel chapado não tem o fenômeno. |
| 09 Polarimétrico | Captura polarimétrica real; irrelevante. |
| 10 DIB-R++ (parte MC / Gaussianas esféricas / BRDF) | Iluminação ambiente e especular não existem no estilo WC3; só a ideia de shading diferido (L8-8) sobrevive. |
| 04 DVR (rede implícita, diferenciação implícita da profundidade) | Exige treinar rede de ocupação; a nossa representação é malha paramétrica. Só a decomposição freespace/occupancy entra (L8-5). |
| 02 NMR: style transfer / 3D DeepDream | Features VGG não medem forma nem cor de cel; CLIP já foi negativo (E2). |
| 03 PyTorch3D como dependência | Compilação CUDA-cêntrica no Mac, sem MPS no rasterizador; nossas malhas são pequenas demais para justificar. |
| 11 DIB-R: câmera por gradiente | A varredura em grade de tilt/azimute (`TURN_STEPS`, varredura do rts) já é exata e custa < 1 s. |
| Raster suave para otimizar **cor/textura** (SoftRas §4.1.1, DIB-R texturas) | O cel é paleta chapada vinda do sheet (`zone_palette`); a cor já é medida por zonas; não há o que otimizar por pixel. |
| Soft rasterizer **no lugar** de `silhouette.py` (gates) | Os gates devem continuar no raster duro (render Blender real); o suave é só para o gradiente. |
