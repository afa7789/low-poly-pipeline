# 13 — Leva 16: o olho escala? (rondas, crítico + consertador, referência WC3 real, pele nas juntas)

- Data: 2026-10-30
- Commit(s): main `aa799b55` (L16-3 Hive), `84726642` (L16-4 pele), `5c2adc6a` (L16-2 crítico), `d069e044` (L16-1 rondas; Leva 16 completa).
  Detalhe por item em `castle_fight/artifacts/model-sheets/PIPELINE.md` §34 (`### 34.L16-1..4`).
- Problema do baseline atacado (ficha 12, L15-5): o estágio com olho ganha semelhança ao concept mas perde "forma contínua" (arestas de primitivas
  nas juntas) e não itera (rondas 0→2 quase iguais; o modelo nunca pede stop). Pergunta do usuário: mais chamadas? modelo mais forte como crítico?
  como se compara com o WC3 real?
- Hipóteses: (H1) mais rondas melhoram; (H2) crítico forte + consertador separado melhora; (H3) pele/solda nas juntas recupera a forma contínua;
  (H4) o WC3 real dá alvos numéricos. **H1, H2, H3 falsas no aceite; H4 verdadeira.**

## Mudança

- L16-1: `--eye-rounds` até 9, `--eye-stop judge|model|never`, ≤ 48 peças, ponta ≥ .01 no prompt; `eye_compare --l16`.
- L16-2: `eye_critic.py` + `prompts/eye-critic.md` (defeitos JSON `{part, view, what, fix, severity}`), `--eye-critic MODEL[@EFFORT]`, `--eye-fixer`,
  custo em micro-USD; crítico = Fable 5.1 @high, consertador = opus (Reflexion, CRITIC em `docs/references.md`).
- L16-3: `mdx_inspect.py` (MDX v800 completo), `hive_sheet.py` (stats, render 6 vistas, pares, juiz), `review_pair --reference <png>`.
- L16-4: `eye_skin.py` (`bridge`, `blend`, `wrap`, `weld`), `--eye-skin`, `skin_compare.py`; juntas por osso/pai-filho ≤ .03 H.

## Protocolo

- Mesmas 6 unidades e câmaras da ficha 12; base `v15-r1`; controlo justo `l15-col-part-outline` (v15 + contorno, resolve o confundidor da ficha 12).
- Juiz pareado `review_pair.py` (sheet/artista/wc3/forma, 4 votos, `session:opus`), 1 trajectória por unidade (n=1), 1 Blender + 1 `claude -p` por agente.
- Hive: 57 modelos WC3 (MDX + texturas, só referência, nunca activo), mediana e p10–p90.

## Resultado

| item | o que mediu | resultado | default? |
|---|---|---|---|
| L16-1 rondas 3/6/9 | 54 rondas, 42 pares | parts satura na ronda 1–2 em 4/6 e oscila (hfoo 9–19/25); r6×r3 sheet+artista 3/6 a 1.65×, r9×r3 1/6 a 2.22×; modelo pediu stop 1/54; regra do juiz pára 2/6 e custa mais do que poupa | não |
| L16-1 controlo justo | 18 pares olho × (v15+contorno) | olho ganha sheet/artista/wc3 **18/18**; forma fica com o controlo 4/6 — **a perda de forma não é o contorno nem falta de rondas** | — |
| L16-2 crítico + consertador | 6 unidades, 12 pares, US$ 24.7 | crítico acha defeitos reais, 85 % "somem" segundo ele; mas parts k/n cai 6/6 vs v16, sheet+artista 1/6 (n02X 4-0 em tudo), tempo 1.82× | não |
| L16-3 Hive | 57 MDX vs 6 v16 | WC3: **6 peças (3–8) de ~100 tris**, 551 tris, verts/tri 1.54, 256² pintada, 14 cores, tinta 8 % dos texels, contraste .28; nós: 38–65 peças de 11–18 tris, cor plana. Com o Hive como referência: v16 ganha wc3 3/3, forma 1/3 | — (alvos) |
| L16-4 pele nas juntas | 4 técnicas × 6, 24 pares | geometria quase indistinguível do v16; componentes 33–70 (alvo ≤ 12); forma ≥ 3-1 em 1–2/6; controlo idêntico dá A 4-0 numa unidade e 2-2 noutra | não |

## O que piorou / limitações

- O juiz de 4 votos varre 4-0 em pares quase idênticos e não é transitivo (n005: r6>r3, r9<r6, r9>r3): precisa de limiar parts/IoU antes de contar.
- Consertador sem os renders desfaz o que estava certo e não listado; "resolvido" é o que o crítico vê, não o que o gate mede.
- `bridge` só liga tubo–tubo ponta com ponta (0–6 pontes/unidade); `weld` não chega a malha única (tubos de 8 lados têm vincos de 45°).
- Fable @max com o prompt real: > 24 min numa chamada; @high 267 s / US$ 1.22.
- n=1 trajectória por unidade; ruído de amostragem do LLM não medido.

## Conclusão (1 frase para o paper)

Escalar o laço com olho em chamadas (rondas, crítico de modelo mais forte) ou remendar as juntas depois não move o juiz: o olho satura em 1–2 rondas e
a lacuna para o WC3 real é estrutural — 6 peças pintadas de ~100 tris contra 40–65 primitivas planas de ~15 — pelo que o próximo passo é a união por
material (SDF/booleana por grupo de peças) e textura pintada procedural, não mais LLM.
