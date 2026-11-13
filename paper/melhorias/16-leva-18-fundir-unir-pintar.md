# 16 — Leva 18: fundir cores ≤ 12 → unir por osso (QEM | CVT) → pintar por campos de peça; quantos votos precisa o juiz

- Data: 2026-10-31
- Commit(s): main `1e387a79` (L18-0, ficha 15), `f8cb6c89` (L18-1..4; Leva 18 completa; histórico linear).
  Detalhe em `castle_fight/artifacts/model-sheets/PIPELINE.md` §36 (`### 36.L18-1..3`, `### 36.L18-4`).
- Problema atacado (ficha 14): 15–20 materiais por unidade → união por material dava 13–19 malhas e cada uma perdia detalhe; pintura sobre ~300
  ilhas UV (~12 texels/ilha) lia como camuflagem. A ordem proposta era fundir cores → unir → pintar ilhas grandes.
- Hipóteses: (H1) fusão perceptual (OKLab) a ≤ 12 materiais baixa os componentes para ≤ 12; (H2) a união por bone com CVT em vez de QEM fica no
  orçamento e lê melhor; (H3) cartas por componente × eixo + cor por campo de peça dão ≥ 100 texels/ilha e o juiz passa a preferir a malha pintada;
  (H4) 4 votos chegam — mais votos não compram repetibilidade. **H1 metade (materiais sim, componentes não), H2 sim no par directo, H3 falsa no
  juiz, H4 verdadeira.**

## Mudança

- L18-1 `eye_fuse.py` (`--eye-fuse N`, 0 = off): classes glow / glass / skin / other; distância OKLab (Ottosson 2020, nova linha em
  `docs/references.md`); pares da mesma classe a < .04 fundem, depois o par mais próximo até ≤ N; cor = média ponderada por triângulos.
- L18-2 `eye_union.DETAIL = .10 H` (peça com lado < 10 % H fica rígida: fivela, fenda, olho, lente); `--eye-union-reduce qem|cvt` (surface nets →
  `retopo.reduce` QEM guardado `max_dev` .015 H, ou `retopo.cvt` Voronoi por curvatura no mesmo orçamento).
- L18-3 `--eye-paint box`: cartas por componente soldado × eixo da normal (overlap 0–8 texels); **cor por texel pelo campo das peças** (`fields.json`:
  planos convexos de cada peça; o texel toma o material da peça mais próxima, não do triângulo — tira a costura em ziguezague da L17-3); linha de
  tinta por texel nas fronteiras de material + diedros > 40°.
- L18-4 `judge_n.py`: `review_pair.compare` com N = 2/4/6/8 votos, 2 repetições independentes por N, 6 unidades (48 chamadas, 240 votos).
- `tools/blender/leva18.py` (`run`, `table`, `timing`, `judge`): cópia do `v18-r0` → fusão → união → medida do gate **antes** da pintura → pintura →
  casco → stretch; `timing.json` por run.

## Protocolo

- Base `v18-r0` (ficha 15: olho, 3 rondas, `face_kind`), 6 unidades; variantes `v18-qem` e `v18-cvt` (`--eye-fuse 12 --eye-union bone
  --eye-union-reduce qem|cvt --eye-paint box --outline hull`).
- Juiz `review_pair --votes 4` com troca, um voto de cada vez, A = run mais antigo: v18-qem × v16-r3, v18-cvt × v16-r3, v18-cvt × v18-qem
  (`runs/draft/<id>/<B>/pairwise4-<A>.json`; `history/2026-10-31-l18/judge4.md`).
- Aceite por variante: forma ≥ 3-1 para o v18 **e** sheet+artista ≥ 2-2 em ≥ 4/6.
- Gate de peças medido antes da pintura (com atlas único o gate lê `mat 0.0` em tudo — limite do instrumento, não regressão).

## Resultado

Medida (`history/2026-10-31-l18/table.md`; mats = materiais do DSL antes → depois; comps = componentes do corpo; tris sem casco; texels/ilha = mediana (mín)):

| un. | mats | comps qem / cvt | tris qem / cvt | ilhas qem / cvt | texels/ilha qem / cvt | parts k/n r0 → qem / cvt | IoU frente r0 → qem / cvt | s qem / cvt |
|---|---|---|---|---|---|---|---|---|
| n005 | 17 → 9 | 13 / 13 | 696 / 620 | 277 / 194 | 40 (1) / 81 (2) | 28/28 → 28 / 27 | .880 → .872 / .871 | 38 / 23 |
| n00U | 6 → 6 | 19 / 19 | **818** / 704 | 283 / 203 | 16 (1) / 55 (1) | 17/21 → 16 / 16 | .875 → .840 / .833 | 36 / 27 |
| hfoo | 8 → 7 | 13 / 13 | **744** / 632 | 252 / 182 | 48 (1) / 99.5 (1) | 14/25 → 18 / 18 | .875 → .783 / .786 | 30 / 18 |
| n017 | 7 → 7 | 13 / 13 | 684 / 622 | 275 / 214 | 33 (1) / 55 (2) | 18/19 → 16 / 16 | .845 → .883 / .853 | 45 / 33 |
| n02X | 14 → 11 | 13 / 13 | 688 / 650 | 230 / 183 | 44 (1) / 142 (1) | 28/39 → 28 / 30 | .903 → .897 / .886 | 36 / 23 |
| n01X | 7 → 5 | 14 / 14 | 642 / 642 | 171 / 162 | 114 (2) / 106.5 (2) | 29/30 → 26 / 27 | .903 → .892 / .878 | 39 / 23 |

(A coluna "parts/IoU base" da `table.md` é o `v18-r0`; os IoU f/l/b completos dos 12 runs estão em `results.csv`.)

Juiz, 4 votos com troca (sheet / artista / wc3 / forma; **B** em negrito = variante nova ganha):

| un. | v18-qem × v16-r3 | v18-cvt × v16-r3 | v18-cvt × v18-qem |
|---|---|---|---|
| n005 | A 4-0 / A 4-0 / A 4-0 / A 4-0 | A 4-0 / A 4-0 / A 4-0 / A 4-0 | **B 4-0 / B 4-0 / B 4-0 / B 4-0** |
| n00U | A 4-0 / A 4-0 / A 4-0 / A 4-0 | A 4-0 / A 4-0 / A 4-0 / A 4-0 | A 4-0 / A 4-0 / A 4-0 / A 3-1 |
| hfoo | A 4-0 / A 4-0 / A 4-0 / A 4-0 | A 4-0 / A 4-0 / A 4-0 / A 4-0 | empate / **B 4-0 / B 4-0 / B 4-0** |
| n017 | A 4-0 / A 4-0 / A 4-0 / empate | A 4-0 / A 4-0 / A 4-0 / empate | empate / empate / empate / **B 3-1** |
| n02X | A 4-0 / A 4-0 / A 4-0 / A 4-0 | A 4-0 / A 4-0 / A 4-0 / A 3-1 | empate / **B 4-0 / B 4-0 / B 4-0** |
| n01X | A 4-0 / A 4-0 / **B 4-0 / B 4-0** | A 4-0 / **B 3-1 / B 4-0 / B 4-0** | A 4-0 / empate / **B 4-0 / B 4-0** |

| item | o que mediu | resultado | default? |
|---|---|---|---|
| L18-1 fusão OKLab ≤ 12 | 6 DSLs | materiais ≤ 12 em **6/6** (17 → 9, 14 → 11, 8 → 7, 7 → 5; n00U/n017 já 6–7) mas componentes **13–19** em 6/6 (≈ 1 malha por osso + rígidos) — alvo ≤ 12 falha 6/6 | não (`--eye-fuse 0`) |
| L18-2 união bone, QEM × CVT | 12 runs, 6 pares cvt×qem | CVT no orçamento 6/6 (620–704); QEM passa em 2/6 (744, 818); CVT 9.5 s vs 23.2 s; par directo: **forma CVT 5/6** (4-0 em 4, 3-1 n017; perde só n00U 3-1), artista 3/6 + 2 empates, wc3 4/6 (n005, hfoo, n02X, n01X) | não (`--eye-union off`, `--eye-union-reduce qem`) |
| L18-3 pintura por campos | 12 runs | texels/ilha mediana ≥ 100 em 2/6 (qem) e 3/6 (cvt); mínimo sempre 1–2; costura em ziguezague resolvida; **vs v16-r3: sheet A 4-0 em 12/12, artista A em 11/12** (n01X cvt B 3-1) | não (`--eye-paint off`) |
| aceite da leva | 2 variantes × 6 | **NÃO nas duas**: forma pró-v18 1/6 (n01X; n017 empate), sheet+artista 0/6 | defaults ficam |
| L18-4 N votos | 48 chamadas, 240 votos | ver tabela abaixo; **N = 4 confirmado** | `VOTES = 4` (já era) |

| N | taxa de empate | concordância reps (4 eixos) | concordância reps (forma) | forma: mesmo vencedor | s / chamada | s total |
|---|---|---|---|---|---|---|
| 2 | .021 | .958 | .833 | 5/6 | 22.5 | 276 |
| **4** | .000 | 1.000 | 1.000 | 6/6 | 36.6 | 456 |
| 6 | .042 | .917 | .833 | 5/6 | 50.8 | 618 |
| 8 | .083 | 1.000 | 1.000 | 6/6 | 65.2 | 784 |

Critério: menor N com forma concordante em ≥ 5/6 que o N seguinte não bate → 4. O que separa os N é o n017 (forma oscila: tie / A 2-0 → A 4-0 /
A 4-0 → A 4-2 / tie → tie / tie) e o artista do n01X: mais votos convertem um 3-1 em 4-4, não em certeza; a taxa de empate **sobe** com N. N = 8 é
1.8× o tempo sem ganho (L17-1 chegara ao mesmo com 2 unidades).

Tempo por estágio (mediana das 6, `timing.json`): `v18-r0` 691 s = artista 638 s (92 %), measure 30.6, build 3.5; `v18-qem` 37 s = união+QEM 23.2 (63 %),
measure 10.1, pintura 1.7; `v18-cvt` 23 s = união+CVT 9.5 (42 %), measure 9.9, pintura 1.7; juiz 35–41 s por par de 4 votos. A leva inteira acrescenta
23–37 s por unidade a 691 s de artista: o custo é o VLM, não a geometria.

Figuras: `figuras/16-hfoo.png`, `figuras/16-n01X.png` (concept | v16-r3 | v18-qem | v18-cvt | Hive | wire qem | wire cvt, 6 vistas + atlas).

Limite do estudo de N: usou só `v18-qem` × `v16-r3`, pares quase todos decisivos, por isso a escolha de N = 4 tem pouca força para pares próximos.

## O que piorou / limitações

- Porque perde: (1) a união arredonda os cantos das peças (ombreiras, botas, capacete) e o juiz lê "menos como a sheet, que é cel plano de arestas
  duras" — o wire mostra triangulação uniforme sem as arestas das caixas; (2) o atlas 256² continua partilhado por 160–280 cartas porque as **peças
  rígidas não se unem** (props, fivelas, lentes, dentes: 6 cartas cada) e puxam a mediana para 16–55 em n00U/n017/n005; gradiente/ruído/oclusão lê
  como "sujo" ao lado do plano; (3) n01X é a excepção (forma e wc3 4-0 nas duas variantes e nas 2 repetições do estudo de N): corpo de ferro fundido,
  poucas peças, cartas grandes — é o caso que a união serve.
- QEM guardado passa do orçamento em 2/6 (`max_dev` fixo); `retopo.cvt` dá `ValueError` em cluster fino (dual vazio) → fallback QEM (patas do n00U,
  a única unidade onde a CVT perde forma).
- `review_pair.shoot` cacheava os renders de A por nome de ficheiro no `work` do run B: a primeira coluna cvt×qem saiu igual à cvt×r3; corrigido
  (um `work` por A), ficheiros `pairwise4-v18-qem-invalid-cached-A.json` mantidos, a coluna acima é a repetição.
- O gate de peças não mede modelos pintados (lê cores de material): com atlas único dá `mat 0.0`; falta gate por cor do render.
- n = 1 trajectória por unidade; a referência Hive não foi repetida (L17-3 já tinha medido o eixo wc3 contra o Hive; com sheet/artista a 0/6 não se
  justificava).

## Conclusão (1 frase para o paper)

Fundir para ≤ 12 materiais, unir por osso e pintar por campos de peça resolve o que era mensurável (materiais 6/6, costuras, CVT no orçamento e 2×
mais rápida, forma CVT > QEM 5/6) e perde na mesma o juiz contra as primitivas planas (sheet A 4-0 em 12/12), porque o que falta não é mais código de
geometria mas unir os ossos adjacentes (tronco + pélvis + cabeça) num campo só e dar um atlas por componente — e 4 votos chegam: mais votos
convertem 3-1 em empate, não em certeza.
