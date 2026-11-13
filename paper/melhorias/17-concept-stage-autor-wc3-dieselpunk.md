# 17 — Estágio de concept refeito à volta do autor: referência WC3 original, lore card como design, regras de prompt e rondas de revisão

- Data: 2026-10-31 → 2026-11-06
- Commit(s): `6475c594` (2026-11-04, "pipeline pós-leva20": `concept_review.py`, `w3x_models.py`, `wc3_ref_renders.py`, `wc3_icons.py`, `fresh_variants.py`, prompts reorganizados por unidade, `wc3-model-map.json`); as rondas de revisão e as variantes de 11-05/06 estão no working tree de `main` (não commitadas em 2026-11-07, pastas `artifacts/model-sheets/history/2026-10-31-review1…review20`, `2026-11-06-n01Y-layout`, `2026-11-06-truncated`).
- Problema do baseline atacado (§7): o concept sheet é o juiz de tudo o que vem depois (ficha 15: erros que nenhum gate vê vêm do prompt; §39.L20: a projecção vaza porque o desenho e o modelo não batem). Até aqui o sheet era gerado uma vez a partir do card de lore e nunca revisto pelo autor; 160 unidades tinham sheet "aprovado" por omissão.
- Hipótese: o sheet tem de ser decidido pelo autor **antes** do modelo, com a identidade do WC3 original como referência e regras de prompt que o modelo 3D consiga cumprir (locomoção visível, cor por unidade, upgrade desenhado sobre o antecessor, sem chibi). A ferramenta do estágio passa a ser a ronda de revisão (só as rejeitadas, com nota), não o prompt isolado.

## Mudança

- **Referência de identidade = o modelo WC3 original.** `tools/blender/w3x_models.py` lê o MPQ protegido do `.w3x` (pré-cabeçalho HM3W, `header_size` partido, tabelas cifradas, hash table com decoys: ficheiro encontrado só pelo hash do nome) e extrai os `.mdx` custom do mapa; `tools/blender/wc3_ref_renders.py` resolve o modelo de cada id (`umdl` do `war3map.w3u`, senão `file` do `unitskin.txt`), busca primeiro no MPQ do mapa e depois na árvore SD do CDN do Hive, e imprime 6 vistas texturadas em `artifacts/reference/hive/renders/<id>.png`; `tools/blender/wc3_icons.py` apanha o ícone do command card pelo endpoint `casc-contents`. Mapa id → modelo em `artifacts/model-sheets/wc3-model-map.json`. Tudo "reference only, never shipped".
- **O lore card continua a ser o design.** O WC3 dá silhueta e identidade (o que a unidade *é*); o card dá a história e o que muda no Castle Fight. O prompt é gerado a partir do card (`unit_facts --emit-prompt` + 1 `claude -p`, §38), nunca escrito à mão.
- **Regras de prompt (todas regras do autor, 2026-10-31):**
  1. **Locomoção visível**: rodas, lagartas, pernas, asas ou flutuação têm de aparecer; nunca uma base fixa.
  2. **Cor por unidade, não por raça**: a paleta sai do próprio sheet; a raça não impõe cor.
  3. **Upgrade desenhado sobre o antecessor**: `prompts/00-template-unit.txt` declara "Rank in its chain: this is the <base / upgraded> body of the <family> family"; o evento de silhueta do upgrade só aparece no tier superior; `concept_review.py` em modo `redesign` desenha sobre o sheet do antecessor quando existe.
  4. **Sem chibi**: proporções de adulto; o estilo é cel plano, não mascote.
  5. **Dieselpunk Trench Crusade para humanóides armados**: `prompts/STYLE-trench-crusade.txt` (armas, roupa e armadura 1920–40, máscara de gás fundida com viseira, Stahlhelm/Brodie, selos de pureza; "pick two or three per unit, as large crude shapes"; **nunca um tanque de combustível nas costas**; raças de fantasia mantêm o corpo).
  6. **Nota PG-12** em todas as chamadas de imagem: `generate.py` prefixa `PG12_NOTE` ("concept art for low-poly units of a PG-12 dark-fantasy video game; menacing and a little scary, with no gore").
- **Rondas de revisão do autor.** `tools/blender/concept_review.py <concept-review.json> --round reviewN [--jobs 8]`: só as unidades rejeitadas, cada uma com a nota do autor; modo `edit` (image-to-image sobre o próprio sheet) ou `redesign` (prompt novo, sobre o sheet do antecessor). Só `sheet.jpg` é redesenhado; os sheets antigos vão para `history/2026-10-31-<round>/<id>/`; as variantes (hard, hard-clean, props) esperam a aprovação (`fresh_variants.py`).
- **Unidades com mais de uma figura.** Duas unidades do roster são grupos: e00E (Twins: 2 crianças) e hmtm (Mortar: 2 anões + o morteiro, sheet aprovado pelo autor). O keying de fundo deixava o painel `back` vazio ("concept panel 'back' is empty after background keying") e o segmentador não separa figuras. Solução: pseudo-unidades `e00E-a/b` e `hmtm-a/b/c` com as caixas de cada painel marcadas à mão (`split.json`: front/left/back/top/bottom por figura, com escala quando o painel left é menor) e `extra-units.json` no run do roster; cada pseudo-unidade corre a cadeia completa como uma unidade.

## Protocolo

- Unidades: as 160 do roster (+ 5 pseudo-unidades).
- Spec author / modelo de imagem: prompts e revisão `claude -p` (`session:sonnet` desde 2026-11-05, quota semanal); imagem nano-banana via gateway ppq (US$ 0,0725 por sheet).
- Runs por unidade: 1 por ronda em que foi rejeitada.
- Métrica principal: **unidades rejeitadas pelo autor por ronda** (não há juiz automático neste estágio: a decisão é do autor a olhar o contact sheet).

## Resultado

Rejeitadas por ronda (contagem das pastas `history/2026-10-31-reviewN/`, menos `_logs`; estimativa a partir do disco, não de um log):

| ronda | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11–20 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rejeitadas | **130** | 17 | 2 | **48** | 21 | 15 | 2 | 8 | 7 | 5 | 1 cada |

- 20 rondas, **266** redesenhos (contagem das pastas em 2026-11-07: a ronda 11 tem 2, as rondas 12–20 têm 1 cada); as sete rondas grandes vão 130 → 17 → 48 → 21 → 15 → 8 → 7 (a ronda 4 sobe porque entrou a regra dieselpunk e a referência WC3: `history/2026-10-31-pre-dieselpunk/`, `pre-wc3-ref/`, `pre-lore/`, `pre-pose/` guardam os sheets de antes de cada regra). A partir da ronda 12 é 1 unidade por ronda até **0 rejeitadas**; todos os 160 sheets ficaram aprovados pelo autor antes do `roster-v6` (ficha 19).
- e00E e hmtm divididos: 5 pseudo-unidades, 4 chegaram a `model.glb` no roster-v6 (e00E-a 684 tris, parts 20/22; e00E-b 664, 25/33; hmtm-a 700; hmtm-b 700); hmtm-c (o morteiro, rig `vehicle`) parou em `parts` (ver ficha 19). Figura `figuras/19-multi-figure-split.png` (painel front do sheet | front | left | rts por pseudo-unidade).

![As 5 pseudo-unidades (e00E-a/b, hmtm-a/b/c) no roster-v6: painel front do sheet, front, left, rts.](figuras/19-multi-figure-split.png)
- Custo de imagem da revisão: 266 × US$ 0,0725 ≈ **US$ 19 nominais** (estimativa: a ronda `edit` gera 1 imagem por unidade; as variantes hard/clean/props vieram depois, no roster). **Horas do autor a olhar os contact sheets: não medidas** — é o custo real deste estágio e falta no paper.

## O que piorou / limitações

- Não há métrica automática deste estágio: a taxa de rejeição é a opinião do autor e muda com as regras que ele acrescenta a meio (ronda 4). Serve como registo de processo, não como ablação.
- O sheet aprovado é o juiz de todos os gates seguintes (IoU, parts, projecção). Logo a qualidade do roster-v6 (ficha 19) é **downstream de 20 rondas de revisão humana**: o "one-shot" do paper vale para o estágio de modelo, não para a cadeia inteira. As regras de prompt (locomoção, cor por unidade, upgrade, dieselpunk, PG-12) entraram juntas; não há ablação de nenhuma.
- O prompt gerado por `claude -p` a partir do card ainda produz layouts fora do padrão de 5 painéis em unidades raras (n01Y: `history/2026-11-06-n01Y-layout/`, painel back vazio; hmtm idem), e o gateway devolveu JPEGs truncados em 5 variantes (`history/2026-11-06-truncated/`): os dois casos só aparecem no roster (ficha 19).
- A referência WC3 é o modelo SD do Hive, não o do mapa, quando o mapa não tem `.mdx` custom; para unidades de raças inventadas (Pandaren Empire, Mech) a referência é fraca.
- Papers/ferramentas novos usados aqui (a registar em `docs/references.md`, não é tarefa desta ficha): formato MPQ/`.w3x` (StormLib/hash de nome), CDN do Hive Workshop (`casc-contents`).

## Conclusão (1 frase para o paper)

O estágio de concept deixou de ser "um prompt, um sheet" e passou a "WC3 original como identidade + lore card como design + regras de prompt que o 3D cumpre + rondas de revisão do autor só sobre as rejeitadas": 130 → 0 rejeitadas em 20 rondas e 266 redesenhos (≈ US$ 19 de imagem, horas do autor não medidas), e é a primeira vez que as 160 unidades entram no estágio de modelo com um sheet que o autor aprovou — é o passo humano de que todo o resto depende, e não tem métrica.
