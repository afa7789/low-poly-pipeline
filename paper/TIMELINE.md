# Timeline — ordem das etapas (pelos commits)

Uma linha por etapa, em ordem de hora. As imagens mostram front | left | câmera do jogo.
Tipo: **L** = largura (one-shot, várias unidades, pipeline igual para todas); **P** = profundidade
(iteração e refino na mesma unidade/imagem); **A/B** = mesma unidade, várias runs one-shot para
comparar configurações. O paper mede em L; P é teto e fonte de regras (ver `01-tese.md`).

Montagem completa por unidade: `figuras/n01X-evolucao.png`, `figuras/hfoo-evolucao.png`.
Números e detalhes: `02-evolucao.md`.

| # | tipo | quando | commit | unidade | etapa | o que mudou | imagem |
|---|---|---|---|---|---|---|---|
| — |  | 10-18 23:32 | `d279a1d` | todas | arte | concept sheets de 5 vistas gerados (nano-banana) | `castle_fight/artifacts/model-sheets/refs/<id>/sheet.jpg` |
| — |  | 10-18 23:58 | `08466d1` | n01X | à mão | primeira unidade rigada, partes escritas no código (GLB não guardado) | — |
| 1 | L | 10-19 00:12 | `5fb0902` | n01X | v3/argon | **direto da imagem**: LLM lê o sheet e escreve partes com coordenadas | [n01X-01](figuras/n01X-01-v3_argon.png) |
| 2 | L | 00:12 | `5fb0902` | n01X | v3/5.5 | idem, spec escrito pelo Claude 5.5 | [n01X-02](figuras/n01X-02-v3_5.5.png) |
| 3 | L | 00:40 | `2718747` | n01X | argon (draft4) | brief + gate de tris, 6 unidades × 2 autores | [n01X-03](figuras/n01X-03-argon_draft4.png) |
| 4 | L | 00:40 | `2718747` | n01X | opus55 (draft4) | idem, autor opus-5.5 (melhor do início) | [n01X-04](figuras/n01X-04-opus55_draft4.png) |
| 5 | L | 00:40 | `2718747` | hfoo | opus55 (draft4) | primeira versão do Footman | [hfoo-01](figuras/hfoo-01-opus55_draft4.png) |
| 6 | L | 00:40 | `2718747` | hfoo | argon (draft4) | idem, autor argon | [hfoo-02](figuras/hfoo-02-argon_draft4.png) |
| 7 | P | 01:01 | `8b45469` | n01X | v6/hand | prismas afunilados + regras de forma | [n01X-05](figuras/n01X-05-v6_hand.png) |
| 8 | P | 01:30 | `121b76f` | n01X | v8 | chunkify + atlas pintado de 3 tons | [n01X-06](figuras/n01X-06-v8.png) |
| 9 | P | 02:01 | `cb4e550` | n01X | v9 | skeleton-first: posição vem do osso | [n01X-07](figuras/n01X-07-v9.png) |
| 10 | P | 02:05 | `5186b8f` | n01X | v10 | união booleana num corpo só (rejeitado) | [n01X-08](figuras/n01X-08-v10.png) |
| — | P | 02:11–07:50 | `08a93e7`…`0673e8a` | n01X | loop | 10–20 iterações com review do Claude; preflight criado | — |
| 11 | P | 08:57 | `069abea` | n01X | v11 | **gates numéricos**: DSL v2 + preflight + IoU de silhueta | [n01X-09](figuras/n01X-09-v11.png) |
| 12 | P | 11:20 | `c88eb93` | n01X | v12 | passes por vista + câmeras calibradas | [n01X-10](figuras/n01X-10-v12.png) |
| 13 | P | 11:20 | `c88eb93` | n01X | v13 | v12 + passes rts, left, back | [n01X-11](figuras/n01X-11-v13.png) |
| 14 | L | 12:52 | `dfff43f` | n01X | v1 (refs) | sheet hard + hard-clean como referências | [n01X-12](figuras/n01X-12-v1_refs.png) |
| 15 | L | 12:52 | `dfff43f` | hfoo | v-ref | pipeline atual, sem referências hard | [hfoo-03](figuras/hfoo-03-v-ref_noref.png) |
| 16 | L | 12:52 | `dfff43f` | hfoo | v1 (refs) | com hard + clean + props | [hfoo-04](figuras/hfoo-04-v1_refs.png) |
| 17 | A/B | 13:58 | `3390397` | hfoo | hardfirst | hard como imagem 1 | [hfoo-05](figuras/hfoo-05-hardfirst.png) |
| 18 | A/B | 13:58 | `3390397` | hfoo | abS1 | A/B: aprovado como imagem 1, sem repair | [hfoo-06](figuras/hfoo-06-abS1.png) |
| 19 | A/B | 13:58 | `3390397` | hfoo | abS2 | repetição do abS1 (ruído) | [hfoo-07](figuras/hfoo-07-abS2.png) |
| 20 | A/B | 13:58 | `3390397` | hfoo | abH1 | A/B: hard como imagem 1, sem repair | [hfoo-08](figuras/hfoo-08-abH1.png) |
| 21 | A/B | 13:58 | `3390397` | hfoo | abH2 | repetição do abH1 (ruído) | [hfoo-09](figuras/hfoo-09-abH2.png) |
| 22 | A/B | 13:58 | `3390397` | hfoo | abR1 | hard + repair por padrão + landmarks do próprio sheet | [hfoo-10](figuras/hfoo-10-abR1.png) |
| 23 | L | 16:00 | `50511d0` | n01X | hard-v1 | **baseline** | [n01X-13](figuras/n01X-13-hard-v1.png) |
| 24 | L | 16:00 | `50511d0` | hfoo | hard-v1 | **baseline** | [hfoo-11](figuras/hfoo-11-hard-v1.png) |

Data de todas: 2026-10-19, exceto as duas primeiras linhas (10-18).
Próximas etapas: continuar a numeração (25, 26...) e seguir `ferramentas/COMO-MEDIR.md`.

2026-10-31 — ficha 15 (L18-0) e balanço de papers (03).
2026-10-31 — Leva 18 fundida em `main` (`1e387a79` L18-0 `face_kind`; `f8cb6c89` L18-1..4 fusão ≤ 12 → união por osso QEM | CVT → pintura por campos, juiz N = 4):
runs `v18-r0`, `v18-qem`, `v18-cvt` nas 6 unidades (L, one-shot), aceite NÃO; fichas 15–16, imagens `figuras/16-hfoo.png`, `figuras/16-n01X.png`
(montagem concept | v16-r3 | v18-qem | v18-cvt | Hive | wires, não a tira front/left/wc3 das etapas 1–24; medir com `ferramentas/medir_etapas.py` fica por fazer).
2026-10-31 — Leva 19 (`v19-default`: receita v18-cvt vira default por decisão do autor contra o juiz; PIPELINE §37), roster batch (§38) e Leva 20 (`v20-proj`, projecção do sheet no atlas, `--eye-project` tight; §39): sem ficha própria, resumidas em `02-evolucao.md` §6.
2026-10-31 → 11-06 — ficha 17: estágio de concept refeito (WC3 original como identidade, lore card como design, regras de prompt, dieselpunk, 20 rondas de revisão do autor 130 → 0 rejeitadas; e00E/hmtm divididos em 5 pseudo-unidades). Imagens: `figuras/19-multi-figure-split.png`.
2026-11-04 — merge `feat/pixel-art` (`bf6906f6`): jogo renderiza em pixel art a 450 px (contexto da ficha 20).
2026-11-04 → 11-05 — ficha 18: alavancas do modelo (cápsula, regras de junção soft, `--outline off`, de-ink, revisor por vista `--eye-views sonnet`, moldes neurais SAM2/TripoSplat, `--eye-mold masks`, `--eye-joints smooth`); pilotos n02S (.70/.66 → .75/.72) e n01G (.58 → .70 front). Imagens: `figuras/18-form-pilot-capsula.png`, `18-eye-views.png`, `18-lever-pilot.png`, `18-sam2-hfoo.png`, `18-triposplat-hfoo.png`.
2026-11-06 → 11-07 — ficha 19: `roster-v6`, 160 unidades + 5 pseudo-unidades, 165 modelos one-shot, ≈ 690 tris, parts .78 (ronda final, 165), ≈ 26 h de relógio (estimativa) / 105,9 h de `model.s` / US$ 24,3 de imagem; 9 classes de falha corrigidas no pipeline; 61 unidades (38 %) entregues sem olho pela regra estrita e refeitas em `roster-v6e`. Imagens: `figuras/19-roster-v6-contact-topo.jpg`, `19-roster-v6-contact-completo.jpg`.
2026-11-07 — revisão hostil do paper (`REVIEW-2026-11-07.md`); IoU e parts do GLB final medidos nas 165 (`results-roster-v6.csv`, `figuras/resultados-roster-v6.png`); `04-resultados-e-descobertas.md` escrito; `01-tese.md` reescrita para o que foi medido.
2026-11-07 — ficha 20: pesquisa de texturas pós-GLB (atlas de paleta + bakes sem IA; inpaint mascarado só para detalhes); trabalho futuro, nada medido.
