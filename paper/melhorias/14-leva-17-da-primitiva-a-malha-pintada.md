# 14 — Leva 17: da primitiva à malha pintada (juiz calibrado, união por material, textura pintada)

- Data: 2026-10-30 → 2026-10-31
- Commit(s): main `1db45b42` (L17-1 juiz), `614ad0c8` (L17-2 união), `9a5a83fd` (L17-3 pintura; Leva 17 completa).
  Detalhe em `castle_fight/artifacts/model-sheets/PIPELINE.md` §35 (`### 35.L17-1..3`).
- Problema atacado (ficha 13): a lacuna para o WC3 real é estrutural — 6 malhas pintadas de ~100 tris contra 40–65 primitivas planas de ~15 — e o
  juiz de 4 votos varre 4-0 em geometria idêntica.
- Hipóteses: (H1) 8 votos + troca de posição + limiar tornam o juiz repetível; (H2) união SDF por grupo de material recupera a forma contínua sem perder
  semelhança; (H3) textura pintada procedural + linha de tinta sobe as stats WC3 e dispensa o casco. **H1 parcial, H2 metade, H3 falsa.**

## Mudança

- L17-1: `review_pair.py --votes N` (par; metade com A/B trocados, desinvertido ao contar), par idêntico por hash = empate sem chamar, `--near-rule`
  opt-in, `judge_calib.py` (Zheng et al. 2023 em `docs/references.md`).
- L17-2: `eye_union.py` — smooth-min (k .02 H) por grupo `material|bone|group`, surface nets (voxel .006 H), QEM com `max_dev` .015 H, props rígidos,
  pesos mistos na junta; `--eye-union`. Substitui a pele (L16-4) em `eye_stage.finish`.
- L17-3: `eye_paint.py` — UV por ilhas (normal ≤ 60°), atlas 256² pintado por posição (gradiente, pincel, luz, oclusão BVH), quantização por material,
  linha de tinta em diedros > 40° e fronteiras de material; `--eye-paint`, `--outline hull|ink|both`.

## Protocolo

- Base `v16-r3` (olho, prompt novo), 6 unidades, controlo justo v15 + contorno, pares com referência do Hive (hfoo/n02X/n005).
- Juiz `--votes 8` com troca (L17-1 entregue cedo e fundido no `main` antes das outras medições); par idêntico/near-idêntico como linha de ruído.

## Resultado

| item | o que mediu | resultado | default? |
|---|---|---|---|
| L17-1 juiz | 80 chamadas: trio n005 r3/r6/r9 ×2, hfoo ×2, A=B forçado | sem troca o juiz escolhe a esquerda **32/32** em renders idênticos; com troca .47 (trio) / **.67 (hfoo)**; 0 ciclos; repetibilidade entre chamadas 25–50 % em pares quase iguais; 8 votos = 2.0× custo (US$ .42/par) | não (fica 4 votos + troca + hash) |
| L17-2 união | 3 modos × 6, 8 votos, 30 pares | **forma ≥ 3-1 para a união em 5/6** (`bone`; 8-0 em n005/n01X) — primeiro item em 3 levas que move a forma; mas sheet+artista 8-0 para v16-r3 em 6/6; componentes 13–19 (alvo ≤ 12, por 15–20 materiais/unidade); tris > 700 em 2/6; stretch 1.00 | não |
| L17-3 pintura | 2 variantes × 6, 8 votos, 15 pares | stats WC3 atingidas: cores 8→11–13 (6/6), contraste ≥ .19 (5/6), tinta 3–12 % (4/6); **juiz 8-0 para a cor plana em sheet/artista/forma 6/6**; `ink` sem casco perde sheet/artista 6/6 (casco é o contorno que o juiz lê); só ganha wc3 contra o Hive 3/3 | não |

## O que piorou / limitações

- Pintura: ~300 ilhas UV num atlas 256² ≈ 12 texels por ilha → lê como camuflagem, não como pincelada (visível em `history/2026-10-30-l17-paint/hfoo.png`).
  Precisa das malhas unidas (poucas ilhas grandes) — a ordem certa é união → pintura, não medida.
- União: detalhe pequeno derrete (mão da n005), non-manifold 8–114 arestas (cluster não fechado antes do QEM), folha de comparação com v16-r3 pós-contorno
  e união pré-contorno (o juiz usou os GLBs certos).
- Juiz: o ruído está entre chamadas repetidas, não entre votos da mesma chamada; mais votos não ajudam. `v16-skin-off` × `v16-r1` só é byte-idêntico em 1/6
  (não-determinismo por investigar).
- n = 1 trajectória por unidade; `review_pair` lança 4 `claude -p` em paralelo por chamada (regra de 1 processo cumprida só por par).

## Conclusão (1 frase para o paper)

Unir as primitivas por grupo de material é a primeira intervenção em três levas que ganha o eixo de forma (5/6 a 8 votos), mas perde a semelhança ao
concept porque o detalhe está na geometria e não na textura; a pintura procedural atinge as estatísticas do WC3 e perde 8-0 por falta de área de atlas —
os dois só fecham a lacuna juntos (fundir cores em ≤ 12 materiais → unir → pintar ilhas grandes), e o juiz tem de ser lido com repetição.
