# Evolução — do "direto da imagem" ao baseline

Todas as etapas foram medidas de novo com a **régua atual** (`silhouette.py` do commit `0a70440`,
sheet aprovado de cada unidade como juiz), para que os números se comparem.
Dados: `evolution-metrics.csv`. Figuras: `figuras/n01X-evolucao.png`, `figuras/hfoo-evolucao.png`
e uma tira por etapa em `figuras/`. Como refazer ou adicionar: `ferramentas/COMO-MEDIR.md`.

Gate de silhueta: front ≥ 0.75 e left ≥ 0.65.

## 1. Ordem pelos commits (2026-10-18 23:32 → 2026-10-19 16:00)

| hora | commit | fase | o que entrou |
|---|---|---|---|
| 10-18 23:32 | `d279a1d` | 0. arte | concept sheets de 5 vistas (nano-banana) |
| 23:58 | `08466d1` | 1. à mão | primeira unidade rigada, partes escritas no código (`SPECS`) |
| 10-19 00:12 | `5fb0902` | 2. **direto da imagem** | LLM lê o sheet e escreve o spec de partes **com coordenadas** (argon, Claude 5.5) |
| 00:24–00:40 | `e88e3b5`, `2718747` | 2b. autores | 8 modelos de spec comparados; 6 unidades × 2 autores + gate de tris |
| 00:42–01:14 | `f99dcd1`, `ac26149`, `8b45469`, `4c3e8e5`, `efe022b` | 3. forma | chanfro testado e rejeitado, MDX reais medidos, prismas afunilados, regras low-poly e chunkify no brief |
| 01:22–01:41 | `d3d22b3`, `20c391d`, `121b76f`, `58ec630`, `fc5013b` | 4. superfície + review à mão | atlas pintado; morph e fuse rejeitados; v5–v6 corrigidos pelo review do Claude |
| 01:46–02:06 | `8313eb2`, `8dcdbf5`, `6321727`, `cb4e550`, `5186b8f` | 5. esqueleto | comparação em 5 vistas; **skeleton-first** (posição vem do osso); modo skin (rejeitado); v9; v10 união booleana (rejeitado) |
| 02:11–07:50 | `08a93e7`, `1427629`, `f9c1f1b`, `0673e8a` | 6. loop fechado | 10–20 iterações modelo → review do Claude → próximo; **preflight executável** |
| 08:57 | `069abea` | 7. **gates numéricos** | v11: DSL v2 + preflight 13 regras + **gate de silhueta (IoU)** |
| 11:20 | `c88eb93` | 8. passes | passes por vista com não-regressão, câmeras calibradas, vista RTS (v12, v13) |
| 12:52 | `dfff43f` | 9. sheet hard | variante facetada + A-pose + props como referências extras |
| 13:42–13:58 | `fb38d11`, `3390397` | 10. landmarks | layout refs/prompts/runs; landmarks do sheet da própria unidade; repair por padrão; A/B da imagem 1 |
| 16:00 | `50511d0` | 11. **baseline** | `hard-v1` nas 7 unidades |

São ~16,5 h de relógio, 37 commits.

## 2. n01X (Iron Golem) — 13 etapas

| # | etapa | commit | fase | tris | IoU front | IoU left | IoU back | gate |
|---|---|---|---|---|---|---|---|---|
| 01 | v3/argon | `5fb0902` | 2 direto da imagem | 676 | 0.565 | 0.686 | 0.565 | FAIL |
| 02 | v3/5.5 | `5fb0902` | 2 direto da imagem | 608 | 0.601 | 0.685 | 0.603 | FAIL |
| 03 | argon (draft4) | `2718747` | 2b brief + gate de tris | 460 | 0.604 | 0.735 | 0.604 | FAIL |
| 04 | opus55 (draft4) | `2718747` | 2b brief + gate de tris | 616 | **0.774** | **0.787** | 0.776 | PASS |
| 05 | v6/hand | `8b45469` | 3 forma | 684 | 0.538 | 0.616 | 0.538 | FAIL |
| 06 | v8 | `121b76f` | 4 chunkify + atlas | 640 | 0.597 | 0.648 | 0.597 | FAIL |
| 07 | v9 | `cb4e550` | 5 skeleton-first | 660 | 0.551 | 0.627 | 0.553 | FAIL |
| 08 | v10 | `5186b8f` | 5 união (rejeitado) | 884 | 0.562 | 0.632 | 0.564 | FAIL |
| 09 | v11 | `069abea` | 7 gates numéricos | 696 | 0.771 | 0.694 | 0.766 | PASS |
| 10 | v12 | `c88eb93` | 8 passes | 652 | 0.829 | 0.829 | 0.823 | PASS |
| 11 | v13 | `c88eb93` | 8 passes + rts/left/back | 652 | 0.858 | **0.832** | 0.854 | PASS |
| 12 | v1 (refs) | `dfff43f` | 9 sheet hard (extra) | 584 | 0.793 | 0.816 | 0.789 | PASS |
| 13 | hard-v1 | `50511d0` | 11 baseline | 620 | **0.871** | 0.773 | **0.869** | PASS |

## 3. hfoo (Footman) — 11 etapas

| # | etapa | commit | fase | tris | IoU front | IoU left | IoU back | gate |
|---|---|---|---|---|---|---|---|---|
| 01 | opus55 (draft4) | `2718747` | 2b direto da imagem | 540 | 0.463 | 0.419 | 0.485 | FAIL |
| 02 | argon (draft4) | `2718747` | 2b direto da imagem | 664 | 0.523 | 0.505 | 0.528 | FAIL |
| 03 | v-ref (sem refs) | `dfff43f` | 9 pipeline atual sem hard | 576 | 0.556 | **0.632** | 0.576 | FAIL |
| 04 | v1 (refs) | `dfff43f` | 9 com hard + clean + props | 556 | 0.702 | 0.540 | 0.663 | FAIL |
| 05 | hardfirst | `3390397` | 10 hard como imagem 1 | 568 | 0.541 | 0.538 | 0.529 | FAIL |
| 06 | abS1 | `3390397` | 10 A/B aprovado, sem repair | 592 | 0.576 | 0.532 | 0.582 | FAIL |
| 07 | abS2 | `3390397` | 10 A/B aprovado, sem repair | 556 | 0.589 | 0.548 | 0.592 | FAIL |
| 08 | abH1 | `3390397` | 10 A/B hard, sem repair | 484 | 0.501 | 0.569 | 0.485 | FAIL |
| 09 | abH2 | `3390397` | 10 A/B hard, sem repair | 540 | 0.621 | 0.558 | 0.659 | FAIL |
| 10 | abR1 | `3390397` | 10 hard + repair | 552 | 0.631 | 0.559 | 0.623 | FAIL |
| 11 | hard-v1 | `50511d0` | 11 baseline | 528 | **0.820** | 0.551 | 0.665 | FAIL |

Etapas 06–09 não são sequenciais: são repetições de um A/B. Servem para medir ruído
(front 0.50–0.62 entre runs da mesma configuração).

## 4. Leituras para o paper

1. **"Direto da imagem" não basta.** O LLM lendo o sheet e escrevendo partes com coordenadas
   dá front 0.57–0.60 (n01X) e 0.46–0.52 (hfoo). Falha o gate nas duas unidades.
2. **Um outlier cedo.** O spec do opus-5.5 no draft4 já passava no n01X (0.774 / 0.787). Não se
   repetiu no hfoo (0.46). Sorte de unidade e de autor, não método. Bom exemplo de por que n=1 engana.
3. **Iterar "no olho" piorou.** Fases 3–6 (forma, chunkify, skeleton-first, review do Claude
   em loop) ficaram em 0.54–0.60 de front pela régua atual, abaixo da etapa 04. Na época o review
   dava nota crescente (4.5 → 5.5), mas a silhueta não melhorava.
4. **O salto veio com o gate numérico.** v9 → v11: front 0.551 → 0.771 (+0.22). A mudança foi
   a régua (IoU + preflight) entrar no loop, não um modelo melhor.
5. **Os passes por vista somam.** v11 → v13: front +0.09, left +0.14, back +0.09.
6. **Sheet hard + landmarks + repair** levam o front ao maior valor (0.871 n01X, 0.820 hfoo), mas
   o left caiu no n01X (0.832 → 0.773) e não sai de ~0.55 no hfoo. O perfil é o problema aberto
   (lança vertical, profundidade do corpo).
7. Tris dentro de 400–700 em todas as etapas, menos v10 (884, união booleana).

## 5. Ressalvas

- n01X é a unidade em que o pipeline foi afinado. hfoo é o primeiro teste fora dela.
- Várias etapas antigas usaram outro builder, brief e sheet. A régua é a mesma, o resto não.
  Isto é evolução histórica, não ablação. A ablação (desligar uma peça por vez no pipeline atual)
  ainda precisa ser feita.
- 1 run por etapa, com ruído medido de até 0.12.
- A figura mostra cor e textura, que o IoU não mede.

## 6. Depois do baseline (2026-10-31 → 2026-11-07): levas 19–20, concept, alavancas e largura

As etapas 25+ não foram medidas com a régua das 24 (`ferramentas/medir_etapas.py`): as unidades, os sheets
e o builder mudaram (ficha 17 redesenhou os concepts, o olho reescreve as peças). Os números abaixo são os
de cada ficha, com a régua indicada nela.

| quando | o quê | ficha / PIPELINE | número que fica |
|---|---|---|---|
| 10-31 | Leva 19: `v18-cvt` vira default (`--eye-fuse 12 --eye-union bone --eye-union-reduce cvt --eye-paint box`), decisão do autor contra o juiz; replay de receita 9–23 s/unidade em vez de ≈ 690 s | §37 | `model.glb` byte-igual ao v18-cvt em 5/6; n00U 704 → 626 tris pela regra "união nunca custa mais que as peças" |
| 10-31 | Roster batch: cadeia prompt → sheets → parts → model com resume; piloto n01I/n01N | §38 | estimativa 82,6 h seq. / US$ 53,66 para 162 |
| 10-31 | Leva 20: sheet delit e projectado no atlas (`--eye-project`), filtro de cor e por peça, acentos protegidos | §39 | 42–45 % do atlas nunca visto; juiz sheet B 4-0 mas autor fica com `v19-default`; `tight` passa a default |
| 10-31 → 11-06 | Concept refeito à volta do autor | ficha 17 | 20 rondas, 130 → 0 rejeitadas, 266 redesenhos; horas do autor não medidas |
| 11-04 → 11-05 | Alavancas do modelo | ficha 18 | n02S front/left .704/.664 → .746/.720; n01G front .581 → .697; molde sozinho +.04/+.04 (n02S), +.01/−.02 (n01G); n = 2, abaixo do ruído .12 |
| 11-06 → 11-07 | `roster-v6`, 165 modelos one-shot | ficha 19, `04-resultados` | 164/166 linhas chegam a `model.glb`; tris 690,5; parts .57 (massing) → .78 (olho); IoU front .77 → .71; 105,9 h de `model.s`; US$ 24,3 de imagem; PASS 0 no gate da Leva 12, 69/165 no gate do baseline (ronda final) |
| 11-07 | Texturas pós-GLB | ficha 20 | pesquisa, sem medição |

Leitura: a largura passou de 7 unidades (baseline) para 165 modelos com a mesma cadeia (corrigida 9 vezes a meio do batch, ficha 19).
O olho sobe as peças reconhecidas (+.21) e baixa a silhueta (−.06 front), nas 165. O artista Opus é a mediana 576 s de um estágio de
2 239 s (26 %): o custo que escala voltou a ser o pré-olho (massing, fit, moldes neurais), não o VLM — o contrário do que `01-tese.md`
"Juiz vs produção" mediu no `v18-r0`. O gate de massing (stage 1, régua da Leva 12) falha em 164/164 porque nunca fechou desde a Leva 12;
com o gate do baseline (front ≥ .75, left ≥ .65) passam 84/165 massings e 69/165 rondas finais. Síntese e descobertas: `04-resultados-e-descobertas.md`.
