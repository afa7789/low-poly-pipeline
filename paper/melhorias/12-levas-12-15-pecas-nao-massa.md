# 12 — Levas 12–15: do gate de massa ao estágio com olho ("peças, não massa")

- Data: 2026-10-29 → 2026-10-30
- Commit(s): main `a560452b` (Levas 1–13 integradas), `e138943b` (Leva 14), `b6248361` (Leva 15 completa). Detalhe por item em
  `castle_fight/artifacts/model-sheets/PIPELINE.md` §30 (L12), §31 (L13), §32 (L14), §33 (L15).
- Problema do baseline atacado (§7 #): spill/bare por vista fora do gate; textura ilegível; modelos que "batem" no IoU mas não lêem como o concept.
- Hipótese: (L12–L13) apertar o gate de silhueta (IoU, spill ≤ .03, bare ≤ .10, contact, body/prop split) e polir a malha (MCP, inscribe, iters)
  fecha o gap; (L14–L15) **falsa**: o gate mede massa, o olho mede peças — o aceite tem de ser por peça + juiz de visão, e a geometria tem de
  nascer como peças.

## Mudança

- L12 (10 itens): gates por vista, ajuste assimétrico, `look.py`, matriz de ablação de todas as opt-ins (`ablation_matrix.py`, 36 variantes).
- L13 (5 itens): `--polish on` (servidor MCP stdio próprio), `--inscribe cut`, `--author-guard`, `--depth` (no-op por dados), `DETERMINISTIC_ITERS` 8→15 (default).
- L14 (3 itens): `--body union|sdf` a 700/1000 tris; 5 texturas procedurais + `--texture sheet`; **3 unidades refeitas à mão por primitivas** (4–13 min) → diagnóstico C1–C6.
- L15 (7 itens): `parts_gate.py` (`--gate parts`), `--sdf-core on` (peças rígidas fora do SDF), `--outline hull` + `--face decal` + `--zone-contrast`,
  `part_rules.py` (prop_side/arm_pose/part_exists/incoherent_part no preflight), **`--eye on` (estágio com olho: `session:opus` vê concept × render ×
  overlay e devolve DSL JSON de primitivas; 3 rondas; `eye_lib/eye_stage/eye_compare`)**, rim do `StyleShader` × luma da base, contorno default.

## Protocolo

- Unidades: n005, n00U, hfoo, n017, n02X, n01X (specs e câmaras da bateria v15 congelados; `--deterministic`, ruído `noise-l12.json`, marca > 2σ).
- Spec author / modelo de imagem: `session:opus` (`claude -p`), sem geradores imagem→3D, textura procedural + decal recortado do concept.
- Runs por unidade: 1 por variante (controlo + variante), 2 processos pesados por agente.
- Métrica principal: IoU/spill/bare por vista (guarda) → **`parts k/n` (L15-1) + juiz pareado `review_pair.py` (sheet/artista/wc3/forma, 4 votos)**.

## Resultado

| leva / item | o que mediu | resultado | default? |
|---|---|---|---|
| L12 gates + matriz | 36 variantes × 6 unidades | PASS 0/6; nenhuma opt-in fecha o spill | pesos de custo não |
| L13 polish / inscribe / iters | idem | polish 0/36→0/36; inscribe fecha só n01X; iters-15 melhora ruído | iters-15 sim |
| L14-1 union × sdf | 24 runs + juiz | union vence forma em 1/6 | não |
| L14-2 texturas | 5 × 6 + juiz | nenhuma vence o cel (painted 3/6) | não |
| L14-3 conserto à mão | 3 unidades, juiz vs v15 | **juiz 11/12 eixos 4-0 pró-conserto; IoU/spill pioram** | — (diagnóstico) |
| L15-1 gate por peça | 6 v15 + 3 consertos | conserto > v15 só em 1/3; correlação juiz×gate −.97 → −.06 | não |
| L15-2 peças rígidas fora do SDF | 12 runs + juiz | forma+artista pró-core 2/6 | não |
| L15-3 contorno / cara / contraste | 24 runs + juiz | **contorno artista+wc3 ≥ 3-1 em 6/6 e 3/3**; cara 5/6 mas 0/3 (usuário rejeitou) | contorno sim (L15-7) |
| L15-4 preflight por peça | 6 unidades | checks acertam n02X/n005; reparo numérico derruba IoU (hfoo left .55→.28) | checks sim, reparos não |
| L15-5 estágio com olho (v16) | 6 unidades, 9 pares | **parts k/n sobe 6/6 (ex. n017 9→19/19); sheet/artista/wc3 4-0 em 18/18 vs v15 e 9/9 vs conserto; forma perde 4/6; stretch 2.2→1.00; 8–22 min/un.** | não (aceite estrito) |

Agregado L15-5 (v15 → v16): IoU médio cai ~.03–.08 por vista na maioria das unidades enquanto `parts` sobe de 98/162 para 137/162; tris ≤ 700 (+hull);
custo 3–4 chamadas `session:opus` por unidade (86–545 s cada).

## O que piorou / limitações

- Primitivas rígidas perdem o eixo "forma contínua" do juiz (4/6 em L15-5, idem L14-3 e L15-2): superfície em degraus nas juntas.
- O juiz em L15-5 viu v16 com contorno e v15 sem — confundido com L15-3; falta controlo v15 + contorno.
- Gate por peça (cover/material/lado/tamanho) ainda não vê rosto/óculos/barriga-vs-caixa: só o olho vê (§4 do diagnóstico).
- Tempo: n017 21.7 min (65 peças, 2 reenvios); meta era ≤ 15.
- n=6 unidades, n=3 consertos: correlações fracas; a bateria de 8 sheets ainda não foi corrida com `--eye on`.

## Conclusão (1 frase para o paper)

Três levas de regras numéricas sobre a silhueta (gates, polimento, SDF, texturas) não moveram o juiz de visão; mover o aceite para peças e dar ao
autor um laço que **vê** o render e remonta primitivas (L15-5) deu 4-0 em 18/18 pares contra o baseline em semelhança ao concept — ao custo do eixo de
forma contínua e de ~10 min de LLM por unidade.
