# L14-3 — Consertar à mão até lembrar o concept, e com isso diagnosticar a pipeline (2026-10-30)

Pedido do usuário: "quero que o claude tente melhorar os modelos, e depois com isso descobrir o que está errado no pipeline (…)
até ao menos lembrar direito, tá muito ruim agora". Três unidades da bateria v15 (`v15-r1`, SDF default, cel): **n02X** (ogro),
**n005** (encapuzado com tanque), **n00U** (aranha). Eu olhei (Read nos PNG) e mexi com as minhas mãos (scripts Blender headless);
nenhum `claude -p` no conserto; o juiz pareado (`review_pair.py`, `session:opus`) só no fim.

Ficheiros: `runs/draft/<id>/l14-fix/` (`fix.py` reproduzível, `diagnosis.md` por unidade, `steps/NN.png` um render por passo,
`model.glb` final, `model.v15.glb` ponto de partida, `fix.json` números antes/depois, `pairwise.json` juiz, `anim.json` rig,
`sil/approved` gate com câmaras pinadas da v15, `sil/sweep` gate com câmaras livres, `time.json`); mãos partilhadas em
`runs/draft/l14fix_lib.py` (primitivas, cor plana por peça, peso 1.0 no osso, reaproveita armadura + clipes da v15),
`render_steps.sh`, `strip.py`, `compare_fix.py`. Não versionados (`.gitignore`): renders por passo `steps/sNN/`, máscaras de render
`sil/*/sil/`, ficheiros de trabalho do juiz `pairwise/`, cópias da v15 `v15/` (origem: `worktrees/v2-hard/.../v15-r1`). Imagens: `history/2026-10-30-l14-fix/<id>.png` = concept | v15 textured |
l14-fix textured | overlay v15 (câmaras pinadas) | overlay fix (pinadas) | overlay fix (câmaras do varrimento), 6 vistas.

## 1. O que fiz, em números

Tempo de relógio por unidade (do primeiro render à última afinação): n02X 13 min (7 passos + 3 afinações), n005 4 min + 2
afinações, n00U 5 min + 1 afinação; orçamento era 45. Parei quando o meu olho disse "lembra" nas 6 vistas. Tris: 724 / 612 / 548
(orçamento 700; o ogro passa 24 por causa das esferas 8×4; não precisei de 1000). Rig: armadura e clipes da v15 intactos, cada
peça pesa 1.0 no seu osso; `anim_check` p99.5 stretch 1.0 / 1.0 / 1.0 nos três clipes (v15: 2.46 / 2.19 / 2.77 — a pele do SDF
estica, a peça rígida não; em troca a peça rígida abre fendas nos joelhos nos clipes, que o WC3 resolve com sobreposição nas juntas).
`mesh_lint`: 0 flipped / degenerate / non-manifold nos três; slivers 6.6 % / 2.6 % / 31 % (patas finas).

Gate honesto (`silhouette.py`, sheet approved, spill ≤ .03 e bare ≤ .10 por vista) e juiz pareado (4 votos A/B trocados):

| un. | run | IoU f/l/b/top/bot/rts | spill | bare | contact | spill ≤ .03 | bare ≤ .10 |
|---|---|---|---|---|---|---|---|
| n02X | v15-r1 (pinado) | .896 / .852 / .898 / .757 / .760 / .747 | .048 / .059 / .044 / .204 / .169 / .097 | .061 / .100 / .063 / .061 / .101 / .188 | .499 / .455 / .464 / .056 / .080 / .222 | 0/6 | 4/6 |
| n02X | l14-fix (câmaras pinadas da v15) | .753 / .777 / .754 / **.388** / **.350** / .630 | .099 / .066 / .096 / .165 / .164 / .245 | .178 / .177 / .180 / .580 / .624 / .208 | .203 / .292 / .236 / .042 / .024 / .089 | 0/6 | 0/6 |
| n02X | l14-fix (varrimento) | .753 / .777 / .754 / .815 / .695 / .700 | .099 / .066 / .096 / .109 / .217 / .110 | .178 / .177 / .180 / .094 / .139 / .234 | .203 / .292 / .236 / .129 / .082 / .118 | 0/6 | 1/6 |
| n005 | v15-r1 (pinado) | .913 / .944 / .934 / .807 / .822 / .884 | .056 / .039 / .050 / .117 / .062 / .067 | .034 / .019 / .018 / .096 / .131 / .057 | .496 / .624 / .657 / .147 / .233 / .331 | 0/6 | 5/6 |
| n005 | l14-fix (pinadas) | .739 / .796 / .733 / .671 / .627 / .744 | .183 / .098 / .191 / .236 / .269 / .201 | .115 / .129 / .114 / .153 / .186 / .086 | .186 / .275 / .197 / .060 / .078 / .091 | 0/6 | 1/6 |
| n005 | l14-fix (varrimento) | .739 / .796 / .733 / .709 / .710 / .761 | .183 / .098 / .191 / .166 / .155 / .175 | .115 / .129 / .114 / .174 / .184 / .093 | .186 / .275 / .197 / .103 / .077 / .124 | 0/6 | 1/6 |
| n00U | v15-r1 (pinado) | .897 / .770 / .887 / .785 / .778 / .702 | .050 / .180 / .060 / .132 / .182 / .247 | .058 / .073 / .059 / .109 / .058 / .089 | .303 / .233 / .263 / .254 / .229 / .180 | 0/6 | 5/6 |
| n00U | l14-fix (pinadas) | .561 / .608 / .558 / .589 / .660 / .555 | .241 / .255 / .248 / .232 / .201 / .265 | .317 / .232 / .316 / .284 / .209 / .306 | .182 / .096 / .165 / .086 / .115 / .099 | 0/6 | 0/6 |
| n00U | l14-fix (varrimento) | .561 / .608 / .558 / .592 / .660 / .622 | .241 / .255 / .248 / .243 / .201 / .264 | .317 / .232 / .316 / .269 / .209 / .200 | .182 / .096 / .165 / .108 / .115 / .129 | 0/6 | 0/6 |

Câmaras que o varrimento escolhe para o modelo consertado (v15 pinado entre parênteses): n02X top +20 / bottom −20 / rts (35, +45)
(v15: −20 / +30 / (35, −30)); n005 −40 / +40 / (35, −60) (v15: −20 / 30 / (35, −45)); n00U −10 / −10 / (35, −30) (v15: −20 / −10 / (65, 60)).

| un. | juiz l14-fix × v15-r1 (sheet / artista / wc3 / forma) |
|---|---|
| n02X | **fix 4-0 / fix 4-0 / fix 4-0 / fix 4-0** |
| n005 | **fix 4-0 / fix 4-0 / fix 4-0** / v15 4-0 |
| n00U | **fix 4-0 / fix 4-0 / fix 4-0 / fix 4-0** |

**Leitura honesta.** O conserto à mão perde no gate de silhueta em todas as vistas coerentes (IoU front .90 → .75, .91 → .74, .90 → .56;
spill e bare sobem para .1–.3) e ganha no juiz de visão em 11 dos 12 eixos, 4-0 cada. As duas medidas discordam de forma sistemática,
não por ruído (σ do `noise-l12.json` é .01–.02). Não é "o modelo ficou mais parecido e o spill subiu por acaso": o modelo ficou
mais parecido *por peças* (cabeça, clava, óculos, presas, calça, botas, capuz, olhos, focinho, tanque, patas com joelho) e menos
parecido *por massa* (o ogro do sheet não tem pescoço e é mais gordo que o meu; as patas da aranha no painel front são cunhas
sobrepostas que formam dois blocos sólidos, ver `n00U/l14-fix/sil/approved/mask-concept-front.png`; o casaco do n005 é um barril
mais largo). O v15 obedeceu à massa e perdeu as peças. Os 0/6 do gate honesto continuam 0/6 nos dois lados.

## 2. Cada conserto e o estágio que devia tê-lo feito

| # | conserto à mão (unidade, vista) | estágio responsável | porque não fez |
|---|---|---|---|
| 1 | cor por peça: pele / calça / botas / cinto / ombreira / tanga (n02X front); casaco / luvas / botas / tanque / latão / olhos (n005); corpo / concha / patas / gema (n00U) | textura (`colour_stage.py`, `build_unit.texturize*`) | o cel pinta zonas do *painel* projetadas no corpo fundido (`zones` por vista); a peça não existe mais depois do SDF, logo não há "material da peça" para pintar; `spec-colour.json` tem a paleta certa por material e ela não chega às faces |
| 2 | rosto legível: óculos + máscara + presas (n02X), olhos vermelhos + focinho (n005), olhos + presas (n00U) | autor/DSL + textura (`decal: sheet`) | o decal da cara é uma imagem de 64 px projetada numa lathe de 8 lados; a 384 px vira listras; a DSL não tem "olho", "lente", "presa" como peça; o retopo QEM a 600 tris não tem orçamento para uma peça de 20 tris no rosto |
| 3 | clava à frente do corpo, na mão erguida (n02X left/top/rts) | autor + preflight (`prop_axis`, `prop_coverage`) | o autor escreveu `forward −0.35..−0.71` (atrás); o preflight mede eixo e cobertura do prop no painel, não o *lado* (frente/trás) em que o painel left o põe; `prop_iou left .11` apareceu no gate e ninguém reage a ele |
| 4 | tirar as placas do peito e do cinto, os antebraços de ferro, o capacete (n02X top/bottom .20/.17 de spill) | autor + guarda autor-vs-massing + preflight | peças que o sheet não tem; a guarda (`author_guard.py`) compara IoU total, uma placa plana de frente custa pouco IoU; não há check "cada peça tem uma zona de cor no sheet com ≥ x % de área" (o `refs/<id>/parts.json` tem a lista de peças do sheet e não é usado contra o spec) |
| 5 | barriga redonda, peito estreito, ombros largos (n02X); capa em degrau sobre as mangas (n005); concha oval lisa com rebordo (n00U) | massing / SDF / retopo | o SDF (k = 1.0) funde tudo num blob e o QEM a 600 tris apaga os degraus que sobram; `planarity`/`crease_chamfer` (L12-9) medem e não gateiam; a matriz L12-10a disse "no" ao union por décimas de IoU |
| 6 | patas finas com joelho, vão entre patas (n00U) | SDF (`thin: inflate`) + gate | o gate quer a tenda (painel front = cunhas sobrepostas, IoU .90 só com patas fundidas); `thin: inflate` engorda o que é fino para a fusão não o perder; o resultado é o que o gate pede |
| 7 | botas com cano, calça curta com vão (n02X), canelas + botas (n005) | SDF + deform | juntas fundidas, `leg_joints` do preflight só olha a DSL |
| 8 | pose: braço direito erguido com a clava, braço esquerdo pendente mais para fora (n02X front) | autor (DSL `from/to`) | o autor repete o A-pose do rig; a DSL permite a pose (`from/to`), o autor não a usa; nada compara a pose do spec com o painel |
| 9 | clava mais comprida: tampa .12 H acima da cabeça (n02X) | fit / verts | só importa porque o gate enquadra pelo bbox (prop decide a escala do corpo); L13-1 e L13-5 já viram isto |
| 10 | orientação do top/bottom (n02X pinado .39/.35 → varrimento .82/.70) | gate (`silhouette.detect_rotated`, `pin_tilts`) | a orientação do painel (cabeça para cima/baixo) e o espelho são decididos **por modelo** pelo IoU; mudar o modelo muda a decisão e as câmaras pinadas de outro run medem o modelo girado 180º (mesma classe do bug hfoo da L13-2) |

## 3. Causas-raiz (com evidência) e a mudança concreta

### C1. A representação do corpo apaga as peças (SDF k=1 + retopo QEM 600 tris)
Evidência: n02X v15 front/top (`history/2026-10-30-l14-fix/n02X.png`, coluna 2: cabeça afundada no peito, placas, ombreira
invisível); n00U v15 front (patas-tenda); n005 v15 (capuz, mangas e saia num volume). O juiz dá **forma** ao conserto rígido em
n02X e n00U 4-0 ("stepped ridges where slices meet" no v15) e ao v15 só em n005 (fendas nos pulsos das minhas peças).
Mudança: `build_unit.sdf_union` (e `fuse`): fundir só o *núcleo* (tronco + pélvis + coxas); cabeça, mãos/punhos, pés/botas, props e
peças "hard" (`plate`, `box` com material metal, qualquer peça com `decal`) ficam como peças separadas, cada uma com o seu material
e osso (o `keep` já existe para props: alargar por regra de papel, não por nome). Retopo por componente com orçamento por peça
(rosto ≥ 40 tris). Medir: `components_body` ≥ 4 nos bípedes; juiz forma/artista pareado contra o SDF inteiro; `planarity`.

### C2. A cor é projetada do painel, não atribuída à peça
Evidência: listras no rosto do ogro, "porta verde" na cara da aranha, n005 sem rosto; `spec-colour.json` tem `skin/iron/darkiron/
canvas/tusk/fuse/brass` com as cores certas e o render é bege uniforme. Mudança: `colour_stage.py` / `texturize`: a face herda o
material da **peça de origem** (nearest part, `transfer_from_parts` faz isso para o union; para o SDF levar o id da peça no
`skin_sdf` junto com os pesos) e só depois o cel modula tom por orientação; o decal do rosto vira peças (lentes, presas, olhos)
quando a peça tem ≥ 3 % da área do painel front. Medir: zona-IoU por material (já existe em `zones`) com o painel ≥ .5 nas 3
unidades (hoje n02X front `#5F554B` .25, `#35302E` .05, `#818181` lost).

### C3. O gate mede massa, o olho mede peças: IoU e juiz discordam de forma sistemática
Evidência: tabela §1 — IoU front cai .14 / .17 / .34 e o juiz prefere o conserto 11/12 eixos 4-0. O fit, o deform, o verts, o inscribe
e o polish optimizam IoU/spill e por isso convergem para o blob; a matriz L12-10a rejeitou o union por décimas de IoU; `look.py`
nunca entrou no aceite. Mudança: (a) IoU/spill gateiam o **corpo** (já separado em `body_iou`) com teto .75 "bom o bastante" e o
resto do aceite é por peça (`prop_iou` ≥ .5, zonas por material ≥ .5) + juiz de visão pareado contra o run anterior como gate de
não-regressão (`review_pair` existe, só relata); (b) otimizadores (fit/deform/verts) param quando body IoU ≥ .80 em vez de puxar
até .90 à custa das peças; (c) `--frame body` consertado (hoje dá front .34 / spill .66 no meu n02X: o enquadramento por corpo
quebra com props à frente); (d) rodar a matriz L12-10a com o juiz como coluna de aceite, não só IoU. Medir: correlação juiz × IoU nas
6 unidades v15 + 3 consertos (hoje negativa).

### C4. Câmara, espelho e orientação pinadas são do modelo medido, não do sheet
Evidência: n02X top/bottom .388/.350 com as câmaras da v15 e .815/.695 com varrimento (overlay pinado mostra o concept de cabeça
para baixo contra o meu modelo); rts azimute (35, −30) → (35, +45); n005 top −20 → −40. Mudança: `silhouette.py`: `detect_rotated`
e a escolha de espelho saem do **sheet** (posição da cabeça/props no painel top via `refs/<id>/parts.json`), calculadas uma vez por
unidade e guardadas em `refs/<id>/sheet.json`; `--tilts` passa a ser por unidade (do massing, L13-2) e a guarda/pipeline nunca
re-detecta por modelo. Medir: o mesmo modelo medido em dois runs dá a mesma orientação; o bug hfoo-180 fecha.

### C5. O autor não vê profundidade nem existência: props atrás, peças inventadas, pose do rig
Evidência: n02X spec `forearm.R prism from fwd −0.35 to −0.71` (clava atrás; sheet left mostra-a à frente, `prop_iou left .11`),
`spine box 1.10×1.04 darkiron` e `pelvis box 1.05×1.02 iron` (placas inexistentes), `forearm frustum darkiron` (manoplas), `head box
darkiron` (capacete), braços em A-pose com a clava erguida no sheet. Mudança: `preflight.py` ganha três regras numéricas sobre o
`refs/<id>/parts.json` + `sheet-props.jpg` (ambos já existem): (1) *lado do prop*: a projeção do prop no painel left tem de cair do
mesmo lado (frente/trás do centro do corpo) que a mancha do prop no sheet; (2) *peça existe*: cada peça com material ≠ pele precisa
de uma zona do painel front com a cor do material dentro de ΔE e área ≥ 1 %; senão `reject-part`; (3) *pose*: ângulo do osso
`arm/forearm` no painel front (da máscara da pele por lado) vs o `from/to` do spec, erro > 25º = aviso ao autor com a medida. Medir:
n02X `prop_iou left` ≥ .5 e top/bottom spill < .10 sem placas.

### C6. Sheet incoerente é absorvido pelo gate, não exposto ao autor
Evidência: tanga do ogro em lados opostos no front e no back; patas da aranha como blocos no front e finas no top (`incoherent`
marca top/bottom do n00U, não o front que é o errado); clava do hfoo (L12-10b). Mudança: `sheet_report` passa a comparar *peças*
entre painéis (prop/zona por lado) e a pedir ao autor uma decisão explícita ("tanga: lado do front/rts") gravada no spec; o gate
ignora o painel contraditório para aquela peça. Medir: `incoherent` por peça, não por vista.

## 4. O que a pipeline NUNCA fará sem ver o resultado

- "O rosto lê?" (óculos, presas, olhos vermelhos): nenhuma métrica de silhueta ou zona distingue listras de olhos; o juiz viu em 4/4.
- "A clava está à frente ou atrás?": IoU do left é .85 com ela atrás (o corpo cobre). Só o prop-IoU por lado ou um olho vê.
- "Isto é uma barriga ou uma caixa?": IoU igual; o juiz e o `form_why` ("stepped ridges where slices meet") veem.
- "As patas são patas ou uma tenda?": o gate *prefere* a tenda (painel front).
- "Que lado da tanga?": decisão de artista perante um sheet contraditório.
- "Ficou parecido o suficiente para parar?": o meu critério de paragem foi o olho; o gate diria continuar a puxar massa.

É o argumento para o laço com olho: um estágio em que o agente **vê** concept | textured | overlay e **refaz peças por primitiva**
(como `l14fix_lib`: tubo, caixa, cunha, esfera, cor plana por peça, peso no osso), não empurra vértices (`polish_ops.erode_toward_view`
chegou a −.008 de spill em L13-1); o gate de silhueta volta a ser o que foi desenhado para ser, um detetor de desastre (IoU < .6), e o
aceite de look é o juiz pareado contra o run anterior.

## 5. Aceite deste item
Pedido: "até ao menos lembrar" — pelo meu olho e pelo juiz (sheet 12-0 nos três), **sim**. Pelo gate honesto, **não** (0/6 como o v15,
e com IoU menor). Nenhum default muda (não toquei em código da pipeline). Aberto: C1–C6 são itens de código, cada um com a sua
medida; a lista do §4 é o brief do estágio com olho.
