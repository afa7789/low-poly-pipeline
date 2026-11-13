# Tese — busca em largura, solução one-shot

## Objetivo

Criar uma forma **fácil** de gerar **muitos** assets 3D para jogos (unidades, criaturas, prédios,
props — e outras coisas), a partir de uma lista de personagens + uma temática.

Chegar a **um pipeline fixo** que, a partir dos prompts dos personagens de uma temática (raça,
facção, jogo), gere os modelos **de primeira**, sem ninguém iterar por unidade: one-shot e seamless.

Castle Fight (estilo Warcraft III, ~167 unidades) é o **primeiro caso de estudo**, não o escopo.
O que nele é específico vira **perfil de estilo** configurável:

| peça do perfil | no Castle Fight |
|---|---|
| orçamento de tris por classe | WC3 SD: 400–700 unidade, 900–1600 herói, 600–800 prédio |
| famílias de rig e clips | 22 famílias; idle/walk/attack/death |
| superfícies e paleta | 14 superfícies pintadas; cores do próprio sheet |
| câmera de jogo | RTS 45°/45° |
| gates | IoU front ≥ 0.75, left ≥ 0.65; 3–8 materiais |
| template do sheet | 5 vistas 3+2 (unidade) ou elevações + teto (prédio) |

Prova de generalidade para o paper: pelo menos **um segundo caso** (outro jogo/estilo ou outro tipo
de asset) rodando o mesmo pipeline e trocando só o perfil. **Estado 2026-11-07: não feito.**

A melhoria do pipeline vem de **busca em largura**: testar muitas unidades diferentes, uma tentativa
cada, ver onde o pipeline falha em comum e corrigir o **pipeline**, não a unidade.

## O que foi alcançado e o que não foi (2026-11-07)

Detalhe e números em `04-resultados-e-descobertas.md`; leitura crítica em `REVIEW-2026-11-07.md`.

| afirmação | estado | evidência |
|---|---|---|
| A cadeia corre em largura sem tocar numa unidade | **sim** | `roster-v6`: 165 modelos de 160 cartões, 164/166 linhas chegam a `model.glb`, ≈ 690 tris, rigados, 4 clips |
| One-shot no estágio de modelo | **sim, com reservas** | 1 run por unidade; mas 3 rondas de artista + reenvios dentro do estágio, 9 correcções do pipeline a meio do batch (`--resume`) e um rerun do olho em 61 unidades |
| One-shot na cadeia inteira | **não** | o sheet (juiz de todos os gates) passou por 20 rondas de revisão do autor (ficha 17) |
| Seamless (mesmo comando para todas) | **sim** | `roster_batch.py --all-units`; excepção: 5 pseudo-unidades com caixas marcadas à mão |
| Taxa de PASS no gate declarado (stage 1, spill ≤ .03) | **0/165** | o gate nunca fechou desde a Leva 12 (0/36 vistas, ficha 11) |
| Taxa de aceite no gate do baseline (front ≥ .75, left ≥ .65) | **78/165 (47 %)** | GLB final medido nas 165; baseline era 3/7 na silhueta |
| Peças reconhecidas (parts k/n) | **.77 (GLB final)**, .57 antes do olho | +.21 em 136/165 unidades |
| Silhueta depois do olho | **pior**: IoU front −.055 em 140/165 | o olho troca silhueta por peças; a união + molde devolve +.016 |
| Bípedes vs resto | **bípedes .77 front, 52/101 no gate; não-bípedes .66, 26/64** | 24 famílias de rig, 20 com n ≤ 8 |
| Segundo caso de estudo | **não** | — |
| Avaliação humana, baseline externo, repetição, ablação em largura | **não** | n = 1 por unidade; juiz é um LLM; nenhum braço de controlo no roster-v6 |

O que o paper pode afirmar: o pipeline **gera em largura** (engenharia demonstrada). O que não pode: que os modelos são bons
(qualidade não demonstrada — não há humano, não há baseline, a métrica declarada dá zero e a secundária desce no estágio mais caro).

## Duas formas de melhorar (e por que só uma conta)

| | profundidade | largura |
|---|---|---|
| o que itera | a mesma unidade, a mesma imagem | o pipeline, sobre muitas unidades |
| quem corrige | humano ou IA, olhando aquele modelo | regra, gate ou prompt que vale para todas |
| ganho | nota alta numa unidade | taxa de acerto de primeira no conjunto |
| risco | overfit: a correção não transfere | ganho médio menor por rodada |
| exemplo no histórico | v6–v13 do n01X (review do Claude, passes na mesma imagem) | draft4 (6×2), draft16 (7 unidades), hard-v1 (7 unidades), roster-v6 (165) |

As etapas de profundidade servem como **teto** ("até onde dá para chegar nesta unidade com esforço")
e como **fonte de regras**: o que se descobre iterando uma unidade vira regra do pipeline (preflight,
landmarks, DSL) e é testado em largura. O resultado do paper é sempre medido em largura.

## Definições

- **One-shot**: uma execução do pipeline por unidade, sem edição humana entre o prompt e o GLB.
  Loops automáticos dentro do pipeline (repair, rondas do olho, reenvios) contam como one-shot porque fazem
  parte dele, mas entram no custo e no tempo. *(Decidido 2026-11-07; o roster-v6 cumpre isto no estágio de modelo.)*
  A revisão humana do sheet (ficha 17) **não** é one-shot: é um estágio humano a montante e tem de ser contado como custo.
- **Seamless**: o mesmo comando para todas as unidades da temática; nenhuma flag, prompt ou correção
  por unidade além do cartão de design.
- **Conjunto de desenvolvimento**: unidades usadas para afinar o pipeline (n01X, hfoo, n005, n00U, n017, n02X, n02S, n01G).
- **Conjunto de teste**: unidades da temática que o pipeline nunca viu durante o ajuste. *Hoje não existe de verdade:
  as 160 tiveram o sheet revisto pelo autor e o pipeline foi corrigido durante o próprio batch.*

## Métrica principal

**Taxa de aceite de primeira no conjunto de teste**, com o pipeline congelado, **no gate do baseline** (IoU front ≥ 0.75 e left ≥ 0.65
contra o sheet aprovado). O gate "honesto" da Leva 12 (spill ≤ .03, bare ≤ .10 por vista) fica como diagnóstico: nunca fechou em nenhuma
unidade e por isso não mede progresso.

Secundárias: parts k/n (peças do sheet reconhecidas no render), IoU médio front/left/back/rts, tris dentro do orçamento, custo e tempo por
unidade, aceitação humana (sim/não olhando a figura — **ainda não medida em nenhuma leva**).

Limite das métricas: IoU mede envelope; parts k/n depende de uma segmentação do sheet por VLM; nenhuma mede "parece WC3". O juiz pareado
(`review_pair.py`) é um LLM: não transitivo (ficha 13) e ignorado pelo autor quando discorda (Leva 19).

## Onde o baseline está, nessa régua

`hard-v1` (one-shot, 7 unidades, 1 run cada):

- todas as 7: **1/7 PASS** (só n01X); silhueta 3/7;
- sem o n01X, que é conjunto de desenvolvimento: **0/6 PASS**, silhueta 2/6 (n005, n01I);
- no n01X, o one-shot hard-v1 (front 0.871) já empata com o teto da profundidade v13 (0.858).
  Ou seja, o que foi aprendido em profundidade virou regra e transferiu, **nessa unidade**.

`roster-v6` (one-shot, 165 unidades, 1 run cada, 2026-11-07): silhueta (gate do baseline) **78/165**; ver `04-resultados-e-descobertas.md`.

## Protocolo para cada melhoria

1. A melhoria muda o pipeline, nunca uma unidade específica.
2. Congela o pipeline (commit) e roda one-shot em todas as unidades do conjunto (hoje 165).
3. Reporta a taxa de aceite e o IoU/parts médio contra a rodada anterior, **na mesma régua** (qualquer mudança em `silhouette.py` ou
   no `parts.json` invalida a comparação — aconteceu em 2026-11-05 com o de-ink).
4. Separa o resultado de desenvolvimento do de teste; reporta bípedes e não-bípedes em separado.
5. Repete 3× se a diferença for menor que o ruído (0.12 de IoU). *Regra escrita em 2026-10-20 e nunca aplicada nas fichas 17–19.*

## Juiz vs produção

- `review_pair.py` é um **comparador A/B**: dois runs da mesma unidade, concept no meio, 4 eixos (sheet / artista / wc3 / forma), 4 votos com troca de
  lado (A|B, A|B, B|A, B|A), maioria por eixo, 2-2 = empate, renders byte-idênticos (hash) = empate sem chamar o modelo (L17-1, ficha 14).
- Serve para **decidir se uma leva muda o default**. Em produção (223 unidades) **não corre**: por unidade corre artista VLM × rondas + revisor por vista +
  gates determinísticos + `--eye-stop model` (default).
- Medido 2026-10-31 (hfoo `v18-r0`, worktree `leva18`, `timing.json` + `review.md`): **626.6 s** total; artista 575.0 s = **91.8 %** (3 rondas de
  202.7 / 145.6 / 226.6 s); `measure` 30.4 s (4.8 %), `blender_build` 3.3 s, boards/clay/outline/stretch ~1 s cada, outros 13.7 s. Modelo: 696 tris,
  38 peças, parts 18/25. O processo Python fica a 0 % CPU durante a chamada: o tempo é VLM, não Python. **Isto era o olho sozinho.**
- Medido 2026-11-07 no `roster-v6` (165 unidades, 4 jobs em paralelo): estágio de modelo mediana **2 239 s**; olho 778 s (35 %); artista Opus
  **576 s = 26 %**; revisor por vista 55 s; os ≈ 1 460 s restantes são pré-olho (massing, fit, SAM2, TripoSplat ≈ 350 s) e não estão itemizados.
  Com os moldes neurais, o custo que escala deixou de ser o VLM. (Ressalva: 4 jobs em paralelo inflam as partes CPU/GPU, não as chamadas.)
- Leva 18 (L18-4, ficha 16) mediu o N de votos: 2 / 4 / 6 / 8 × 2 repetições × 6 unidades; concordância de forma entre repetições 5/6, 6/6, 5/6, 6/6;
  taxa de empate sobe com N (0 → .083); N = 8 é 1.8× o tempo. **`VOTES = 4` confirmado.** Tempo por estágio (mediana das 6): `v18-r0` 691 s (artista 92 %),
  `v18-qem` +37 s, `v18-cvt` +23 s, juiz 35–41 s por par.
