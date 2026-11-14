# low-poly-pipeline

Ferramenta para fazer modelos 3D low-poly riggados e animados (GLB) a partir de uma folha de concept, com Blender +
Python, pensada para ser dirigida por agentes de IA (Claude Code, Codex...). Nasceu para o jogo Castle Fight, mas o
fluxo principal roda sozinho, sem o jogo. Em andamento: funciona, ainda em melhorias.

**Paper:** [`paper/paper.pdf`](paper/paper.pdf) (pt-BR, 55 p.): tese, baseline, as 24 etapas de evolução, 165 modelos
medidos, avaliação humano vs juiz LLM, uma ficha por melhoria. Fonte em `paper/*.md`; `make -C paper pdf` regera.

## Como funciona

```
folha de concept (5 vistas)  ->  script da unidade (peças)  ->  Blender: malha + rig + clipes  ->  model.glb
                                        ^                                                          |
                                        +---- ajusta as peças <---- revisão: silhueta x folha <----+
```

1. **Folha de concept**: uma imagem quadrada, fundo liso, layout 3+2: em cima frente / esquerda / costas, embaixo
   topo / base. Exemplo: [`examples/hfoo/sheet.jpg`](examples/hfoo/sheet.jpg). Pode vir de qualquer gerador de imagem
   ou de desenho à mão.
2. **Script da unidade** `tools/blender/units/<id>.py`: peças facetadas (cunhas, troncos de cone) presas a um osso de
   uma família de rig, mais uma paleta de cores. ~50 linhas. Um agente escreve olhando a folha; 200 exemplos na pasta.
3. **Família de rig** (`tools/blender/rig_families.py`): o esqueleto e os clipes prontos (idle, walk, attack, death,
   spell). 28 famílias: `biped`, `quadruped`, `drake`, `spider`, `vehicle`, `tracked`, `aircraft`, `naga`, `serpent`...
4. **Revisão** `tools/blender/hand_review.sh <id> <família>`: gera o GLB, renderiza as vistas e compara a silhueta
   com a folha (IoU por vista; overlay amarelo = bate, verde = modelo fora da folha, vermelho = folha descoberta).
   Repete o passo 2 até as vistas baterem.

## Requisitos

`blender` 4.x e `python3.14` (com numpy, scipy, Pillow) no PATH, ImageMagick (`magick`); `uvx` para o lint;
`pandoc` + `tectonic` só para o PDF. Testado em macOS.

## Primeiro modelo (5 min)

```bash
git clone https://github.com/afa7789/low-poly-pipeline && cd low-poly-pipeline
scripts/link_output.sh                         # cria ./output (tudo que a ferramenta gera fica fora do git)
make test                                      # testes

# exemplo: o soldado hfoo, a partir da folha de exemplo
mkdir -p artifacts/model-sheets/refs/hfoo
cp examples/hfoo/sheet.jpg artifacts/model-sheets/refs/hfoo/
tools/blender/hand_review.sh hfoo biped
open artifacts/model-sheets/hand/hfoo/         # model.glb, sheet.png, clips.png, overlay.png, silhouette.txt
```

## Seu próprio modelo

1. Ponha a folha em `artifacts/model-sheets/refs/<id>/sheet.jpg`.
2. Copie um script parecido de `tools/blender/units/` para `tools/blender/units/<id>.py`, troque o id no `H.build(...)`
   e a família (2º argumento), ajuste peças e paleta. Ou peça ao agente: "faça `<id>` a partir da folha, família
   `<família>`" (ele segue o [`AGENTS.md`](AGENTS.md) e a régua de arte em `.claude/rules/art-profile.md`).
3. `tools/blender/hand_review.sh <id> <família>` e olhe `overlay.png` / `silhouette.txt`. Itere.
4. Use o `model.glb` (glTF 2.0, com clipes) no seu motor: Godot, Unity, three.js, Blender.

## Pastas

| pasta | o quê |
|---|---|
| `tools/blender/` | o pipeline: `hand_unit.py` (peças), `rig_families.py`, `silhouette.py` (juiz), unidades e prédios de exemplo |
| `tools/` | auxiliares (clipes, instalar no jogo, lotes) |
| `tests/` | `make test`; `make lint` (ruff, complexidade <= 10) |
| `artifacts/model-sheets/PIPELINE.md` | documentação longa, decisões e histórico |
| `paper/` | o paper e as ferramentas de medida |
| `docs/references.md` | papers usados e onde cada um entrou |

## Ligado ao Castle Fight (opcional)

`make link CF_GAME=<checkout do castle_fight>` liga os dados do jogo (`data/*.tsv`, `assets/`, textos de design).
Com ele, `hand_review.sh` também instala o GLB no jogo e os scripts de lote/prédios/mapas funcionam. Sem ele, esses
scripts param pedindo `CF_GAME`.

Fora do git: `output/` (muda com `CF_PIPELINE_OUT`); PDFs dos papers e baseline TRELLIS (~30 GB) numa pasta à parte
(`CF_PAPER=<pasta>` com `papers/` e `baseline/`; lista em `paper/papers/README.md`).
