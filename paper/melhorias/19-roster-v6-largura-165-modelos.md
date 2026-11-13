# 19 — Largura: roster-v6, 160 unidades + 5 pseudo-unidades, 165 modelos one-shot; taxonomia de falhas; rerun do olho em 61 unidades

- Data: 2026-11-06 → 2026-11-07 (batch), rerun do olho `roster-v6e` 2026-11-07
- Commit(s): working tree de `main` sobre `6475c594` (receita da ficha 18; `roster_batch.py` com `extra-units.json`, `final-models.json`, `--resume`); run `artifacts/model-sheets/runs/roster/roster-v6/` (`status.json`, `table.md`, `logs/` 166 ficheiros), modelos em `runs/draft/<id>/roster-v6/` e `roster-v6e/`; contact sheets em `artifacts/model-sheets/history/2026-11-07-roster-v6/contact.jpg`, `contact2.jpg`. Log da sessão: `roster-v6.log` (scratchpad).
- Problema do baseline atacado (§7 / 01-tese): a tese é busca em largura, one-shot; até aqui a maior bateria tinha 7 unidades (hard-v1) e 6 (levas 15–20). O `roster-pilot` (§38) tinha estimado 82,6 h sequenciais / US$ 53,66 para 162 unidades sem nunca ter gasto uma chamada de imagem.
- Hipótese: a cadeia prompt → sheets → parts → model com a receita da ficha 18 corre sobre o roster inteiro sem tocar numa unidade à mão; as falhas que aparecerem são do **pipeline** (regra, parser, gateway) e corrigem-se uma vez para todas.

## Mudança

- `roster_batch.py --all-units --jobs 4 --run-id roster-v6 --resume`: 4 estágios por unidade (§38), salto por outputs em disco, falha de uma unidade vira linha e não pára as outras; `extra-units.json` acrescenta as 5 pseudo-unidades (ficha 17); `final-models.json` lista o `model.glb` final por id (165 entradas).
- Modelos: artista `session:opus`; prompts, parts e revisor por vista `session:sonnet` (quota semanal); imagens nano-banana via ppq.
- Correcções feitas **durante** o batch, todas no pipeline, nenhuma na unidade (taxonomia abaixo); depois de cada uma, `--resume` retoma só o que faltava.
- `roster-v6e` (`eye_rerun.py`): para as unidades cujo estágio do olho morreu em "the resend is still invalid" (regras de junção estritas, ficha 18), repetir só o olho com as regras soft a partir das rondas pagas (`--eye-from roster-v6`), 4 em paralelo.

## Protocolo

- Unidades: 160 do roster + 5 pseudo-unidades = 165 ids, 166 linhas no `status.json` (a linha `hmtm` original fica como FAIL em `sheets`).
- Spec author / modelo de imagem: como acima; 1 run por unidade, **nenhuma iteração por unidade**.
- Runs por unidade: 1 (+ 1 rerun do olho em 61).
- Métricas: unidades que chegam a `model.glb`; tris; parts k/n (gate de peças do olho, última ronda); preflight / stage 1 / stage 2; segundos e US$ por unidade (`status.json`).

## Resultado

Agregado (`status.json` e `table.md` final do `roster-v6`, 2026-11-07):

| métrica | valor |
|---|---|
| ids com `model.glb` | **164 / 166 linhas** (`reached: model`); `final-models.json` = **165** modelos (inclui os do `roster-v6e`); só hmtm (grupo original, substituído por hmtm-a/b/c) e hmtm-c (morteiro, parou em `parts`) sem modelo |
| tris | média **690,5** (164 modelos; 588–700; 62 unidades a 699–700: o orçamento é preenchido por construção — é tecto, não resultado) |
| parts k/n (gate de peças do olho) | **.571 antes do olho → .779 na ronda final → .770 no `model.glb` final** (média nas 165, medido 2026-11-07; `results-roster-v6.csv`). O `table.md` do batch tinha .76 em 103 unidades e `–` nas 61 do rerun |
| IoU (régua `eye_stage.measure`, concept de-inked) | GLB final: front **.726** / left **.660** / back **.709** / rts .679 (n = 118); antes do olho .765 / .678 / .750 / .728 — **o olho baixa a silhueta** (front −.055 em 140/165) e a união + molde devolve +.016 (121/165). Detalhe em `04-resultados-e-descobertas.md` |
| gate do baseline (front ≥ .75 e left ≥ .65) | massing 84/165; ronda final 69/165; **GLB final 78/165** (bípedes 52/101, não-bípedes 26/64) |
| preflight | PASS 41 / FAIL 123 |
| stage 1 (massing, gate da Leva 12: spill ≤ .03, bare ≤ .10) | FAIL 164/164 — **este gate nunca fechou em nenhuma unidade desde a Leva 12** (ficha 11: 0/36 vistas); no GLB final, spill ≤ .03 em front e left: 0/165 |
| stage 2 (olho) | PASS 116 / FAIL 48 |
| veredito | CHECK 164 (exit 1 com `model.glb`: gate falhou, modelo existe) |
| tempo de máquina | **105,9 h** somadas no `model.s` do `status.json` (109,5 h com `sheets` e `parts`; ≈ 106 h sem repetições de estágio, estimativa do autor); mediana **2 239 s** por unidade (1 252–4 475 s); dentro disso o olho 778 s (artista Opus 576 s = 26 %, revisor por vista 55 s); os ≈ 1 460 s restantes (massing, fit, SAM2, TripoSplat) não estão itemizados |
| relógio | ≈ **26 h** em 4 jobs (**estimativa do autor**; os `logs/` vão de 2026-11-06 03:31 a 2026-11-07 02:31, e o batch começou antes do primeiro log) |
| custo de imagem | **US$ 24,3 nominais** (`cost_usd` por estágio; 40 unidades pagaram `sheets`, 0,0725–0,46 por unidade); o artista Opus e os Sonnet são quota de sessão, não crédito — **não comparável** com a estimativa do §38 (US$ 53,66), que incluía LLM a preço de lista |

Comparado com a estimativa do §38 (82,6 h sequenciais, US$ 53,66 para 162): a máquina custou 1,3× o estimado porque o modelo passou de 1 629 s para ≈ 2 240 s por unidade (moldes neurais + revisor por vista), e as imagens custaram menos porque a maioria dos sheets já existia das rondas da ficha 17 (e porque o US$ 53,66 contava LLM a preço de lista).

Rerun do olho `roster-v6e` (`eye-rerun.log`): **61 unidades** (38 % do roster) tinham o estágio do olho morto na regra estrita ("the resend is still invalid"). **O pipeline entregou nessas 61 o `eye/input.glb` como `model.glb`** (tamanho byte-igual em 61/61) e marcou `reached: model`, `verdict: CHECK` — ou seja, 38 % do roster era massing sem olho e a tabela não o dizia. É uma falha silenciosa do validador, não um sucesso do rerun. Com a regra soft 59/61 concluíram à primeira (ronda final 0: 9, 1: 14, 2: 26, 3: 12; 349–1 822 s), n00X e n01O falharam (rc 1) e concluíram na repetição: 61/61. Efeito do olho nessas 61 (mesma régua): parts .587 → .807 (52↑ 6↓), IoU front .775 → .720 (10↑ 51↓) — o mesmo padrão das outras 104.

Rondas: `best_round` (sem desastre → mais peças → mais recente) escolhe a ronda 0 em 36/165 e a 1 em 33: em 42 % das unidades as 2–3 rondas seguintes de Opus não melhoraram a ronda entregue. Reenvios por regra de junção: 0 em 15, 1 em 54, 2 em 41, 3 em 38, 4 em 17.

Taxonomia de falhas do batch (do `roster-v6.log`; a causa é a do traceback, o nome da classe é meu):

| classe | sintoma no log | unidades | correcção (no pipeline) |
|---|---|---|---|
| saldo do gateway (ppq) | `HTTP 402 insufficient_balance` em `sheets` | ≈ 40 unidades × 2 passagens | carregar crédito, `--resume` (a cadeia salta o que já existe) |
| JPEG truncado do gateway | `magick … sheet-props.jpg` `CalledProcessError`; 5 ficheiros em `history/2026-11-06-truncated/` | n01V, o005 (+ h007, h06Q, o007 variantes) | detectar ficheiro truncado e regenerar a variante |
| barra no nome da peça | `FileNotFoundError … sam2/front/forearm/fist.L.png` | h02Y | sanitizar o nome da peça no cache SAM2 |
| osso de comprimento zero | `ZeroDivisionError: division by zero` no modelo (provável) | n00H | guarda no rig (comprimento mínimo) |
| máscara de asa vazia | `ValueError: attempt to get argmin of an empty sequence` (provável) | n010 (drake) | máscara vazia → cai para a caixa `box2d` |
| filtro de conteúdo | `HTTP 400 … flagged by a content checker` | n00I | prompt reescrito (nota PG-12 já estava); passou à 2.ª |
| layout do sheet fora do padrão | `concept panel 'back' is empty after background keying` | n01Y, hmtm | n01Y: sheet refeito (`history/2026-11-06-n01Y-layout/`); hmtm: dividido em hmtm-a/b/c com caixas à mão (ficha 17) |
| regras de junção estritas | `no usable reply (the resend is still invalid)` no olho | 61 | regra soft (ficha 18) + `roster-v6e` |
| sem causa registada | `n01D model: failed Error:` (684 s) | n01D | repetido com `--resume`, concluiu |

Figuras: `figuras/19-roster-v6-contact-topo.jpg` (primeiras filas do contact sheet, 1600 px; o contact completo tem 2380 × 15620 px: `figuras/19-roster-v6-contact-completo.jpg` é a miniatura, o original fica em `castle_fight/artifacts/model-sheets/history/2026-11-07-roster-v6/contact2.jpg`); `figuras/19-multi-figure-split.png` (as 5 pseudo-unidades).

![roster-v6, primeiras filas do contact sheet (concept | modelo por unidade).](figuras/19-roster-v6-contact-topo.jpg)

## O que piorou / limitações

- **Nenhuma unidade passa o gate do stage 1** (CHECK 164/164), e isso diz pouco: o gate (spill ≤ .03, bare ≤ .10, Leva 12) não fechou em nenhuma unidade de nenhuma leva desde 2026-10-30. No gate do baseline (front ≥ .75, left ≥ .65) o GLB final passa em 78/165 — a mesma taxa do baseline (3/7), em 165. A taxa de PASS depende da régua, não do modelo.
- **O olho baixa a silhueta** (IoU front −.055 em 140/165) enquanto sobe as peças (+.21 em 136/165): as duas métricas do pipeline puxam em sentidos opostos e a ficha original só reportava a que sobe.
- **É um pipeline de bípedes**: 101 bípedes front .765 / parts .81 / gate 52; 64 não-bípedes em 24 famílias (20 com n ≤ 8) .664 / .70 / gate 26; os 12 piores em parts são todos não-bípedes (n03U ray .08, n00H wyrm .15, n01N/n01W spider_high .25/.31, u000 bird .30, h06Q/h06R aircraft, n017 quadruped, h016 mounted_flyer, n01D/n001/n01B drake ≈ .40). Naga 1/11 no gate.
- 62 unidades a 699–700 tris: o artista enche o orçamento por construção; não há folga para a pele/juntas (lição L16-4).
- As falhas foram corrigidas a meio do batch: as unidades de antes e de depois da correcção não correram exactamente o mesmo código (o `--resume` só repete o estágio falhado). Logo "o mesmo pipeline nas 165" é aproximado.
- Sem juiz pareado, sem avaliação humana, sem braço de controlo (todas as alavancas da ficha 18 ligadas): o roster-v6 mostra que a cadeia corre, não que as alavancas ajudam. O IoU/parts do GLB final foi medido em 2026-11-07 (`results-roster-v6.csv`), não durante o batch.
- rts medido só em 118/165 (painel rts ausente ou incoerente nas outras).
- hmtm-c (o morteiro, rig `vehicle`) parou em `parts` (22 s, sem erro registado na tabela): a 166.ª linha.

## Conclusão (1 frase para o paper)

A cadeia prompt → sheet → parts → modelo correu sobre o roster inteiro sem tocar numa unidade à mão e devolveu 165 modelos de ≈ 690 tris com .77 de peças reconhecidas e IoU front .73 no GLB final (78/165 no gate do baseline; bípedes 52/101, não-bípedes 26/64), em ≈ 26 h de relógio (estimativa), 106 h de máquina e US$ 24 de imagens; as 9 classes de falha que apareceram eram todas do pipeline e cada uma se corrigiu uma vez, incluindo uma regra de validação que tinha entregue 61 unidades (38 %) sem olho em silêncio — mas o olho baixa a silhueta enquanto sobe as peças, o gate do stage 1 nunca fechou desde a Leva 12, e sem avaliação humana nem braço de controlo a largura prova que a cadeia corre, não que os modelos são bons.
