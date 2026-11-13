# Baseline — estado inicial do pipeline de geração de modelos 3D por IA

Snapshot: 2026-10-20. Repositório `castle_fight`, branch `feat/skill-new-mechanics`, HEAD `0a70440`.
Último commit que mexeu no pipeline: `50511d0` (runs `hard-v1` das 7 unidades).
Código: `tools/blender/` (22 scripts Python) + `artifacts/model-sheets/` (prompts, refs, runs, `PIPELINE.md`).
Testes do pipeline: 77, todos passam (`python3 -m unittest discover -s tests/tools/blender`).
Histórico: 34 commits entre 2026-10-18 23:58 (`08466d1`, primeira unidade rigada) e 2026-10-19 16:00.

Tudo que vier depois deste arquivo é **melhoria** e deve ser medido contra os números da §6.

---

## 1. Problema

Jogo RTS (Castle Fight, clone de mapa de WC3) com ~167 unidades em 14 raças. Cada unidade precisa de
um modelo 3D próprio, no estilo Warcraft III clássico:

- low-poly: 400–700 triângulos por unidade comum (900–1600 herói, 600–800 prédio);
- rigado (1 skin) com 4 animações: `idle`, `walk`, `attack`, `death`;
- 3–8 materiais num único atlas pintado (o detalhe é pintado, não modelado);
- legível a 32×32 px na câmera do jogo.

Modelagem manual de 167 unidades não cabe no projeto. Modelos abertos (CC0/CC-BY) não cobrem o
roster. Pergunta do paper: **dá para gerar modelos game-ready a partir de texto com IA, de forma
determinística, verificável e barata?**

## 2. Ideia central

Separar o que a IA faz bem (desenhar, ler imagem, descrever partes) do que ela faz mal
(coordenadas, topologia, rig, orçamento). A IA nunca produz malha. Ela produz:

1. uma **imagem** (concept sheet de 5 vistas), e
2. um **spec JSON** de partes (primitivas ligadas a ossos).

Um builder determinístico no Blender transforma o spec em GLB. Gates numéricos julgam o resultado.

```
cartão de design ─► prompt ─► [IA imagem] ─► sheet aprovado (5 vistas)  ◄── juiz
                                    │
                                    └─► [IA imagem, i2i] ─► sheet hard / hard-clean / props / RTS
                                                               │
                                     [IA visão → spec JSON] ◄──┘   (imagem 1 = sheet hard)
                                               │
                          preflight (regras sobre o spec, 0.1 s) ──► repair pass (IA, patch)
                                               │
                              build_unit.py (Blender headless) ──► GLB rigado + 4 clips
                                               │
               check_gates (tris, mats, skin, clips) + silhouette IoU vs sheet aprovado
                                               │
                        passes por vista (IA, patch ≤6 partes, aceita só se IoU sobe)
                                               │
                  textura procedural pintada ─► compare.png, turntable.gif, review.md (PASS/CHECK)
```

## 3. Estágios

### 3.1 Concept sheet (texto → imagem)

- Modelo: `nano-banana-2-1` via gateway ppq (`generate.py`), 2K, 1:1. Preço de lista $0.046/imagem.
- Único modelo testado que respeita o layout 3+2 e o ponto de vista de cada painel
  (flux-2-pro repete a vista; gpt-image-2 detalha demais; krea só silhueta).
- Prompt em 10 blocos a partir de template + `unit_facts.py` (cartão de design, compêndio, paleta):
  layout, uma linha por painel dizendo o que é visível, orçamento de estilo, silhueta ≤20 palavras,
  paleta sugerida, rosto, **arma coerente com o alcance**, **posição na cadeia de upgrade**.
- Regra raiz aprendida: *o modelo desenha o que é afirmado como massa física, não o que o cartão
  sabe.* Relação espacial ausente não se corrige com limite de detalhe.

### 3.2 Variantes hard (imagem → imagem)

Mesmo design redesenhado com massas em polígonos planos (edição, não texto→imagem — senão inventa
outro personagem):

| arquivo | conteúdo | uso |
|---|---|---|
| `sheet.jpg` | sheet aprovado | **juiz** (gate de silhueta, compare) |
| `sheet-hard.jpg` | facetado, props no lugar | **imagem 1** do spec author; `measure()` e cores |
| `sheet-hard-clean.jpg` | A-pose, mãos vazias | posição de membros |
| `sheet-props.jpg` | props destacados em escala | forma dos props |
| `*-rts.jpg` | mesma unidade na câmera do jogo | pass RTS |

Drift check: IoU hard vs aprovado < 0.90 → avisa "regenerar" (não aborta).

### 3.3 Spec author (imagem → JSON)

- Modelo padrão: `google/gemini-4-argon`, ~$0.011/unidade. Referência de qualidade:
  `claude-opus-5.5`, ~$0.048/unidade.
- Saída: lista de partes `{bone, kind, radius/size, material, from/to, ...}` + `palette` + `rig`.
- **O LLM não escreve posição.** `resolve_skeleton()` deriva posição (ponto médio do osso),
  comprimento (1.15× osso) e sobreposição. Membro flutuando fica impossível por construção.
- DSL v2: `box`, `prism` (6/8 lados, afunilado), `frustum`, `dome`, `ring`, `wheel`; `from`/`to`
  resolvidos pelo builder; `spin`, `scale`.
- Validação nunca confia no JSON: osso/kind/material em conjuntos permitidos, aridade, `ground_fix`
  levanta qualquer parte abaixo de y=0.
- 22 famílias de rig (`rig_families.py`): biped, quadruped, spider, serpent, vehicle, drake,
  harpy, wyrm, mounted, naga, centaur, wraith, pod, ... building. Clips derivados dos nomes dos ossos.

### 3.4 Preflight (regras sobre o spec, antes do Blender)

`preflight.py`, ~13 regras, 0.1 s: orçamento de tris, 3–8 materiais, cobertura de ossos,
landmarks do bípede **medidos no sheet da própria unidade** (ombros, punhos, base, ±15%),
pé, cabeça, eixo da roda, fração de ornamento ≤22%, chão, sobreposição.
Falhou → **repair pass** (padrão): falhas voltam ao spec author como patch.

### 3.5 Build (Blender 5.2.2 headless)

`build_unit.py`: partes → uma malha, rigid skin (1 osso por peça, peso 1), 4 actions, export glTF
(conversão Z-up→Y-up). Sem bevel, sem solda: medido que chanfro e voxel-fuse pioram a leitura WC3.

### 3.6 Gates sobre o GLB

| gate | limiar |
|---|---|
| `check_gates.py` | tris por classe, 3–8 materiais, 1 skin, 4 clips (0 em prédio) |
| silhueta (`silhouette.py`) | IoU de máscara ortográfica vs sheet aprovado, normalizado pela altura. **front ≥ 0.75, left ≥ 0.65.** Back reportado. Top/bottom não gated (painéis inclinados = ruído) |

Câmeras calibradas: varredura de inclinação (top/bottom) e elevação×azimute (RTS), sem espelhar.

### 3.7 Passes por vista (refino fechado)

`--passes rts,left,back,front`: manda vista do concept + render do modelo + overlay da silhueta;
recebe patch de ≤6 partes. Aceito só se o IoU daquela vista sobe, nenhuma vista gated cai > 0.01 e
o preflight não quebra (regra de não-regressão).

### 3.8 Superfície

Textura procedural pintada por padrão (`surfaces.py`, 14 superfícies: metal, couro, pano, pedra,
quitina, vidro, glow...). Um atlas por unidade. Cores tiradas do próprio sheet (k-means). Brilho
pintado (engine só desenha albedo). Decais de olhos sem geometria. Projeção do concept foi
**rejeitada** (copiava fundo branco para a textura).

### 3.9 Saída

`runs/draft/<id>/<run>/`: `spec.json`, `model.glb`, `compare.png`, `turntable.gif`,
`silhouette.json`, `review.md` com veredito **PASS/CHECK**.
**Gate reprovado nunca aborta** — sempre sai algo para olhar; só GLB ausente é fatal.

## 4. Decisões de projeto (candidatas a contribuição)

| # | decisão | evidência |
|---|---|---|
| D1 | IA não escreve coordenada; posição é código (skeleton-first) | membros flutuando sumiram; preflight pega em 0.1 s o que 10 rodadas de review acharam |
| D2 | gates numéricos decidem, não a opinião sobre o render | gpt-5.4 "desenhou bem" e estourou orçamento 60%, perdeu o acento de cor |
| D3 | comparação em 5 vistas, nunca 3/4 | mesmo modelo: 5.5 em 3/4, 4.0 em 5 vistas (colapso do perfil invisível em 3/4) |
| D4 | sheet hard constrói, sheet aprovado julga | o refino não consegue passar o próprio erro de um redraw que derivou |
| D5 | detalhe pintado, partes separadas rigid-bound (WC3 real) | MDX medidos: 26–301 tris; chanfro e fuse pioraram |
| D6 | landmarks do sheet de cada unidade, não de uma unidade-modelo | com régua do n01X todo humanoide falhava; com a própria, hfoo vira 12/12 |
| D7 | hard-surface empilhado > pele contínua para máquinas | 7.0 empilhado, 5.5 skeleton, 1.5 skin, 3.5 skin+placas |
| D8 | never-abort | uma rodada sem artefato não ensina nada |

## 5. Histórico resumido (como se chegou aqui)

| fase | o que mudou | resultado (n01X, Iron Golem) |
|---|---|---|
| v1–v8 | partes à mão, depois loop "modelo → review do Claude → próximo" | geometria satura; nota Claude 4.8 → 5.5 |
| v9 | skeleton-first, rig por família | review 4.5/10; front IoU 0.551 |
| v10 | união booleana sem bevel | descartado (WC3 não solda) |
| v11 | DSL v2 + preflight 13 regras + gate de silhueta | front 0.771 / left 0.694; Claude 6.0 |
| v12 | passes por vista + câmeras calibradas | front 0.829 / left 0.829 / back 0.823 |
| v13 | v12 + passes rts,left,back | front 0.857 / left 0.832 / back 0.854 |
| hard-v1 | sheet hard como imagem 1, landmarks por unidade, repair padrão | front 0.871 / left 0.773 / back 0.869, **PASS** |

## 6. Métricas do baseline

### 6.1 Run `hard-v1`, 7 unidades, spec author `gemini-4-argon`, 1 run cada

| unidade | tris | mats | preflight | IoU front | IoU left | IoU back | silhueta | veredito |
|---|---|---|---|---|---|---|---|---|
| hfoo (Footman) | 528 | 6 | FAIL | 0.820 | 0.551 | 0.665 | FAIL | CHECK |
| n005 | 600 | 6 | FAIL | 0.770 | 0.781 | 0.829 | PASS | CHECK |
| n00U | 512 | 5 | PASS | 0.535 | 0.640 | 0.530 | FAIL | CHECK |
| n01I | 464 | 5 | FAIL | 0.803 | 0.708 | 0.800 | PASS | CHECK |
| n01N | 508 | 4 | PASS | 0.360 | 0.437 | 0.364 | FAIL | CHECK |
| n01X (Iron Golem) | 620 | 4 | PASS | 0.871 | 0.773 | 0.869 | PASS | **PASS** |
| n02X | 540 | 7 | FAIL | 0.705 | 0.638 | 0.749 | FAIL | CHECK |
| **agregado** | 7/7 no orçamento | 7/7 em 3–8 | 3/7 | **0.695** | **0.647** | **0.687** | 3/7 | **1/7 PASS** |

IoU vs sheet aprovado (o juiz). 1 skin e 4 clips em 7/7. Dados brutos: `baseline-metrics.csv`.

### 6.2 Efeito das referências hard (draft4 → draft16, mesmo modelo/brief)

Front sobe em hfoo (0.523→0.702), n00U (0.604→0.739), n01X (0.604→0.793); left sobe em
n005, n01I, n02X. Contagem de partes cai (hfoo 34→27). Defeitos do preflight não mudam:
referências afiam a leitura, não corrigem erro do spec author.

### 6.3 Ruído

A/B no hfoo sem repair: duas runs idênticas diferem até **0.12** de IoU front. Qualquer melhoria
abaixo disso com n=1 não é sinal. Imagem 1 hard vs aprovado ficou dentro do ruído.

### 6.4 Custo (preço de lista; gateway devolveu `cost: 0`, conciliar com extrato)

| item | modelo | US$ |
|---|---|---|
| sheet 2K | nano-banana-2-1 | 0.046 / imagem |
| spec | gemini-4-argon | ~0.011 / unidade (1.7k in / 1.9k out) |
| spec (referência) | claude-opus-5.5 | ~0.048 / unidade |

Por unidade entram ~4–6 imagens (sheet, hard, hard-clean, props, 1–2 RTS) + spec + repair/passes.
Custo total por unidade **não foi medido** — pendência.

## 7. Problemas abertos no baseline (= fila de melhorias)

1. **Largura de ombro nos humanoides.** hfoo: modelos 0.60–0.76 H vs sheet 0.46 H. Repair corrige
   (abR1 0.51 H) mas silhueta segue FAIL (front 0.63).
2. **Migração de massa entre partes.** IoU é envelope: torso 2× largo coexistiu com front 0.755.
   Proposta registrada: *part-box gate* (render com cor por parte, ±15% em centro e W/H/D).
3. **Pose de props.** Lança do hfoo vertical no perfil, diagonal no concept (left 0.56).
4. **Pass front rejeitado** pela não-regressão do left no hfoo.
5. **n01N**: spec author desenhou corpo muito menor que o sheet (0.36); drift left 0.76.
6. **n00U**: preflight PASS mas silhueta 0.53 — preflight e silhueta discordam.
7. **Top/bottom** sem gate (painel inclinado); gate 32×32 inconclusivo.
8. **Team colour**: slot `team` só discutido.
9. **Fiação no engine**: GLB → `assets/models/`, `.rig/.joints`, `data/models.tsv` — não feito.
10. **Escala**: 156 unidades sem prompt; só 7 sheets aprovados.
11. Avaliação: n=1 por unidade, sem repetição, sem baseline humano/alternativo.

## 8. Ameaças à validade (para o paper)

- Amostra pequena (7 unidades, 1 run cada) e dominada por bípedes.
- IoU de silhueta mede envelope, não proporção interna nem qualidade visual.
- Juiz é um sheet gerado por IA, não arte humana; e "aprovado" foi decisão do autor.
- Nota do Claude-revisor é LLM-as-judge, não calibrada contra humanos.
- Custos de lista, não faturados.
- Gateway único (ppq); disponibilidade de modelos muda.

## 9. Reproduzir o baseline

```bash
cd castle_fight && git checkout 0a70440
python3 -m unittest discover -s tests/tools/blender          # 77 testes
python3 tools/blender/spec_pipeline.py --id n01X --race Mech --name "Iron Golem" \
  --sheet artifacts/model-sheets/refs/n01X/sheet.jpg \
  --hard artifacts/model-sheets/refs/n01X/sheet-hard.jpg \
  --hard-clean artifacts/model-sheets/refs/n01X/sheet-hard-clean.jpg \
  --model google/gemini-4-argon --kind mass --run hard-v1 \
  --out artifacts/model-sheets/runs/draft/n01X/hard-v1
```

Requer Blender 5.2.2 headless e `PPQ_API_KEY`. Referência completa: `artifacts/model-sheets/PIPELINE.md`.
