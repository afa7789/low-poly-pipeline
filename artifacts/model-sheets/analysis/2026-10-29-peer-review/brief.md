# Artefacto em revisão: resultados v13/v14 do pipeline de modelos 3D (Castle Fight) + duas perguntas

Repo (worktree, só leitura para ti): `/Users/afa/Developer/arthur/castle_fight/.claude/worktrees/v2-hard`
Docs: `artifacts/model-sheets/PIPELINE.md` (§23.L5-4 e §23.L5-4b = profundidade já tentada; §26.L8-8 = luma/shading;
§28 = leva 10 corpo SDF; §29 = leva 11 laço VLM), `artifacts/model-sheets/ROADMAP-papers.md`, `tools/blender/*.py`.
Imagens (PODES e DEVES ler com a ferramenta Read): `artifacts/model-sheets/history/2026-10-29-v14/<id>-full.png`
para id em n005 n00U hfoo n017 n02X. Layout: esquerda v13-r1 (default atual), direita v14-r1 (com laço guardado);
colunas concept | clay | wire | overlay (cinza = acerto, vermelho = modelo a mais, verde = sheet não coberto) | texturizado;
linhas FRONT LEFT BACK TOP BOTTOM RTS + FORM.

## 1. O que o pipeline faz hoje (resumo)
Concept sheet (6 vistas desenhadas por IA de imagem, estilo WC3 low-poly) → `massing` determinístico lê as silhuetas e
escreve um pré-spec (uma massa por osso) → autor LLM (Opus) edita o spec na DSL de peças (box, prism, frustum, lathe,
plate, cyl, limb, chain; `cut: sheet` recorta a massa pelas silhuetas front/left/top; `decal: sheet` projeta a cara do
sheet na face da cabeça) → preflight (regras) → `fit_spec` (Powell; move/escala peças para subir IoU de silhueta nas 6
vistas, proxy 2D) → `build_unit` (Blender headless; corpo por SDF union suave com skinning por osso, `BODY="sdf"`) →
`deform_to_sheet` → `optimize_verts` (vértices contra silhuetas) → gates (`silhouette.py` IoU por vista, `mesh_lint`) →
cor procedural (cel, zonas do sheet) → rig/clipes. Métricas: IoU por vista contra a silhueta do sheet, bare (% sheet não
coberto), spill (% modelo fora), FORM (nd, fairness, slivers, sdf_dev).
Leva 11 (v14): laço guardado `--loop N` (VLM diagnostica → deltas por peça → rebuild determinístico → aceita só se nenhuma
vista cai > .01 e média +≥ .005). Resultado: 1 de 19 deltas aceite; PASS 3/5 igual à v13; fica opt-in.
Em curso: L11-7 matriz de ablação de todos os opt-ins. Planeado (aguarda aprovação): Leva 12 = passe final de alguns
minutos por modelo via Blender MCP (agente mexe peças na cena, gates depois).

## 2. Resultados (v13-r1 = default; IoU front/left/back/top/bottom/rts; bare/spill em %)
| id | tipo | veredito | front | left | back | top | bottom | rts | pior sintoma visível |
|---|---|---|---|---|---|---|---|---|---|
| n005 | encapuzado c/ máscara de gás, mochila-tanque | PASS | .921 | .947 | .932 | .764 | .833 | .878 | capuz = bloco liso; rosto/máscara sem recesso; top: ombros a mais (spill 16%) |
| n02X | ogro/brutamontes c/ clava, ombreira, 3/4 pose | PASS | .907 | .837 | .918 | .766 | .774 | .805 | top/bottom: spill 19/13%; clava inclinada no sheet vs reta no modelo; mão esquerda |
| n017 | lobo c/ arreio e corrente | PASS | .924 | .775 | .870 | .822 | .871 | .700 FAIL | left bare 17% (pernas/corrente); rts bare 10 spill 24; cauda/corrente não lidas |
| n00U | aranha 8 patas c/ carapaça | CHECK | .886 | .782 | .885 | .738 | .704 | .665 FAIL | patas: pontas erradas em todas as vistas (bare 5–11, spill 7–27); cor falha (stage 2 não corre) |
| hfoo | soldado c/ lança diagonal, mochila | CHECK | .847 | .415 FAIL | .853 | .796 | .859 | .703 | left .415: lança diagonal no sheet (left) vs vertical (front); modelo põe lança vertical; mochila/pernas spill 40% |

v14 (laço) muda ≤ .02 e não resolve nenhum dos sintomas acima; n017 left +.064 veio do spec novo do autor, não do laço.
Juiz pareado VLM (sheet/artista/wc3/forma): forma prefere v13 em 4/5.

## 3. Profundidade: o que já foi tentado (e o veredito)
- §23.L5-4 `--fit-parts`: parts.json (caixas 2D por parte, `box3d` triangulada front×left, `depth_order`) → termo de máscara
  por parte + restrição de ordem z no fit. Ganho de silhueta veio de "o fit correr em todas as peças", não da profundidade.
  Neutro, opt-in. Bug até ontem: `associate` rebentava com `box3d: null` (4 de 5 unidades) → `--fit-parts`/`--depth`
  estavam de facto mortos nas baterias (corrigido na matriz L11-7, ainda não medido).
- §23.L5-4b `--depth`: Depth Anything V2 small (HF, MPS) no crop front/left → disparidade por parte → calibra z com o left
  (`z = a·disp + b`) → só move peças sem máscara left e só se |r| ≥ .3. Correlação com o z do left: Pearson .35–.74 por
  sheet. Ganho de IoU zero. Opt-in. Nota: ordem de oclusão (tanque atrás do tronco .71 vs .82; máscara à frente .93) acerta.
- §26.L8-8 `--fit-luma`: shading diferido (normal por pixel do clay + luz + tons por slot ajustados aos quantis de luma do
  sheet). Serve à COR, nunca foi usado ao contrário (luma do sheet → normais → relevo).
- As vistas TOP e BOTTOM do sheet existem e são usadas como silhueta (IoU) e pelo `cut: sheet` (front/left/top). A vista RTS
  (3/4) é usada só como IoU.
- A DSL já tem a regra "HOODS: capuz = frustum/box fundo e escuro na cabeça, aberto à frente e recuado; cara = decal na face
  da frente da peça cabeça, empurrada ligeiramente à frente da parede de trás do capuz". No n005 o autor/fit não a cumpre: o
  capuz sai um bloco liso e a cara é um decal numa face plana.

## 4. Regras fixas (não discutas, aplica)
- Nunca geradores imagem→3D (TRELLIS, Hunyuan, TripoSR, Meshy), nem como experiência. Redes de INFERÊNCIA (profundidade
  relativa, normais, segmentação) são permitidas: Depth Anything V2 já foi aceite.
- Textura sempre procedural. Low-poly WC3 (400–700 tris por unidade). Pipeline por lotes (233 edifícios + unidades): tudo tem
  de correr headless, determinístico, com gates numéricos; um passe manual por modelo é no máximo alguns minutos (Leva 12).
- Medir sempre; mudanças viram opt-in até ganharem numa bateria de 5 unidades com o mesmo spec e as mesmas câmeras.

## 5. As duas perguntas (responde às duas, em secções separadas)
A. REVISÃO POR MODELO + PROCESSO: para cada uma das 5 unidades, o que está errado de facto (olha as imagens), qual a
   causa raiz provável (sheet incoerente? spec do autor? fit? SDF? optimize_verts? gate que mede a coisa errada?) e UMA
   correção concreta e mensurável. Depois: 3–5 mudanças de PROCESSO (não de modelo) com maior retorno, com como medir.
B. PROFUNDIDADE A PARTIR DA ARTE: como descobrir, a partir do sheet (6 vistas 2D, cel-shading com linhas pretas, luz fixa),
   profundidades que as silhuetas não dão — ex.: quão recuado está o rosto do encapuzado n005 dentro do capuz; o relevo da
   máscara de gás; a concavidade do carapaça da aranha. Candidatos a discutir e classificar (custo, ganho esperado, como
   validar): (1) triangulação entre vistas (top/bottom/rts dão z onde front/left são ambíguas; epipolar com câmeras
   ortográficas conhecidas); (2) linhas de contorno interno do cel (uma linha preta fechada dentro da silhueta = degrau de
   profundidade/oclusão; T-junções dão ordem); (3) shape-from-shading com a luz fixa do sheet (inverter o L8-8); (4) redes
   de inferência: Depth Anything V2 (já), normais (ex. StableNormal/Marigold-normals), e porque é que a tentativa anterior
   deu zero (calibração com caixas a olho); (5) perguntar ao VLM uma estimativa semântica por parte ("rosto 0.15 H atrás do
   bordo do capuz") com validação por vista top/rts; (6) priors por classe (capuz, máscara, carapaça) na DSL / massing.
   Diz o que faria primeiro e como provar em 1 dia que funciona (métrica: IoU rts/top + juiz pareado + uma métrica nova de
   profundidade, p.ex. erro de z nas juntas trianguladas).

## 6. Contrato de saída
Escreve em português. ANALYSIS curta; REWRITE = o documento final "Peer review v13/v14 + plano de profundidade", com as
secções: Resumo executivo (≤ 8 linhas) · Por modelo (tabela: unidade, defeito, causa raiz, correção, métrica alvo) ·
Processo (3–5 itens priorizados) · Profundidade (ranking dos candidatos com custo/ganho/validação, o que fazer primeiro,
experimento de 1 dia) · Riscos. Máximo ~120 linhas. Cita ficheiros/secções reais do repo quando afirmas algo sobre o
pipeline (verifica com Read/grep antes de afirmar).
