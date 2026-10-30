# Peer review v13/v14 + plano de profundidade (painel de 7 revisores, 2026-10-29)

Método: 7 agentes independentes (Graphics, MLOps, Testing, Tech Lead, Prototyping, Data Eng., Debugging/n01X), cada um
leu o brief + as 5 folhas `history/2026-10-29-v14/<id>-full.png` + repo, escreveu análise e reescrita; depois cada um
pontuou cegamente as outras 6 (42 avaliações, 5 eixos). Material completo (brief, 7 reescritas, 7 revisões, mapa de
anonimização): `scratchpad/peer-review/` da sessão. Factos em disputa foram verificados no repo pelo integrador (§6).

## 0. Critério novo do usuário (acima de tudo)
"Tem muito vermelho ainda; pode ter verde sobrando, e pouco; vermelho não pode. Em nenhum dos ângulos." E: "falar que está
certo na silhueta é sacanagem" — PASS ≠ certo. Consequências:
- Spill (modelo fora do sheet) ≤ ~3 % em **cada** uma das 6 vistas; bare (sheet não coberto) ≤ ~10 %. Sem média.
- Fit assimétrico: custo de spill ≫ bare. Hoje IoU trata os dois igual e o gate foi calibrado nos runs que existiam
  (`RIG_GATES` spider .65, caps "+.03") — gate frouxo, não silhueta certa.
- Régua honesta hoje: **PASS 0/5** (spill por vista: n005 5–16 %, n02X 6–19 %, n017 5–24 %, n00U 7–27 %, hfoo 8–40 %;
  mesmo o n01X, melhor caso, 4–13 %).
- Segundo eixo, "look": mesmo com silhueta certa o n02X "está longe de um low poly legal" — wire em sopa de triângulos,
  sem creases, textura em manchas. Tratado em §5.

## 1. Resumo executivo
1. v14 (laço VLM) não muda nada que o olho veja (≤ .02, 1/19 deltas); fica opt-in. Unanimidade.
2. **O massing determinístico já dá 90–100 % do IoU final; o autor LLM piora 2/5** (hfoo left .719→.415, n017 top
   .920→.822). Verificado. A guarda do laço v14 ("nenhuma vista cai > .01") está no sítio errado: tem de guardar o spec do
   autor contra o massing. (P7; melhor achado do painel, originalidade 9.0.)
3. **Otimizador e gate não medem com a mesma câmara**: `optimize_verts` reporta top .831/.889/.849 (n005/n017/n02X) e o gate
   mede .764/.822/.766 (lacuna .07–.08); n01X lacuna 0. Verificado. Pinar câmaras antes de qualquer trabalho de profundidade.
4. **3 não-PASS = 3 sheets com vista marcada `incoherent`** (`silhouette.py:194`, `COHERENCE_MIN=.6`: hfoo rts .57, n00U
   top .53 / bottom .49, n017 rts .58) e o fit dá peso 2.0 a essas vistas (`views.py:42-44`): o pipeline mede a mentira do
   sheet e otimiza contra ela. (P6.)
5. **Regras da DSL são prosa, não gate**: HOODS (`spec_pipeline.py:115`) tem zero ocorrências em `preflight.py`; o spec
   v13 do n005 nem tem peça capuz (cabeça = lathe + decal). (P1/P6; unanimidade.)
6. **Flags mortas sem alarme**: `--fit-parts`/`--depth` rebentavam com `box3d: null` em 4/5 unidades durante baterias
   inteiras; os vereditos "neutro" de §23.L5-4/L5-4b são não-testes. Teste "flag viva" obrigatório. (unanimidade)
7. Stage 2 (cor) não corre quando S1 falha → o juiz pareado comparou clay (n00U, hfoo) com texturizado: o "forma prefere
   v13 4/5" é amostra inválida. Stage 2 corre sempre; "stage not run" = FAIL de infra, nunca CHECK. (P1/P4/P6)
8. Profundidade: **primeiro a régua, depois o método**. Sem métrica de z/relevo todo candidato "dá zero" como L5-4b.
   Ordem: triangulação por peça a partir dos painéis que já existem + priors de classe como preflight; linhas interiores
   do cel como localizador; redes só recalibradas contra juntas trianguladas; shape-from-shading por último. (6 de 7)
9. Só 1 das 5 unidades (n005) tem a profundidade como defeito principal; 3 são props/apêndices finos (lança, clava,
   corrente/cauda, patas), 1 é sheet. Plano que começa por profundidade ataca 20 % do problema. (P5; aceite pelo painel)

## 2. Por modelo (v13-r1; das imagens; causa verificada quando marcada ✓)
| unidade | defeito visto | causa raiz | correção (uma) | métrica alvo |
|---|---|---|---|---|
| n005 | capuz = bloco liso; cara = decal plano; top spill 16 % (ombros) | spec sem peça capuz (lathe + decal) ✓; HOODS sem gate ✓; silhueta não vê recesso | preflight `hood_recess`: unidade com capuz exige peça `hood` aberta à frente + face da cabeça ≥ .08 H atrás do bordo; spec rejeitado antes do fit | recesso medido no clay ≥ .08 H; top spill ≤ 3 %; juiz forma ≥ 3/5 |
| n02X | top/bottom spill 19/13 % (ombreira, barriga, clava); clava reta vs inclinada; mão esq. | sheet front em pose 3/4 (r_sym .72) ✓; câmara gate ≠ otimizador (.083) ✓; prop sem `rot` | pinar câmara + `prop_axis` (eixo 2D do prop em front e left → `rot` 3D) | top/bottom spill ≤ 3 %; rts ≥ .85 |
| n017 | left bare 17 % (pernas, corrente); rts .700 FAIL; top caiu | **autor piorou o massing** (top .920→.822) ✓; corrente/cauda sem peça; rts incoerente .58 c/ peso 2.0 | guarda autor-vs-massing (rejeita spec se alguma vista < massing − .01); `chain` da corrente no pré-spec | top ≥ .90; left bare ≤ 8 %; rts ≥ .75 |
| n00U | pontas das 8 patas erradas em 6/6 vistas; bottom .704; rts .665; sem cor | patas só de front/left (`massing.leg_geometry`); painel top (8 patas) não lido por peça; top/bottom incoerentes .53/.49 c/ peso 2.0; stage 2 bloqueado | triangular pontas: (x,z) do painel top + y do front → `limb from/to` por pata; stage 2 corre sempre | erro z pontas ≤ .05 H; top/bottom spill ≤ 3 %; texturizado presente |
| hfoo | left .415: lança vertical vs diagonal; mochila/pernas spill 40 % | **meio sheet, meio spec**: front vertical + left diagonal é coerente (lança inclinada no plano sagital) e o spec pôs `to` vertical; mas o painel top não desenha a lança comprida (`LEAN_PROPS` off: left +.23, top −.24) ✓ | IoU corpo e prop separados (gate no corpo); lança com `rot` de front×left e mascarada nas vistas onde o sheet não a desenha | left (corpo) ≥ .70; uncovered_prop left ≤ 5 % |

## 3. n01X (robô) como controlo — porque acerta top/bottom/rts
- Sheet: r_sym front .978 (outros .66–.76), 0 props, coerência top/bottom .74/.71 — **igual** aos outros. Não é "painel
  mais claro"; é forma prismática: o casco front×left **é** o objeto.
- Massing sozinho: .847/.906/.849/.826/.856/.843 — já acima do final de n005/n02X/n00U nas vistas de profundidade.
- Spec: lathes com anéis [w, d, zc] (d ≠ w, zc ≠ 0) e limbs com z explícito. Fit 0 evals, cut rejeitado: não contribuiu.
- Única unidade com câmara do otimizador = câmara do gate (lacuna 0).
- Repetição no mesmo sheet: top .782 (v12) / .785 (v13 antigo) / .893 (l10 SDF, spec v10) / .868 (v13-r1, spec novo);
  front .880 → .833 só por trocar o spec do autor. **Variância do autor > ganho de qualquer flag.** Medir 3× antes de aceitar.
- Transferível: z por peça lido do painel certo (top → patas/ombros; left → eixo de props); autor só ganha quando
  acrescenta z explícito, nunca quando substitui o massing; câmara pinada. Não transferível: "casco = objeto" (capuzes e
  carapaças têm recessos que nenhuma silhueta vê).

## 4. Processo (ordem de execução; cada item com medida)
1. **Spill como gate e como custo** (§0). `SPILL_MAX` ≤ .03 por vista, `UNCOVERED_MAX` ≤ .10; termo de spill com peso
   ≥ 3× no `fit_spec`/`optimize_verts`. Medir: spill por vista nas 5 + n01X antes/depois; relatório mostra spill ao lado
   do IoU em todas as tabelas de bateria.
2. **Pinar câmaras** (`silhouette.pin_tilts` existe; `sdf_batch.tilts_arg` só pina o build): `optimize_verts`/`deform`
   usam o tilt+flip do gate. Medir: |verts.after − gate| < .01 em 6/6 × 6 unidades (hoje .07–.08 em 3).
3. **Guarda autor-vs-massing**: spec do autor rejeitado (ou peça revertida ao massing) se alguma vista cair > .01 abaixo do
   massing. Colunas massing/autor/final por vista em `review.md` e `results.csv`. Medir: hfoo left e n017 top ≥ massing.
4. **Piso de ruído**: 3 rebuilds por unidade (`compare_runs.py --stability` existe); σ por vista publicado; aceite de
   qualquer delta só > 2σ. Substitui GAIN .005/DROP .01 do laço, que estão abaixo do ruído documentado (.02–.05).
5. **Sheet como dado com qualidade**: vista `incoherent` → peso 0 no fit e **reportada** no gate (IoU bruto ao lado), sheet
   marcado para regeneração; props separados do corpo no IoU. Medir: FAIL atribuídos ao sheet vs ao modelo.
6. **Prosa vira preflight**: auditar a DSL regra a regra; HOODS → `hood_recess`, PROPS → `prop_axis`/`prop_coverage`,
   arthropod → ≥ 1 junta por pata. Medir: specs v13 rejeitados (esperado n005, n017, n00U).
7. **Flag viva + stage 2 sempre + infra = FAIL**: teste por opt-in que exige ≥ 1 número diferente ou log "no-op: motivo";
   stage 2 corre em CHECK/FAIL; estágio em falta = FAIL(infra). Medir: 0 flags mortas na matriz L11-7; 6/6 texturizados.
8. L11-7 (matriz) continua (regra do usuário: medir todos), mas **re-corre depois de 1–3**: ablação sobre câmaras
   desalinhadas e flags mortas mede ruído. Leva 12 (MCP) só depois de 1–3 e 6: minutos humanos não sobrevivem ao rebuild.

## 5. Eixo "look" (low-poly legal), separado da silhueta
- Wire: MC + QEM dá triangulação aleatória. Alvo WC3: poucas arestas, intencionais, faces planas. CVT (L11-6) melhora
  fairness; falta "snap a plano" por região + crease onde `edge_bands` do sheet-hard desenha faceta.
- Creases: o SDF suaviza tudo; `edges.drawn` já existe e não é gate. Métrica: chamfer arestas do wire ↔ tinta do sheet.
- Textura: zonas certas, sem linha de tinta nas arestas nem bandas de cel limpas. Pintar linha escura 1–2 px nas creases.
- Métrica interior (6 de 7 pedem): luma L1 por zona / `relief_agreement` (degraus do z-pass do clay vs linhas interiores
  do sheet, precisão/recall, SLACK 4 px). n01X top IoU .893 com luma L1 .146: silhueta certa, relevo errado.

## 6. Profundidade a partir da arte — ranking consolidado
Régua primeiro: `z_err` = |z do clay − z triangulado| em 8–12 marcos por sheet (juntas, pontas de props, bordo do
capuz/carapaça), com resíduo de reprojeção na 3.ª vista como auto-validação (sheet incoerente ⇒ resíduo alto ⇒ marco
descartado). Complemento: `relief_agreement` (§5) para o que nenhuma vista vê (cara dentro do capuz).

| ordem | candidato | custo | ganho | validação | notas do painel |
|---|---|---|---|---|---|
| 1 | Triangulação por peça: top → (x,z) de patas/ombros/raio do capuz; front×left → eixo de props; usar o **tilt varrido** do gate, não ortográfica pura | baixo (`segment_sheet.triangulate_joints`, `box3d` existem; estavam mortos) | alto: n00U patas, hfoo lança, n005 abertura do capuz | `z_err` ≤ .05 H; spill top/bottom | 5 de 7 em 1.º; não vê o fundo do capuz |
| 1b | Priors por classe como preflight (capuz recuado .08–.15 H, máscara +.03 H, carapaça côncava), tabela por família de rig, não global | muito baixo | médio-alto; corrige n005 hoje | `hood_recess` no clay; juiz | fazer junto com 1 |
| 2 | Linhas interiores do cel: contorno fechado = degrau, T-junção = ordem (`silhouette.edges()` já extrai a tinta) | baixo-médio (vetorizar + T-junções) | localiza o recesso, não dá magnitude | concordância com ordem z triangulada ≥ 80 % | 2.º em 5 de 7 |
| 3 | Redes de inferência: Depth Anything (só ordem de oclusão) + normais (StableNormal/Marigold) | médio (MPS ok) | só com recalibração contra marcos triangulados; L5-4b deu zero por calibrar com caixas a olho — **alvo errado, não a rede** | Pearson vs z triangulado ≥ .7 antes de mover peça | opt-in |
| 4 | VLM estimativa semântica por parte | baixo, não determinístico | útil **offline** para gerar a tabela de priors (1b) uma vez por classe; nunca por run | tabela revista por humano | — |
| 5 | Shape-from-shading com a luz do `fit_luma` | alto | cel de 2–3 tons = ~1.5 bit de normal; mal-posto | — | 1 revisor em 1.º (P1), 6 em último; tensão resolvida contra P1 por falta de evidência de integração |

**Experimento de 1 dia** (5 unidades + n01X controlo, mesmo spec, câmaras pinadas, 3 repetições):
- Manhã: pinar câmaras (4.2) e guarda autor-vs-massing (4.3) → medir lacuna e hfoo left / n017 top.
- Tarde: triangulação (6.1): patas n00U pelo top; eixo da lança hfoo por front×left; raio do capuz n005 pelo top +
  `hood_recess` à mão no spec do n005 (prova de que a régua mexe: `relief_agreement`/luma cabeça cai ≥ 30 %, IoU Δ ≤ σ,
  juiz forma ≥ 3/5; se a régua não mexe com um modelo visivelmente melhor, parar e redesenhar a métrica).
- Aceite: spill ≤ 3 % em ≥ 4 vistas por unidade; média top+bottom+rts +≥ .03; nenhuma vista −2σ; n01X ±σ.

## 7. Tensões e como foram resolvidas
- **hfoo "sheet incoerente" (P1/P2/P3/P6) vs "spec errado, sheet coerente" (P4/P7)**: ambos meio certos. Front/left são
  coerentes com lança inclinada no plano sagital (P4/P7); top/rts não desenham a lança nessa pose (registo §20.L7-4,
  `LEAN_PROPS` off por isso). Resolução: prop separado do corpo + `rot` de front×left + máscara do prop nas vistas onde o
  sheet não o desenha. Gates de "ângulo do prop igual em todas as vistas ±15°" (P3/P6) **rejeitados**: reprovariam sheets
  corretos.
- **"fit otimiza 3 vistas, gate 6" (P4)**: falso; `fit(..., wide=not args.fit_fast)` já otimiza 6. A lacuna real é a câmara
  (P7). P4 fica com o mérito de "regra sem gate não é regra" e "falha de infra = FAIL".
- **SfS em 1.º (P1)**: rejeitado por 6/7 e pela premissa do próprio P1 (sinal quantizado). Fica último.
- **Peso 0 em vistas incoerentes (P6)** vs "esconde sheets maus" (P1/P7): adotado com IoU bruto reportado ao lado e sheet
  marcado para regeneração; nunca "passar por eliminação".
- **Suspender L11-7 (P4)**: rejeitado (regra do usuário: medir todos os opt-ins); mas re-correr depois de 4.1–4.3.
- **Profundidade é polish de placeholder (P5)**: aceite como limite de esforço (1 dia + 1 bateria) — mas o critério §0
  (spill zero) e o eixo look (§5) não são polish: são o que o usuário vê.

## 8. Matriz cega (7 × 6; média dos 5 eixos, 0–10)
| reescrita | média | sd | Clarity | Quality | Consistency | Structure | Originality |
|---|---|---|---|---|---|---|---|
| P4 Tech Lead | 7.80 | .66 | 8.0 | 7.8 | 7.3 | 8.0 | 7.8 |
| P6 Data Eng. | 7.60 | .31 | 8.0 | 7.8 | 7.3 | 8.0 | 6.8 |
| P5 Prototyping | 7.43 | .27 | 8.0 | 6.8 | 7.2 | 7.8 | 7.3 |
| P7 Debug/n01X | 7.27 | .09 | 6.0 | 8.0 | 7.3 | 6.0 | 9.0 |
| P1 Graphics | 7.17 | .31 | 7.3 | 6.5 | 6.3 | 7.8 | 7.8 |
| P2 MLOps | 6.90 | .34 | 7.2 | 6.7 | 6.3 | 7.3 | 7.0 |
| P3 Testing | 6.67 | .09 | 7.0 | 6.7 | 4.8 | 7.8 | 7.0 |
Nota: P4 pontuou alto com a afirmação central errada (wide), apanhada por 1 revisor em 6; P7 pontuou baixo em clareza e
máximo em originalidade/qualidade — a síntese pesa o que foi **verificado**, não a média.

## 9. Riscos
- Gate de sheet / peso 0 pode virar desculpa: IoU bruto sempre visível; sheet incoerente obriga regeneração antes de final-use.
- Guarda autor-vs-massing pode congelar o autor em specs "seguros": juiz pareado continua, e o autor só é obrigado a não
  piorar vistas, não a não mexer.
- Câmara pinada muda os números históricos: recalcular linha de base v13 antes de comparar levas.
- Hard-min / `carve` no capuz pode criar slivers: FORM na bateria.
- Priors por classe errados afetam 233 edifícios: por família de rig, opt-in com bateria de 5.
- Leva 12 (MCP) antes de 4.1–4.3: horas humanas a corrigir o que o massing já tinha certo.
