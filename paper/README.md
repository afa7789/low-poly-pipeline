# IA_gen_paper

Registro das melhorias do pipeline de geração de modelos 3D por IA (Castle Fight), para um paper.

| arquivo | o quê |
|---|---|
| `00-baseline.md` | estado inicial (2026-10-20, commit `0a70440`): arquitetura, decisões, métricas, problemas abertos |
| `baseline-metrics.csv` | números brutos do baseline (run `hard-v1`, 7 unidades) |
| `01-tese.md` | **objetivo, o que foi alcançado e o que não foi (2026-11-07); métrica e protocolo**; secção "Juiz vs produção" (custo que escala: VLM no `v18-r0`, pré-olho no `roster-v6`) |
| `TIMELINE.md` | **ordem cronológica das 24 etapas com link para cada imagem** |
| `02-evolucao.md` | ordem das etapas pelos commits + 24 etapas (n01X, hfoo) medidas com a régua atual |
| `evolution-metrics.csv` | números das 24 etapas |
| `04-resultados-e-descobertas.md` | **resultados e descobertas** (2026-11-07): resumo, o que o roster-v6 mede nas 165 unidades (massing → olho → GLB final), descobertas com tamanho de efeito, resultados negativos, limitações, ameaças à validade, trabalho futuro (incl. texturas) |
| `05-avaliacao-humana-vs-juiz.md` | **avaliação humana vs juiz LLM** (2026-11-07): protocolo, amostra de 30 (15 bípedes + 15 não-bípedes, semente 7), as mesmas 3 perguntas 1–5 nos dois testes, resultados do juiz (Sonnet) e tabela a preencher pelo teste humano (`viewer /eval` → `eval_report.py`) |
| `results-roster-v6.csv` | uma linha por modelo final do roster-v6 (165): raça, rig, tris, gates, parts k/n e IoU front/left/back/rts do massing (`base_*`), da ronda final do olho (`eye_*`) e do `model.glb` final (`glb_*`, medido 2026-11-07 com `eye_stage.measure`); colunas `roster-v5_*`/`roster-v1_*`/`roster-v2_*` para as unidades com run antigo (régua diferente: só indicativo) |
| `figuras/resultados-roster-v6.png` | parts share massing vs GLB final; IoU front antes/depois do olho por rig; IoU médio por família de rig |
| `REVIEW-2026-11-07.md` | leitura hostil do paper, secção a secção: o que é afirmado, o que o sustenta, o que é hype; (a) o resultado é bom? (b) o que descobrimos (c) o que não está mostrado (d) o que um revisor exigiria |
| `03-balanco-papers.md` | **balanço dos papers do pipeline de modelos**: 3 grupos (default e resolveu / código sem juiz / só ideia), linhas por paper em `references.md`, o que muda para a Leva 18+ |
| `figuras/` | tira front/left/wc3 por etapa + `<unit>-evolucao.png` |
| `ferramentas/` | `etapas.csv` + `medir_etapas.py` + `COMO-MEDIR.md` (como adicionar etapa nova) |
| `melhorias/` | uma ficha por melhoria: `NN-slug.md` a partir de `melhorias/_template.md` |
| `melhorias/15-l18-0-olhos-que-o-concept-nao-tem.md` | ficha 15 (L18-0): default "bípede ⇒ olhos" em 4 camadas, 6/6 unidades com cara que o concept não tem; correcção `face_kind` medida: hfoo 4 → 0 peças de rosto, forma 4/6; figura `figuras/hfoo-15-olhos-concept-vs-modelo.png` |
| `melhorias/16-leva-18-fundir-unir-pintar.md` | ficha 16 (Leva 18): fusão OKLab ≤ 12 (6/6) → união por osso QEM \| CVT → pintura por campos; aceite NÃO (sheet A 4-0 em 12/12), CVT > QEM forma 5/6; juiz N = 4 confirmado; figuras `figuras/16-hfoo.png`, `figuras/16-n01X.png` |
| `melhorias/17-concept-stage-autor-wc3-dieselpunk.md` | ficha 17 (2026-10-31 → 11-06): estágio de concept refeito — WC3 original extraído do `.w3x` como identidade, lore card como design, regras de prompt (locomoção, cor por unidade, upgrade sobre o antecessor, sem chibi, dieselpunk Trench Crusade, PG-12), 20 rondas de revisão do autor 130 → 0 rejeitadas, e00E/hmtm divididos em 5 pseudo-unidades; figura `figuras/19-multi-figure-split.png` |
| `melhorias/18-alavancas-do-modelo-capsula-molde-juntas.md` | ficha 18 (2026-11-04/05): cápsula + "nada vivo é uma caixa", regras de junção soft, `--outline off`, de-ink, revisor por vista (Sonnet), moldes neurais SAM2/TripoSplat (invisíveis para a malha), `--eye-mold masks`, `--eye-joints smooth`; n02S .704/.664 → .746/.720, n01G front .581 → .697; figuras `figuras/18-*.png` |
| `melhorias/19-roster-v6-largura-165-modelos.md` | ficha 19 (2026-11-06/07): **largura** — 160 unidades + 5 pseudo-unidades, 165 modelos one-shot, tris 690,5, parts .57 → .78 (massing → olho), IoU front .77 → .71, ≈ 26 h relógio (estimativa) / 105,9 h máquina / US$ 24,3 de imagem; 9 classes de falha corrigidas no pipeline; 61 unidades (38 %) entregues sem olho pela regra estrita e refeitas (`roster-v6e`); PASS 0 no gate da Leva 12, 69/165 no gate do baseline; figuras `figuras/19-roster-v6-contact-*.jpg` |
| `melhorias/20-texturas-pos-glb-pesquisa-trabalho-futuro.md` | ficha 20 (2026-11-07): pesquisa de texturas pós-GLB para pixel art a 450 px — atlas de paleta + bakes sem IA primeiro, inpaint mascarado só para detalhes; trabalho futuro, nada medido |
| `results.csv` | uma linha por run medida depois do baseline (mesmas colunas do baseline; v18-qem/v18-cvt: tris, materiais pós-fusão, IoU f/l/b lidos de `leva18.json`, gate e drift vazios; pilotos da ficha 18 (`roster-v5`, `views-pilot2`, `form-pilot*`, `lever-pilot*`) com IoU do `eye_stage.measure`, commit `wt-<data>` = working tree não commitado) |
| `Makefile` / `paper.pdf` | `make pdf` gera o paper inteiro na ordem desta tabela (01-tese, 00-baseline, TIMELINE, 02-evolucao, 04-resultados, 05-avaliacao, melhorias/01–20, 03-balanco) com pandoc + tectonic (XeTeX, fontes DejaVu); `ferramentas/pandoc-header.tex` tem o cabeçalho LaTeX |

## Regra de registro

1. Toda melhoria cita o problema aberto do baseline (§7) que ataca.
2. Mede contra o baseline nas mesmas 7 unidades, mesmo spec author.
3. Ruído medido é 0.12 de IoU entre runs iguais: com n=1, ganho menor que isso não conta.
   Preferir ≥3 runs por unidade e reportar média ± desvio.
4. Anota commit, custo e o que piorou — resultado negativo também entra.
